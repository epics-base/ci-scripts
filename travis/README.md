# Travis-CI Scripts for EPICS Modules

## Features

 - Use different compilers (gcc, clang)
 - Use different gcc versions
 - Cross-compile for Windows 32bit and 64bit using MinGW and WINE
 - Cross-compile for RTEMS 4.9 and 4.10
 - Compile on MacOS
 - Released versions of dependencies are cached (for faster builds)

## How to Use these Scripts

 1. Get an account on [Travis-CI](https://travis-ci.org/), connect
    it to your GitHub account and activate your support module's
    repository. For more details, please refer to the
    [Travis-CI Tutorial](https://docs.travis-ci.com/user/tutorial/).
    Make sure to use `travis-ci.org` and not their `.com` site.

 2. Add the ci-scripts respository as a Git Submodule
    (see [README](../README.md) one level above).

 3. Add settings files defining which dependencies in which versions
    you want to build against
    (see [README](../README.md) one level above).

 4. Create a Travis configuration by copying one of the examples into
    the root directory of your module.
    ```
    $ cp .ci/travis/.travis.yml.example-full .travis.yml
    ```
	
 5. Edit the `.travis.yml` configuration to include the jobs you want
    Travis to run. (The examples are commented.)
	
 6. Push your changes and check
    [travis-ci.org](https://travis-ci.org/) for your build results.
