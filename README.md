<a target="_blank" href="http://semver.org">![Version][badge.version]</a>
<a target="_blank" href="https://travis-ci.org/epics-base/ci-scripts">![Travis status][badge.travis]</a>
<a target="_blank" href="https://ci.appveyor.com/project/epics-base/ci-scripts">![AppVeyor status][badge.appveyor]</a>
<a target="_blank" href="https://github.com/epics-base/ci-scripts/actions">![GitHub Actions status][badge.gh-actions]</a>
<a target="_blank" href="https://gitlab.com/epics-base/ci-scripts/-/pipelines">![GitLab CI/CD status][badge.gitlab]</a>

# Continuous Integration for EPICS Modules

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
never break your existing use.

## This Repository

In addition to the script that runs the builds and tests, this repository
contains service specific documentation and example configuration files
(in the subdirectories), and a small test suite that is used to verify
functionality and features of the ci-scripts module itself

The example files are your best reference. They are kept up-to-date and
show a fully-featured and a minimal setup.

You are welcome to use the test suite as a secondary reference, but keep in
mind that in your main module the path to the scripts has one level more
(e.g., `./abc` here would be `./.ci/abc` in your
module).
Also, the test suite does not show the same quality and documentation
levels as the example files.

## Features

 - Compile against different branches or releases of EPICS Base and
   additional dependencies (modules like asyn, std, sequencer, etc.).

 - Define setup files that declare sets of dependencies with their
   versions and locations.

 - Define hooks for any dependency.
   Hooks are run on the dependency module before it is compiled, so
   the module can be patched or further configured.

 - Define shared (default) or static builds (for executables and libraries).
 
 - Define optimized (default) or debug builds.

 - Run tests (using the EPICS build system, i.e., `make runtests`
   and friends).

## Supported CI Services

The listed properties and instructions for the CI services apply to
their free tiers for open source projects, hosted in the cloud on
their infrastructure.

The companies behind these services also offer "enterprise" installations
on customer infrastructure, which will have different performance
and limitations.

### [Travis-CI](https://travis-ci.org/)
 - Five parallel runners on Linux/Windows (one runner on MacOS)
 - Ubuntu 12/14/16/18, MacOS 10.13, Windows Server v1809
 - Compile natively on Linux (different versions of gcc, clang)
 - Compile natively on MacOS (clang)
 - Compile natively on Windows (gcc/MinGW, Visual Studio 2017)
 - Cross-compile for Windows 32bit and 64bit using MinGW and WINE
 - Cross-compile for RTEMS 4.9 and 4.10 (Base >= 3.15)
 - Built dependencies are cached (for faster builds).
 
See specific
**[ci-scripts on Travis-CI README](travis/README.md)**
for more details.

### [AppVeyor](https://www.appveyor.com/)
 - One parallel runner (all builds are sequential)
 - Windows Server 2012/2016/2019
 - Compile using gcc/MinGW or different Visual Studio versions: \
   2008, 2010, 2012, 2013, 2015, 2017, 2019
 - Compile for Windows 32bit and 64bit
 - No useful caching available.

See specific
**[ci-scripts on AppVeyor README](appveyor/README.md)**
for more details.

### [GitHub Actions](https://github.com/)
 - 20 parallel runners on Linux/Windows (5 runners on MacOS)
 - Ubuntu 16/18/20, MacOS 10.15, Windows Server 2016/2019
 - Compile natively on Linux (gcc, clang)
 - Compile natively on MacOS (clang)
 - Compile natively on Windows (gcc/MinGW, Visual Studio 2017 & 2019)
 - Cross-compile for Windows 32bit and 64bit using MinGW and WINE
 - Cross-compile for RTEMS 4.9 and 4.10 (Base >= 3.15)
 - Caching not supported by ci-scripts yet.

See specific
**[ci-scripts on GitHub Actions README](github-actions/README.md)**
for more details.

### [GitLab CI/CD](https://gitlab.com/)

 - Docker-based runners on Linux (one VM instance per job)
 - Can use any Docker image from Dockerhub (the examples use
  `ubuntu:bionic`)
 - Compile natively using different compilers (gcc, clang)
 - Cross-compile for Windows 32bit and 64bit using MinGW and WINE
 - Cross-compile for RTEMS 4.9 and 4.10 (Base >= 3.15)
 - Built dependencies are cached (for faster builds).

See specific
**[ci-scripts on GitLab CI/CD README](gitlab/README.md)**
for more details.

## How to Use the CI-Scripts

 1. Get an account on a supported CI service provider platform
    (e.g. [Travis-CI](https://travis-ci.org/),
    [AppVeyor](https://www.appveyor.com/), ...).
    GitHub Actions does not require a separate account.

    (More details in the specific README of the subdirectory.)

 2. In your module, add this ci-scripts repository
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

## Calling the cue.py Script

Independent from CI service and platform, the runner script is called
from your main configuration as:

`python .ci/cue.py <action>`

where `<action>` is one of:

`prepare`\
Prepare the build by cloning Base and the configured dependency modules,
set up the EPICS build system, then
compile Base and these modules in the order they appear in the `MODULES`
setting.

`build`\
Build your main module.

`test`\
Run the tests of your main module.

`test-results`\
Collect the results of your tests and print a summary.

`exec`\
Execute the remainder of the line using the default command shell.

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

A job uses a setup file if `SET=<setup>` (without the `.set` extension
of the setup file) is set for the job in the main configuration file.

## Setup File Syntax

Setup files are loaded by the build script. They are found by searching
the locations in `SETUP_PATH` (space or colon separated list of directories,
relative to your module's root directory).

Setup files can include other setup files by calling `include <setup>`
(again omitting the `.set` extension of the setup file). The configured
`SETUP_PATH` is searched for the include.

Any `VAR=value` setting of a variable in a setup file is only executed if
`VAR` is unset or empty.
That way any settings can be overridden by setting them in the job
description inside the main configuration file (e.g., `.travis.yml`).

Empty lines or lines starting with `#` are ignored.

`MODULES=<list of names>` should list the dependencies (software modules)
by using their well-known slugs, separated by spaces.
EPICS Base (slug: `base`) will always be a dependency and will be added and
compiled first. The other dependencies are added and compiled in the order
they are defined in `MODULES`.

Modules needed only for specific jobs (e.g., on specific architectures)
can be added from the main configuration file by setting `ADD_MODULES`
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

`FOO_HOOK=<hook>` Set the name of a `.patch` file, a `.zip` or `.7z` archive
or a script that will be applied (using `-p1`), extracted or run after cloning
the module, before compiling it.
Working directory is the root of the targeted module,
e.g., `.../.cache/foo-1.2`). [default: no hook]

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

Set `PARALLEL_MAKE` to the number of parallel make jobs that you want your
build to use. [default is the number of CPUs on the runner]

Set `CLEAN_DEPS` to `NO` if you want to leave the object file directories
(`**/O.*`) in the cached dependencies. [default is to run `make clean`
after building a dependency]

Service specific options are described in the README files
in the service specific subdirectories:

- [Travis-CI README](travis/README.md)
- [AppVeyor README](appveyor/README.md)

## References: EPICS Modules Using ci-scripts

[EPICS Base](https://github.com/epics-base/epics-base) and its submodules
[pvData](https://github.com/epics-base/pvDataCPP),
[pvAccess](https://github.com/epics-base/pvAccessCPP),
[pva2pva](https://github.com/epics-base/pva2pva),
[PVXS](https://github.com/mdavidsaver/pvxs)

EPICS Modules:
[ASYN](https://github.com/epics-modules/asyn),
[autosave](https://github.com/epics-modules/autosave),
[busy](https://github.com/epics-modules/busy),
[devlib2](https://github.com/epics-modules/devlib2),
[ecmc](https://github.com/epics-modules/ecmc),
[gtest](https://github.com/epics-modules/gtest),
[ip](https://github.com/epics-modules/ip),
[lua](https://github.com/epics-modules/lua),
[MCoreUtils](https://github.com/epics-modules/MCoreUtils),
[modbus](https://github.com/epics-modules/modbus),
[motor](https://github.com/epics-modules/motor),
[mrfioc2](https://github.com/epics-modules/mrfioc2),
[OPCUA](https://github.com/ralphlange/opcua),
[PCAS](https://github.com/epics-modules/pcas),
[softGlueZync](https://github.com/epics-modules/softGlueZynq),
[sscan](https://github.com/epics-modules/sscan),
[std](https://github.com/epics-modules/std),
[vac](https://github.com/epics-modules/vac),
[xxx](https://github.com/epics-modules/xxx)

ESS: [EtherCAT MC Motor Driver][ref.ethercatmc]

## Migration Hints

Look for changes in the example configuration files, and check how they
apply to your module.

If comments in the example have changed, copy them to your configuration
to always have up-to-date documentation in your file.

### 2.x to 3.x Migration

Update the script and test settings in your configuration to call the
new script, following the example file.

`python .ci/cue.py <action>`

#### AppVeyor

The `configuration:` setting options have changed; they are now
`default`, `static`, `debug` and `static-debug`.

MinGW builds are now using the `CMP: gcc` compiler setting.

Adding arguments to make is supported through the `EXTRA` .. `EXTRA5`
variables. Each variable value will be passed as one argument.

#### Travis

The new `BCFG` (build configuration) variable accepts the same options as
the AppVeyor `configuration:` setting. Replace any`STATIC=YES` settings with
`BCFG=static`.

Remove `bash` in the `homebrew:` section of `addons:`. There are no more
bash scripts.

MinGW builds (cross-builds using WINE as well as native builds on Windows)
are now using the `gcc` compiler setting.
Since `gcc` is the default, you can simply remove `compiler: mingw` lines.

For Windows, Travis offers native MinGW and Visual Studio 2017 compilers.
Use `os: windows` and set `compiler:` to `gcc` or `vs2017`
 for those builds.

Chocolatey packages to be installed for the Windows jobs are set by adding
them to the environment variable `CHOCO`.

## Frequently Asked Questions

##### How can I see what the dependency building jobs are actually doing?

Set `VV=1` in the configuration line of the job you are interested in.
This will make all builds (not just for your module) verbose.

##### How do I update my module to use a newer minor release of ci-scripts?

Update the submodule in `.ci` first, then change your CI configuration
(if needed) and commit both to your module. E.g., to update your Travis
setup to release 3.2.0 of ci-scripts:
```bash
cd .ci
git pull origin v3.2.0
cd -
git add .ci
  # if needed:
  edit .travis.yml     # and/or other CI service configurations
  git add .travis.yml
git commit -m "Update ci-scripts submodule to v3.2.0"
```

Check the example configuration files inside ci-scripts (and their
changes) to see what might be needed and/or interesting to change
in your configuration.

Depending on the changes contained in the ci-scripts update, it might
be advisable to clear the CI caches after updating ci-scripts. E.g.,
a change in setting up EPICS Base will not be applied if Base is found 
in the cache.

##### How do I add a dependency module only for a specific job?

Add the additional dependency in the main configuration file by setting
`ADD_MODULES` for the specific job(s).

##### Why the name _cue_?

The noun _cue_ is defined as "_a signal (such as a word, phrase, or bit of
stage business) to a performer to begin a specific speech or action_".
(Merriam-Webster)

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
(Unless for using a new feature.)

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
[badge.gh-actions]: https://github.com/epics-base/ci-scripts/workflows/ci-scripts%20build/test/badge.svg
[badge.gitlab]: https://gitlab.com/epics-base/ci-scripts/badges/master/pipeline.svg

[reddit.bash]: https://www.reddit.com/r/bash/comments/393oqv/why_is_the_version_of_bash_included_in_os_x_so_old/

[ref.ethercatmc]: https://github.com/EuropeanSpallationSource/m-epics-ethercatmc
