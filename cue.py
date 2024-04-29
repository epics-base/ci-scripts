#!/usr/bin/env python
"""EPICS CI build script for Linux/MacOS/Windows on Travis/GitLab/AppVeyor/GitHub-Actions
"""

from __future__ import print_function

import sys, os, stat, shlex, shutil
import fileinput
import logging
import re
import time
import threading
from glob import glob
import subprocess as sp
import sysconfig
import shutil

logger = logging.getLogger(__name__)

# Keep track of all files we write/append for later logging
_realopen = open
_modified_files = set()
def open(fname, mode='r'):
    F = _realopen(fname, mode)
    if 'w' in mode or 'a' in mode:
        _modified_files.add(os.path.normpath(os.path.abspath(fname)))
    return F

def log_modified():
    for fname in _modified_files:
        with Folded(os.path.basename(fname), 'Contents of '+fname):
            with open(fname, 'r') as F:
                sys.stdout.write(F.read())
            sys.stdout.write(os.linesep)

def whereis(cmd):
    if hasattr(shutil, 'which'): # >= py3.3
        loc = shutil.which(cmd)
        print('{0}Found exec {1} at {2!r} {3}'.format(ANSI_CYAN, cmd, loc, ANSI_RESET))

def prepare_env():
    '''HACK
    github actions yaml configuration doesn't allow
    conditional (un)setting of environments, only values.
    Currently this script treats unset and empty environment
    variables differently.
    While this is the case, we unset any empty environment variables.
    '''
    toclear = tuple(k for k,v in os.environ.items() if len(v.strip())==0)
    for var in toclear:
        print('{0}Clearing empty environment variable {1}{2}'.format(ANSI_CYAN, var, ANSI_RESET))
        del os.environ[var]

# Detect the service and set up context hash accordingly
def detect_context():
    global homedir

    buildconfig = 'default'
    ci['cachedir'] = os.path.join(homedir, '.cache')

    if 'TRAVIS' in os.environ:
        ci['service'] = 'travis'
        ci['os'] = os.environ['TRAVIS_OS_NAME']
        ci['platform'] = 'x64'
        ci['compiler'] = os.environ['TRAVIS_COMPILER']
        ci['choco'] += ['strawberryperl']
        if re.match(r'^vs', ci['compiler']):
            # Only Visual Studio 2017 available
            ci['compiler'] = 'vs2017'
        if 'BCFG' in os.environ:
            buildconfig = os.environ['BCFG'].lower()

    if 'GITLAB_CI' in os.environ:
        ci['service'] = 'gitlab'
        ci['os'] = 'linux'
        ci['platform'] = 'x64'
        ci['sudo'] = []                                      # No sudo in GitLab Docker containers
        ci['cachedir'] = os.path.join(curdir, '.cache')    # No caches outside project directory
        if 'CMP' in os.environ:
            ci['compiler'] = os.environ['CMP']
        if 'BCFG' in os.environ:
            buildconfig = os.environ['BCFG'].lower()

    if 'APPVEYOR' in os.environ:
        ci['service'] = 'appveyor'
        if re.match(r'^Visual', os.environ['APPVEYOR_BUILD_WORKER_IMAGE']):
            ci['os'] = 'windows'
        elif re.match(r'^Ubuntu', os.environ['APPVEYOR_BUILD_WORKER_IMAGE']):
            ci['os'] = 'linux'
        elif re.match(r'^macOS', os.environ['APPVEYOR_BUILD_WORKER_IMAGE']):
            ci['os'] = 'osx'
        ci['platform'] = os.environ['PLATFORM'].lower()
        if 'CMP' in os.environ:
            ci['compiler'] = os.environ['CMP']
        buildconfig = os.environ['CONFIGURATION'].lower()

    if 'GITHUB_ACTIONS' in os.environ:
        ci['service'] = 'github-actions'
        if os.environ['RUNNER_OS'] == 'macOS':
            ci['os'] = 'osx'
        else:
            ci['os'] = os.environ['RUNNER_OS'].lower()
        ci['platform'] = 'x64'
        if 'CMP' in os.environ:
            ci['compiler'] = os.environ['CMP']
        ci['choco'] += ['strawberryperl']
        if 'BCFG' in os.environ:
            buildconfig = os.environ['BCFG'].lower()

    if re.search('static', buildconfig):
        ci['static'] = True
    if re.search('debug', buildconfig):
        ci['debug'] = True

    if 'STATIC' in os.environ:
        print("{0}WARNING: Variable 'STATIC' not supported anymore; use 'BCFG' instead{1}"
              .format(ANSI_RED, ANSI_RESET))
        sys.stdout.flush()
    if not re.match(r'^((default|static|shared|dynamic|optimized|debug)-?)+$', buildconfig):
        print("{0}WARNING: Unrecognized build configuration setting '{1}'{2}"
              .format(ANSI_RED, buildconfig, ANSI_RESET))
        sys.stdout.flush()

    if ci['static']:
        ci['configuration'] = 'static'
    else:
        ci['configuration'] = 'shared'
    if ci['debug']:
        ci['configuration'] += '-debug'
    else:
        ci['configuration'] += '-optimized'

    ci['scriptsdir'] = os.path.abspath(os.path.dirname(sys.argv[0]))

    if 'CACHEDIR' in os.environ:
        ci['cachedir'] = os.environ['CACHEDIR']

    if 'CHOCO' in os.environ:
        ci['choco'].extend(os.environ['CHOCO'].split())

    if 'APT' in os.environ:
        ci['apt'].extend(os.environ['APT'].split())

    if 'BREW' in os.environ:
        ci['homebrew'].extend(os.environ['BREW'].split())

    ci['test'] = True
    if 'TEST' in os.environ and os.environ['TEST'].lower() == 'no':
        ci['test'] = False

    ci['parallel_make'] = 2
    if 'PARALLEL_MAKE' in os.environ:
        ci['parallel_make'] = int(os.environ['PARALLEL_MAKE'])

    ci['clean_deps'] = True
    if 'CLEAN_DEPS' in os.environ and os.environ['CLEAN_DEPS'].lower() == 'no':
        ci['clean_deps'] = False

    logger.debug('Detected a build hosted on %s, using %s on %s (%s) configured as %s '
                 + '(test: %s, clean_deps: %s)',
                 ci['service'], ci['compiler'], ci['os'], ci['platform'], ci['configuration'],
                 ci['test'], ci['clean_deps'])


curdir = os.getcwd()

ci = {}
seen_setups = []
modules_to_compile = []
setup = {}
places = {}
extra_makeargs = []
make_timeout = 0.

is_base314 = False
is_make3 = False
has_test_results = False
silent_dep_builds = True
skip_dep_builds = False
do_recompile = False
installed_7z = False


def clear_lists():
    global is_base314, has_test_results, silent_dep_builds, is_make3
    global _modified_files, do_recompile, building_base
    del seen_setups[:]
    del modules_to_compile[:]
    del extra_makeargs[:]
    setup.clear()
    places.clear()
    is_base314 = False
    is_make3 = False
    has_test_results = False
    silent_dep_builds = True
    do_recompile = False
    building_base = False
    _modified_files = set()
    ci['service'] = '<none>'
    ci['os'] = '<unknown>'
    ci['platform'] = '<unknown>'
    ci['compiler'] = '<unknown>'
    ci['static'] = False
    ci['debug'] = False
    ci['configuration'] = '<unknown>'
    ci['scriptsdir'] = ''
    ci['cachedir'] = ''
    ci['choco'] = ['make']
    ci['apt'] = []
    ci['homebrew'] = []
    ci['sudo'] = ['sudo']


clear_lists()

if 'BASE' in os.environ and os.environ['BASE'] == 'SELF':
    building_base = True
    skip_dep_builds = True
    places['EPICS_BASE'] = curdir

# Setup ANSI Colors
ANSI_RED = "\033[31;1m"
ANSI_GREEN = "\033[32;1m"
ANSI_YELLOW = "\033[33;1m"
ANSI_BLUE = "\033[34;1m"
ANSI_MAGENTA = "\033[35;1m"
ANSI_CYAN = "\033[36;1m"
ANSI_RESET = "\033[0m"
ANSI_CLEAR = "\033[0K"


# Travis log fold control
# from https://github.com/travis-ci/travis-rubies/blob/build/build.sh
# GitHub Actions fold control
# from https://github.com/actions/toolkit/blob/master/docs/commands.md#group-and-ungroup-log-lines

def fold_start(tag, title):
    if ci['service'] == 'travis':
        print('travis_fold:start:{0}{1}{2}{3}'
              .format(tag, ANSI_YELLOW, title, ANSI_RESET))
    elif ci['service'] == 'github-actions':
        print('::group::{0}{1}{2}'
              .format(ANSI_YELLOW, title, ANSI_RESET))
    elif ci['service'] == 'appveyor':
        print('{0}===== \\/ \\/ \\/ ===== START: {1} ====={2}'
              .format(ANSI_YELLOW, title, ANSI_RESET))
    sys.stdout.flush()


def fold_end(tag, title):
    if ci['service'] == 'travis':
        print('\ntravis_fold:end:{0}\r'
              .format(tag), end='')
    elif ci['service'] == 'github-actions':
        print('::endgroup::'
              .format(ANSI_YELLOW, title, ANSI_RESET))
    elif ci['service'] == 'appveyor':
        print('{0}----- /\\ /\\ /\\ -----   END: {1} -----{2}'
              .format(ANSI_YELLOW, title, ANSI_RESET))
    sys.stdout.flush()

class Folded(object):
    def __init__(self, tag, title):
        self.tag, self.title = tag, title
    def __enter__(self):
        fold_start(self.tag, self.title)
    def __exit__(self,A,B,C):
        fold_end(self.tag, self.title)

homedir = curdir
if 'HomeDrive' in os.environ:
    homedir = os.path.join(os.getenv('HomeDrive'), os.getenv('HomePath'))
elif 'HOME' in os.environ:
    homedir = os.getenv('HOME')
toolsdir = os.path.join(homedir, '.tools')


vcvars_table = {
    # https://en.wikipedia.org/wiki/Microsoft_Visual_Studio#History
    'vs2022': [r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvarsall.bat',
               r'C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvarsall.bat'],
    'vs2019': [r'C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvarsall.bat',
               r'C:\Program Files (x86)\Microsoft Visual Studio\2019\Enterprise\VC\Auxiliary\Build\vcvarsall.bat'],
    'vs2017': [r'C:\Program Files (x86)\Microsoft Visual Studio\2017\Community\VC\Auxiliary\Build\vcvarsall.bat',
               r'C:\Program Files (x86)\Microsoft Visual Studio\2017\Enterprise\VC\Auxiliary\Build\vcvarsall.bat',
               r'C:\Program Files (x86)\Microsoft Visual Studio\2017\BuildTools\VC\Auxiliary\Build\vcvarsall.bat'],
    'vs2015': [r'C:\Program Files (x86)\Microsoft Visual Studio 14.0\VC\vcvarsall.bat'],
    'vs2013': [r'C:\Program Files (x86)\Microsoft Visual Studio 12.0\VC\vcvarsall.bat'],
    'vs2012': [r'C:\Program Files (x86)\Microsoft Visual Studio 11.0\VC\vcvarsall.bat'],
    'vs2010': [r'C:\Program Files (x86)\Microsoft Visual Studio 10.0\VC\vcvarsall.bat'],
    'vs2008': [r'C:\Program Files (x86)\Microsoft Visual Studio 9.0\VC\vcvarsall.bat'],
}

vcvars_found = {}
for key in vcvars_table:
    for dir in vcvars_table[key]:
        if os.path.exists(dir):
            vcvars_found[key] = dir


def modlist():
    if building_base:
        ret = []
    else:
        for var in ['ADD_MODULES', 'MODULES']:
            setup.setdefault(var, '')
            if var in os.environ:
                setup[var] = os.environ[var]
                logger.debug('ENV assignment: %s = %s', var, setup[var])
        ret = ['BASE'] + setup['ADD_MODULES'].upper().split() + setup['MODULES'].upper().split()
    return ret


def host_info():
    print('{0}Build using {1} compiler on {2} ({3}) hosted by {4}{5}'
          .format(ANSI_CYAN, ci['compiler'], ci['os'], ci['platform'], ci['service'], ANSI_RESET))

    print('{0}Python setup{1}'.format(ANSI_CYAN, ANSI_RESET))
    print(sys.version)
    print('PYTHONPATH')
    for dname in sys.path:
        print(' ', dname)
    print('platform =', sysconfig.get_platform())

    if ci['os'] == 'windows':
        print('{0}Available Visual Studio versions{1}'.format(ANSI_CYAN, ANSI_RESET))
        for comp in vcvars_found:
            print(comp, 'in', vcvars_found[comp])

    sys.stdout.flush()


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
        raise NameError("{0}Search path for setup files (SETUP_PATH) is empty{1}".format(ANSI_RED, ANSI_RESET))

    for set_dir in setup_dirs:
        set_file = os.path.join(set_dir, name) + ".set"

        if set_file in seen_setups:
            print("Ignoring already included setup file {0}".format(set_file))
            return

        if os.path.isfile(set_file):
            seen_setups.append(set_file)
            print("Opening setup file {0}".format(set_file))
            sys.stdout.flush()
            with open(set_file) as fp:
                for line in fp:
                    if not line.strip() or line.strip()[0] == '#':
                        continue
                    if line.startswith("include"):
                        logger.debug('%s: Found include directive, reading %s next',
                                     set_file, line.split()[1])
                        source_set(line.split()[1])
                        continue
                    assign = line.replace('"', '').strip().split("=", 1)
                    setup.setdefault(assign[0], os.getenv(assign[0], ""))
                    if not setup[assign[0]].strip():
                        logger.debug('%s: setup[%s] = %s', set_file, assign[0], assign[1])
                        setup[assign[0]] = assign[1]
            logger.debug('Done with setup file %s', set_file)
            break
    else:
        raise NameError("{0}Setup file {1}.set does not exist in SETUP_PATH search path ({2}){3}"
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
    release_local = os.path.join(ci['cachedir'], 'RELEASE.local')
    updated_line = '{0}={1}'.format(var, location.replace('\\', '/'))
    places[var] = location

    if not os.path.exists(release_local):
        logger.debug('RELEASE.local does not exist, creating it')
        try:
            os.makedirs(ci['cachedir'])
        except:
            pass
        touch = open(release_local, 'w')
        touch.close()
    base_line = ''
    found = False
    logger.debug("Opening RELEASE.local for adding '%s'", updated_line)
    for line in fileinput.input(release_local, inplace=1):
        output_line = line.strip()
        if 'EPICS_BASE=' in line:
            base_line = line.strip()
            logger.debug("Found EPICS_BASE line '%s', not writing it", base_line)
            continue
        elif '{0}='.format(var) in line:
            logger.debug("Found '%s=' line, replacing", var)
            found = True
            output_line = updated_line
        logger.debug("Writing line to RELEASE.local: '%s'", output_line)
        print(output_line)
    fileinput.close()
    release_local = open(release_local, "a")
    if not found:
        logger.debug("Adding new definition: '%s'", updated_line)
        print(updated_line, file=release_local)
    if base_line:
        logger.debug("Writing EPICS_BASE line: '%s'", base_line)
        print(base_line, file=release_local)
    release_local.close()


def set_setup_from_env(dep):
    for postf in ['', '_DIRNAME', '_REPONAME', '_REPOOWNER', '_REPOURL',
                  '_VARNAME', '_RECURSIVE', '_DEPTH', '_HOOK']:
        if dep + postf in os.environ:
            setup[dep + postf] = os.environ[dep + postf]
            logger.debug('ENV assignment: %s = %s', dep + postf, setup[dep + postf])


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


def call_make(args=None, **kws):
    global make_timeout
    if args is None:
        args = []
    place = kws.get('cwd', os.getcwd())
    parallel = kws.pop('parallel', ci['parallel_make'])
    silent = kws.pop('silent', False)
    use_extra = kws.pop('use_extra', False)
    # no parallel make for Base 3.14
    if parallel <= 0 or is_base314:
        makeargs = []
    else:
        makeargs = ['-j{0}'.format(parallel)]
        if not is_make3:
            makeargs += ['-Otarget']
    if silent:
        makeargs += ['-s']
    if use_extra:
        makeargs += extra_makeargs
    logger.debug("EXEC '%s' in %s", ' '.join(['make'] + makeargs + args), place)
    sys.stdout.flush()
    sys.stderr.flush()

    child = sp.Popen(['make'] + makeargs + args, **kws)
    if make_timeout:
        def expire(child):
            logger.error('Timeout')
            child.terminate()
        timer = threading.Timer(make_timeout, expire, args=(child,))
        timer.start()

    exitcode = child.wait()
    if make_timeout:
        timer.cancel()
    logger.debug('EXEC DONE')
    if exitcode != 0:
        sys.exit(exitcode)


def apply_patch(file, **kws):
    place = kws.get('cwd', os.getcwd())
    print('Applying patch {0} in {1}'.format(file, place))
    logger.debug("EXEC '%s' in %s", ' '.join(['patch', '-p1', '-i', file]), place)
    sys.stdout.flush()
    sp.check_call(['patch', '-p1', '-i', file], cwd=place)
    logger.debug('EXEC DONE')


def extract_archive(file, **kws):
    place = kws.get('cwd', os.getcwd())
    print('Extracting archive {0} in {1}'.format(file, place))
    logger.debug("EXEC '%s' in %s", ' '.join(['7z', 'x', '-aoa', '-bd', file]), place)
    sys.stdout.flush()
    sp.check_call(['7z', 'x', '-aoa', '-bd', file], cwd=place)
    logger.debug('EXEC DONE')


def get_git_hash(place):
    logger.debug("EXEC 'git log -n1 --pretty=format:%%H' in %s", place)
    sys.stdout.flush()
    head = sp.check_output(['git', 'log', '-n1', '--pretty=format:%H'], cwd=place).decode()
    logger.debug('EXEC DONE')
    return head


def complete_setup(dep):
    set_setup_from_env(dep)
    setup.setdefault(dep, 'master')
    setup.setdefault(dep + "_DIRNAME", dep.lower())
    setup.setdefault(dep + "_REPONAME", dep.lower())
    setup.setdefault('REPOOWNER', 'epics-modules')
    setup.setdefault(dep + "_REPOOWNER", setup['REPOOWNER'])
    setup.setdefault(dep + "_REPOURL", 'https://github.com/{0}/{1}.git'
                     .format(setup[dep + '_REPOOWNER'], setup[dep + '_REPONAME']))
    setup.setdefault(dep + "_VARNAME", dep)
    setup.setdefault(dep + "_RECURSIVE", 'YES')
    setup.setdefault(dep + "_DEPTH", -1)


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
    global do_recompile
    recurse = setup[dep + '_RECURSIVE'].lower()
    if recurse not in ['0', 'no']:
        recursearg = ["--recursive"]
    elif recurse not in ['1', 'yes']:
        recursearg = []
    else:
        raise RuntimeError("Invalid value for {}_RECURSIVE='{}' not 0/NO/1/YES".format(dep, recurse))
    deptharg = {
        '-1': ['--depth', '5'],
        '0': [],
    }.get(str(setup[dep + '_DEPTH']), ['--depth', str(setup[dep + '_DEPTH'])])

    tag = setup[dep]

    logger.debug('Adding dependency %s with tag %s', dep, setup[dep])

    # determine if dep points to a valid release or branch
    if call_git(['ls-remote', '--quiet', '--exit-code', '--refs', setup[dep + '_REPOURL'], tag]):
        raise RuntimeError("{0}{1} is neither a tag nor a branch name for {2} ({3}){4}"
                           .format(ANSI_RED, tag, dep, setup[dep + '_REPOURL'], ANSI_RESET))

    dirname = setup[dep + '_DIRNAME'] + '-{0}'.format(tag)
    place = os.path.join(ci['cachedir'], dirname)
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
        if not os.path.isdir(ci['cachedir']):
            os.makedirs(ci['cachedir'])
        # clone dependency
        print('Cloning {0} of dependency {1} into {2}'
              .format(tag, dep, place))
        sys.stdout.flush()
        call_git(['clone', '--quiet'] + deptharg + recursearg + ['--branch', tag, setup[dep + '_REPOURL'], dirname],
                 cwd=ci['cachedir'])

        sp.check_call(['git', 'log', '-n1'], cwd=place)
        logger.debug('Setting do_recompile = True (all following modules will be recompiled')
        do_recompile = True

        if dep == 'BASE':
            # add MSI 1.7 to Base 3.14
            versionfile = os.path.join(place, 'configure', 'CONFIG_BASE_VERSION')
            if os.path.exists(versionfile):
                with open(versionfile) as f:
                    if 'BASE_3_14=YES' in f.read():
                        print('Adding MSI 1.7 to {0}'.format(place))
                        sys.stdout.flush()
                        sp.check_call(['patch', '-p1', '-i', os.path.join(ci['scriptsdir'], 'add-msi-to-314.patch')],
                                      cwd=place)
        else:
            # force including RELEASE.local for non-base modules by overwriting their configure/RELEASE
            release = os.path.join(place, "configure", "RELEASE")
            if os.path.exists(release):
                with open(release, 'w') as fout:
                    print('-include $(TOP)/../RELEASE.local', file=fout)

        # Apply HOOK
        if dep + '_HOOK' in setup:
            hook = setup[dep + '_HOOK']
            hook_file = os.path.join(curdir, hook)
            hook_ext = os.path.splitext(hook_file)[1]
            if os.path.exists(hook_file):
                if hook_ext == '.patch':
                    apply_patch(hook_file, cwd=place)
                elif hook_ext in ('.zip', '.7z'):
                    extract_archive(hook_file, cwd=place)
                elif hook_ext == '.py':
                    print('Running py hook {0} in {1}'.format(hook, place))
                    sp.check_call([sys.executable, hook_file], cwd=place)
                else:
                    print('Running hook {0} in {1}'.format(hook, place))
                    sys.stdout.flush()
                    sp.check_call(hook_file, shell=True, cwd=place)
            else:
                print('Skipping invalid hook {0} in {1}'.format(hook, place))

        # write checked out commit hash to marker file
        head = get_git_hash(place)
        logger.debug('Writing hash of checked-out dependency (%s) to marker file', head)
        with open(checked_file, "w") as fout:
            print(head, file=fout)
        fout.close()

    if do_recompile:
        modules_to_compile.append(dep)
    update_release_local(setup[dep + "_VARNAME"], place)


def detect_epics_host_arch():
    if ci['os'] == 'windows':
        if re.match(r'^vs', ci['compiler']):
            # there is no combined static and debug EPICS_HOST_ARCH target,
            # so a combined debug and static target will appear to be just static
            # but debug will have been specified in CONFIG_SITE by prepare()
            hostarchsuffix = ''
            if ci['debug']:
                hostarchsuffix = '-debug'
            if ci['static']:
                hostarchsuffix = '-static'

            if ci['platform'] == 'x86':
                os.environ['EPICS_HOST_ARCH'] = 'win32-x86' + hostarchsuffix
            elif ci['platform'] == 'x64':
                os.environ['EPICS_HOST_ARCH'] = 'windows-x64' + hostarchsuffix

        elif ci['compiler'] == 'gcc':
            if ci['platform'] == 'x86':
                os.environ['EPICS_HOST_ARCH'] = 'win32-x86-mingw'
            elif ci['platform'] == 'x64':
                os.environ['EPICS_HOST_ARCH'] = 'windows-x64-mingw'

    if 'EPICS_HOST_ARCH' not in os.environ:
        logger.debug('Running script to detect EPICS host architecture in %s', places['EPICS_BASE'])
        os.environ['EPICS_HOST_ARCH'] = 'unknown'
        eha_scripts = [
            os.path.join(places['EPICS_BASE'], 'src', 'tools', 'EpicsHostArch.pl'),
            os.path.join(places['EPICS_BASE'], 'startup', 'EpicsHostArch.pl'),
        ]
        for eha in eha_scripts:
            if os.path.exists(eha):
                os.environ['EPICS_HOST_ARCH'] = sp.check_output(['perl', eha]).decode('ascii').strip()
                logger.debug('%s returned: %s',
                             eha, os.environ['EPICS_HOST_ARCH'])
                break


def setup_for_build(args):
    global is_base314, has_test_results, is_make3
    dllpaths = []

    logger.debug('Setting up the build environment')

    if ci['os'] == 'windows':
        if os.path.exists(r'C:\Strawberry\perl\bin'):
            # Put strawberry perl in front of the PATH (so that Git Perl is further behind)
            # Put Chocolatey\bin ahead to select correct make.exe
            logger.debug('Adding Strawberry Perl in front of the PATH')
            os.environ['PATH'] = os.pathsep.join([r'C:\ProgramData\Chocolatey\bin',
                                                  r'C:\Strawberry\c\bin',
                                                  r'C:\Strawberry\perl\site\bin',
                                                  r'C:\Strawberry\perl\bin',
                                                  os.environ['PATH']])

        if ci['service'] == 'appveyor' and ci['compiler'] == 'gcc':
            logger.debug('Adding AppVeyor MSYS2/MinGW installation to PATH and INCLUDE')
            if 'INCLUDE' not in os.environ:
                os.environ['INCLUDE'] = ''
            if ci['platform'] == 'x86':
                os.environ['INCLUDE'] = os.pathsep.join(
                    [r'C:\msys64\mingw32\include',
                     os.environ['INCLUDE']])
                os.environ['PATH'] = os.pathsep.join([r'C:\msys64\mingw32\bin',
                                                      os.environ['PATH']])
            elif ci['platform'] == 'x64':
                os.environ['INCLUDE'] = os.pathsep.join(
                    [r'C:\msys64\mingw64\include',
                     os.environ['INCLUDE']])
                os.environ['PATH'] = os.pathsep.join([r'C:\msys64\mingw64\bin',
                                                      os.environ['PATH']])

    # Find BASE location
    if not building_base:
        with open(os.path.join(ci['cachedir'], 'RELEASE.local'), 'r') as f:
            lines = f.readlines()
            for line in lines:
                (mod, place) = line.strip().split('=')
                if mod == 'EPICS_BASE':
                    places['EPICS_BASE'] = place
    else:
        places['EPICS_BASE'] = '.'

    logger.debug('Using EPICS Base at %s', places['EPICS_BASE'])

    detect_epics_host_arch()

    if ci['os'] == 'windows':
        if not building_base:
            with open(os.path.join(ci['cachedir'], 'RELEASE.local'), 'r') as f:
                lines = f.readlines()
                for line in lines:
                    (mod, place) = line.strip().split('=')
                    bin_dir = os.path.join(place, 'bin', os.environ['EPICS_HOST_ARCH'])
                    if os.path.isdir(bin_dir):
                        dllpaths.append(bin_dir)
        # Add DLL location to PATH
        bin_dir = os.path.join(os.getcwd(), 'bin', os.environ['EPICS_HOST_ARCH'])
        if os.path.isdir(bin_dir):
            dllpaths.append(bin_dir)
        os.environ['PATH'] = os.pathsep.join(dllpaths + [os.environ['PATH']])
        logger.debug('DLL paths added to PATH: %s', os.pathsep.join(dllpaths))

    cfg_base_version = os.path.join(places['EPICS_BASE'], 'configure', 'CONFIG_BASE_VERSION')
    if os.path.exists(cfg_base_version):
        with open(cfg_base_version) as myfile:
            if 'BASE_3_14=YES' in myfile.read():
                is_base314 = True
    logger.debug('Check if EPICS Base is a 3.14 series: %s', is_base314)

    if not is_base314:
        rules_build = os.path.join(places['EPICS_BASE'], 'configure', 'RULES_BUILD')
        if os.path.exists(rules_build):
            with open(rules_build) as myfile:
                for line in myfile:
                    if re.match('^test-results:', line):
                        has_test_results = True

    # apparently %CD% is handled automagically, so use getcwd() instead
    os.environ['TOP'] = os.getcwd()
    os.environ['MAKE'] = 'make'
    os.environ['EPICS_BASE'] = places['EPICS_BASE']

    changed_vars = set()

    for extra_env_var in args.extra_env_vars:
        try:
            key_value = extra_env_var.split('=')
            key = key_value[0]
            value = key_value[1]
            expanded_value = value.format(**os.environ)

            # Update the environment right now so later variables have access
            if key in os.environ:
                old_value = [os.environ[key]]
            else:
                old_value = []

            os.environ[key] = os.pathsep.join(old_value + [expanded_value])
            changed_vars.add(key)
        except KeyError:
            print('Environment')
            [print('  ', K, '=', repr(V)) for K, V in os.environ.items()]
            raise

    for key in changed_vars:
        print("{0}{2} = {3}{1}".format(ANSI_CYAN, ANSI_RESET, key, os.environ[key]))

    # os.environ completely updated at this point

    logger.debug('Final PATH')
    for loc in os.environ['PATH'].split(os.pathsep):
        logger.debug('  %r', loc)

    # Check make version
    if re.match(r'^GNU Make 3', sp.check_output(['make', '-v']).decode('ascii')):
        is_make3 = True
    logger.debug('Check if make is a 3.x series: %s', is_make3)

    # Add EXTRA make arguments
    for tag in ['EXTRA', 'EXTRA1', 'EXTRA2', 'EXTRA3', 'EXTRA4', 'EXTRA5']:
        val = os.environ.get(tag, "")
        if len(val)>0:
            extra_makeargs.extend(shlex.split(val))


def fix_etc_hosts():
    # Several travis-ci images throw us a curveball in /etc/hosts
    # by including two entries for localhost.  The first for 127.0.1.1
    # causes epicsSockResolveTest to fail.
    #  cat /etc/hosts
    #  ...
    #  127.0.1.1 localhost localhost ip4-loopback
    #  127.0.0.1 localhost nettuno travis vagrant travis-job-....

    logger.debug("EXEC sudo sed -ie '/^127\\.0\\.1\\.1/ s|localhost\\s*||g' /etc/hosts")
    sys.stdout.flush()
    sp.call(['sudo', 'sed', '-ie', '/^127\\.0\\.1\\.1/ s|localhost\\s*||g', '/etc/hosts'])
    logger.debug('EXEC DONE')


def edit_make_file(mode, path, values):
    """Edit an EPICS Make file.

    mode should be either "a" or "w", as for the open function.

    path should be a list, e.g. ["configure", "CONFIG_SITE"]

    values should be a dictionary of values to edit. If the value starts with
    a "+" the value will be appended.

    Example usage:

        edit_make_file("a", ["configure", "CONFIG_SITE"], {
            "VARIABLE": "value",
            "APPENDED_VARIABLE": "+value",
        })
    """
    with open(os.path.join(places["EPICS_BASE"], *path), mode) as f:
        for variable, value in values.items():
            if value.startswith("+"):
                op = "+="
                value = value[1:]
            else:
                op = "="

            f.write(variable + op + value + "\n")


def handle_old_cross_variables():
    if "CI_CROSS_TARGETS" not in os.environ:
        os.environ["CI_CROSS_TARGETS"] = ""

    if "RTEMS" in os.environ:
        if 'RTEMS_TARGET' in os.environ:
            rtems_target = os.environ['RTEMS_TARGET']
        else:
            if os.environ['RTEMS'] == '5':
                rtems_target = 'RTEMS-pc686-qemu'
            else:
                rtems_target = 'RTEMS-pc386'
                if os.path.exists(os.path.join(places['EPICS_BASE'], 'configure', 'os',
                                         'CONFIG.Common.RTEMS-pc386-qemu')):
                    # Base 3.15 doesn't have -qemu target architecture
                    rtems_target = 'RTEMS-pc386-qemu'

        new_cross_target = ":" + rtems_target + "@" + os.environ["RTEMS"]
        os.environ["CI_CROSS_TARGETS"] += new_cross_target

        print(
            "{0}WARNING: deprecated RTEMS environment variable was specified." \
            " Please add '{1}' to CI_CROSS_TARGETS instead.{2}".format(
                ANSI_RED, new_cross_target, ANSI_RESET
            )
        )
        logger.debug('Replaced deprecated RTEMS target with new entry in CI_CROSS_TARGETS: %s', new_cross_target)

    if "WINE" in os.environ:
        if os.environ['WINE'] == '32':
            new_cross_target = ":win32-x86-mingw"
        else:
            new_cross_target = ":windows-x64-mingw"
        os.environ["CI_CROSS_TARGETS"] += new_cross_target

        print(
            "{0}WARNING: deprecated WINE environment variable was specified." \
            " Please add '{1}' to CI_CROSS_TARGETS instead.{2}".format(
                ANSI_RED, new_cross_target, ANSI_RESET
            )
        )
        logger.debug('Replaced deprecated WINE target with new entry in CI_CROSS_TARGETS: %s', new_cross_target)


def prepare_cross_compilation(cross_target_info):
    """Prepare the configuration for a single value of the CI_CROSS_TARGETS
    variable.

    See the README.md file for more information on this variable."""
    cross_target_info = cross_target_info.split("@")
    if len(cross_target_info) == 2:
        target_param = cross_target_info[1]
    else:
        target_param = None

    target = cross_target_info[0]

    if target.startswith("RTEMS-"):
        prepare_rtems_cross(target, target_param)
    elif target.endswith("-mingw"):
        prepare_wine_cross(target)
    elif target.startswith("linux-"):
        prepare_linux_cross(target, target_param)
    else:
        raise ValueError(
            "Unknown CI_CROSS_TARGETS {0}. "
            "Please see the ci-scripts README for available values.".format(target)
        )


def prepare_rtems_cross(epics_arch, version):
    """Prepare the configuration for RTEMS cross-compilation for the given
    RTEMS version.

    If version is None, it defaults to version 5 for RTEMS-pc686-*, 4.10
    otherwise."""
    if version is None:
        if epics_arch.startswith("RTEMS-pc686"):
            version = "5"
        else:
            version = "4.10"

    # eg. "RTEMS-pc386" or "RTEMS-pc386-qemu" -> "pc386"
    rtems_bsp = re.match("^RTEMS-([^-]*)(?:-qemu)?$", epics_arch).group(1)

    print("Cross compiler RTEMS{0} @ {1}".format(version, epics_arch))

    if ci["os"] == "linux":
        download_rtems(version, rtems_bsp)

    edit_make_file(
        "a",
        ["configure", "os", "CONFIG_SITE.Common.RTEMS"],
        {
            "RTEMS_VERSION": version,
            "RTEMS_BASE": "/opt/rtems/" + version,
        },
    )

    edit_make_file(
        "a",
        ["configure", "CONFIG_SITE"],
        {"CROSS_COMPILER_TARGET_ARCHS": epics_arch},
    )

    ci["apt"].extend(
        ["re2c", "g++-mingw-w64-i686", "g++-mingw-w64-x86-64", "qemu-system-x86"]
    )

def download_rtems(version, rtems_bsp):
    rsb_release = os.environ.get("RSB_BUILD", "20210306")
    tar_name = "{0}-rtems{1}.tar.xz".format(rtems_bsp, version)
    print("Downloading RTEMS {0} cross compiler: {1}".format(version, tar_name))
    sys.stdout.flush()
    sp.check_call(
        [
            "curl",
            "-fsSL",
            "--retry",
            "3",
            "-o",
            tar_name,
            "https://github.com/mdavidsaver/rsb/releases/download/{0}%2F{1}/{2}".format(
                version, rsb_release, tar_name
            ),
        ],
        cwd=toolsdir,
    )
    sudo_prefix = []
    if ci["service"] == "github-actions":
        sudo_prefix = ["sudo"]
    sp.check_call(
        sudo_prefix + ["tar", "-C", "/", "-xmJ", "-f", os.path.join(toolsdir, tar_name)]
    )
    os.remove(os.path.join(toolsdir, tar_name))
    for rtems_cc in glob("/opt/rtems/*/bin/*-gcc"):
        print("{0}{1} --version{2}".format(ANSI_CYAN, rtems_cc, ANSI_RESET))
        sys.stdout.flush()
        sp.check_call([rtems_cc, "--version"])


def prepare_wine_cross(epics_arch):
    """Prepare the configuration for Wine cross-compilation for the given mingw
    architecture."""

    if epics_arch == "win32-x86-mingw":
        gnu_arch = "i686-w64-mingw32"
        deb_arch = "mingw-w64-i686"
        bits = "32"
    elif epics_arch == "windows-x64-mingw":
        gnu_arch = "x86_64-w64-mingw32"
        deb_arch = "mingw-w64-x86-64"
        bits = "64"
    else:
        raise ValueError(
            "Unknown architecture '{0}' for WINE target. "
            "Please see the ci-scripts README for available values.".format(epics_arch)
        )

    print("Cross compiler mingw{} / Wine".format(bits))

    edit_make_file(
        "a",
        ["configure", "os", "CONFIG.linux-x86." + epics_arch],
        {"CMPLR_PREFIX": gnu_arch + "-"},
    )

    edit_make_file(
        "a",
        ["configure", "CONFIG_SITE"],
        {"CROSS_COMPILER_TARGET_ARCHS": "+" + epics_arch},
    )

    ci['apt'].extend(["re2c", "g++-" + deb_arch])


def prepare_linux_cross(epics_arch, gnu_arch):
    """Prepare the configuration for Linux cross-compilation for the given
    architecture.

    If gnu_arch is None, this function will try to guess it using the
    epics_arch value.

    linux-arm architecture defaults to arm-linux-gnueabi (soft floats)."""
    # This list is kind of an intersection between the set of cross-compilers
    # provided by Ubuntu[1] and the list of architectures found in
    # `epics-base/configure/os`
    #
    # [1]: https://packages.ubuntu.com/source/focal/gcc-10-cross
    if gnu_arch is None:
        if epics_arch == "linux-x86":
            gnu_arch = "i686-linux-gnu"
        elif epics_arch == "linux-arm":
            gnu_arch = "arm-linux-gnueabi"
        elif epics_arch == "linux-aarch64":
            gnu_arch = "aarch64-linux-gnu"
        elif epics_arch == "linux-ppc":
            gnu_arch = "powerpc-linux-gnu"
        elif epics_arch == "linux-ppc64":
            gnu_arch = "powerpc64le-linux-gnu"
        else:
            raise ValueError(
                "Could not guess the GNU architecture for EPICS arch: {}. "
                "Please use the '@' syntax of the 'CI_CROSS_TARGETS' variable".format(
                    epics_arch
                )
            )

    print(
        "Setting up Linux cross-compiling arch {0} with GNU arch {1}".format(
            epics_arch, gnu_arch
        )
    )

    edit_make_file(
        "w",
        ["configure", "os", "CONFIG_SITE.linux-x86_64." + epics_arch],
        {
            "GNU_TARGET": gnu_arch,
            "COMMANDLINE_LIBRARY": "EPICS",
        },
    )

    edit_make_file(
        "a",
        ["configure", "CONFIG_SITE"],
        {"CROSS_COMPILER_TARGET_ARCHS": "+" + epics_arch},
    )

    ci["apt"].extend(["re2c", "g++-" + gnu_arch])


def prepare(args):
    host_info()

    fold_start('load.setup', 'Loading setup files')

    if 'SET' in os.environ:
        source_set(os.environ['SET'])
    source_set('defaults')

    [complete_setup(mod) for mod in modlist()]

    fold_end('load.setup', 'Loading setup files')

    logger.debug('Loaded setup')
    kvs = list(setup.items())
    kvs.sort()
    [logger.debug(' %s = "%s"', *kv) for kv in kvs]

    logger.debug('Effective module list: %s', modlist())

    if ci['service'] == 'travis' and ci['os'] == 'linux':
        fix_etc_hosts()

    # we're working with tags (detached heads) a lot: suppress advice
    call_git(['config', '--global', 'advice.detachedHead', 'false'])

    fold_start('check.out.dependencies', 'Checking/cloning dependencies')

    [add_dependency(mod) for mod in modlist()]

    if not building_base:
        if os.path.isdir('configure'):
            targetdir = 'configure'
        else:
            targetdir = '.'
        shutil.copy(os.path.join(ci['cachedir'], 'RELEASE.local'), targetdir)

    fold_end('check.out.dependencies', 'Checking/cloning dependencies')

    cxx = None
    if ci['compiler'].startswith('clang'):
        cxx = re.sub(r'clang', r'clang++', ci['compiler'])
    elif ci['compiler'].startswith('gcc'):
        cxx = re.sub(r'gcc', r'g++', ci['compiler'])

    if not os.path.isdir(toolsdir):
        os.makedirs(toolsdir)

    if 'BASE' in modules_to_compile or building_base:
        fold_start('set.up.epics_build', 'Configuring EPICS build system')

        detect_epics_host_arch()

        # Set static/debug in CONFIG_SITE
        with open(os.path.join(places['EPICS_BASE'], 'configure', 'CONFIG_SITE'), 'a') as f:
            if ci['static']:
                f.write('SHARED_LIBRARIES=NO\n')
                f.write('STATIC_BUILD=YES\n')
                linktype = 'static'
            else:
                linktype = 'shared (DLL)'
            if ci['debug']:
                f.write('HOST_OPT=NO\n')
                optitype = 'debug'
            else:
                optitype = 'optimized'

        print('EPICS Base build system set up for {0} build with {1} linking'
                  .format(optitype, linktype))

        # Enable/fix parallel build for VisualStudio compiler on older Base versions
        if ci['os'] == 'windows' and re.match(r'^vs', ci['compiler']):
            add_vs_fix = True
            config_win = os.path.join(places['EPICS_BASE'], 'configure', 'os', 'CONFIG.win32-x86.win32-x86')
            with open(config_win) as f:
                for line in f:
                    if re.match(r'^ifneq \(\$\(VisualStudioVersion\),11\.0\)', line):
                        add_vs_fix = False
            if add_vs_fix:
                logger.debug('Adding parallel build fix for VisualStudio to %s', config_win)
                with open(config_win, 'a') as f:
                    f.write('''
# Fix parallel build for some VisualStudio versions
ifneq ($(VisualStudioVersion),)
ifneq ($(VisualStudioVersion),11.0)
ifeq ($(findstring -FS,$(OPT_CXXFLAGS_NO)),)
  OPT_CXXFLAGS_NO += -FS
  OPT_CFLAGS_NO += -FS
endif
else
  OPT_CXXFLAGS_NO := $(filter-out -FS,$(OPT_CXXFLAGS_NO))
  OPT_CFLAGS_NO := $(filter-out -FS,$(OPT_CFLAGS_NO))
endif
endif''')

        # Cross-compilations from Linux platform
        if ci['os'] == 'linux':
            handle_old_cross_variables()

            for cross_target_info in os.environ.get("CI_CROSS_TARGETS", "").split(":"):
                if cross_target_info == "":
                    continue
                prepare_cross_compilation(cross_target_info)

        print('Host compiler', ci['compiler'])

        if ci['compiler'].startswith('clang'):
            with open(os.path.join(places['EPICS_BASE'], 'configure', 'os',
                                   'CONFIG_SITE.Common.'+os.environ['EPICS_HOST_ARCH']), 'a') as f:
                f.write('''
GNU         = NO
CMPLR_CLASS = clang
CC          = {0}
CCC         = {1}'''.format(ci['compiler'], cxx))

            # hack
            with open(os.path.join(places['EPICS_BASE'], 'configure', 'CONFIG.gnuCommon'), 'a') as f:
                f.write('''
CMPLR_CLASS = clang''')

        elif ci['compiler'].startswith('gcc'):
            with open(os.path.join(places['EPICS_BASE'], 'configure', 'os',
                                   'CONFIG_SITE.Common.' + os.environ['EPICS_HOST_ARCH']), 'a') as f:
                f.write('''
CC          = {0}
CCC         = {1}'''.format(ci['compiler'], cxx))

        elif ci['compiler'].startswith('vs'):
            pass # nothing special

        else:
            raise ValueError('Unknown compiler name {0}.  valid forms include: gcc, gcc-4.8, clang, vs2019'.format(ci['compiler']))

        # Add additional settings to CONFIG_SITE
        extra_config = ''
        if 'USR_CPPFLAGS' in os.environ:
            extra_config += '''
USR_CPPFLAGS += {0}'''.format(os.environ['USR_CPPFLAGS'])
        if 'USR_CFLAGS' in os.environ:
            extra_config += '''
USR_CFLAGS += {0}'''.format(os.environ['USR_CFLAGS'])
        if 'USR_CXXFLAGS' in os.environ:
            extra_config += '''
USR_CXXFLAGS += {0}'''.format(os.environ['USR_CXXFLAGS'])
        if ci['service'] == 'github-actions' and ci['os'] == 'windows':
            extra_config += '''
PERL = C:/Strawberry/perl/bin/perl -CSD'''

        if extra_config:
            with open(os.path.join(places['EPICS_BASE'], 'configure', 'CONFIG_SITE'), 'a') as f:
                f.write(extra_config)

        # enable color in error and warning messages if the (cross) compiler supports it
        with open(os.path.join(places['EPICS_BASE'], 'configure', 'CONFIG'), 'a') as f:
            f.write('''
ifdef T_A
  COLOR_FLAG_$(T_A) := $(shell $(CPP) -fdiagnostics-color -E - </dev/null >/dev/null 2>/dev/null && echo -fdiagnostics-color)
  USR_CPPFLAGS += $(COLOR_FLAG_$(T_A))
endif''')

        fold_end('set.up.epics_build', 'Configuring EPICS build system')

    if ci['os'] == 'windows' and ci['choco']:
        fold_start('install.choco', 'Installing CHOCO packages')
        for i in range(0,3):
            try:
                sp.check_call(['choco', 'install'] + ci['choco'] + ['-y', '--limitoutput', '--no-progress'])
            except Exception as e:
                print(e)
                print("Retrying choco install attempt {} after 30 seconds".format(i+1))
                time.sleep(30)
            else:
                break
        fold_end('install.choco', 'Installing CHOCO packages')

    if ci['os'] == 'linux' and ci['apt']:
        fold_start('install.apt', 'Installing APT packages')
        sp.check_call(ci['sudo'] + ['apt-get', '-y', 'update'])
        sp.check_call(ci['sudo'] + ['apt-get', 'install', '-y', '-qq'] + ci['apt'])
        fold_end('install.apt', 'Installing APT packages')

    if ci['os'] == 'osx' and ci['homebrew']:
        fold_start('install.homebrew', 'Installing Homebrew packages')
        sp.check_call(['brew', 'install'] + ci['homebrew'])
        fold_end('install.homebrew', 'Installing Homebrew packages')

    setup_for_build(args)

    print('{0}EPICS_HOST_ARCH = {1}{2}'.format(ANSI_CYAN, os.environ['EPICS_HOST_ARCH'], ANSI_RESET))
    whereis('make')
    print('{0}$ make --version{1}'.format(ANSI_CYAN, ANSI_RESET))
    sys.stdout.flush()
    call_make(['--version'], parallel=0)
    whereis('perl')
    print('{0}$ perl --version{1}'.format(ANSI_CYAN, ANSI_RESET))
    sys.stdout.flush()
    sp.check_call(['perl', '--version'])

    if re.match(r'^vs', ci['compiler']):
        whereis('cl')
        print('{0}$ cl{1}'.format(ANSI_CYAN, ANSI_RESET))
        sys.stdout.flush()
        sp.check_call(['cl'])
    else:
        cc = ci['compiler']
        whereis(cc)
        print('{0}$ {1} --version{2}'.format(ANSI_CYAN, cc, ANSI_RESET))
        sys.stdout.flush()
        sp.check_call([cc, '--version'])
        if cxx:
            whereis(cxx)
            print('{0}$ {1} --version{2}'.format(ANSI_CYAN, cxx, ANSI_RESET))
            sys.stdout.flush()
            sp.check_call([cxx, '--version'])

    if logging.getLogger().isEnabledFor(logging.DEBUG):
        log_modified()

    if not skip_dep_builds:
        fold_start('build.dependencies', 'Build missing/outdated dependencies')
        for mod in modules_to_compile:
            place = places[setup[mod + "_VARNAME"]]
            print('{0}Building dependency {1} in {2}{3}'.format(ANSI_YELLOW, mod, place, ANSI_RESET))
            call_make(cwd=place, silent=silent_dep_builds)
            if ci['clean_deps']:
                call_make(args=['clean'], cwd=place, silent=silent_dep_builds)
        fold_end('build.dependencies', 'Build missing/outdated dependencies')

        print('{0}Dependency module information{1}'.format(ANSI_CYAN, ANSI_RESET))
        print('Module     Tag          Binaries    Commit')
        print(100 * '-')
        for mod in modlist():
            if mod in modules_to_compile:
                stat = 'rebuilt'
            else:
                stat = 'from cache'
            commit = sp.check_output(['git', 'log', '-n1', '--oneline'], cwd=places[setup[mod + "_VARNAME"]])\
                .decode('ascii').strip()
            print("%-10s %-12s %-11s %s" % (mod, setup[mod], stat, commit))

        print('{0}Contents of RELEASE.local{1}'.format(ANSI_CYAN, ANSI_RESET))
        with open(os.path.join(ci['cachedir'], 'RELEASE.local'), 'r') as f:
            print(f.read().strip())

def build(args):
    setup_for_build(args)
    fold_start('build.module', 'Build the main module')
    call_make(args.makeargs, use_extra=True)
    fold_end('build.module', 'Build the main module')


def test(args):
    if ci['test']:
        setup_for_build(args)
        fold_start('test.module', 'Run the main module tests')
        if has_test_results:
            call_make(['tapfiles'])
        else:
            call_make(['runtests'])
        fold_end('test.module', 'Run the main module tests')
    else:
        print("{0}Action 'test' skipped as per configuration{1}"
              .format(ANSI_YELLOW, ANSI_RESET))


def test_results(args):
    if ci['test']:
        setup_for_build(args)
        fold_start('test.results', 'Sum up main module test results')
        if has_test_results:
            call_make(['test-results'], parallel=0, silent=True)
        else:
            print("{0}Base in {1} does not implement 'test-results' target{2}"
                  .format(ANSI_YELLOW, places['EPICS_BASE'], ANSI_RESET))
        fold_end('test.results', 'Sum up main module test results')
    else:
        print("{0}Action 'test-results' skipped as per configuration{1}"
              .format(ANSI_YELLOW, ANSI_RESET))


def doExec(args):
    'exec user command with vcvars'
    setup_for_build(args)
    fold_start('exec.command', 'Execute command {}'.format(args.cmd))
    sp.check_call(' '.join(args.cmd), shell=True)
    fold_end('exec.command', 'Execute command {}'.format(args.cmd))


def with_vcvars(cmd):
    '''re-exec main script with a (hopefully different) command
    '''
    CC = ci['compiler']

    # cf. https://docs.microsoft.com/en-us/cpp/build/building-on-the-command-line

    info = {
        'python': sys.executable,
        'self': sys.argv[0],
        'cmd': cmd,
    }

    info['arch'] = {
        'x86': 'x86',  # 'amd64_x86' ??
        'x64': 'amd64',
    }[ci['platform']]  # 'x86' or 'x64'

    info['vcvars'] = vcvars_found[CC]

    script = '''
call "{vcvars}" {arch}

"{python}" "{self}" {cmd}
'''.format(**info)

    print('{0}Calling vcvars-trampoline.bat to set environment for {1} on {2}{3}'
          .format(ANSI_YELLOW, CC, ci['platform'], ANSI_RESET))
    sys.stdout.flush()

    logger.debug('----- Creating vcvars-trampoline.bat -----')
    for line in script.split('\n'):
        logger.debug(line)
    logger.debug('----- snip -----')

    with open('vcvars-trampoline.bat', 'w') as F:
        F.write(script)

    returncode = sp.call('vcvars-trampoline.bat', shell=True)
    if returncode != 0:
        sys.exit(returncode)


def getargs():
    from argparse import ArgumentParser, ArgumentError, REMAINDER
    def timespec(s):
        M = re.match(r'^\s*(\d+)\s*([A-Za-z]*)', s)
        if not M:
            raise ArgumentError('Expected timespec not {!r}'.format(s))
        val = float(M.group(1))
        try:
            mult = {
                '':1.0,
                'S':1.0,
                'M':60.0,
                'H':60.0*60.0,
            }[M.group(2).upper()]
        except KeyError:
            raise ArgumentError('Expect suffix S, M, or H.  not {!r}'.format(s))
        return val*mult

    p = ArgumentParser()
    p.add_argument('--no-vcvars', dest='vcvars', default=True, action='store_false',
                   help='Assume vcvarsall.bat has already been run')
    p.add_argument('--add-path', dest='extra_env_vars', type=lambda x: "PATH={}".format(x), default=[], action='append',
                   help='Append directory to $PATH or %%PATH%%. Expands {ENVVAR}. Equivalent to: "--add-env PATH=<PATHS>"')
    p.add_argument('--add-env', dest='extra_env_vars', default=[], action='append',
                   help='Append directory to the specified $ENVVAR or %%ENVVAR%%. Expands {OTHER_ENVVAR}. Example: "--add-env \'LD_LIBRARY_PATH={EPICS_BASE}/lib/{EPICS_HOST_ARCH}\'"')
    p.add_argument('-T', '--timeout', type=timespec, metavar='DLY',
                   help='Terminate make after delay.  DLY interpreted as second, or may be qualified with "S", "M", or "H".  (default no timeout)')
    subp = p.add_subparsers()

    cmd = subp.add_parser('prepare')
    cmd.set_defaults(func=prepare)

    cmd = subp.add_parser('build')
    cmd.add_argument('makeargs', nargs=REMAINDER)
    cmd.set_defaults(func=build)

    cmd = subp.add_parser('test')
    cmd.set_defaults(func=test)

    cmd = subp.add_parser('test-results')
    cmd.set_defaults(func=test_results)

    cmd = subp.add_parser('exec')
    cmd.add_argument('cmd', nargs=REMAINDER)
    cmd.set_defaults(func=doExec)

    return p


def main(raw):
    global silent_dep_builds
    global make_timeout
    args = getargs().parse_args(raw)
    if 'VV' in os.environ and os.environ['VV'] == '1':
        logging.basicConfig(level=logging.DEBUG)
        silent_dep_builds = False
    else:
        logging.basicConfig(level=logging.CRITICAL)

    make_timeout = args.timeout
    if make_timeout:
        logger.info('Will timeout after %.1f seconds', make_timeout)

    prepare_env()
    detect_context()

    if args.vcvars and ci['compiler'].startswith('vs'):
        # re-exec with MSVC in PATH
        with_vcvars(' '.join(['--no-vcvars'] + raw))
    else:
        args.func(args)


if __name__ == '__main__':
    main(sys.argv[1:])
