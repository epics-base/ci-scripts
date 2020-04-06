#!/bin/bash

# Module ci-scripts unit tests

# SET=test00 in .travis.yml runs the tests in this script
# all other jobs are started as compile jobs

# The following if clause can be removed for ci-scripts major version 3
if [ "$TRAVIS_OS_NAME" == osx -a "$BASH_VERSINFO" -lt 4 ]
then
    brew install bash
    if [ $(/usr/local/bin/bash -c 'echo $BASH_VERSINFO') -lt 4 ]
    then
        echo "Failed to install a recent bash" >&2
        exit 1
    fi
    exec /usr/local/bin/bash $0 "$@"
fi

# Set VV empty in .travis.yml to make scripts terse
[ "${VV:-1}" ] && set -x

[ "$SET" != "test00" ] && exec ./travis/build.sh

UTILS_UNITTEST=1

# Perl version of "readlink -f" (which MacOS does not provide)
readlinkf() { perl -MCwd -e 'print Cwd::abs_path shift' "$1"; }

# test utilities
fail() {
  echo -e "${ANSI_RED}$1${ANSI_RESET}"
  exit 1
}

fn_exists() {
  LC_ALL=C type -t $1 | grep -q function
}

repo_exists() {
  DEP=$1
  dep_lc=${DEP,,}
  eval dirname=\${${DEP}_DIRNAME:=${dep_lc}}
  eval reponame=\${${DEP}_REPONAME:=${dep_lc}}
  eval repourl=\${${DEP}_REPOURL:="https://github.com/\${${DEP}_REPOOWNER:=${REPOOWNER:-epics-modules}}/${reponame}.git"}

  git ls-remote --quiet --heads --exit-code $repourl > /dev/null 2>&1
}

SETUP_DIRS=${SETUP_PATH//:/ }

SCRIPTDIR=$(dirname $(readlinkf $0))/travis
CURDIR="$PWD"
CACHEDIR=${CACHEDIR:-${HOME}/.cache}
[ -e ${CACHEDIR} ] || mkdir -p ${CACHEDIR}

echo "Testing contents of utils.sh"

[ -d "$SCRIPTDIR" ] || fail "SCRIPTDIR does not exist"
[ -e "$SCRIPTDIR/utils.sh" ] || fail "SCRIPTDIR/utils.sh does not exist"

# source functions
. $SCRIPTDIR/utils.sh

# check for functions
fn_exists fold_start || fail "function fold_start missing from SCRIPTDIR/utils.sh"
fn_exists fold_end || fail "function fold_end missing from SCRIPTDIR/utils.sh"
fn_exists source_set || fail "function source_set missing from SCRIPTDIR/utils.sh"
fn_exists update_release_local || fail "function update_release_local missing from SCRIPTDIR/utils.sh"
fn_exists add_dependency || fail "function add_dependency missing from SCRIPTDIR/utils.sh"

# test source_set()
######################################################################

SETUP_PATH= source_set test01 | grep -q "(SETUP_PATH) is empty" || fail "empty search path not detected"
source_set xxdoesnotexistxx | grep -q "does not exist" || fail "missing setup file not detected"
source_set test01 | grep -q "Loading setup file" || fail "test01 setup file not found"
unset SEEN_SETUPS
export BASE=foo
source_set test01
[ "$BASE" = "foo" ] || fail "preset module BASE version does not override test01 setup file (expected foo got $BASE)"
unset SEEN_SETUPS
BASE=
source_set test02
[ "$BASE" = "foo" ] || fail "BASE set in test02 does not override included test01 setup file (expected foo got $BASE)"
[ "$FOO" = "bar" ] || fail "Setting of single word does not work"
[ "$FOO2" = "bar bar2" ] || fail "Setting of multiple words does not work"
[ "$FOO3" = "bar bar2" ] || fail "Indented setting of multiple words does not work"
[ "$SNCSEQ" = "R2-2-7" ] || fail "Setup test01 was not included"
unset SEEN_SETUPS
source_set test03 | grep -q "Ignoring already included setup file" || fail "test01 setup file included twice"

# test default settings file
######################################################################

echo "Testing default settings for completeness and valid git repo settings"

[ -e ./defaults.set ] || fail "defaults.set does not exist"
source_set defaults

repo_exists BASE || fail "Defaults for BASE do not point to a valid git repository at $repourl"
repo_exists PVDATA || fail "Defaults for PVDATA do not point to a valid git repository at $repourl"
repo_exists PVACCESS || fail "Defaults for PVACCESS do not point to a valid git repository at $repourl"
repo_exists NTYPES || fail "Defaults for NTYPES do not point to a valid git repository at $repourl"
repo_exists SNCSEQ || fail "Defaults for SNCSEQ do not point to a valid git repository at $repourl"
repo_exists STREAM || fail "Defaults for STREAM do not point to a valid git repository at $repourl"
repo_exists ASYN || fail "Defaults for ASYN do not point to a valid git repository at $repourl"
repo_exists STD || fail "Defaults for STD do not point to a valid git repository at $repourl"
repo_exists CALC || fail "Defaults for CALC do not point to a valid git repository at $repourl"
repo_exists AUTOSAVE || fail "Defaults for AUTOSAVE do not point to a valid git repository at $repourl"
repo_exists BUSY || fail "Defaults for BUSY do not point to a valid git repository at $repourl"
repo_exists SSCAN || fail "Defaults for SSCAN do not point to a valid git repository at $repourl"
repo_exists IOCSTATS || fail "Defaults for IOCSTATS do not point to a valid git repository at $repourl"
repo_exists MOTOR || fail "Defaults for MOTOR do not point to a valid git repository at $repourl"
repo_exists IPAC || fail "Defaults for IPAC do not point to a valid git repository at $repourl"

# test update_release_local()
######################################################################

echo "Testing updating the RELEASE.local file"

release_local=$CACHEDIR/RELEASE.local

rm -f $release_local

# Set a module
update_release_local MOD1 /tmp/mod1
updated_line="MOD1=/tmp/mod1"
grep -q "MOD1=" $release_local || fail "Line for MOD1 not added to RELEASE.local"
existing_line=$(grep "MOD1=" $release_local)
[ "${existing_line}" = "${updated_line}" ] || fail "Wrong line for MOD1 in RELEASE.local (expected=\"$updated_line\" found=\"$existing_line\")"

# Set base
update_release_local EPICS_BASE /tmp/base
updated_line="EPICS_BASE=/tmp/base"
grep -q "EPICS_BASE=" $release_local || fail "Line for EPICS_BASE not added to RELEASE.local"

# Set another module
update_release_local MOD2 /tmp/mod2
updated_line="MOD2=/tmp/mod2"
grep -q "MOD2=" $release_local || fail "Line for MOD2 not added to RELEASE.local"
existing_line=$(grep "MOD2=" $release_local)
[ "${existing_line}" = "${updated_line}" ] || fail "Wrong line for MOD2 in RELEASE.local (expected=\"$updated_line\" found=\"$existing_line\")"
tail -n 1 $release_local | grep -q "EPICS_BASE=" || fail "Line for EPICS_BASE not moved to the end of RELEASE.local"

# Update a module
update_release_local MOD1 /tmp/mod1b
updated_line="MOD1=/tmp/mod1b"
grep -q "MOD1=" $release_local || fail "Line for MOD1 not present in RELEASE.local"
existing_line=$(grep "MOD1=" $release_local)
[ "${existing_line}" = "${updated_line}" ] || fail "Wrong line for MOD1 in RELEASE.local (expected=\"$updated_line\" found=\"$existing_line\")"
head -n 1 $release_local | grep -q "MOD1=" || fail "Line for MOD1 not at the top of RELEASE.local"
tail -n 1 $release_local | grep -q "EPICS_BASE=" || fail "Line for EPICS_BASE not moved to the end of RELEASE.local"

# Check that RELEASE.local only contains variable settings
[ $(grep -v -c '[^ =]*=.*' $release_local) -ne 0 ] && fail "RELEASE.local contains invalid lines"

rm -f $release_local

# test add_dependency()
######################################################################

echo "Testing adding a specific commit (branch or tag) of a dependency"

hash_3_15_6="ce7943fb44beb22b453ddcc0bda5398fadf72096"
location=$CACHEDIR/base-R3.15.6

# CAREFUL: order of the following check matters (speeds up the test)

# dependency does not exist in the cache
rm -fr $location; modules_to_compile=
add_dependency BASE R3.15.6
[ -e $location/LICENSE ] || fail "Missing dependency was not checked out"
BUILT=$(cat "$location/built")
[ "$BUILT" != "$hash_3_15_6" ] && fail "Wrong commit of dependency checked out (expected=\"$hash_3_15_6\" found=\"$BUILT\")"
grep -q "include \$(TOP)/../RELEASE.local" $location/configure/RELEASE && fail "RELEASE in Base includes RELEASE.local"
[ "$do_recompile" ] || fail "do_recompile flag was not set for missing dependency"
echo "$modules_to_compile" | grep -q "$location" || fail "Missing dependency was not set to compile"

# up-to-date dependency does exist in the cache
( cd $CACHEDIR; git clone --quiet --depth 5 --recursive --branch R3.15.6 https://github.com/epics-base/epics-base.git base-R3.15.6 )
rm -f $location/LICENSE
unset do_recompile; modules_to_compile=
add_dependency BASE R3.15.6
[ -e $location/LICENSE ] && fail "Existing correct dependency was checked out on top"
[ "$do_recompile" ] && fail "do_recompile flag was set for up-to-date dependency"
echo "$modules_to_compile" | grep -q "$location" && fail "Up-to-date dependency was set to compile"

do_recompile=yes
add_dependency BASE R3.15.6
echo "$modules_to_compile" | grep -q "$location" || fail "Up-to-date module was not set to compile wile do_recompile=yes"

# dependency in the cache is outdated
echo "nottherighthash" > "$location/built"
unset do_recompile
add_dependency BASE R3.15.6
[ -e $location/LICENSE ] || fail "Outdated dependency was not checked out"
BUILT=$(cat "$location/built")
[ "$BUILT" != "$hash_3_15_6" ] && fail "Wrong commit of dependency checked out (expected=\"$hash_3_15_6\" found=\"$BUILT\")"
[ "$do_recompile" ] || fail "do_recompile flag was not set for outdated dependency"
echo "$modules_to_compile" | grep -q "$location" || fail "Outdated dependency was not set to compile"

# msi is automatically added to 3.14
rm -fr $location; modules_to_compile=
location=$CACHEDIR/base-R3.14.12.1
rm -fr $location;
add_dependency BASE R3.14.12.1
[ -e $location/src/dbtools/msi.c ] || fail "MSI was not added to Base 3.14"

rm -fr $CACHEDIR/*; modules_to_compile=

# missing inclusion of RELEASE.local in configure/RELEASE
location=$CACHEDIR/std-R3-4
add_dependency STD R3-4
grep -q "include \$(TOP)/../RELEASE.local" $location/configure/RELEASE || fail "Inclusion of RELEASE.local not added to configure/RELEASE"
rm -fr $location; modules_to_compile=

# correct handling of FOO_RECURSIVE setting (https://github.com/epics-base/ci-scripts/issues/25 regression)
export SSCAN_RECURSIVE=NO
add_dependency SSCAN master
add_dependency ASYN master
[ -e $CACHEDIR/sscan-master/.ci/README.md ] && fail "Sscan was checked out recursively despite SSCAN_RECURSIVE=NO"
[ -e $CACHEDIR/asyn-master/.ci/README.md ] || fail "Asyn was not checked out recursively"
rm -fr $CACHEDIR/*; modules_to_compile=

unset SSCAN_RECURSIVE
export ASYN_RECURSIVE=NO
add_dependency SSCAN master
add_dependency ASYN master
[ -e $CACHEDIR/sscan-master/.ci/README.md ] || fail "Sscan was not checked out recursively"
[ -e $CACHEDIR/asyn-master/.ci/README.md ] && fail "Asyn was checked out recursively despite ASYN_RECURSIVE=NO"
rm -fr $CACHEDIR/*
