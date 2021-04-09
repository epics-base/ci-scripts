# GitLab CI/CD Scripts for EPICS Modules

## Features

 - Docker-based runners on Linux (one VM instance per job)
 - Can use any Docker image from Dockerhub (the examples use
  `ubuntu:bionic`)
 - Compile natively using different compilers (gcc, clang)
 - Cross-compile for Windows 32bit and 64bit using MinGW and WINE
 - Cross-compile for RTEMS 4.9 and 4.10 (pc386, Base >= 3.15)
 - Cross-compile for RTEMS 5 (10 BSPs, Base >= 7.0.5.1)
 - Built dependencies are cached (for faster builds).

## How to Use these Scripts

 1. Get an account on [GitLab](https://gitlab.com/), create a project
    for your support module and have it mirror your upstream GitHub
    repository. For more details, please refer to the
    [GitLab CI/CD documentation](https://docs.gitlab.com/ee/README.html).
    
    (This applies when using the free tier offered to open source
    projects. Things will be different using an "Enterprise"
    installation on customer hardware.)

 2. Add the ci-scripts respository as a Git Submodule
    (see [README](../README.md) one level above).

 3. Add settings files defining which dependencies in which versions
    you want to build against
    (see [README](../README.md) one level above).

 4. Create a GitLab configuration by copying one of the examples into
    the root directory of your module.
    ```
    $ cp .ci/gitlab/.gitlab-ci.yml.example-full .gitlab-ci.yml
    ```
	
 5. Edit the `.gitlab-ci.yml` configuration to include the jobs you want
    GitLab CI/CD to run.

    Build jobs are declared in the list at the end of the file.
    Each element (starting with the un-indented line) defines the
    settings for one build job. `extends:` specifies a template to use as
    a default structure, `variables:` controls the setting of environment
    variables (overwriting settings from the template).
    Also see the comments in the examples for more hints, and the
    [GitLab CI/CD documentation](https://docs.gitlab.com/ee/README.html)
    for more options and details.
	
 6. Push your changes to GitHub, wait for the synchronization (every 5min)
    and check [GitLab](https://gitlab.com/) for your build results.

## Caches

GitLab is configured to keep the caches separate for different jobs.

However, changing the job description (in the `.gitlab-ci.yml` 
configuration file) or its environment settings or changing a value
inside a setup file will _not_ invalidate the cache - you will
have to manually delete the caches through the GitLab web interface.

Caches are automatically removed after approx. four weeks.
Your jobs will have to rebuild them once in a while.

## Miscellanea

To use the feature to extract `.zip`/`.7z` archives by setting
`*_HOOK` variables, the Linux and MacOS runners need the APT package
`p7zip-full` resp. the Homebrew package `p7zip` installed.
