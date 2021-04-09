# Travis-CI Scripts for EPICS Modules

## Features

 - Two parallel runners on Linux/Windows (two runners on MacOS)
 - Ubuntu 14/16/18/20, MacOS 10.13/14/15, Windows Server v1809
 - Use different compilers (gcc, clang)
 - Use different gcc versions
 - Cross-compile for Windows 32bit and 64bit using MinGW and WINE
 - Cross-compile for RTEMS 4.9 and 4.10 (pc386, Base >= 3.15)
 - Cross-compile for RTEMS 5 (10 BSPs, Base >= 7.0.5.1)
 - Compile natively on MacOS (clang)
 - Compile natively on Windows (gcc/MinGW, Visual Studio 2017)
 - Built dependencies are cached (for faster builds).

## How to Use these Scripts

 1. Get an account on [Travis-CI](https://travis-ci.org/), connect
    it to your GitHub account and activate your support module's
    repository. For more details, please refer to the
    [Travis-CI Tutorial](https://docs.travis-ci.com/user/tutorial/).
    Make sure to use `travis-ci.org` and not their `.com` site.
    
    (This applies when using the free tier offered to open source
    projects. Things will be different using an "Enterprise"
    installation on customer hardware.)

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
    Travis to run.

    Build jobs are declared in the list following the `jobs: include:`
    declaration. Each element (starting with a dash) defines the
    settings for one build job. `env:` controls the setting of environment
    variables,`dist:` specifies the Linux distribution,
    `os:` the operating system.
    Also see the comments in the examples for more hints, and the Travis-CI
    documentation for more options and more details.
	
 6. Push your changes and check
    [travis-ci.org](https://travis-ci.org/) for your build results.

## Caches

Travis keeps the caches separate for different jobs. As soon as the job
description (in the `.travis.yml` configuration file) or its environment
settings change (adding a space character is enough), the cache is different
and will be rebuilt when the job runs.

This also means that changing a value inside a setup file will _not_
invalidate the cache - in that case you will have to manually delete the cache
through the Travis web interface. (Or add a space character in the job
configuration.)

Caches are automatically removed after approx. four weeks.
Your jobs will have to rebuild them once in a while.

## Miscellanea

To use the feature to extract `.zip`/`.7z` archives by setting
`*_HOOK` variables, the Linux and MacOS runners need the APT package
`p7zip-full` resp. the Homebrew package `p7zip` installed.
