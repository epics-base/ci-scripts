<a target="_blank" href="http://semver.org">![Version][badge.version]</a>
<a target="_blank" href="https://travis-ci.org/epics-base/ci-scripts">![Travis status][badge.travis]</a>
<a target="_blank" href="https://ci.appveyor.com/project/epics-base/ci-scripts">![AppVeyor status][badge.appveyor]</a>

# Continuous Integration Scripts for EPICS Modules

The scripts inside this repository are intended to provide a common,
easy-to-use and flexible way to add Continuous Integration to EPICS
software modules, e.g. Device or Driver Support modules.

By including this repository as a Git Submodule, you will be able to
use the same flexible, powerful CI setup that EPICS Bases uses,
including a way to specify sets of dependent modules
(with versions) that you want to compile your module against.

By using the submodule mechanism, your module will always use an
explicit commit, i.e. a fixed version of the scripts.
This ensures that any further development of the ci-scripts will
never break existing use.

## This Repository

In addition to the script that runs the builds and tests, this repository
contains service specific documentation and example configuration files
(in the subdirectories), and a small test suite that is used to verify
functionality and features of the ci-scripts module itself

You are welcome to use the test suite as a reference, but keep in
mind that in your main module the path to the scripts has one level more
(e.g., `./abc` here would be `./.ci/abc` in your
module).
Also, a test suite might not show the same quality and documentation levels
as an example.

## Features

 - Compile against different branches or releases of EPICS Base and
   additional dependencies (modules like asyn, std, sequencer, etc.).

 - Define settings files that declare sets of dependencies
   with their versions and locations.

 - Define hooks for any dependency.
   Hooks are run on the dependency module before it is compiled, so
   the module can be patched or further configured.

 - Define shared (default) or static builds (for executables and libraries).
 
 - Define optimized (default) or debug builds.

 - Run tests (using the EPICS build system, i.e., `make runtests`
   and friends).

## Supported CI Services

### [Travis-CI](https://travis-ci.org/)
 - Five parallel runners on Linux/Windows (one runner on MacOS)
 - Use different compilers (gcc, clang)
 - Use different gcc versions
 - Cross-compile for Windows 32bit and 64bit using MinGW and WINE
 - Cross-compile for RTEMS 4.9 and 4.10 (Base >= 3.15)
 - Compile natively on MacOS (clang)
 - Compile natively on Windows (gcc/MinGW, Visual Studio 2017)
 - Built dependencies are cached (for faster builds).
 
See specific
**[ci-scripts on Travis-CI README](travis/README.md)**
for more details.

### [AppVeyor](https://www.appveyor.com/)
 - One parallel runner (all builds are sequential)
 - Use different compilers (Visual Studio, gcc/MinGW)
 - Use different Visual Studio versions: \
   2008, 2010, 2012, 2013, 2015, 2017, 2019
 - Compile for Windows 32bit and 64bit
 - No useful caching available.

See specific
**[ci-scripts on AppVeyor README](appveyor/README.md)**
for more details.

## How to Use the CI-Scripts

 1. Get an account on a supported CI service provider platform.
    (e.g. [Travis-CI](https://travis-ci.org/),
    [AppVeyor](https://www.appveyor.com/), ...)

    (More details in the specific README of the subdirectory.)

 2. In your Support Module, add this ci-scripts repository
    as a Git Submodule (name suggestion: `.ci`).
    ```bash
    git submodule add https://github.com/epics-base/ci-scripts .ci
    ```

 3. Create setup files for different sets of dependencies you
    want to compile against. (See below.)

    E.g., a setup file `stable.set` specifying
    ```
    MODULES=sncseq asyn

    BASE=3.15
    ASYN=R4-34
    SNCSEQ=R2-2-8
    ```
    will compile against the EPICS Base 3.15 branch, the Sequencer
    release 2.2.8 and release 4.34 of asyn.
    (Any settings can be overridden from the specific job line
    in the service configuration, e.g., `.travis.yml`.)

 4. Create a configuration for the CI service by copying one of
    the examples provided in the service specific subdirectory
    and editing it to include the jobs you want the service to run.
    Use your setup by defining e.g. `SET=stable` in the environment of
    a job.

 5. Push your changes and check the CI service for your build results.

## Setup Files

Your module might depend on EPICS Base and a few other support modules.
(E.g., a specific driver might need StreamDevice, ASYN and the Sequencer.)
In that case, building against every possible combination of released
versions of those dependencies is not possible:
Base (39) x StreamDevice (50) x ASYN (40) x Sequencer (52) would produce
more than 4 million different combinations, i.e. build jobs.

A more reasonable approach is to create a few setups, each being a
combination of dependency releases, that do a few scans of the available
"version space". One for the oldest versions you want to support, one or two
for stable versions that many of your users have in production, one for the
latest released versions and one for the development branches.

## Setup File Syntax

Setup files are loaded by the build scripts. They are found by searching
the locations in `SETUP_PATH` (space or colon separated list of directories,
relative to your module's root directory).

Setup files can include other setup files by calling `include <setup>`
(omitting the `.set` extension of the setup file). The configured
`SETUP_PATH` is searched for the include.

Any `VAR=value` setting of a variable is only executed if `VAR` is unset or
empty. That way any settings can be overridden by settings in the main
configuration (e.g., `.travis.yml`).

Empty lines or lines starting with `#` are ignored.

`MODULES=<list of names>` should list the dependencies (software modules)
by using their well-known slugs, separated by spaces.
EPICS Base (slug: `base`) will always be a dependency and will be added and
compiled first. The other dependencies are added and compiled in the order
they are defined in `MODULES`.
Modules needed only for specific jobs (e.g., on specific architectures)
can be added in the main configuration file by setting `ADD_MODULES`
for the specific job(s).

`REPOOWNER=<name>` sets the default GitHub owner (or organization) for all
dependency modules. Useful if you want to compile against a complete set
of dependencies forked into your private GitHub area.

For any module mentioned as `foo` in the `MODULES` setting (and for `BASE`),
the following settings can be configured:

`FOO=<version>` Set version of the module that should be used. Must either
be a *tag* name or a *branch* name. [default: `master`]

`FOO_REPONAME=<name>` Set the name of the remote repository as `<name>.git`.
[default is the slug in lower case: `foo`]

`FOO_REPOOWNER=<name>` Set the name of the GitHub owner (or organization)
that the module repository can be found under.

`FOO_REPOURL="<url>"` Set the complete URL of the remote repository. Useful
for dependencies that are not hosted on GitHub.

The default URL for the repository is pointing to GitHub, under
`$FOO_REPOOWNER` else `$REPOOWNER` else `epics-modules`,
using `$FOO_REPONAME` else `foo` and the extension`.git`.

`FOO_DEPTH=<number>` Set the depth of the git clone operation. Use 0 for a
full clone. [default: 5]

`FOO_RECURSIVE=YES/NO` Set to `NO` (or `0`) for a flat clone without
recursing into submodules. [default is including submodules: `YES`]

`FOO_DIRNAME=<name>` Set the local directory name for the checkout. This will
be always be extended by the release or branch name as `<name>-<version>`.
[default is the slug in lower case: `foo`]

`FOO_HOOK=<script>` Set the name of a script that will be run after cloning
the module, before compiling it. Working directory when running the script
is the root of the targeted module (e.g. `.../.cache/foo-1.2`).
[default: no hooks are run]

`FOO_VARNAME=<name>` Set the name that is used for the module when creating
the `RELEASE.local` files. [default is the slug in upper case: `FOO`]

The ci-scripts module contains default settings for widely used modules, so
that usually it is sufficient to set `FOO=<version>`.
You can find the list of supported (and tested) modules in `defaults.set`.
Feel free to suggest more default settings using a Pull Request.

## Debugging

Setting `VV=1` in your service configuration (e.g., `.travis.yml`) for a
specific job will run the job with high verbosity,
printing every command as it is being executed and switching the dependency
builds to higher verbosity.

For debugging on your local machine, you may set `CACHEDIR` to change the 
location for the dependency builds. [default is `$HOME/.cache`]

Service specific debugging options are described in the README files
in the service specific subdirectories:

- [Travis-CI README](travis/README.md)
- [AppVeyor README](appveyor/README.md)


## References: EPICS Modules Using ci-scripts

[EPICS Base](https://github.com/epics-base/epics-base) and its submodules
[pvData](https://github.com/epics-base/pvDataCPP),
[pvAccess](https://github.com/epics-base/pvAccessCPP),
[pva2pva](https://github.com/epics-base/pva2pva)

EPICS Modules:
[ASYN](https://github.com/epics-modules/asyn),
[devlib2](https://github.com/epics-modules/devlib2),
[ecmc](https://github.com/epics-modules/ecmc),
[ip](https://github.com/epics-modules/ip),
[lua](https://github.com/epics-modules/lua),
[MCoreUtils](https://github.com/epics-modules/MCoreUtils),
[modbus](https://github.com/epics-modules/modbus),
[motor](https://github.com/epics-modules/motor),
[PCAS](https://github.com/epics-modules/pcas),
[sscan](https://github.com/epics-modules/sscan),
[vac](https://github.com/epics-modules/vac)

ESS: [EtherCAT MC Motor Driver][ref.ethercatmc]

ITER: [OPC UA Device Support](https://github.com/ralphlange/opcua)

## Frequently Asked Questions

**How can I see what the dependency building jobs are actually doing?**

Set `VV=1` in the configuration line of the job you are interested in.
This will make all builds (not just for your module) verbose.

**How do I update my module to use a newer release of ci-scripts?**

Update the submodule in `.ci` first, then change your CI configuration
(if needed) and commit both to your module. E.g., to update your Travis
setup to release 2.3.5 of ci-scripts:
```bash
cd .ci
git pull origin v2.3.5
cd -
git add .ci
  # if needed:
  edit .travis.yml
  git add .travis.yml
git commit -m "Update ci-scripts submodule to v2.3.5"
```

Check the example configuration files inside ci-scripts (and their
changes) to see what might be needed and/or interesting to change
in your configuration.

Depending on the changes contained in the ci-scripts update, it might
be advisable to clear the CI caches after updating ci-scripts. E.g.,
a change in setting up EPICS Base will not be applied if Base is found 
in the cache.

**Why does running the scripts locally on my MacOS machine fail?**

The ci-scripts for Travis-CI require Bash version 4.
As Apple ships an older Bash for [political reasons][reddit.bash],
you need to install a more recent Bash, e.g. using MacPorts
or Homebrew.

## Release Numbering of this Module

The module tries to apply [Semantic Versioning](https://semver.org/).

Major release numbers refer to the API, which is more or less defined
by the full configuration examples in the service specific
subdirectories.
If one of these files has to be changed for the existing configuration
options or important new options are being added, a new major release
is created.

Minor release numbers refer to additions and enhancements that do not
require the configuration inside an existing user module to be changed.

Again: using the git submodule mechanism to include these scripts means
that user modules always work with a fixed, frozen version.
I.e., developments in the ci-scripts repository will never break an
existing application.
These release numbering considerations are just a hint to assess the
risks when updating the submodule.

## License

This module is distributed subject to a Software License Agreement found
in file LICENSE that is included with this distribution.

<!-- Links -->
[badge.version]: https://badge.fury.io/gh/epics-base%2Fci-scripts.svg
[badge.travis]: https://travis-ci.org/epics-base/ci-scripts.svg?branch=master
[badge.appveyor]: https://ci.appveyor.com/api/projects/status/8b578alg974axvux?svg=true

[reddit.bash]: https://www.reddit.com/r/bash/comments/393oqv/why_is_the_version_of_bash_included_in_os_x_so_old/

[ref.ethercatmc]: https://github.com/EuropeanSpallationSource/m-epics-ethercatmc
