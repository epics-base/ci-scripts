#!/usr/bin/env python
"""Windows (AppVeyor) ci build script
"""

import sys, os
import logging
import subprocess as SP
import distutils.util
from glob import glob

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

# Used from unittests
def clear_lists():
    del seen_setups[:]
    setup.clear()

# source_set(setup)
#
# Source a settings file (extension .set) found in the setup_dirs path
# May be called recursively (from within a setup file)
def source_set(args):
    found = False

    setup_dirs = os.getenv('SETUP_PATH', "").replace(':', ' ').split()
    if len(setup_dirs) == 0:
        raise NameError("{0}Search path for setup files (SETUP_PATH) is empty{1}".format(ANSI_RED,ANSI_RESET))

    for set_dir in setup_dirs:
        set_file = os.path.join(set_dir, args) + ".set"

        if set_file in seen_setups:
            print("Ignoring already included setup file {0}".format(set_file))
            return

        if os.path.isfile(set_file):
            seen_setups.append(set_file)
            print("Loading setup file {0}".format(set_file))
            with open(set_file) as fp:
                for line in fp:
                    logging.debug('Next line: {0}'.format(line.strip()))
                    if not line.strip() or line.strip()[0] == '#':
                        continue
                    if line.startswith("include"):
                        logging.debug('Found an include, reading {0}'.format(line.split()[1]))
                        source_set(line.split()[1])
                        continue
                    assign = line.replace('"', '').strip().split("=", 1)
                    logging.debug('Interpreting as assignment')
                    if assign[0] not in setup:
                        setup[assign[0]] = os.getenv(assign[0], "")
                    if not setup[assign[0]].strip():
                        logging.debug('Doing assignment: {0} = {1}'.format(assign[0], assign[1]))
                        setup[assign[0]] = assign[1]
            found = True
            break

    if not found:
        raise NameError("{0}Setup file {1} does not exist in SETUP_PATH search path ({2}){3}"
                        .format(ANSI_RED,set_file,setup_dirs,ANSI_RESET))

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
