#!/bin/sh
set -e

# Set VV in .travis.yml to make scripts verbose
[ "$VV" ] && set -x

make -j2 $EXTRA

if [ "$TEST" != "NO" ]
then
  make tapfiles
  make -s test-results
fi
