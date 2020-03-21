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

# ensure our 'make' found first
os.environ['PATH'] = os.pathsep.join([toolsdir, os.environ['PATH']])

zip7 = 'C:\\Program Files\\7-Zip\\7z'

def host_info():
    print(sys.version)
    print('PYTHONPATH')
    for dname in sys.path:
        print(' ', dname)
    print('platform = ', distutils.util.get_platform())

    print('Listing available VS versions')
    from fnmatch import fnmatch
    for base in (r'C:\Program Files (x86)', r'C:\Program Files'):
        for root, dirs, files in os.walk(base):
            for fname in files:
                if fnmatch(fname, 'vcvars*.bat'):
                    print('Found', os.path.join(root, fname))

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
    found = False

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
            found = True
            break

    if not found:
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
    for postf in ['_DIRNAME', '_REPONAME', '_REPOOWNER', '_REPOURL',
                  '_VARNAME', '_RECURSIVE', '_DEPTH', '_HOOK']:
        if dep+postf in os.environ:
            setup[dep+postf] = os.getenv(dep+postf)

def call_git(args, **kws):
    logger.debug("EXEC '%s' in %s", ' '.join(['git'] + args), os.getcwd())
    sys.stdout.flush()
    exitcode = sp.call(['git'] + args, **kws)
    logger.debug('EXEC DONE')
    return exitcode

def get_git_hash(place):
    logger.debug("EXEC 'git log -n1 --pretty=format:%%H' in %s", place)
    sys.stdout.flush()
    head = sp.check_output(['git', 'log', '-n1', '--pretty=format:%H'], cwd=place).decode()
    logger.debug('EXEC DONE')
    return head

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
        call_git(['clone', '--quiet'] + deptharg + [recursearg, '--branch', tag, setup[dep+'_REPOURL'], dirname], cwd=cachedir)

        sp.check_call(['git', 'log', '-n1'])
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

                sp.check_call(hook, shell=True, cwd=place)

        # write checked out commit hash to marker file
        head = get_git_hash(place)
        logger.debug('Writing hash of checked-out dependency (%s) to marker file', head)
        with open(checked_file, "w") as fout:
            print(head, file=fout)
        fout.close()

    update_release_local(setup[dep+"_VARNAME"], place)

def prepare(*args):
    host_info()

    print('{0}Loading setup files{1}'.format(ANSI_YELLOW, ANSI_RESET))
    source_set('defaults')
    if 'SET' in os.environ:
        source_set(os.environ['SET'])

    # we're working with tags (detached heads) a lot: suppress advice
    call_git(['config', '--global', 'advice.detachedHead', 'false'])

    print('{0}Checking/cloning dependencies{1}'.format(ANSI_YELLOW, ANSI_RESET))

    add_modules = ''
    if 'ADD_MODULES' in os.environ:
        add_modules = os.environ['ADD_MODULES']
    modules = ''
    if 'MODULES' in os.environ:
        modules = os.environ['MODULES']
    modlist = 'BASE {0} {1}'.format(add_modules, modules).upper().split()
    [add_dependency(mod) for mod in modlist]

    if os.path.isdir('configure'):
        release_local = os.path.join(cachedir, 'RELEASE.local')
        shutil.copy(release_local, 'configure')

    print('{0}Setting up EPICS build system{1}'.format(ANSI_YELLOW, ANSI_RESET))

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

    print('EPICS Base set up for {0} build with {1} linking'.format(optitype, linktype))

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

        sp.check_call('relocation.pl.bat', shell=True,
                      cwd=os.path.join(toolsdir, 'strawberry'))

    for mod in modlist:
        place = places[setup[mod+"_VARNAME"]]
        print('Building '+place)
        sp.check_call('make', shell=True, cwd=place)

def build(*args):
    print('{0}Building the module{1}'.format(ANSI_YELLOW, ANSI_RESET))


def test(*args):
    print('Running the tests')

def doExec(*args):
    'exec user command with vcvars'
    print('Execute command {}'.format(args))

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
    }[os.environ['PLATFORM']] # 'x86' or 'x64'

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

    print('vcvars-trampoline.bat')
    print(script)

    with open('vcvars-trampoline.bat', 'w') as F:
        F.write(script)

    sys.stdout.flush()
    sp.check_call('vcvars-trampoline.bat', shell=True)

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
        print('IN', name, 'with', args)
        actions[name](*args)