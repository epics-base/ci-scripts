#!/bin/sh
set -e -x

CURDIR="$PWD"

# determine if BASE is a release or a branch
git ls-remote --quiet --exit-code --tags https://github.com/${REPOBASE:-epics-base}/epics-base.git "$BASE" && BASE_RELEASE=YES
git ls-remote --quiet --exit-code --heads https://github.com/${REPOBASE:-epics-base}/epics-base.git "$BASE" && BASE_BRANCH=YES

if [ "$BASE_RELEASE" = "YES" ]
then
  # TODO: use a cached location
  BASE_LOCATION=$HOME/.source/epics-base
else
  if [ "$BASE_BRANCH" = "YES" ]
  then
  BASE_LOCATION=$HOME/.source/epics-base
  else
  echo $BASE is neither a tag nor a branch name for BASE
  exit 1
  fi
fi

cat << EOF > $CURDIR/configure/RELEASE.local
EPICS_BASE=$BASE_LOCATION
EOF

install -d "$HOME/.source"
cd "$HOME/.source"

add_gh_flat() {
  MODULE=$1
  REPOOWNER=$2
  REPONAME=$3
  BRANCH=$4
  MODULE_UC=$5
  ( git clone --quiet --depth 5 --branch $BRANCH https://github.com/$REPOOWNER/$REPONAME.git $MODULE && \
  cd $MODULE && git log -n1 )
  cat < $CURDIR/configure/RELEASE.local > $MODULE/configure/RELEASE.local
  cat << EOF >> $CURDIR/configure/RELEASE.local
${MODULE_UC}=$HOME/.source/$MODULE
EOF
}

# not recursive
git clone --quiet --depth 5 --branch "$BASE" https://github.com/${REPOBASE:-epics-base}/epics-base.git epics-base
(cd epics-base && git log -n1 )
for modrepo in ${MODULES}
do
  module=${modrepo%CPP}
  module_uc=$(echo $module | tr 'a-z' 'A-Z')
  eval add_gh_flat $module \${REPO${module_uc}:-epics-base} $modrepo \${BR${module_uc}:-master} $module_uc
done

if [ -e $CURDIR/configure/RELEASE.local ]
then
  cat $CURDIR/configure/RELEASE.local
fi

[ "$EPICS_HOST_ARCH" ] || EPICS_HOST_ARCH=`sh epics-base/startup/EpicsHostArch`

# requires wine and g++-mingw-w64-i686
if [ "$WINE" = "32" ]
then
  echo "Cross mingw32"
  sed -i -e '/CMPLR_PREFIX/d' epics-base/configure/os/CONFIG_SITE.linux-x86.win32-x86-mingw
  cat << EOF >> epics-base/configure/os/CONFIG_SITE.linux-x86.win32-x86-mingw
CMPLR_PREFIX=i686-w64-mingw32-
EOF
  cat << EOF >> epics-base/configure/CONFIG_SITE
CROSS_COMPILER_TARGET_ARCHS+=win32-x86-mingw
EOF

elif [ "$WINE" = "64" ]
then
  echo "Cross mingw64"
  sed -i -e '/CMPLR_PREFIX/d' epics-base/configure/os/CONFIG_SITE.linux-x86.windows-x64-mingw
  cat << EOF >> epics-base/configure/os/CONFIG_SITE.linux-x86.windows-x64-mingw
CMPLR_PREFIX=x86_64-w64-mingw32-
EOF
  cat << EOF >> epics-base/configure/CONFIG_SITE
CROSS_COMPILER_TARGET_ARCHS+=windows-x64-mingw
EOF
fi

if [ "$STATIC" = "YES" ]
then
  echo "Build static libraries/executables"
  cat << EOF >> epics-base/configure/CONFIG_SITE
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
  cat << EOF >> epics-base/configure/os/CONFIG_SITE.Common.$EPICS_HOST_ARCH
GNU         = NO
CMPLR_CLASS = clang
CC          = ${HOST_CCMPLR_NAME}$HOST_CMPLR_VER_SUFFIX
CCC         = ${HOST_CPPCMPLR_NAME}$HOST_CMPLR_VER_SUFFIX
EOF

  # hack
  sed -i -e 's/CMPLR_CLASS = gcc/CMPLR_CLASS = clang/' epics-base/configure/CONFIG.gnuCommon

  ${HOST_CCMPLR_NAME}$HOST_CMPLR_VER_SUFFIX --version
  ;;
gcc)
  echo "Host compiler is GCC"
  HOST_CPPCMPLR_NAME=$(echo "$HOST_CCMPLR_NAME" | sed 's/gcc/g++/g')
  cat << EOF >> epics-base/configure/os/CONFIG_SITE.Common.$EPICS_HOST_ARCH
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

cat <<EOF >> epics-base/configure/CONFIG_SITE
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

  sed -i -e '/^RTEMS_VERSION/d' -e '/^RTEMS_BASE/d' epics-base/configure/os/CONFIG_SITE.Common.RTEMS
  cat << EOF >> epics-base/configure/os/CONFIG_SITE.Common.RTEMS
RTEMS_VERSION=$RTEMS
RTEMS_BASE=$HOME/.rtems
EOF
  cat << EOF >> epics-base/configure/CONFIG_SITE
CROSS_COMPILER_TARGET_ARCHS += RTEMS-pc386-qemu
EOF
fi

for modrepo in epics-base ${MODULES}
do
  module=${modrepo%CPP}
  make -j2 -C $module $EXTRA
done
