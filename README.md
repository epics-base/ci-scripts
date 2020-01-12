<a target="_blank" href="http://semver.org">![Version][badge.version]</a>

# Continuous Integration Scripts for EPICS Modules

The scripts inside this repository are intended to provide a common,
easy-to-use and flexible way to add Continuous Integration to EPICS
software modules, e.g. Device or Driver Support modules.

By including this repository as a Git Submodule, you will be able to
use the same flexible, powerful CI setup that EPICS Bases uses,
including a mechanism to specify sets of dependent modules
(with versions) that you want to compile your module against.

By using the submodule mechnism, your module will always use an
explicit commit, i.e. a fixed version of the scripts.
This ensures that any further development of the ci-scripts will
never break existing use.

## This Repository

In addition to the scripts themselves (in the subdirectories),
this repository contains the test suite that is used to verify
functionality and features of the ci-scripts.

You are welcome to use the test suite as a reference, but keep in
mind that in your module the path to the scripts has one level more
(e.g., `./travis/abc` here would be `./.ci/travis/abc` in your
module).
Also, a test suite might not show the same level of quality as an
example.

## Features

 - Compile against different branches or releases of EPICS Base and
   additional dependencies (modules like asyn, std, etc.).

 - Define settings files that declare sets of dependencies
   with their versions and locations.

 - Define hook scripts for any dependency.
   Hooks are run on the dependency module before it is compiled, so
   the module can be patched or further configured.

 - Define static or shared builds (executables, libraries).

 - Run tests (using the EPICS unit test suite).

## Supported CI Services

### Travis-CI
 - Use different compilers (gcc, clang)
 - Use different gcc versions
 - Cross-compile for Windows 32bit and 64bit using MinGW and WINE
 - Cross-compile for RTEMS 4.9 and 4.10 (Base >= 3.16.2)
 - Compile on MacOS
 - Built dependencies are cached (for faster builds)
 
## How to Use the CI-Scripts

 1. Get an account on a supported CI service provider platform.
    (e.g. [Travis-CI](https://travis-ci.org/),
    Appveyor, Azure Pipelines...)

    (More details in the specific README of the subdirectory.)

 2. In your Support Module, add this ci-scripts respository
    as a Git Submodule (name suggestion: `.ci`).
    ```
    $ git submodule add https://github.com/epics-base/ci-scripts .ci
    ```
 3. Create setup files for different sets of dependencies you
    want to compile against. (See below.)

    E.g., a setup file `stable.set` specifying
    ```
    MODULES=sncseq asyn

    BASE=R3.15.6
    ASYN=R4-34
    SNCSEQ=R2-2-7
    ```
    will compile against the EPICS Base release 3.15.6, the Sequencer
    release 2.2.7 and release 4.34 of asyn.
    (Any settings can be overridden from `.travis.yml`.)

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
Base (37) x StreamDevice (50) x ASYN (40) x Sequencer (51) would produce
more than 3.7 million different combinations, i.e. build jobs.

A more reasonable approach is to create a few setups, each being a
combination of dependency releases, that do a few scans of the available
"version space". One for the oldest versions you want to support, one or two
for stable versions that many of your users have in production, one for the
latest released versions and one for the development branches.

## Setup File Syntax

Setup files are loaded by the bash scripts. They are found by searching
the locations in `SETUP_PATH` (space or colon separated list of directories,
relative to your module's root directory).

Setup files can include other setup files by calling `include <setup>`
(omitting the `.set` extension of the setup file). The configured
`SETUP_PATH` is searched for the include.

Any `VAR=value` setting of a variable is only executed if `VAR` is unset or
empty. That way any settings can be overridden by settings in `.travis.yml`.

Empty lines or lines starting with `#` are ignored.

`MODULES=<list of names>` should list the dependencies (software modules)
by using their well-known slugs, separated by spaces.
EPICS Base (slug: `base`) will always be a dependency and will be added and
compiled first. The other dependencies are added and compiled in the order
they are defined in `MODULES`.

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

Setting `VV=1` in your `.travis.yml` configuration for a specific job
will run the job with high verbosity, printing every command as it is being
executed and switching the dependency builds to higher verbosity.

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
I.e., developments in the ci-scripts repository will never break an\
existing application.
These release numbering considerations are just a hint to assess the
risks when updating the submodule.

## License

This module is distributed subject to a Software License Agreement found
in file LICENSE that is included with this distribution.

<!-- Links -->
[badge.version]: https://badge.fury.io/gh/epics-base%2Fci-scripts.png
