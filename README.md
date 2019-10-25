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
 - Cross-compile for RTEMS 4.9 and 4.10
 - Compile on MacOS
 - Released versions of dependencies are cached (for faster builds)
 
### How to Use the CI-Scripts

 1. Get an account on a supported CI service provider platform.
    (More details in the specific README of the subdirectory.)

 2. In your Support Module, add this ci-scripts respository
    as a Git Submodule (name suggestion: `.ci`).
    ```
    $ git submodule add https://github.com/epics-base/ci-scripts .ci
    ```
 3. Create settings files for different sets of dependencies you
    want to compile against. E.g., a settings file `foo.set`
    specifying
    ```
    MODULES="sncseq asyn"

    BASE=R3.15.6
    ASYN=master
    SNCSEQ=R2-2-7
    ```
    will compile against the EPICS Base release 3.15.6, the Sequencer
    release 2.2.7 and the latest commit on the `master` branch of asyn.

 4. Create a configuration for the CI service by copying one of
    the examples provided in the service specific subdirectory
    and editing it to include the jobs you want the service to run.
    Use your dependency settings by defining e.g. `SET=foo` in your jobs.
	
 5. Push your changes and check the CI service for your build results.

## Settings File Syntax

Settings files are sourced by the bash scripts. They are found by searching
the locations in `SETUP_PATH` (space or colon separated list of directories,
relative to your module's root directory).

`MODULES="<list of names>"` should list the dependencies (software modules)
by using their well-known slugs, separated by spaces.
EPICS Base (`BASE`) will always be a dependency and will be added and
compiled first. The other dependencies are added and compiled in the order
they are defined in `MODULES`.

`REPOOWNER=<name>` sets the default GitHub owner (or organization) for all
dependency modules. Useful if you want to compile against a complete set
of dependencies forked into your private GitHub area.

For any module mentioned as `foo` in the `MODULES` setting (and for `BASE`),
the following settings can be configured:

`FOO=<version>` Set version of the module that should be used. Must either
be a *tag* name (in that case the module is checked out into Travis' cache
system) or a *branch* name (in that case the module is always checked out
and recompiled as part of the job). [default: `master`]

`FOO_REPONAME=<name>` Set the name of the remote repository as `<name>.git`.
[default is the slug in lower case: `foo`]

`FOO_REPOOWNER=<name>` Set the name of the GitHub owner (or organization)
that the module repository can be found under.

`FOO_REPOURL="<url>"` Set the complete URL of the remote repository.

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
Feel free to suggest more default settings using a Pull Request.

## Release Numbering of this Module

Major release numbers refer to the API, which is more or less defined
by the full configuration examples in the service specific
subdirectories.
If one of these files has to be changed for the existing configuration
options or important new options are being added, a new major release
is created.

Minor release numbers refer to bugfixes that should not require the
configuration inside a user module to be changed.

Again: using the git submodule mechanism to include these scripts means
that user modules always work with a fixed, frozen version.
I.e., developments in the ci-scripts repository will never break an\
existing application.
These release numbering considerations are just a hint to assess the
risks when updating the submodule.
