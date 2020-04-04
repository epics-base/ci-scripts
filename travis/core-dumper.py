#!/usr/bin/env python
"""core-file analysis for Linux CI
"""

import logging
import errno
import tempfile
import sys
import os
import re
import fcntl
import traceback
from glob import glob
import subprocess as SP

log = logging.getLogger('core-dumper')

core_pattern = '/proc/sys/kernel/core_pattern'

# The following definitions will be **replaced** for dump()
# output directory.
output_dir = None
# location of GDB
gdb_loc = None

class FLock(object):
    def __init__(self, file):
        self._file = file
    def __enter__(self):
        fcntl.flock(self._file.fileno(), fcntl.LOCK_EX)
    def __exit__(self,A,B,C):
        fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)

def install(args):
    logging.basicConfig(level=logging.DEBUG)

    if not os.path.isfile(core_pattern):
        log.info('Not Linux')
        return

    if not args.gdb:
        for path in os.environ['PATH'].split(os.pathsep):
            gdb = os.path.join(path, 'gdb')
            if os.path.isfile(gdb):
                args.gdb = gdb
                break

    if not os.path.isfile(args.gdb or ''):
        log.error("gdb not Found.  Skipping install.  (add 'gdb' to apt package list)")
        return

    try:
        os.makedirs(args.outdir)
    except OSError as e:
        if e.errno!=errno.EEXIST:
            raise
        # EEXIST is expected

    outfile = os.path.join(tempfile.gettempdir(), os.path.basename(__file__))
    log.info('Installing as %s', outfile)

    with open(outfile, 'w') as OF, open(__file__, 'r') as IF:
        for line in IF:
            # re-write some strip lines to that dump doesn't depend on environment when exec'd by Linux kernel
            if re.match('^#!/usr/bin/env\s+python\s*$', line):
                OF.write('#!{0.executable}\n'.format(sys))
            elif re.match('^\s*output_dir\s*=\s*None\s*$', line):
                OF.write('output_dir = "{0.outdir}"\n'.format(args))
            elif re.match('^\s*gdb_loc\s*=\s*None\s*$', line):
                OF.write('gdb_loc = "{0.gdb}"\n'.format(args))
            else:
                OF.write(line)

    # executable
    os.chmod(outfile, 0o755)

    try:
        with open(core_pattern, 'w') as F:
            F.write('|{} dump %p %t'.format(outfile))
    except IOError as e:
        if e.errno==errno.EACCES:
            log.error('Insufficient permission to open "{}".  sudo?'.format(core_pattern))
            sys.exit(1)
        raise

    with open(core_pattern, 'r') as F:
        log.debug('core_pattern: %s', repr(F.read()))

    log.info('core-dumper.py installed.  Logging to: %s', args.outdir)

def uninstall(args):
    logging.basicConfig(level=logging.DEBUG)

    if not os.path.isfile(core_pattern):
        log.info('Not Linux')
        return

    with open(core_pattern, 'w') as F:
        F.write('core')

def dump(args):
    os.umask(0o022)

    logging.basicConfig(level=logging.DEBUG, filename=os.path.join(output_dir, 'core-dumper.log'))

    log.debug('Dumping PID %s @ %s', args.pid, args.time)

    corefile = os.path.join(output_dir, '{0.time}.{0.pid}.core'.format(args))
    logfile = os.path.join(output_dir, '{0.time}.{0.pid}.txt'.format(args))

    with open(logfile, 'w', 0) as LOG, FLock(LOG):
        LOG.write('# Dumping PID {} @ {}\n'.format(args.pid, args.time))

        try:
            if hasattr(sys.stdin, 'buffer'):
                IF = sys.stdin.buffer # py3
            else:
                IF = sys.stdin # py2 (!win32)

            # read info from /proc of dump'd process
            exe = os.readlink('/proc/{0.pid}/exe'.format(args))
            with open('/proc/{0.pid}/cmdline'.format(args), 'rb') as F:
                cmdline = [arg.decode('ascii') for arg in F.read().split(b'\0')]
            cmdline.pop() # result of final nil

            LOG.write('CORE: {}\nEXE: {}\nCMDLINE: {}\n'.format(corefile, exe, cmdline))

            # copy blob content
            with open(corefile, 'wb') as OF:
                while True:
                    blob = IF.read(1024*32)
                    if not blob:
                        break
                    OF.write(blob)

            cmd = [
                gdb_loc,
                '--nx', '--nw', '--batch', # no .gitinit, no UI, no interactive
                '-ex', 'set pagination 0',
                '-ex', 'thread apply all bt',
                exe, corefile
            ]
            log.debug('exec: %s', cmd)
            LOG.flush()

            with open(os.devnull, 'r') as NULL:
                trace = SP.check_output(cmd, stdin=NULL, stderr=SP.STDOUT)

            LOG.write(trace)
            LOG.write('\nComplete\n')

        except:
            traceback.print_exc(file=LOG)
        finally:
            # always flush before unlock
            LOG.flush()
            os.fsync(LOG.fileno())

    log.debug('Complete')

def report(args):
    logging.basicConfig(level=logging.DEBUG)

    for report in glob(os.path.join(args.outdir, '*.txt')):
        sys.stdout.write('Report {}\n'.format(report))
        with open(report, 'r', 0) as F, FLock(F):
            for line in F:
                sys.stdout.write(line)

    sys.stdout.write('Log:\n')
    try:
        with open(os.path.join(args.outdir, 'core-dumper.log'), 'r') as F:
            for line in F:
                sys.stdout.write(line)
    except IOError as e:
        if e.errno==errno.ENOENT:
            sys.stdout.write('No log')
        else:
            raise

def getargs():
    from argparse import ArgumentParser
    P = ArgumentParser(description='Linux CI core dump analyzer.'\
        +'  Run install prior to exec of suspect code.'\
        +'  Then uninstall and report afterwards.'\
        +'  install and uninstall require root (sudo).')

    SP = P.add_subparsers()

    CMD = SP.add_parser('install')
    CMD.add_argument('--outdir', default=os.path.join(tempfile.gettempdir(), 'cores'),
                     help='Write backtraces to this directory')
    CMD.add_argument('--gdb')
    CMD.set_defaults(func=install)

    CMD = SP.add_parser('uninstall')
    CMD.set_defaults(func=uninstall)

    CMD = SP.add_parser('dump')
    CMD.add_argument('pid')
    CMD.add_argument('time')
    CMD.set_defaults(func=dump)

    CMD = SP.add_parser('report')
    CMD.add_argument('--outdir', default=os.path.join(tempfile.gettempdir(), 'cores'),
                     help='Write backtraces to this directory')
    CMD.set_defaults(func=report)

    return P

if __name__=='__main__':
    args = getargs().parse_args()
    args.func(args)
