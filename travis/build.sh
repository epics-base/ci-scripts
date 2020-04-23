#!/bin/bash
set -e

# Set VV in .travis.yml to make scripts verbose
[ "$VV" ] && set -x

CACHEDIR=${CACHEDIR:-${HOME}/.cache}

eval $(grep "EPICS_BASE=" ${CACHEDIR}/RELEASE.local)
export EPICS_BASE

[ -z "$EPICS_HOST_ARCH" -a -f $EPICS_BASE/src/tools/EpicsHostArch.pl ] && EPICS_HOST_ARCH=$(perl $EPICS_BASE/src/tools/EpicsHostArch.pl)
[ -z "$EPICS_HOST_ARCH" -a -f $EPICS_BASE/startup/EpicsHostArch.pl ] && EPICS_HOST_ARCH=$(perl $EPICS_BASE/startup/EpicsHostArch.pl)
export EPICS_HOST_ARCH

[ -z "$EXTRA" ] && make -j2 || make -j2 "$EXTRA"

ret=0

if [ "$TEST" != "NO" ]
then
  make tapfiles || ret=$?

  make -sk test-results
fi

exit $ret
