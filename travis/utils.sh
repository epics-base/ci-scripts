# Utility functions for Travis scripts in ci-scripts
#
# This file is sourced by the executable scripts

# Travis log fold control
# from https://github.com/travis-ci/travis-rubies/blob/build/build.sh

fold_start() {
  echo "travis_fold:start:$1\033[33;1m$2\033[0m"
}

fold_end() {
  echo "\ntravis_fold:end:$1\r"
}

# source_set(settings)
#
# Source a settings file (extension .set) found in the SETUP_DIRS path
# May be called recursively (from within a settings file)
source_set() {
  local set_file=$1
  local set_dir
  for set_dir in ${SETUP_DIRS}
  do
    if [ -e $set_dir/$set_file.set ]
    then
      echo "Loading setup file $set_dir/$set_file.set"
      . $set_dir/$set_file.set
      break
    fi
  done
}

# update_release_local(varname, place)
#   varname   name of the variable to set in RELEASE.local
#   place     place (absolute path) of where variable should point to
#
# Manipulate RELEASE.local in the cache location:
# - replace "$varname=$place" line if it exists and has changed
# - otherwise add "$varname=$place" line and possibly move EPICS_BASE=... line to the end
update_release_local() {
  local var=$1
  local place=$2
  local release_local=${CACHEDIR}/RELEASE.local
  local updated_line="${var}=${place}"

  local ret=0
  [ -e ${release_local} ] && grep -q "${var}=" ${release_local} || ret=$?
  if [ $ret -eq 0 ]
  then
    existing_line=$(grep "${var}=" ${release_local})
    if [ "${existing_line}" != "${updated_line}" ]
    then
      sed -i "s|${var}=.*|${var}=${place}|g" ${release_local}
    fi
  else
    echo "$var=$place" >> ${release_local}
    grep -q "EPICS_BASE=" ${release_local} || ret=$?
    if [ $ret -eq 0 ]
    then
      base_line=$(grep "EPICS_BASE=" ${release_local})
      sed -i 's|EPICS_BASE=||g' ${release_local}
      echo ${base_line} >> ${release_local}
    fi
  fi
}

# add_dependency(dep, tag)
#
# Add a dependency to the cache or source area:
# - if $tag is a branch name, check out flat (no submodules) in the SOURCE area
# - if $tag is a release name, check out recursive (w/ submodules) in the CACHE area
#   unless it already exists
# - Defaults:
#   $dep_DIRNAME = lower case ($dep)
#   $dep_REPONAME = lower case ($dep)
#   $dep_REPOURL = GitHub / $dep_REPOOWNER (or $REPOOWNER or epics-modules) / $dep_REPONAME .git
#   $dep_VARNAME = $dep
#   $dep_DEPTH = 5
# - Add $dep_VARNAME line to the RELEASE.local file in the cache area (unless already there)
# - Add full path to $modules_to_compile
add_dependency() {
  curdir="$PWD"
  DEP=$1
  TAG=$2
  dep_lc=$(echo $DEP | tr 'A-Z' 'a-z')
  eval dirname=\${${DEP}_DIRNAME:=${dep_lc}}
  eval reponame=\${${DEP}_REPONAME:=${dep_lc}}
  eval repourl=\${${DEP}_REPOURL:="https://github.com/\${${DEP}_REPOOWNER:=${REPOOWNER:-epics-modules}}/${reponame}.git"}
  eval varname=\${${DEP}_VARNAME:=${DEP}}

  # determine if BASE points to a release or a branch
  git ls-remote --quiet --exit-code --tags $repourl "$TAG" && tagtype=release
  git ls-remote --quiet --exit-code --heads $repourl "$TAG" && tagtype=branch

  case "${tagtype}" in
  "release" )
    location=${CACHEDIR}
    recursive="--recursive"
    ;;
  "branch" )
    location=${SOURCEDIR}
    recursive=""
    ;;
  * )
    echo "$TAG is neither a tag nor a branch name for $DEP ($repourl)"
    exit 1
    ;;
  esac

  if [ ! -e $location/$dirname-$TAG ]
  then
    cd $location
    eval depth=\${${DEP}_DEPTH:-"-1"}
    case ${depth} in
    -1 )
      deptharg="--depth 5"
      ;;
    0 )
      deptharg=""
      ;;
    * )
      deptharg="--depth $depth"
      ;;
    esac
    git clone --quiet $deptharg $recursive --branch "$TAG" $repourl $dirname-$TAG
    ( cd $dirname-$TAG && git log -n1 )
    modules_to_compile="${modules_to_compile} $location/$dirname-$TAG"
    # run hook
    eval hook="\${${DEP}_HOOK}"
    if [ ! -z "$hook" ]
    then
      if [ -x "$curdir/$hook" ]
      then
        ( cd $location/$dirname-$TAG; "$curdir/$hook" )
      else
        echo "Hook script $hook is not executable or does not exist."
        exit 1
      fi
    fi
    cd "$curdir"
  fi
  update_release_local ${varname} $location/$dirname-$TAG
}
