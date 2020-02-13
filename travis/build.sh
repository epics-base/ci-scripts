#!/bin/bash
set -e

# Set VV in .travis.yml to make scripts verbose
[ "$VV" ] && set -x

CACHEDIR="$HOME/.cache/EPICS"
mkdir -p "$CACHEDIR"

eval $(grep "EPICS_BASE=" ${CACHEDIR}/RELEASE.local)
export EPICS_BASE

[ -z "$EPICS_HOST_ARCH" -a -f $EPICS_BASE/src/tools/EpicsHostArch.pl ] && EPICS_HOST_ARCH=$(perl $EPICS_BASE/src/tools/EpicsHostArch.pl)
[ -z "$EPICS_HOST_ARCH" -a -f $EPICS_BASE/startup/EpicsHostArch.pl ] && EPICS_HOST_ARCH=$(perl $EPICS_BASE/startup/EpicsHostArch.pl)
export EPICS_HOST_ARCH

make -j2 $EXTRA

if [ "$TEST" != "NO" ]
then
  make tapfiles
  make -s test-results
fi
