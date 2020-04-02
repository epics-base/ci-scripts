#!/bin/bash
set -e

# Set VV in .travis.yml to make scripts verbose
[ "$VV" ] && set -x

MYDIR="$(dirname "${BASH_SOURCE[0]}")"

CACHEDIR=${CACHEDIR:-${HOME}/.cache}

eval $(grep "EPICS_BASE=" ${CACHEDIR}/RELEASE.local)
export EPICS_BASE

[ -z "$EPICS_HOST_ARCH" -a -f $EPICS_BASE/src/tools/EpicsHostArch.pl ] && EPICS_HOST_ARCH=$(perl $EPICS_BASE/src/tools/EpicsHostArch.pl)
[ -z "$EPICS_HOST_ARCH" -a -f $EPICS_BASE/startup/EpicsHostArch.pl ] && EPICS_HOST_ARCH=$(perl $EPICS_BASE/startup/EpicsHostArch.pl)
export EPICS_HOST_ARCH

make -j2 $EXTRA

if [ "$TEST" != "NO" ]
then
  ulimit -c unlimited

  sudo ${PYTHON:-python} "$MYDIR"/core-dumper.py install

  ret=0
  make tapfiles || ret=$?

  sudo ${PYTHON:-python} "$MYDIR"/core-dumper.py uninstall
  ${PYTHON:-python} "$MYDIR"/core-dumper.py report

  make -s test-results
  exit $ret
fi
