#!/bin/sh
set -x

UTILS_UNITTEST=1

# Perl version of "readlink -f" (which MacOS does not provide)
readlinkf() { perl -MCwd -e 'print Cwd::abs_path shift' "$1"; }

# test utilities
die() {
  echo $1
  exit 1
}

fn_exists() {
  LC_ALL=C type -t $1 | grep -q function
}

repo_exists() {
  DEP=$1
  dep_lc=$(echo $DEP | tr 'A-Z' 'a-z')
  eval dirname=\${${DEP}_DIRNAME:=${dep_lc}}
  eval reponame=\${${DEP}_REPONAME:=${dep_lc}}
  eval repourl=\${${DEP}_REPOURL:="https://github.com/\${${DEP}_REPOOWNER:=${REPOOWNER:-epics-modules}}/${reponame}.git"}

  git ls-remote --quiet --heads --exit-code $repourl > /dev/null 2>&1
}

SETUP_DIRS=$(echo $SETUP_PATH | tr ":" "\n")

SCRIPTDIR=$(dirname $(readlinkf $0))/travis
CURDIR="$PWD"
CACHEDIR="$HOME/.cache"

echo "Testing contents of utils.sh"

[ -d "$SCRIPTDIR" ] || die "SCRIPTDIR does not exist"
[ -e "$SCRIPTDIR/utils.sh" ] || die "SCRIPTDIR/utils.sh does not exist"

# source functions
. $SCRIPTDIR/utils.sh

# check for functions
fn_exists fold_start || die "function fold_start missing from SCRIPTDIR/utils.sh"
fn_exists fold_end || die "function fold_end missing from SCRIPTDIR/utils.sh"
fn_exists source_set || die "function source_set missing from SCRIPTDIR/utils.sh"
fn_exists update_release_local || die "function update_release_local missing from SCRIPTDIR/utils.sh"
fn_exists add_dependency || die "function add_dependency missing from SCRIPTDIR/utils.sh"

# test source_set()
######################################################################

SETUP_DIRS= source_set test01 | grep -q "(SETUP_PATH) is empty" || die "empty search path not detected"
source_set xxdoesnotexistxx | grep -q "does not exist" || die "missing setup file not detected"
source_set test01 | grep -q "Loading setup file" || die "test01 setup file not found"

# test default settings file
######################################################################

echo "Testing default settings for completeness and valid git repo settings"

[ -e ./defaults.set ] || die "defaults.set does not exist"
source_set defaults

repo_exists BASE || die "Defaults for BASE do not point to a valid git repository at $repourl"
repo_exists PVDATA || die "Defaults for PVDATA do not point to a valid git repository at $repourl"
repo_exists PVACCESS || die "Defaults for PVACCESS do not point to a valid git repository at $repourl"
repo_exists NTYPES || die "Defaults for NTYPES do not point to a valid git repository at $repourl"
repo_exists SNCSEQ || die "Defaults for SNCSEQ do not point to a valid git repository at $repourl"
repo_exists STREAM || die "Defaults for STREAM do not point to a valid git repository at $repourl"
repo_exists ASYN || die "Defaults for STREAM do not point to a valid git repository at $repourl"
repo_exists STD || die "Defaults for STD do not point to a valid git repository at $repourl"
repo_exists CALC || die "Defaults for CALC do not point to a valid git repository at $repourl"
repo_exists AUTOSAVE || die "Defaults for AUTOSAVE do not point to a valid git repository at $repourl"
repo_exists BUSY || die "Defaults for BUSY do not point to a valid git repository at $repourl"
repo_exists SSCAN || die "Defaults for SSCAN do not point to a valid git repository at $repourl"
repo_exists IOCSTATS || die "Defaults for IOCSTATS do not point to a valid git repository at $repourl"

# test update_release_local()
######################################################################

echo "Testing updating the RELEASE.local file"

release_local=$CACHEDIR/RELEASE.local

rm -f $release_local

# Set a module
update_release_local MOD1 /tmp/mod1
updated_line="MOD1=/tmp/mod1"
grep -q "MOD1=" $release_local || die "Line for MOD1 not added to RELEASE.local"
existing_line=$(grep "MOD1=" $release_local)
[ "${existing_line}" = "${updated_line}" ] || die "Wrong line for MOD1 in RELEASE.local (expected=\"$updated_line\" found=\"$existing_line\")"

# Set base
update_release_local EPICS_BASE /tmp/base
updated_line="EPICS_BASE=/tmp/base"
grep -q "EPICS_BASE=" $release_local || die "Line for EPICS_BASE not added to RELEASE.local"

# Set another module
update_release_local MOD2 /tmp/mod2
updated_line="MOD2=/tmp/mod2"
grep -q "MOD2=" $release_local || die "Line for MOD2 not added to RELEASE.local"
existing_line=$(grep "MOD2=" $release_local)
[ "${existing_line}" = "${updated_line}" ] || die "Wrong line for MOD2 in RELEASE.local (expected=\"$updated_line\" found=\"$existing_line\")"
tail -n 1 $release_local | grep -q "EPICS_BASE=" || die "Line for EPICS_BASE not moved to the end of RELEASE.local"

# Update a module
update_release_local MOD1 /tmp/mod1b
updated_line="MOD1=/tmp/mod1b"
grep -q "MOD1=" $release_local || die "Line for MOD1 not present in RELEASE.local"
existing_line=$(grep "MOD1=" $release_local)
[ "${existing_line}" = "${updated_line}" ] || die "Wrong line for MOD1 in RELEASE.local (expected=\"$updated_line\" found=\"$existing_line\")"
head -n 1 $release_local | grep -q "MOD1=" || die "Line for MOD1 not at the top of RELEASE.local"
tail -n 1 $release_local | grep -q "EPICS_BASE=" || die "Line for EPICS_BASE not moved to the end of RELEASE.local"

# Check that RELEASE.local only contains variable settings
[ $(grep -v -c '[^ =]*=.*' $release_local) -ne 0 ] && die "RELEASE.local contains invalid lines"

rm -f $release_local

# test add_dependency()
######################################################################

echo "Testing adding a specific commit (branch or tag) of a dependency"

hash_3_15_6="ce7943fb44beb22b453ddcc0bda5398fadf72096"
location=$CACHEDIR/base-R3.15.6

# CAREFUL: order of the following check matters (speeds up the test)

# dependency does not exist in the cache
rm -fr $location
add_dependency BASE R3.15.6
[ -e $location/LICENSE ] || die "Missing dependency was not checked out"
BUILT=$(cat "$location/built")
[ "$BUILT" != "$hash_3_15_6" ] && die "Wrong commit of dependency checked out (expected=\"$hash_3_15_6\" found=\"$BUILT\")"

# up-to-date dependency does exist in the cache
( cd $CACHEDIR; git clone --quiet --depth 5 --recursive --branch R3.15.6 https://github.com/epics-base/epics-base.git base-R3.15.6 )
rm -f $location/LICENSE
add_dependency BASE R3.15.6
[ -e $location/LICENSE ] && die "Existing correct dependency was checked out on top"

# dependency in the cache is outdated
echo "nottherighthash" > "$location/built"
add_dependency BASE R3.15.6
[ -e $location/LICENSE ] || die "Outdated dependency was not checked out"
BUILT=$(cat "$location/built")
[ "$BUILT" != "$hash_3_15_6" ] && die "Wrong commit of dependency checked out (expected=\"$hash_3_15_6\" found=\"$BUILT\")"

rm -fr $location
