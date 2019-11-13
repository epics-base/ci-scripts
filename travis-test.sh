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
SOURCEDIR="$HOME/.source"

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

# test source_set ()

source_set xxdoesnotexistxx | grep -q "does not exist" || die "missing setup file not detected"
source_set test01 | grep -q "Loading setup file" || die "test01 setup file not found"

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
