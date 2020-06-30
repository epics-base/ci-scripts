# GitHub Actions Scripts for EPICS Modules

## Features

 - 20 parallel runners on Linux/Windows (5 runners on MacOS)
 - Ubuntu 16/18/20, MacOS 10.15, Windows Server 2016/2019
 - Compile natively on Linux (gcc, clang)
 - Compile natively on MacOS (clang)
 - Compile natively on Windows (gcc/MinGW, Visual Studio 2017 & 2019)
 - Cross-compile for Windows 32bit and 64bit using MinGW and WINE
 - Cross-compile for RTEMS 4.9 and 4.10 (Base >= 3.15)
 - Caching not supported yet.

## How to Use these Scripts

 1. Add the ci-scripts respository as a Git Submodule
    (see [README](../README.md) one level above).

 2. Add settings files defining which dependencies in which versions
    you want to build against
    (see [README](../README.md) one level above).

 3. Create a GitHub Actions configuration by copying one of the workflow 
    examples into the directory `.github/workflows` of your module.
    ```bash
    $ mkdir -p .github/workflows
    $ cp .ci/github-actions/ci-scripts-build.yml.example-full .github/workflows/ci-scripts-build.yml
    ```
	
 4. Edit the workflow configuration to include the build jobs you want
    GitHub Actions to run.

    Build jobs are specified in the `jobs: <job-name>: strategy:`
    declaration. The `matrix:` element specifies the axes as configuration
    parameters with their lists of values,
    `env:` (on the build level) controls the setting of environment variables
    (which can be matrix parameters).
    The `runs-on:` setting specifies the image (operating system) of the
    runner.
    The `name:` is what shows up in the web interface for the workflow,
    builds and jobs, and the elements under `steps:` describe the actions
    executed for each job of the matrix.

    Please check the comments in the examples for more hints, and the 
    [GitHub Actions documentation](https://help.github.com/en/actions)
    for a lot more options and details.

 5. Push your changes and click on the `Actions` tab of your GitHub repository
    page to see your build results.

## Specifics

#### Quote Environment Variable Values

Variable settings distinguish between numerical and string values.
Better quote all branch and tag names. E.g.,
```yaml
env:
  BASE: "7.0"
```
to avoid ci-scripts trying to `git clone` with `--branch 7`.

## Caches

GitHub Actions provides caching of dependencies.

However, since their cache restore and create algorithm is fundamentally
different from those used by Travis and AppVeyor, this will require some
more changes in ci-scripts to work. Be patient.
