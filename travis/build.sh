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

# Base 3.15 doesn't have -qemu target architecture and needs an extra define
[ -e $EPICS_BASE/configure/os/CONFIG.Common.RTEMS-pc386-qemu ] || EXTRA_QEMU=RTEMS_QEMU_FIXUPS=YES

# use array variable to get the quoting right while using separate words for arguments
[ -n "$EXTRA0" ] && EXTRA[0]="$EXTRA0"
[ -n "$EXTRA1" ] && EXTRA[1]="$EXTRA1"
[ -n "$EXTRA2" ] && EXTRA[2]="$EXTRA2"
[ -n "$EXTRA3" ] && EXTRA[3]="$EXTRA3"
[ -n "$EXTRA4" ] && EXTRA[4]="$EXTRA4"
[ -n "$EXTRA5" ] && EXTRA[5]="$EXTRA5"

make -j2 $EXTRA_QEMU "${EXTRA[@]}"

ret=0

if [ "$TEST" != "NO" ]
then
  make tapfiles || ret=$?

  make -sk test-results
fi

exit $ret
