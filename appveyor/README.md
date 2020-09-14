# AppVeyor Scripts for EPICS Modules

## Features

 - One parallel runner (all builds are sequential)
 - Windows Server 2012/2016/2019
 - Compile using gcc/MinGW or different Visual Studio versions: \
   2008, 2010, 2012, 2013, 2015, 2017, 2019
 - Compile for Windows 32bit and 64bit
 - No useful caching available.

## How to Use these Scripts

 1. Get an account on [AppVeyor](https://www.appveyor.com/), connect
    it to your GitHub account and activate your support module's
    repository. For more details, please see below and refer to the
    [AppVeyor documentation](https://www.appveyor.com/docs/).
    
    (This applies when using the free tier offered to open source
    projects. Things will be different using an "Enterprise"
    installation on customer hardware.)

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
    Select shared (DLL) or static as well as optimized or debug builds. \
    Default: `shared-optimized`
    2. `platform:` \
    Select 32bit or 64bit processor architecture.
    3. `environment: / matrix:` \
    List of environment variable settings. Each list element (starting with
    a dash) is one step on the axis of the build matrix. \
    Set `CMP` to select the compiler: `gcc` for the native
    [MinGW](http://mingw-w64.org/) GNU compiler, `vs2008` ...`vs2019` 
    (options listed above) for the Microsoft Visual Studio compilers.

    Your builds will take long. \
    AppVeyor only grants a single parallel runner VM - all jobs of the matrix
    are executed sequentially. AppVeyor also does not provide a usable cache
    mechanism to retain dependency artifacts across builds.
    Each job will take between 6 and 15 minutes, plus testing time, every time.

    The `matrix: / exclude:` setting can be used to reduce the number of
    jobs. Check the [AppVeyor docs][appveyor.doc.matrix]
    for more ways to reduce the build matrix size. \
    E.g., you can opt for not creating matrix axes for `configuration:`
    and`platform:` by moving these configurations into the job lines
    under `environment: / matrix:`.

 6. Push your changes and check
    [ci.appveyor.com](https://ci.appveyor.com/) for your build results.

## GitHub / AppVeyor Integration and Authentication

### Security
Enabling Two-Factor-Authentication (2FA) is always a good idea, for all 
your web based services, including GitHub and AppVeyor. \
Get an app for your phone (Authy works fine for me, but there are plenty),
and your phone will generate one-time passwords to verify your identity
to the service if required (e.g., when logging in from a new device).

### Authentication
You can use different ways and services to authenticate when you log into
your AppVeyor account. The easiest way - at least when you're using the
service with repositories on GitHub - is to use GitHub authentication.

### GitHub Integration
AppVeyor offers two ways to integrate with GitHub: through a GitHub
application or through an OAuth application. GitHub applications are using
the newer API, allow easier fine-grained access rights tuning and are
preferred.

The differences are mostly visible when you work with repositories under
organizational GitHub accounts: Using OAuth, AppVeyor always has the full
rights of your personal GitHub account.
GitHub applications on the other hand have separate instances and
configuration for every organizational account you are using on GitHub.

### Enabling Builds for your Repository
On the 'Projects' tab of your AppVeyor web interface, create a new project.
If the repository is not listed on the project creation page,
verify the Integration settings. Most of the relevant configuration
is taken from GitHub and has to be set up there.

### AppVeyor Account Sharing
You can always invite other AppVeyor users to have access to an AppVeyor
account, forming a team. Such additional shared accounts are a way to make
the AppVeyor limits (e.g., one parallel builder per account) more manageable.

## Known Issues

#### Build Worker Images
The AppVeyor documentation on build worker images doesn't seem to fully
describe the way things are handled internally.

The tested and suggested reproducible way of defining the build worker image
is shown in the example configuration files:

 - Set the default image using the `image:` tag.
 - Override the image for specific jobs by setting the
   `APPVEYOR_BUILD_WORKER_IMAGE` environment variable.

<!-- Links -->
[appveyor.doc.matrix]: https://www.appveyor.com/docs/build-configuration/#build-matrix
