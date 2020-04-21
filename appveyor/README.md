# AppVeyor Scripts for EPICS Modules

## Features

 - Use different compilers (Visual Studio, MinGW)
 - Use different VS versions (2008, 2010, 2012, 2013, 2015, 2017, 2019)
 - Compile for Windows 32bit and 64bit
 - Create static libraries or DLLs (plus the matching executables)
 - Create optimized or debug builds

## How to Use these Scripts

 1. Get an account on [AppVeyor](https://www.appveyor.com/), connect
    it to your GitHub account and activate your support module's
    repository. For more details, please refer to the
    [AppVeyor documentation](https://www.appveyor.com/docs/).

 2. Add the ci-scripts respository as a Git Submodule
    (see [README](../README.md) one level above).

 3. Add settings files defining which dependencies in which versions
    you want to build against
    (see [README](../README.md) one level above).

 4. Create an AppVeyor configuration by copying one of the examples into
    the root directory of your module.
    ```
    $ cp .ci/appveyor/.appveyor.yml.example-full .appveyor.yml
    ```
	
 5. Edit the `.appveyor.yml` configuration to include the jobs you want
    AppVeyor to run.

    AppVeyor automatically creates a build matrix with the following axes:
    1. `configuration:` \
    Select static or dynamic (DLL) as well as regular or debug builds.
    2. `platform:` \
    Select 32bit or 64bit processor architecture.
    3. `environment: / matrix:` \
    List of environment variable settings. Each list element (starting with
    a dash) is one step on the axis of the build matrix.
    
    Your builds will take long.
    
    AppVeyor only grants a single worker VM - all jobs of the matrix are
    executed sequentially. Each job will take around 10 minutes.
    
    The `matrix: / exclude:` setting can be used to reduce the number of
    jobs. Check the [AppVeyor docs](https://www.appveyor.com/docs/build-configuration/#build-matrix)
    for more ways to reduce the build matrix size.
	
 6. Push your changes and check
    [ci.appveyor.com](https://ci.appveyor.com/) for your build results.
