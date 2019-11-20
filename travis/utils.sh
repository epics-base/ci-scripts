# Utility functions for Travis scripts in ci-scripts
#
# This file is sourced by the executable scripts

# Portable version of 'sed -i'  (that MacOS doesn't provide)

# sedi (cmd, file)
# Do the equivalent of "sed -i cmd file"
sedi () {
  cat $2 | sed "$1" > $2.tmp$$; mv -f $2.tmp$$ $2
}

# Travis log fold control
# from https://github.com/travis-ci/travis-rubies/blob/build/build.sh

fold_start() {
  echo -en "travis_fold:start:$1\\r\033[33;1m$2\033[0m"
}

fold_end() {
  echo -en "travis_fold:end:$1\\r"
}

# source_set(settings)
#
# Source a settings file (extension .set) found in the SETUP_DIRS path
# May be called recursively (from within a settings file)
source_set() {
  local set_file=$1
  local set_dir
  local found=0
  for set_dir in ${SETUP_DIRS}
  do
    if [ -e $set_dir/$set_file.set ]
    then
      echo "Loading setup file $set_dir/$set_file.set"
      . $set_dir/$set_file.set
      found=1
      break
    fi
  done
  if [ $found -eq 0 ]
  then
    echo "Setup file $set_file.set does not exist in SETUP_DIRS search path ($SETUP_DIRS)"
    [ "$UTILS_UNITTEST" ] || exit 1
  fi
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
      sedi "s|${var}=.*|${var}=${place}|g" ${release_local}
    fi
  else
    echo "$var=$place" >> ${release_local}
    ret=0
    grep -q "EPICS_BASE=" ${release_local} || ret=$?
    if [ $ret -eq 0 ]
    then
      base_line=$(grep "EPICS_BASE=" ${release_local})
      sedi '\|EPICS_BASE=|d' ${release_local}
      echo ${base_line} >> ${release_local}
    fi
  fi
}

# add_dependency(dep, tag)
#
# Add a dependency to the cache area:
# - check out (recursive if configured) in the CACHE area unless it already exists and the
#   required commit has been built
# - Defaults:
#   $dep_DIRNAME = lower case ($dep)
#   $dep_REPONAME = lower case ($dep)
#   $dep_REPOURL = GitHub / $dep_REPOOWNER (or $REPOOWNER or epics-modules) / $dep_REPONAME .git
#   $dep_VARNAME = $dep
#   $dep_DEPTH = 5
#   $dep_RECURSIVE = 1/YES (0/NO to for a flat clone)
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
  eval recursive=\${${DEP}_RECURSIVE:=1}
  recursive=$(echo $recursive | tr 'A-Z' 'a-z')
  [ "$recursive" != "0" -a "$recursive" != "no" ] && recurse="--recursive"

  # determine if BASE points to a valid release or branch
  if ! git ls-remote --quiet --exit-code --refs $repourl "$TAG"
  then
    echo "$TAG is neither a tag nor a branch name for $DEP ($repourl)"
    [ "$UTILS_UNITTEST" ] || exit 1
  fi

  if [ -e $CACHEDIR/$dirname-$TAG ]
  then
    [ -e $CACHEDIR/$dirname-$TAG/built ] && BUILT=$(cat $CACHEDIR/$dirname-$TAG/built) || BUILT="never"
    HEAD=$(cd "$CACHEDIR/$dirname-$TAG" && git log -n1 --pretty=format:%H)
    [ "$HEAD" != "$BUILT" ] && rm -fr $CACHEDIR/$dirname-$TAG
  fi

  if [ ! -e $CACHEDIR/$dirname-$TAG ]
  then
    cd $CACHEDIR
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
    git clone --quiet $deptharg $recurse --branch "$TAG" $repourl $dirname-$TAG
    ( cd $dirname-$TAG && git log -n1 )
    modules_to_compile="${modules_to_compile} $CACHEDIR/$dirname-$TAG"
    # run hook
    eval hook="\${${DEP}_HOOK}"
    if [ "$hook" ]
    then
      if [ -x "$curdir/$hook" ]
      then
        ( cd $CACHEDIR/$dirname-$TAG; "$curdir/$hook" )
      else
        echo "Hook script $hook is not executable or does not exist."
        exit 1
      fi
    fi
    HEAD=$(cd "$CACHEDIR/$dirname-$TAG" && git log -n1 --pretty=format:%H)
    echo "$HEAD" > "$CACHEDIR/$dirname-$TAG/built"
    cd "$curdir"
  fi

  update_release_local ${varname} $CACHEDIR/$dirname-$TAG
}
