#!/bin/sh
set -e

# Set VV in .travis.yml to make scripts verbose
[ "$VV" ] && set -x

# Perl version of "readlink -f" (which MacOS does not provide)
readlinkf() { perl -MCwd -e 'print Cwd::abs_path shift' "$1"; }

SETUP_DIRS=$(echo $SETUP_PATH | tr ":" "\n")

SCRIPTDIR=$(dirname $(readlinkf $0))
CURDIR="$PWD"
CACHEDIR="$HOME/.cache"

# source functions
. $SCRIPTDIR/utils.sh

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

fold_start check.out.dependencies "Checking/cloning dependencies"

for mod in BASE $MODULES
do
  mod_uc=$(echo $mod | tr 'a-z' 'A-Z')
  eval add_dependency $mod_uc \${${mod_uc}:-master}
done
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
echo "${ANSI_GREEN}EPICS build system already set up (Base was loaded from cache)${ANSI_RESET}"
fi

# Download RTEMS cross compiler
if [ -n "$RTEMS" ]
then
  echo "Downloading RTEMS${RTEMS} cross compiler for pc386"
  curl -L "https://github.com/mdavidsaver/rsb/releases/download/20171203-${RTEMS}/i386-rtems${RTEMS}-trusty-20171203-${RTEMS}.tar.bz2" \
  | tar -C / -xmj
fi

fold_end set.up.compiler

# Build required dependencies
# ---------------------------

fold_start build.dependencies "Rebuild missing dependencies"

[ "$VV" ] && silent="-s" || silent=

for module in ${modules_to_compile}
do
  name=$(basename $module)
  fold_start build.$name "Build $name"
  make -j2 $silent -C $module $EXTRA
  fold_end build.$name
done

fold_end build.dependencies
