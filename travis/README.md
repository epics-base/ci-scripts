# Travis-CI Scripts for EPICS Modules

## Features

 -  Compile against different branches or releases of EPICS Base
 -  Use different versions of compilers (gcc, clang)
 -  Cross-compile for Windows 32bit using MinGW and WINE
 -  Cross-compile for RTEMS 4.9 and 4.10
 -  Compile on MacOS
 
## How to Use these Scripts

 1. Get an account on [Travis-CI](https://travis-ci.org/), connect
    it to your GitHub account and activate your support module's
    repository. For more details, please refer to the
    [Travis-CI Tutorial](https://docs.travis-ci.com/user/tutorial/).
    Make sure to use `travis-ci.org` and not their `.com` site.

 2. In your Support Module, add this respository as a Git Submodule
    (name suggestion: `.ci`).
    ```
    $ git submodule add https://github.com/epics-base/ci-scripts .ci
    ```
	
 3. Create a Travis configuration by copying one of the examples into
    the root directory of your module.
    ```
    $ cp .ci/travis/.travis.yml.example-full .travis.yml
    ```
	
 4. Edit the `.travis.yml` configuration to include the jobs you want
    Travis to run.
	
 5. Push your changes and check
    [travis-ci.org](https://travis-ci.org/) for your build results.
