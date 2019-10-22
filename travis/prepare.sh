#!/bin/sh
set -e -x

SETUP_DIRS=$(echo $SETUP_PATH | tr ":" "\n")

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
    eval git clone --quiet $deptharg $recursive --branch "$TAG" $repourl $dirname-$TAG
    ( cd $dirname-$TAG && git log -n1 )
    modules_to_compile="${modules_to_compile} $location/$dirname-$TAG"
    cd "$curdir"
  fi
  update_release_local ${varname} $location/$dirname-$TAG
}

CURDIR="$PWD"
CACHEDIR="$HOME/.cache"
SOURCEDIR="$HOME/.source"

# Load settings
# -------------

fold_start load.settings "Loading settings"

# load default settings for well-known modules
source_set defaults

# source configured settings
[ -z "${SET+x}" ] || source_set $SET

fold_end load.settings

# Check out dependencies
# ----------------------

fold_start check.out.dependencies "Checking out dependencies"

mkdir -p $SOURCEDIR

for mod in BASE $MODULES
do
  mod_uc=$(echo $mod | tr 'a-z' 'A-Z')
  eval add_dependency $mod_uc \${${mod_uc}:-master}
done
cp ${CACHEDIR}/RELEASE.local ${SOURCEDIR}/RELEASE.local
[ -e ./configure ] && cp ${CACHEDIR}/RELEASE.local ./configure/RELEASE.local

fold_end check.out.dependencies

# Set up compiler
# ---------------

fold_start set.up.compiler "Setting up compiler"

eval $(grep "EPICS_BASE=" ${CACHEDIR}/RELEASE.local)

[ "$EPICS_HOST_ARCH" ] || EPICS_HOST_ARCH=$(sh $EPICS_BASE/startup/EpicsHostArch)

if echo ${modules_to_compile} | grep -q "$EPICS_BASE"
then

  # requires wine and g++-mingw-w64-i686
  if [ "$WINE" = "32" ]
  then
    echo "Cross mingw32"
    sed -i -e '/CMPLR_PREFIX/d' $EPICS_BASE/configure/os/CONFIG_SITE.linux-x86.win32-x86-mingw
    cat << EOF >> $EPICS_BASE/configure/os/CONFIG_SITE.linux-x86.win32-x86-mingw
CMPLR_PREFIX=i686-w64-mingw32-
EOF
    cat << EOF >> $EPICS_BASE/configure/CONFIG_SITE
CROSS_COMPILER_TARGET_ARCHS+=win32-x86-mingw
EOF

  elif [ "$WINE" = "64" ]
  then
    echo "Cross mingw64"
    sed -i -e '/CMPLR_PREFIX/d' $EPICS_BASE/configure/os/CONFIG_SITE.linux-x86.windows-x64-mingw
    cat << EOF >> $EPICS_BASE/configure/os/CONFIG_SITE.linux-x86.windows-x64-mingw
CMPLR_PREFIX=x86_64-w64-mingw32-
EOF
    cat << EOF >> $EPICS_BASE/configure/CONFIG_SITE
CROSS_COMPILER_TARGET_ARCHS+=windows-x64-mingw
EOF
  fi

  if [ "$STATIC" = "YES" ]
  then
    echo "Build static libraries/executables"
    cat << EOF >> $EPICS_BASE/configure/CONFIG_SITE
SHARED_LIBRARIES=NO
STATIC_BUILD=YES
EOF
  fi

  HOST_CCMPLR_NAME=`echo "$TRAVIS_COMPILER" | sed -E 's/^([[:alpha:]][^-]*(-[[:alpha:]][^-]*)*)+(-[0-9\.]+)?$/\1/g'`
  HOST_CMPLR_VER_SUFFIX=`echo "$TRAVIS_COMPILER" | sed -E 's/^([[:alpha:]][^-]*(-[[:alpha:]][^-]*)*)+(-[0-9\.]+)?$/\3/g'`
  HOST_CMPLR_VER=`echo "$HOST_CMPLR_VER_SUFFIX" | cut -c 2-`

  case "$HOST_CCMPLR_NAME" in
  clang)
    echo "Host compiler is clang"
    HOST_CPPCMPLR_NAME=$(echo "$HOST_CCMPLR_NAME" | sed 's/clang/clang++/g')
    cat << EOF >> $EPICS_BASE/configure/os/CONFIG_SITE.Common.$EPICS_HOST_ARCH
GNU         = NO
CMPLR_CLASS = clang
CC          = ${HOST_CCMPLR_NAME}$HOST_CMPLR_VER_SUFFIX
CCC         = ${HOST_CPPCMPLR_NAME}$HOST_CMPLR_VER_SUFFIX
EOF

    # hack
    sed -i -e 's/CMPLR_CLASS = gcc/CMPLR_CLASS = clang/' $EPICS_BASE/configure/CONFIG.gnuCommon

    ${HOST_CCMPLR_NAME}$HOST_CMPLR_VER_SUFFIX --version
    ;;
  gcc)
    echo "Host compiler is GCC"
    HOST_CPPCMPLR_NAME=$(echo "$HOST_CCMPLR_NAME" | sed 's/gcc/g++/g')
    cat << EOF >> $EPICS_BASE/configure/os/CONFIG_SITE.Common.$EPICS_HOST_ARCH
CC          = ${HOST_CCMPLR_NAME}$HOST_CMPLR_VER_SUFFIX
CCC         = ${HOST_CPPCMPLR_NAME}$HOST_CMPLR_VER_SUFFIX
EOF

    ${HOST_CCMPLR_NAME}$HOST_CMPLR_VER_SUFFIX --version
    ;;
  *)
    echo "Host compiler is default"
    gcc --version
    ;;
  esac

  cat <<EOF >> $EPICS_BASE/configure/CONFIG_SITE
USR_CPPFLAGS += $USR_CPPFLAGS
USR_CFLAGS += $USR_CFLAGS
USR_CXXFLAGS += $USR_CXXFLAGS
EOF

  # set RTEMS to eg. "4.9" or "4.10"
  # requires qemu, bison, flex, texinfo, install-info
  if [ -n "$RTEMS" ]
  then
    echo "Cross RTEMS${RTEMS} for pc386"
    curl -L "https://github.com/mdavidsaver/rsb/releases/download/20171203-${RTEMS}/i386-rtems${RTEMS}-trusty-20171203-${RTEMS}.tar.bz2" \
    | tar -C / -xmj

    sed -i -e '/^RTEMS_VERSION/d' -e '/^RTEMS_BASE/d' $EPICS_BASE/configure/os/CONFIG_SITE.Common.RTEMS
    cat << EOF >> $EPICS_BASE/configure/os/CONFIG_SITE.Common.RTEMS
RTEMS_VERSION=$RTEMS
RTEMS_BASE=$HOME/.rtems
EOF
    cat << EOF >> $EPICS_BASE/configure/CONFIG_SITE
CROSS_COMPILER_TARGET_ARCHS += RTEMS-pc386-qemu
EOF
  fi

else
  echo "EPICS Base will not be recompiled - compiler setup already done"
fi

fold_end set.up.compiler

# Build required dependencies
# ---------------------------

fold_start build.dependencies "Rebuild missing dependencies"

for module in ${modules_to_compile}
do
  name=$(basename $module)
  fold_start build.$name "Build $name"
  make -j2 -C $module $EXTRA
  fold_end build.$name
done

fold_end build.dependencies
