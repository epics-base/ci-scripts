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

## Supported CI Services

 - Travis-CI
 
### How to Use the CI-Scripts

 1. Get an account on a supported CI service provider platform.
    (More details in the specific README of the subdirectory.)

 2. In your Support Module, add this ci-scripts respository
    as a Git Submodule (name suggestion: `.ci`).
    ```
    $ git submodule add https://github.com/epics-base/ci-scripts .ci
    ```

 3. Create a configuration for the CI service by copying one of
    the examples provided in the service specific subdirectory
    and editing it to include the jobs you want the service to run.
	
 4. Push your changes and check the CI service for your build results.

## Releases and Numbering of this Module

Major release numbers refer to the API, which is more or less defined
by the full configuration examples in the service specific
subdirectories.
If one of these files has to be changed for the existing configuration
options or new options are being added, a new major release is created.

Minor release numbers refer to bugfixes that should not require the
configuration inside a user module to be changed.

Again: using the git submodule mechanism to include these scripts means
that user modules always work with a fixed, frozen version.
I.e., developments in the ci-scripts repository will never break an\
existing application.
These release numbering considerations are just a hint to assess the
risks when updating the submodule.
