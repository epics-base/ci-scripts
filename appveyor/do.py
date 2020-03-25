#!/usr/bin/env python
"""Windows (AppVeyor) ci build script
"""

from __future__ import print_function

import sys, os, stat, shutil
import fileinput
import logging
import re
import subprocess as sp
import distutils.util

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

# Setup ANSI Colors
ANSI_RED = "\033[31;1m"
ANSI_GREEN = "\033[32;1m"
ANSI_YELLOW = "\033[33;1m"
ANSI_BLUE = "\033[34;1m"
ANSI_MAGENTA = "\033[35;1m"
ANSI_CYAN = "\033[36;1m"
ANSI_RESET = "\033[0m"
ANSI_CLEAR = "\033[0K"

seen_setups = []
modules_to_compile = []
setup = {}
places = {}

if 'HomeDrive' in os.environ:
    cachedir = os.path.join(os.getenv('HomeDrive'), os.getenv('HomePath'), '.cache')
    toolsdir = os.path.join(os.getenv('HomeDrive'), os.getenv('HomePath'), '.tools')
elif 'HOME' in os.environ:
    cachedir = os.path.join(os.getenv('HOME'), '.cache')
    toolsdir = os.path.join(os.getenv('HOME'), '.tools')
else:
    cachedir = os.path.join('.', '.cache')
    toolsdir = os.path.join('.', '.tools')


def modlist():
    add_modules = os.environ.get('ADD_MODULES', '').upper().split()
    modules = os.environ.get('MODULES', '').upper().split()
    ret = ['BASE'] + add_modules + modules
    logger.debug('Effective module list: %s', ret)
    return ret

zip7 = r'C:\Program Files\7-Zip\7z'
make = ''
makeargs = []

def host_info():
    print('{0}Python setup{1}'.format(ANSI_CYAN, ANSI_RESET))
    print(sys.version)
    print('PYTHONPATH')
    for dname in sys.path:
        print(' ', dname)
    print('platform =', distutils.util.get_platform())

    print('{0}Available Visual Studio versions{1}'.format(ANSI_CYAN, ANSI_RESET))
    from fnmatch import fnmatch
    for base in (r'C:\Program Files (x86)', r'C:\Program Files'):
        for root, dirs, files in os.walk(base):
            for fname in files:
                if fnmatch(fname, 'vcvarsall.bat'):
                    print('Found', os.path.join(root, fname))
    sys.stdout.flush()

# Used from unittests
def clear_lists():
    del seen_setups[:]
    del modules_to_compile[:]
    setup.clear()
    places.clear()

# Error-handler to make shutil.rmtree delete read-only files on Windows
def remove_readonly(func, path, excinfo):
    os.chmod(path, stat.S_IWRITE)
    func(path)

# source_set(setup)
#
# Source a settings file (extension .set) found in the setup_dirs path
# May be called recursively (from within a setup file)
def source_set(name):
    # allowed separators: colon or whitespace
    setup_dirs = os.getenv('SETUP_PATH', "").replace(':', ' ').split()
    if len(setup_dirs) == 0:
        raise NameError("{0}Search path for setup files (SETUP_PATH) is empty{1}".format(ANSI_RED,ANSI_RESET))

    for set_dir in setup_dirs:
        set_file = os.path.join(set_dir, name) + ".set"

        if set_file in seen_setups:
            print("Ignoring already included setup file {0}".format(set_file))
            return

        if os.path.isfile(set_file):
            seen_setups.append(set_file)
            print("Loading setup file {0}".format(set_file))
            sys.stdout.flush()
            with open(set_file) as fp:
                for line in fp:
                    logger.debug('Next line: %s', line.strip())
                    if not line.strip() or line.strip()[0] == '#':
                        continue
                    if line.startswith("include"):
                        logger.debug('Found an include, reading %s', line.split()[1])
                        source_set(line.split()[1])
                        continue
                    assign = line.replace('"', '').strip().split("=", 1)
                    logger.debug('Interpreting as assignment')
                    setup.setdefault(assign[0], os.getenv(assign[0], ""))
                    if not setup[assign[0]].strip():
                        logger.debug('Doing assignment: %s = %s', assign[0], assign[1])
                        setup[assign[0]] = assign[1]
            break
    else:
        raise NameError("{0}Setup file {1} does not exist in SETUP_PATH search path ({2}){3}"
                        .format(ANSI_RED, name, setup_dirs, ANSI_RESET))

# update_release_local(var, location)
#   var       name of the variable to set in RELEASE.local
#   location  location (absolute path) of where variable should point to
#
# Manipulate RELEASE.local in the cache location:
# - replace "$var=$location" line if it exists and has changed
# - otherwise add "$var=$location" line and possibly move EPICS_BASE=... line to the end
# Set places[var] = location
def update_release_local(var, location):
    release_local = os.path.join(cachedir, 'RELEASE.local')
    updated_line = '{0}={1}'.format(var, location)
    places[var] = location

    if not os.path.exists(release_local):
        logger.debug('RELEASE.local does not exist, creating it')
        try:
            os.makedirs(cachedir)
        except:
            pass
        fout = open(release_local, 'w')
        fout.close()
    base_line = ''
    found = False
    logger.debug("Opening RELEASE.local for adding '%s'", updated_line)
    for line in fileinput.input(release_local, inplace=1):
        outputline = line.strip()
        if 'EPICS_BASE=' in line:
            base_line = line.strip()
            logger.debug("Found EPICS_BASE line '%s', not writing it", base_line)
            continue
        elif '{0}='.format(var) in line:
            logger.debug("Found '%s=' line, replacing", var)
            found = True
            outputline = updated_line
        logger.debug("Writing line to RELEASE.local: '%s'", outputline)
        print(outputline)
    fileinput.close()
    fout = open(release_local,"a")
    if not found:
        logger.debug("Adding new definition: '%s'", updated_line)
        print(updated_line, file=fout)
    if base_line:
        logger.debug("Writing EPICS_BASE line: '%s'", base_line)
        print(base_line, file=fout)
    fout.close()

def set_setup_from_env(dep):
    for postf in ['', '_DIRNAME', '_REPONAME', '_REPOOWNER', '_REPOURL',
                  '_VARNAME', '_RECURSIVE', '_DEPTH', '_HOOK']:
        if dep+postf in os.environ:
            setup[dep+postf] = os.environ[dep+postf]
            logger.debug('ENV assignment: %s = %s', dep+postf, setup[dep+postf])

def call_git(args, **kws):
    if 'cwd' in kws:
        place = kws['cwd']
    else:
        place = os.getcwd()
    logger.debug("EXEC '%s' in %s", ' '.join(['git'] + args), place)
    sys.stdout.flush()
    exitcode = sp.call(['git'] + args, **kws)
    logger.debug('EXEC DONE')
    return exitcode

def call_make(args=[], **kws):
    if 'cwd' in kws:
        place = kws['cwd']
    else:
        place = os.getcwd()
    logger.debug("EXEC '%s' in %s", ' '.join([make] + makeargs + args), place)
    sys.stdout.flush()
    exitcode = sp.call([make] + makeargs + args, **kws)
    logger.debug('EXEC DONE')
    if exitcode != 0:
        sys.exit(exitcode)

def get_git_hash(place):
    logger.debug("EXEC 'git log -n1 --pretty=format:%%H' in %s", place)
    sys.stdout.flush()
    head = sp.check_output(['git', 'log', '-n1', '--pretty=format:%H'], cwd=place).decode()
    logger.debug('EXEC DONE')
    return head

def complete_setup(dep):
    set_setup_from_env(dep)
    setup.setdefault(dep, 'master')
    setup.setdefault(dep+"_DIRNAME", dep.lower())
    setup.setdefault(dep+"_REPONAME", dep.lower())
    setup.setdefault('REPOOWNER', 'epics-modules')
    setup.setdefault(dep+"_REPOOWNER", setup['REPOOWNER'])
    setup.setdefault(dep+"_REPOURL", 'https://github.com/{0}/{1}.git'
                     .format(setup[dep+'_REPOOWNER'], setup[dep+'_REPONAME']))
    setup.setdefault(dep+"_VARNAME", dep)
    setup.setdefault(dep+"_RECURSIVE", 1)
    setup.setdefault(dep+"_DEPTH", -1)

# add_dependency(dep, tag)
#
# Add a dependency to the cache area:
# - check out (recursive if configured) in the CACHE area unless it already exists and the
#   required commit has been built
# - Defaults:
#   $dep_DIRNAME = lower case ($dep)
#   $dep_REPONAME = lower case ($dep)
#   $dep_REPOURL = GitHub / $dep_REPOOWNER (or $REPOOWNER or epics-modules) / $dep_REPONAME .git
#   $dep_VARNAME = $dep
#   $dep_DEPTH = 5
#   $dep_RECURSIVE = 1/YES (0/NO to for a flat clone)
# - Add $dep_VARNAME line to the RELEASE.local file in the cache area (unless already there)
# - Add full path to $modules_to_compile
def add_dependency(dep):
    if setup[dep+'_RECURSIVE'] not in [0, 'no']:
        recursearg = "--recursive"
    else:
        recursearg = ''

    tag = setup[dep]

    logger.debug('Adding dependency %s with tag %s', dep, setup[dep])

    # determine if dep points to a valid release or branch
    if call_git(['ls-remote', '--quiet', '--exit-code', '--refs', setup[dep+'_REPOURL'], tag]):
        raise RuntimeError("{0}{1} is neither a tag nor a branch name for {2} ({3}){4}"
                           .format(ANSI_RED, tag, dep, setup[dep+'_REPOURL'], ANSI_RESET))

    dirname = setup[dep+'_DIRNAME']+'-{0}'.format(tag)
    place = os.path.join(cachedir, dirname)
    checked_file = os.path.join(place, "checked_out")

    if os.path.isdir(place):
        logger.debug('Dependency %s: directory %s exists, comparing checked-out commit', dep, place)
        # check HEAD commit against the hash in marker file
        if os.path.exists(checked_file):
            with open(checked_file, 'r') as bfile:
                checked_out = bfile.read().strip()
            bfile.close()
        else:
            checked_out = 'never'
        head = get_git_hash(place)
        logger.debug('Found checked_out commit %s, git head is %s', checked_out, head)
        if head != checked_out:
            logger.debug('Dependency %s out of date - removing', dep)
            shutil.rmtree(place, onerror=remove_readonly)
        else:
            print('Found {0} of dependency {1} up-to-date in {2}'.format(tag, dep, place))
            sys.stdout.flush()

    if not os.path.isdir(place):
        if not os.path.isdir(cachedir):
            os.makedirs(cachedir)
        # clone dependency
        deptharg = {
            -1:['--depth', '5'],
            0:[],
        }.get(setup[dep+'_DEPTH'], ['--depth', setup[dep+'_DEPTH']])
        print('Cloning {0} of dependency {1} into {2}'
              .format(tag, dep, place))
        sys.stdout.flush()
        call_git(['clone', '--quiet'] + deptharg + [recursearg, '--branch', tag, setup[dep+'_REPOURL'], dirname], cwd=cachedir)

        sp.check_call(['git', 'log', '-n1'], cwd=place)
        modules_to_compile.append(place)

        # force including RELEASE.local for non-base modules by overwriting their configure/RELEASE
        if dep != 'BASE':
            release = os.path.join(place, "configure", "RELEASE")
            if os.path.exists(release):
                with open(release, 'w') as fout:
                    print('-include $(TOP)/../RELEASE.local', file=fout)

        # run hook if defined
        if dep+'_HOOK' in setup:
            hook = os.path.join(place, setup[dep+'_HOOK'])
            if os.path.exists(hook):
                print('Running hook {0} in {1}'.format(setup[dep+'_HOOK'], place))
                sys.stdout.flush()
                sp.check_call(hook, shell=True, cwd=place)

        # write checked out commit hash to marker file
        head = get_git_hash(place)
        logger.debug('Writing hash of checked-out dependency (%s) to marker file', head)
        with open(checked_file, "w") as fout:
            print(head, file=fout)
        fout.close()

    update_release_local(setup[dep+"_VARNAME"], place)

def setup_for_build():
    global make, makeargs

    make = os.path.join(toolsdir, 'make')
    makeargs = ['-j2', '-Otarget']
    # no parallel make for Base 3.14
    with open(os.path.join(cachedir, 'RELEASE.local'), 'r') as f:
        lines = f.readlines()
        for line in lines:
            if re.search(r'^EPICS_BASE=', line):
                base_place = line.split('=')[1].strip()
                break
    with open(os.path.join(base_place, 'configure', 'CONFIG_BASE_VERSION')) as myfile:
        if 'BASE_3_14=YES' in myfile.read():
            makeargs = []

    if os.environ['PLATFORM'].lower() == 'x86':
        os.environ['EPICS_HOST_ARCH'] = 'win32-x86'
    elif os.environ['PLATFORM'].lower() == 'x64':
        os.environ['EPICS_HOST_ARCH'] = 'windows-x64'

    if os.environ['CC'] == 'vs2019':
        # put our strawberry 'perl' in the PATH
        os.environ['PATH'] = os.pathsep.join([os.path.join(toolsdir, 'strawberry', 'perl', 'site', 'bin'),
                                              os.path.join(toolsdir, 'strawberry', 'perl', 'bin'),
                                              os.environ['PATH']])
    if os.environ['CC'] == 'mingw':
        if 'INCLUDE' not in os.environ:
            os.environ['INCLUDE'] = ''
        if os.environ['PLATFORM'].lower() == 'x86':
            os.environ['EPICS_HOST_ARCH'] = 'win32-x86-mingw'
            os.environ['INCLUDE'] = os.pathsep.join([r'C:\mingw-w64\i686-6.3.0-posix-dwarf-rt_v5-rev1\mingw32\include',
                                                     os.environ['INCLUDE']])
            os.environ['PATH'] = os.pathsep.join([r'C:\mingw-w64\i686-6.3.0-posix-dwarf-rt_v5-rev1\mingw32\bin',
                                                  os.environ['PATH']])
        elif os.environ['PLATFORM'].lower() == 'x64':
            os.environ['EPICS_HOST_ARCH'] = 'windows-x64-mingw'
            os.environ['INCLUDE'] = os.pathsep.join([r'C:\mingw-w64\x86_64-8.1.0-posix-seh-rt_v6-rev0\mingw64\include',
                                                     os.environ['INCLUDE']])
            os.environ['PATH'] = os.pathsep.join([r'C:\mingw-w64\x86_64-8.1.0-posix-seh-rt_v6-rev0\mingw64\bin',
                                                  os.environ['PATH']])

def prepare(*args):
    host_info()

    print('{0}Loading setup files{1}'.format(ANSI_YELLOW, ANSI_RESET))
    source_set('defaults')
    if 'SET' in os.environ:
        source_set(os.environ['SET'])

    [complete_setup(mod) for mod in modlist()]

    logger.debug('Loaded setup')
    kvs = list(setup.items())
    kvs.sort()
    [logger.debug(' %s = "%s"', *kv) for kv in kvs]

    # we're working with tags (detached heads) a lot: suppress advice
    call_git(['config', '--global', 'advice.detachedHead', 'false'])

    print('{0}Checking/cloning dependencies{1}'.format(ANSI_YELLOW, ANSI_RESET))
    sys.stdout.flush()

    [add_dependency(mod) for mod in modlist()]

    if os.path.isdir('configure'):
        release_local = os.path.join(cachedir, 'RELEASE.local')
        shutil.copy(release_local, 'configure')

    print('{0}Configuring EPICS build system{1}'.format(ANSI_YELLOW, ANSI_RESET))

    with open(os.path.join(places['EPICS_BASE'], 'configure', 'CONFIG_SITE'), 'a') as config_site:
        if re.search('static', os.environ['CONFIGURATION']):
            config_site.write('SHARED_LIBRARIES=NO')
            config_site.write('STATIC_BUILD=YES')
            linktype = 'static'
        else:
            linktype = 'dynamic (DLL)'
        if re.search('debug', os.environ['CONFIGURATION']):
            config_site.write('HOST_OPT=NO')
            optitype = 'debug'
        else:
            optitype = 'optimized'

    print('EPICS Base build system set up for {0} build with {1} linking'
          .format(optitype, linktype))

    if not os.path.isdir(toolsdir):
        os.makedirs(toolsdir)

    print('Installing Make 4.2.1 from ANL web site')
    sys.stdout.flush()
    sp.check_call(['curl', '-fsS', '--retry', '3', '-o', 'make-4.2.1.zip',
                   'https://epics.anl.gov/download/tools/make-4.2.1-win64.zip'],
                  cwd=toolsdir)
    sp.check_call([zip7, 'e', 'make-4.2.1.zip'], cwd=toolsdir)

    perlver = '5.30.0.1'
    if os.environ['CC'] == 'vs2019':
        print('Installing Strawberry Perl {0}'.format(perlver))
        sys.stdout.flush()
        sp.check_call(['curl', '-fsS', '--retry', '3', '-o', 'perl-{0}.zip'.format(perlver),
                       'http://strawberryperl.com/download/{0}/strawberry-perl-{0}-64bit.zip'.format(perlver)],
                      cwd=toolsdir)
        sp.check_call([zip7, 'x', 'perl-{0}.zip'.format(perlver), '-ostrawberry'], cwd=toolsdir)

        with open(os.devnull, 'w') as devnull:
            sp.check_call('relocation.pl.bat', shell=True, stdout=devnull,
                          cwd=os.path.join(toolsdir, 'strawberry'))

    setup_for_build()

    print('{0}EPICS_HOST_ARCH = {1}{2}'.format(ANSI_CYAN, os.environ['EPICS_HOST_ARCH'], ANSI_RESET))
    print('{0}make arguments = {1}{2}'.format(ANSI_CYAN, ' '.join(makeargs), ANSI_RESET))
    print('{0}$ {1} --version{2}'.format(ANSI_CYAN, make, ANSI_RESET))
    sys.stdout.flush()
    sp.check_call([make, '--version'])
    print('{0}$ perl --version{1}'.format(ANSI_CYAN, ANSI_RESET))
    sys.stdout.flush()
    sp.check_call(['perl', '--version'])

    if os.environ['CC'] == 'mingw':
        print('{0}$ gcc --version{1}'.format(ANSI_CYAN, ANSI_RESET))
        sys.stdout.flush()
        sp.check_call(['gcc', '--version'])
    else:
        print('{0}$ cl{1}'.format(ANSI_CYAN, ANSI_RESET))
        sys.stdout.flush()
        sp.check_call(['cl'])

    for mod in modlist():
        place = places[setup[mod+"_VARNAME"]]
        print('{0}Building dependency {1} in {2}{3}'.format(ANSI_YELLOW, mod, place, ANSI_RESET))
        call_make(cwd=place)

def build(*args):
    setup_for_build()
    print('{0}Building the main module{1}'.format(ANSI_YELLOW, ANSI_RESET))
    call_make()

def test(*args):
    setup_for_build()
    print('{0}Running the main module tests{1}'.format(ANSI_YELLOW, ANSI_RESET))
    call_make(['tapfiles'])

def doExec(*args):
    'exec user command with vcvars'
    setup_for_build()
    print('Execute command {}'.format(args))
    sys.stdout.flush()
    sp.check_call(' '.join(args), shell=True)

def with_vcvars(cmd):
    '''re-exec main script with a (hopefully different) command
    '''
    CC = os.environ['CC']

    # cf. https://docs.microsoft.com/en-us/cpp/build/building-on-the-command-line

    info = {
        'python':sys.executable,
        'self':sys.argv[0],
        'cmd':cmd,
    }

    info['arch'] = {
        'x86':'x86',   # 'amd64_x86' ??
        'x64':'amd64',
    }[os.environ['PLATFORM'].lower()] # 'x86' or 'x64'

    info['vcvars'] = {
        # https://en.wikipedia.org/wiki/Microsoft_Visual_Studio#History
        'vs2019':r'C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvarsall.bat',
        'vs2017':r'C:\Program Files (x86)\Microsoft Visual Studio\2017\Community\VC\Auxiliary\Build\vcvarsall.bat',
        'vs2015':r'C:\Program Files (x86)\Microsoft Visual Studio 14.0\VC\vcvarsall.bat',
        'vs2013':r'C:\Program Files (x86)\Microsoft Visual Studio 12.0\VC\vcvarsall.bat',
        'vs2012':r'C:\Program Files (x86)\Microsoft Visual Studio 11.0\VC\vcvarsall.bat',
        'vs2010':r'C:\Program Files (x86)\Microsoft Visual Studio 10.0\VC\vcvarsall.bat',
        'vs2008':r'C:\Program Files (x86)\Microsoft Visual Studio 9.0\VC\vcvarsall.bat',
    }[CC]

    script='''
call "{vcvars}" {arch}

"{python}" "{self}" {cmd}
'''.format(**info)

    logger.debug('----- Creating vcvars-trampoline.bat -----')
    for line in script.split('\n'):
        logger.debug(line)
    logger.debug('----- snip -----')

    with open('vcvars-trampoline.bat', 'w') as F:
        F.write(script)

    print('{0}Calling vcvars-trampoline.bat to set environment for {1} on {2}{3}'
          .format(ANSI_YELLOW, CC, os.environ['PLATFORM'], ANSI_RESET))
    sys.stdout.flush()
    returncode = sp.call('vcvars-trampoline.bat', shell=True)
    if returncode != 0:
        sys.exit(returncode)

actions = {
    'prepare': prepare,
    'build': build,
    'test': test,
    'exec': doExec,
    '_vcvars':lambda:None,
}

if __name__=='__main__':
    args = sys.argv[1:]
    if args[0]!='_vcvars' and os.environ['CC']!='mingw':
        # re-exec with MSVC in PATH
        with_vcvars(' '.join(['_vcvars']+args))

    else:
        name = args.pop(0)
        logger.debug('DO running action %s with %s', name, args)
        actions[name](*args)
