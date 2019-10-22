# Continuous Integration Scripts for EPICS Modules

The scripts in this repository are intended to provide a common,
easy-to-use and flexible way to add Continuous Integration to EPICS
software modules, e.g. Device Support modules.

By including this repository as a Git Submodule, your module will
always use an explicit commit, i.e. a fixed version of the scripts.
That ensures that further development of these scripts cannot break
your setup.

## Travis-CI

### Features

 -  Compile against different branches or releases of EPICS Base
 -  Use different versions of compilers (gcc, clang)
 -  Cross-compile for Windows 32bit and 64bit using MinGW and WINE
 -  Cross-compile for RTEMS 4.9 and 4.10
 -  Compile on MacOS
 
### How to Use these Scripts

 1. Get an account on [Travis-CI](https://travis-ci.org/), connect
    it to your GitHub account and activate your support module's
    repository. For more details, please refer to the
    [Travis-CI Tutorial](https://docs.travis-ci.com/user/tutorial/).
    Make sure to use `travis-ci.org` and not their `.com` site.

 1. In your Support Module, add this respository as a Git Submodule
    (name suggestion: `.ci`).
    ```
    $ git submodule add https://github.com/epics-base/ci-scripts .ci
    ```
	
 1. Create a Travis configuration by copying one of the examples.
    ```
    $ cp .ci/.travis.yml.example-full .travis.yml
    ```
	
 1. Edit the `.travis.yml` configuration to include the jobs you want
    Travis to run.
	
 1. Push your changes and check 
    [travis-ci.org](https://travis-ci.org/) for your build results.

## Releases and Numbering

Major release numbers refer to the API, which is more or less defined
by the `.travis.yml.example-full` configuration example.
Changing this file for the existing configuration options or to add
new configurations options will usually cause a new major release.

Minor release numbers refer to bugfixes that should not require a user
module (i.e., its `.travis.yml`) to be changed.

Again: using git submodule to include these scripts means that user
modules always work with a fixed, frozen version of these scripts.
I.e., developments in the ci-scripts will never break an existing
application.
These release numbering considerations are just a hint to assess the
risk when updating the submodule.
