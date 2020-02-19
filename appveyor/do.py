#!/usr/bin/env python
"""Windows (AppVeyor) ci build script
"""

from __future__ import print_function

import sys, os, fileinput
import logging
import subprocess as SP
import distutils.util

logger = logging.getLogger(__name__)
#logging.basicConfig(level=logging.DEBUG)

# Setup ANSI Colors
ANSI_RED = "\033[31;1m"
ANSI_GREEN = "\033[32;1m"
ANSI_YELLOW = "\033[33;1m"
ANSI_BLUE = "\033[34;1m"
ANSI_RESET = "\033[0m"
ANSI_CLEAR = "\033[0K"

seen_setups = []
setup = {}
if 'HomeDrive' in os.environ:
    cachedir = os.path.join(os.getenv('HomeDrive'), os.getenv('HomePath'), '.cache')
elif 'HOME' in os.environ:
    cachedir = os.path.join(os.getenv('HOME'), '.cache')
else:
    cachedir = os.path.join('.', '.cache')

# Used from unittests
def clear_lists():
    del seen_setups[:]
    setup.clear()

# source_set(setup)
#
# Source a settings file (extension .set) found in the setup_dirs path
# May be called recursively (from within a setup file)
def source_set(set):
    found = False

    setup_dirs = os.getenv('SETUP_PATH', "").replace(':', ' ').split()
    if len(setup_dirs) == 0:
        raise NameError("{0}Search path for setup files (SETUP_PATH) is empty{1}".format(ANSI_RED,ANSI_RESET))

    for set_dir in setup_dirs:
        set_file = os.path.join(set_dir, set) + ".set"

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
                        .format(ANSI_RED,set_file,setup_dirs,ANSI_RESET))

# update_release_local(var, place)
#   var    name of the variable to set in RELEASE.local
#   place  place (absolute path) of where variable should point to
#
# Manipulate RELEASE.local in the cache location:
# - replace "$var=$place" line if it exists and has changed
# - otherwise add "$var=$place" line and possibly move EPICS_BASE=... line to the end
def update_release_local(var, place):
    release_local = os.path.join(cachedir, 'RELEASE.local')
    updated_line = '{0}={1}'.format(var, place)

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
        if 'EPICS_BASE=' in line:
            logger.debug("Found EPICS_BASE line '%s', not writing it", base_line)
            base_line = line.strip()
            continue
        elif '{0}='.format(var) in line:
            logger.debug("Found '%s=' line, replacing", var)
            found = True
            line = updated_line
        logger.debug("Writing line to RELEASE.local: '%s'", outputline)
        print(line)
    fileinput.close()
    fout = open(release_local,"a")
    if not found:
        logger.debug("Adding new definition: '%s'", updated_line)
        print(updated_line, file=fout)
    if base_line:
        logger.debug("Writing EPICS_BASE line: '%s'", base_line)
        print(base_line, file=fout)
    fout.close()

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
def add_dependency(dep, tag):
    pass

def prepare(args):
    print(sys.version)
    print('PYTHONPATH')
    for dname in sys.path:
        print(' ', dname)
    print('platform = ', distutils.util.get_platform())

    print('{0}Loading setup files{1}'.format(ANSI_YELLOW, ANSI_RESET))
    source_set(default)
    if 'SET' in os.environ:
        source_set(os.environ['SET'])

    print('Installing dependencies')

def build(args):
    print('Building the module')

def test(args):
    print('Running the tests')

actions = {
    'prepare': prepare,
    'build': build,
    'test': test,
}

if __name__=='__main__':
    args = sys.argv[1:]
    while len(args)>0:
        name = args.pop(0)
        print('IN', name, 'with', args)
        actions[name](args)
