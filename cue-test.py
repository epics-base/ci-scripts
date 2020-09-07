#!/usr/bin/env python
"""Module ci-scripts unit tests
"""

# SET=test00 in the environment and run the tests in this script
# all other jobs are started as compile jobs

from __future__ import print_function

import sys, os, shutil, fileinput
import distutils.util
import re
import subprocess as sp
import unittest
import logging
from argparse import Namespace

builddir = os.getcwd()

# Detect basic context (service, os)
if 'TRAVIS' in os.environ:
    ci_service = 'travis'
    ci_os = os.environ['TRAVIS_OS_NAME']

if 'APPVEYOR' in os.environ:
    ci_service = 'appveyor'
    if re.match(r'^Visual', os.environ['APPVEYOR_BUILD_WORKER_IMAGE']):
        ci_os = 'windows'
    elif re.match(r'^Ubuntu', os.environ['APPVEYOR_BUILD_WORKER_IMAGE']):
        ci_os = 'linux'
    elif re.match(r'^macOS', os.environ['APPVEYOR_BUILD_WORKER_IMAGE']):
        ci_os = 'osx'

if 'GITHUB_ACTIONS' in os.environ:
    ci_service = 'github-actions'
    if os.environ['RUNNER_OS'] == 'macOS':
        ci_os = 'osx'
    else:
        ci_os = os.environ['RUNNER_OS'].lower()


def find_in_file(regex, filename):
    file = open(filename, "r")
    for line in file:
        if re.search(regex, line):
            return True
    return False


def getStringIO():
    if sys.version_info > (3, 0):
        import io
        return io.StringIO()
    else:
        import StringIO
        return StringIO.StringIO()


sys.path.append('.')
import cue

# we're working with tags (detached heads) a lot: suppress advice
cue.call_git(['config', '--global', 'advice.detachedHead', 'false'])


class TestSourceSet(unittest.TestCase):

    def setUp(self):
        os.environ['SETUP_PATH'] = '.:appveyor'
        if 'BASE' in os.environ:
            del os.environ['BASE']
        cue.clear_lists()
        os.chdir(builddir)

    def test_EmptySetupDirsPath(self):
        del os.environ['SETUP_PATH']
        self.assertRaisesRegexp(NameError, '\(SETUP_PATH\) is empty', cue.source_set, 'test01')

    def test_InvalidSetupName(self):
        self.assertRaisesRegexp(NameError, 'does not exist in SETUP_PATH', cue.source_set, 'xxdoesnotexistxx')

    def test_ValidSetupName(self):
        capturedOutput = getStringIO()
        sys.stdout = capturedOutput
        cue.source_set('test01')
        sys.stdout = sys.__stdout__
        self.assertEqual(cue.setup['BASE'], '7.0', 'BASE was not set to \'7.0\'')

    def test_SetupDoesNotOverridePreset(self):
        os.environ['BASE'] = 'foo'
        capturedOutput = getStringIO()
        sys.stdout = capturedOutput
        cue.source_set('test01')
        sys.stdout = sys.__stdout__
        self.assertEqual(cue.setup['BASE'], 'foo',
                         'Preset BASE was overridden by test01 setup (expected \'foo\' got {0})'
                         .format(cue.setup['BASE']))

    def test_IncludeSetupFirstSetWins(self):
        captured_output = getStringIO()
        sys.stdout = captured_output
        cue.source_set('test02')
        sys.stdout = sys.__stdout__
        self.assertEqual(cue.setup['BASE'], 'foo',
                         'BASE set in test02 was overridden by test01 setup (expected \'foo\' got {0})'
                         .format(cue.setup['BASE']))
        self.assertEqual(cue.setup['FOO'], 'bar', 'Setting of single word does not work')
        self.assertEqual(cue.setup['FOO2'], 'bar bar2', 'Setting of multiple words does not work')
        self.assertEqual(cue.setup['FOO3'], 'bar bar2', 'Indented setting of multiple words does not work')
        self.assertEqual(cue.setup['SNCSEQ'], 'R2-2-8', 'Setup test01 was not included')

    def test_DoubleIncludeGetsIgnored(self):
        capturedOutput = getStringIO()
        sys.stdout = capturedOutput
        cue.source_set('test03')
        sys.stdout = sys.__stdout__
        self.assertRegexpMatches(capturedOutput.getvalue(), 'Ignoring already included setup file')


class TestUpdateReleaseLocal(unittest.TestCase):
    release_local = os.path.join(cue.cachedir, 'RELEASE.local')

    def setUp(self):
        if os.path.exists(self.release_local):
            os.remove(self.release_local)
        os.chdir(builddir)

    def test_SetModule(self):
        cue.update_release_local('MOD1', '/foo/bar')
        found = 0
        for line in fileinput.input(self.release_local, inplace=1):
            if 'MOD1=' in line:
                self.assertEqual(line.strip(), 'MOD1=/foo/bar', 'MOD1 not set correctly')
                found += 1
        fileinput.close()
        self.assertEqual(found, 1, 'MOD1 not written once to RELEASE.local (found {0})'.format(found))

    def test_SetBaseAndMultipleModules(self):
        cue.update_release_local('EPICS_BASE', '/bar/foo')
        cue.update_release_local('MOD1', '/foo/bar')
        cue.update_release_local('MOD2', '/foo/bar2')
        cue.update_release_local('MOD1', '/foo/bar1')
        found = {}
        foundat = {}
        for line in fileinput.input(self.release_local, inplace=1):
            if 'MOD1=' in line:
                self.assertEqual(line.strip(), 'MOD1=/foo/bar1',
                                 'MOD1 not set correctly (expected \'MOD1=/foo/bar1\' found \'{0}\')'
                                 .format(line))
                if 'mod1' in found:
                    found['mod1'] += 1
                else:
                    found['mod1'] = 1
                foundat['mod1'] = fileinput.filelineno()
            if 'MOD2=' in line:
                self.assertEqual(line.strip(), 'MOD2=/foo/bar2',
                                 'MOD2 not set correctly (expected \'MOD2=/foo/bar2\' found \'{0}\')'
                                 .format(line))
                if 'mod2' in found:
                    found['mod2'] += 1
                else:
                    found['mod2'] = 1
                foundat['mod2'] = fileinput.filelineno()
            if 'EPICS_BASE=' in line:
                self.assertEqual(line.strip(), 'EPICS_BASE=/bar/foo',
                                 'EPICS_BASE not set correctly (expected \'EPICS_BASE=/bar/foo\' found \'{0}\')'
                                 .format(line))
                if 'base' in found:
                    found['base'] += 1
                else:
                    found['base'] = 1
                foundat['base'] = fileinput.filelineno()
        fileinput.close()
        self.assertEqual(found['mod1'], 1,
                         'MOD1 does not appear once in RELEASE.local (found {0})'.format(found['mod1']))
        self.assertEqual(found['mod2'], 1,
                         'MOD2 does not appear once in RELEASE.local (found {0})'.format(found['mod2']))
        self.assertEqual(found['base'], 1,
                         'EPICS_BASE does not appear once in RELEASE.local (found {0})'.format(found['base']))
        self.assertGreater(foundat['base'], foundat['mod2'],
                           'EPICS_BASE (line {0}) appears before MOD2 (line {1})'
                           .format(foundat['base'], foundat['mod2']))
        self.assertGreater(foundat['mod2'], foundat['mod1'],
                           'MOD2 (line {0}) appears before MOD1 (line {1})'.format(foundat['mod2'], foundat['mod1']))


class TestAddDependencyUpToDateCheck(unittest.TestCase):
    hash_3_15_6 = "ce7943fb44beb22b453ddcc0bda5398fadf72096"
    location = os.path.join(cue.cachedir, 'base-R3.15.6')
    licensefile = os.path.join(location, 'LICENSE')
    checked_file = os.path.join(location, 'checked_out')
    release_file = os.path.join(location, 'configure', 'RELEASE')

    def setUp(self):
        os.environ['SETUP_PATH'] = '.:appveyor'
        if os.path.exists(self.location):
            shutil.rmtree(self.location, onerror=cue.remove_readonly)
        cue.clear_lists()
        os.chdir(builddir)
        cue.source_set('defaults')
        cue.complete_setup('BASE')

    def test_MissingDependency(self):
        cue.setup['BASE'] = 'R3.15.6'
        cue.add_dependency('BASE')
        self.assertTrue(os.path.exists(self.licensefile), 'Missing dependency was not checked out')
        self.assertTrue(os.path.exists(self.checked_file), 'Checked-out commit marker was not written')
        with open(self.checked_file, 'r') as bfile:
            checked_out = bfile.read().strip()
        bfile.close()
        self.assertEqual(checked_out, self.hash_3_15_6,
                         'Wrong commit of dependency checked out (expected=\"{0}\" found=\"{1}\")'
                         .format(self.hash_3_15_6, checked_out))
        self.assertFalse(find_in_file('include \$\(TOP\)/../RELEASE.local', self.release_file),
                         'RELEASE in Base includes TOP/../RELEASE.local')

    def test_UpToDateDependency(self):
        cue.setup['BASE'] = 'R3.15.6'
        cue.add_dependency('BASE')
        os.remove(self.licensefile)
        cue.add_dependency('BASE')
        self.assertFalse(os.path.exists(self.licensefile), 'Check out on top of existing up-to-date dependency')

    def test_OutdatedDependency(self):
        cue.setup['BASE'] = 'R3.15.6'
        cue.add_dependency('BASE')
        os.remove(self.licensefile)
        with open(self.checked_file, "w") as fout:
            print('XXX not the right hash XXX', file=fout)
        fout.close()
        cue.add_dependency('BASE')
        self.assertTrue(os.path.exists(self.licensefile), 'No check-out on top of out-of-date dependency')
        with open(self.checked_file, 'r') as bfile:
            checked_out = bfile.read().strip()
        bfile.close()
        self.assertEqual(checked_out, self.hash_3_15_6,
                         "Wrong commit of dependency checked out (expected='{0}' found='{1}')"
                         .format(self.hash_3_15_6, checked_out))


def is_shallow_repo(place):
    check = sp.check_output(['git', 'rev-parse', '--is-shallow-repository'], cwd=place).strip().decode('ascii')
    if check == '--is-shallow-repository':
        if os.path.exists(os.path.join(place, '.git', 'shallow')):
            check = 'true'
        else:
            check = 'false'
    return check == 'true'


class TestAddDependencyOptions(unittest.TestCase):
    location = os.path.join(cue.cachedir, 'mcoreutils-master')
    testfile = os.path.join(location, '.ci', 'LICENSE')

    def setUp(self):
        os.environ['SETUP_PATH'] = '.'
        if os.path.exists(cue.cachedir):
            shutil.rmtree(cue.cachedir, onerror=cue.remove_readonly)
        cue.clear_lists()
        cue.detect_context()
        cue.source_set('defaults')
        cue.complete_setup('MCoreUtils')
        cue.setup['MCoreUtils'] = 'master'

    def test_Default(self):
        cue.add_dependency('MCoreUtils')
        self.assertTrue(os.path.exists(self.testfile),
                        'Submodule (.ci) not checked out recursively (requested: default=YES')
        self.assertTrue(is_shallow_repo(self.location),
                        'Module not checked out shallow (requested: default=5)')

    def test_SetRecursiveNo(self):
        cue.setup['MCoreUtils_RECURSIVE'] = 'NO'
        cue.add_dependency('MCoreUtils')
        self.assertFalse(os.path.exists(self.testfile), 'Submodule (.ci) checked out recursively')

    def test_SetDepthZero(self):
        cue.setup['MCoreUtils_DEPTH'] = '0'
        cue.add_dependency('MCoreUtils')
        self.assertFalse(is_shallow_repo(self.location), 'Module checked out shallow (requested full)')

    def test_SetDepthThree(self):
        cue.setup['MCoreUtils_DEPTH'] = '3'
        cue.add_dependency('MCoreUtils')
        self.assertTrue(is_shallow_repo(self.location),
                        'Module not checked out shallow (requested: depth=3)')

    def test_AddMsiTo314(self):
        cue.complete_setup('BASE')
        cue.setup['BASE'] = 'R3.14.12.1'
        msifile = os.path.join(cue.cachedir, 'base-R3.14.12.1', 'src', 'dbtools', 'msi.c')
        cue.add_dependency('BASE')
        self.assertTrue(os.path.exists(msifile), 'MSI was not added to Base 3.14')

    def test_DefaultBaseBranch(self):
        cue.complete_setup('BASE')
        self.assertEqual(cue.setup['BASE'], '7.0',
                         'Default Base branch is not 7.0 (found {0})'.format(cue.setup['BASE']))


def repo_access(dep):
    cue.set_setup_from_env(dep)
    cue.setup.setdefault(dep + "_DIRNAME", dep.lower())
    cue.setup.setdefault(dep + "_REPONAME", dep.lower())
    cue.setup.setdefault('REPOOWNER', 'epics-modules')
    cue.setup.setdefault(dep + "_REPOOWNER", cue.setup['REPOOWNER'])
    cue.setup.setdefault(dep + "_REPOURL", 'https://github.com/{0}/{1}.git'
                         .format(cue.setup[dep + '_REPOOWNER'], cue.setup[dep + '_REPONAME']))
    with open(os.devnull, 'w') as devnull:
        return cue.call_git(['ls-remote', '--quiet', '--heads', cue.setup[dep + '_REPOURL']],
                            stdout=devnull, stderr=devnull)


class TestDefaultModuleURLs(unittest.TestCase):
    modules = ['BASE', 'PVDATA', 'PVACCESS', 'NTYPES',
               'SNCSEQ', 'STREAM', 'ASYN', 'STD',
               'CALC', 'AUTOSAVE', 'BUSY', 'SSCAN',
               'IOCSTATS', 'MOTOR', 'IPAC', ]

    def setUp(self):
        os.environ['SETUP_PATH'] = '.:appveyor'
        cue.clear_lists()
        os.chdir(builddir)
        cue.source_set('defaults')

    def test_Repos(self):
        for mod in self.modules:
            self.assertEqual(repo_access(mod), 0, 'Defaults for {0} do not point to a valid git repository at {1}'
                             .format(mod, cue.setup[mod + '_REPOURL']))

@unittest.skipIf(ci_os != 'windows', 'VCVars test only applies to windows')
class TestVCVars(unittest.TestCase):
    def test_vcvars(self):
        if ci_service == 'travis':
            os.environ['TRAVIS_COMPILER'] = 'vs2017'
        else:
            os.environ['CONFIGURATION'] = 'default'
            if ci_service == 'github-actions' and os.environ['IMAGEOS'] == 'win16':
                os.environ['CMP'] = 'vs2017'
            else:
                os.environ['CMP'] = 'vs2019'
        cue.detect_context()
        cue.with_vcvars('env')


@unittest.skipIf(ci_service != 'travis', 'Run travis tests only on travis')
class TestTravisDetectContext(unittest.TestCase):
    def setUp(self):
        os.environ['TRAVIS'] = 'true'
        os.environ['TRAVIS_OS_NAME'] = 'linux'
        os.environ['TRAVIS_COMPILER'] = 'gcc'

    def tearDown(self):
        cue.clear_lists()
        os.environ.pop('BCFG', None)
        os.environ.pop('TEST', None)
        os.environ.pop('STATIC', None)

    def test_LinuxGccNone(self):
        cue.detect_context()
        self.assertEqual(cue.ci['service'], 'travis', "ci['service'] is {0} (expected: travis)"
                         .format(cue.ci['service']))
        self.assertEqual(cue.ci['os'], 'linux', "ci['os'] is {0} (expected: linux)"
                         .format(cue.ci['os']))
        self.assertEqual(cue.ci['compiler'], 'gcc', "ci['compiler'] is {0} (expected: gcc)"
                         .format(cue.ci['compiler']))
        self.assertEqual(cue.ci['platform'], 'x64', "ci['platform'] is {0} (expected: x64)"
                         .format(cue.ci['platform']))
        self.assertFalse(cue.ci['static'], "ci['static'] is True (expected: False)")
        self.assertFalse(cue.ci['debug'], "ci['debug'] is True (expected: False)")
        self.assertEqual(cue.ci['configuration'], 'shared-optimized',
                         "ci['configuration'] is {0} (expected: shared-optimized)"
                         .format(cue.ci['configuration']))

    def test_LinuxClangNone(self):
        os.environ['TRAVIS_COMPILER'] = 'clang'
        cue.detect_context()
        self.assertEqual(cue.ci['service'], 'travis', "ci['service'] is {0} (expected: travis)"
                         .format(cue.ci['service']))
        self.assertEqual(cue.ci['os'], 'linux', "ci['os'] is {0} (expected: linux)"
                         .format(cue.ci['os']))
        self.assertEqual(cue.ci['compiler'], 'clang', "ci['compiler'] is {0} (expected: clang)"
                         .format(cue.ci['compiler']))
        self.assertEqual(cue.ci['platform'], 'x64', "ci['platform'] is {0} (expected: x64)"
                         .format(cue.ci['platform']))
        self.assertFalse(cue.ci['static'], "ci['static'] is True (expected: False)")
        self.assertFalse(cue.ci['debug'], "ci['debug'] is True (expected: False)")
        self.assertEqual(cue.ci['configuration'], 'shared-optimized',
                         "ci['configuration'] is {0} (expected: shared-optimized)"
                         .format(cue.ci['configuration']))

    def test_BcfgShared(self):
        os.environ['BCFG'] = 'shared'
        cue.detect_context()
        self.assertFalse(cue.ci['static'], "ci['static'] is True (expected: False)")
        self.assertFalse(cue.ci['debug'], "ci['debug'] is True (expected: False)")
        self.assertEqual(cue.ci['configuration'], 'shared-optimized',
                         "ci['configuration'] is {0} (expected: shared-optimized)"
                         .format(cue.ci['configuration']))

    def test_BcfgStatic(self):
        os.environ['BCFG'] = 'static'
        cue.detect_context()
        self.assertTrue(cue.ci['static'], "ci['static'] is False (expected: True)")
        self.assertFalse(cue.ci['debug'], "ci['debug'] is True (expected: False)")
        self.assertEqual(cue.ci['configuration'], 'static-optimized',
                         "ci['configuration'] is {0} (expected: static-optimized)"
                         .format(cue.ci['configuration']))

    def test_BcfgDebug(self):
        os.environ['BCFG'] = 'debug'
        cue.detect_context()
        self.assertFalse(cue.ci['static'], "ci['static'] is True (expected: False)")
        self.assertTrue(cue.ci['debug'], "ci['debug'] is False (expected: True)")
        self.assertEqual(cue.ci['configuration'], 'shared-debug',
                         "ci['configuration'] is {0} (expected: shared-debug)"
                         .format(cue.ci['configuration']))

    def test_BcfgStaticDebug(self):
        os.environ['BCFG'] = 'static-debug'
        cue.detect_context()
        self.assertTrue(cue.ci['static'], "ci['static'] is False (expected: True)")
        self.assertTrue(cue.ci['debug'], "ci['debug'] is False (expected: True)")
        self.assertEqual(cue.ci['configuration'], 'static-debug',
                         "ci['configuration'] is {0} (expected: static-debug)"
                         .format(cue.ci['configuration']))

    def test_TestNo(self):
        os.environ['TEST'] = 'NO'
        cue.detect_context()
        self.assertFalse(cue.ci['test'], "ci['test'] is True (expected: False)")

    def test_WindowsGccNone(self):
        os.environ['TRAVIS_OS_NAME'] = 'windows'
        cue.detect_context()
        self.assertEqual(cue.ci['service'], 'travis', "ci['service'] is {0} (expected: travis)"
                         .format(cue.ci['service']))
        self.assertEqual(cue.ci['os'], 'windows', "ci['os'] is {0} (expected: windows)"
                         .format(cue.ci['os']))
        self.assertEqual(cue.ci['compiler'], 'gcc', "ci['compiler'] is {0} (expected: gcc)"
                         .format(cue.ci['compiler']))
        self.assertEqual(cue.ci['platform'], 'x64', "ci['platform'] is {0} (expected: x64)"
                         .format(cue.ci['platform']))
        self.assertFalse(cue.ci['static'], "ci['static'] is True (expected: False)")
        self.assertFalse(cue.ci['debug'], "ci['debug'] is True (expected: False)")
        self.assertEqual(cue.ci['configuration'], 'shared-optimized',
                         "ci['configuration'] is {0} (expected: shared-optimized)"
                         .format(cue.ci['configuration']))
        self.assertIn('strawberryperl', cue.ci['choco'], "'strawberryperl' is not in ci['choco']")
        self.assertIn('make', cue.ci['choco'], "'make' is not in ci['choco']")

    def test_WindowsVs2017None(self):
        os.environ['TRAVIS_OS_NAME'] = 'windows'
        os.environ['TRAVIS_COMPILER'] = 'vs2017'
        cue.detect_context()
        self.assertEqual(cue.ci['service'], 'travis', "ci['service'] is {0} (expected: travis)"
                         .format(cue.ci['service']))
        self.assertEqual(cue.ci['os'], 'windows', "ci['os'] is {0} (expected: windows)"
                         .format(cue.ci['os']))
        self.assertEqual(cue.ci['compiler'], 'vs2017', "ci['compiler'] is {0} (expected: vs2017)"
                         .format(cue.ci['compiler']))
        self.assertEqual(cue.ci['platform'], 'x64', "ci['platform'] is {0} (expected: x64)"
                         .format(cue.ci['platform']))
        self.assertFalse(cue.ci['static'], "ci['static'] is True (expected: False)")
        self.assertFalse(cue.ci['debug'], "ci['debug'] is True (expected: False)")
        self.assertEqual(cue.ci['configuration'], 'shared-optimized',
                         "ci['configuration'] is {0} (expected: shared-optimized)"
                         .format(cue.ci['configuration']))
        self.assertIn('strawberryperl', cue.ci['choco'], "'strawberryperl' is not in ci['choco']")
        self.assertIn('make', cue.ci['choco'], "'make' is not in ci['choco']")

    def test_WindowsVs2019None(self):
        os.environ['TRAVIS_OS_NAME'] = 'windows'
        os.environ['TRAVIS_COMPILER'] = 'vs2019'
        cue.detect_context()
        self.assertEqual(cue.ci['service'], 'travis', "ci['service'] is {0} (expected: travis)"
                         .format(cue.ci['service']))
        self.assertEqual(cue.ci['os'], 'windows', "ci['os'] is {0} (expected: windows)"
                         .format(cue.ci['os']))
        self.assertEqual(cue.ci['compiler'], 'vs2017', "ci['compiler'] is {0} (expected: vs2017)"
                         .format(cue.ci['compiler']))
        self.assertEqual(cue.ci['platform'], 'x64', "ci['platform'] is {0} (expected: x64)"
                         .format(cue.ci['platform']))
        self.assertFalse(cue.ci['static'], "ci['static'] is True (expected: False)")
        self.assertFalse(cue.ci['debug'], "ci['debug'] is True (expected: False)")
        self.assertEqual(cue.ci['configuration'], 'shared-optimized',
                         "ci['configuration'] is {0} (expected: shared-optimized)"
                         .format(cue.ci['configuration']))
        self.assertIn('strawberryperl', cue.ci['choco'], "'strawberryperl' is not in ci['choco']")
        self.assertIn('make', cue.ci['choco'], "'make' is not in ci['choco']")

    def test_OsxClangNone(self):
        os.environ['TRAVIS_OS_NAME'] = 'osx'
        os.environ['TRAVIS_COMPILER'] = 'clang'
        cue.detect_context()
        self.assertEqual(cue.ci['service'], 'travis', "ci['service'] is {0} (expected: travis)"
                         .format(cue.ci['service']))
        self.assertEqual(cue.ci['os'], 'osx', "ci['os'] is {0} (expected: osx)"
                         .format(cue.ci['os']))
        self.assertEqual(cue.ci['compiler'], 'clang', "ci['compiler'] is {0} (expected: clang)"
                         .format(cue.ci['compiler']))
        self.assertEqual(cue.ci['platform'], 'x64', "ci['platform'] is {0} (expected: x64)"
                         .format(cue.ci['platform']))
        self.assertFalse(cue.ci['static'], "ci['static'] is True (expected: False)")
        self.assertFalse(cue.ci['debug'], "ci['debug'] is True (expected: False)")
        self.assertEqual(cue.ci['configuration'], 'shared-optimized',
                         "ci['configuration'] is {0} (expected: shared-optimized)"
                         .format(cue.ci['configuration']))

    def test_StaticGetsWarning(self):
        os.environ['STATIC'] = 'YES'
        capturedOutput = getStringIO()
        sys.stdout = capturedOutput
        cue.detect_context()
        sys.stdout = sys.__stdout__
        self.assertRegexpMatches(capturedOutput.getvalue(), "Variable 'STATIC' not supported anymore")

    def test_MisspelledBcfgGetsWarning(self):
        os.environ['BCFG'] = 'static-dubug'
        capturedOutput = getStringIO()
        sys.stdout = capturedOutput
        cue.detect_context()
        sys.stdout = sys.__stdout__
        self.assertRegexpMatches(capturedOutput.getvalue(), "Unrecognized build configuration setting")


@unittest.skipIf(ci_service != 'appveyor', 'Run appveyor tests only on appveyor')
class TestAppveyorDetectContext(unittest.TestCase):
    def setUp(self):
        os.environ['APPVEYOR'] = 'True'
        os.environ['APPVEYOR_BUILD_WORKER_IMAGE'] = 'Visual Studio 2019'
        os.environ['CMP'] = 'vs2019'
        os.environ['CONFIGURATION'] = 'default'
        os.environ['PLATFORM'] = 'x64'

    def tearDown(self):
        cue.clear_lists()
        os.environ.pop('STATIC', None)
        os.environ.pop('TEST', None)

    def test_Platform32(self):
        os.environ['PLATFORM'] = 'x86'
        cue.detect_context()
        self.assertFalse(cue.ci['static'], "ci['static'] is True (expected: False)")
        self.assertFalse(cue.ci['debug'], "ci['debug'] is True (expected: False)")
        self.assertEqual(cue.ci['configuration'], 'shared-optimized',
                         "ci['configuration'] is {0} (expected: shared-optimized)"
                         .format(cue.ci['configuration']))
        self.assertEqual(cue.ci['platform'], 'x86',
                         "ci['platform'] is {0} (expected: x86)"
                         .format(cue.ci['platform']))

    def test_Platform64(self):
        cue.detect_context()
        self.assertFalse(cue.ci['static'], "ci['static'] is True (expected: False)")
        self.assertFalse(cue.ci['debug'], "ci['debug'] is True (expected: False)")
        self.assertEqual(cue.ci['configuration'], 'shared-optimized',
                         "ci['configuration'] is {0} (expected: shared-optimized)"
                         .format(cue.ci['configuration']))
        self.assertEqual(cue.ci['platform'], 'x64',
                         "ci['platform'] is {0} (expected: x64)"
                         .format(cue.ci['platform']))

    def test_PlatformX64(self):
        os.environ['PLATFORM'] = 'X64'
        cue.detect_context()
        self.assertFalse(cue.ci['static'], "ci['static'] is True (expected: False)")
        self.assertFalse(cue.ci['debug'], "ci['debug'] is True (expected: False)")
        self.assertEqual(cue.ci['configuration'], 'shared-optimized',
                         "ci['configuration'] is {0} (expected: shared-optimized)"
                         .format(cue.ci['configuration']))
        self.assertEqual(cue.ci['platform'], 'x64',
                         "ci['platform'] is {0} (expected: x64)"
                         .format(cue.ci['platform']))

    def test_ConfigDefault(self):
        cue.detect_context()
        self.assertFalse(cue.ci['static'], "ci['static'] is True (expected: False)")
        self.assertFalse(cue.ci['debug'], "ci['debug'] is True (expected: False)")
        self.assertEqual(cue.ci['configuration'], 'shared-optimized',
                         "ci['configuration'] is {0} (expected: shared-optimized)"
                         .format(cue.ci['configuration']))

    def test_ConfigStatic(self):
        os.environ['CONFIGURATION'] = 'static'
        cue.detect_context()
        self.assertTrue(cue.ci['static'], "ci['static'] is False (expected: True)")
        self.assertFalse(cue.ci['debug'], "ci['debug'] is True (expected: False)")
        self.assertEqual(cue.ci['configuration'], 'static-optimized',
                         "ci['configuration'] is {0} (expected: static-optimized)"
                         .format(cue.ci['configuration']))

    def test_ConfigDebug(self):
        os.environ['CONFIGURATION'] = 'debug'
        cue.detect_context()
        self.assertFalse(cue.ci['static'], "ci['static'] is True (expected: False)")
        self.assertTrue(cue.ci['debug'], "ci['debug'] is False (expected: True)")
        self.assertEqual(cue.ci['configuration'], 'shared-debug',
                         "ci['configuration'] is {0} (expected: shared-debug)"
                         .format(cue.ci['configuration']))

    def test_ConfigStaticDebug(self):
        os.environ['CONFIGURATION'] = 'static-debug'
        cue.detect_context()
        self.assertTrue(cue.ci['static'], "ci['static'] is False (expected: True)")
        self.assertTrue(cue.ci['debug'], "ci['debug'] is False (expected: True)")
        self.assertEqual(cue.ci['configuration'], 'static-debug',
                         "ci['configuration'] is {0} (expected: static-debug)"
                         .format(cue.ci['configuration']))

    def test_TestNo(self):
        os.environ['TEST'] = 'NO'
        cue.detect_context()
        self.assertFalse(cue.ci['test'], "ci['test'] is True (expected: False)")

    def test_WindowsGccNone(self):
        os.environ['CMP'] = 'gcc'
        cue.detect_context()
        self.assertEqual(cue.ci['service'], 'appveyor', "ci['service'] is {0} (expected: appveyor)"
                         .format(cue.ci['service']))
        self.assertEqual(cue.ci['os'], 'windows', "ci['os'] is {0} (expected: windows)"
                         .format(cue.ci['os']))
        self.assertEqual(cue.ci['compiler'], 'gcc', "ci['compiler'] is {0} (expected: gcc)"
                         .format(cue.ci['compiler']))
        self.assertEqual(cue.ci['platform'], 'x64', "ci['platform'] is {0} (expected: x64)"
                         .format(cue.ci['platform']))
        self.assertFalse(cue.ci['static'], "ci['static'] is True (expected: False)")
        self.assertFalse(cue.ci['debug'], "ci['debug'] is True (expected: False)")
        self.assertEqual(cue.ci['configuration'], 'shared-optimized',
                         "ci['configuration'] is {0} (expected: shared-optimized)"
                         .format(cue.ci['configuration']))
        self.assertIn('make', cue.ci['choco'], "'make' is not in ci['choco']")

    def test_WindowsVs2017None(self):
        os.environ['APPVEYOR_BUILD_WORKER_IMAGE'] = 'Visual Studio 2017'
        os.environ['CMP'] = 'vs2017'
        os.environ['PLATFORM'] = 'x86'
        cue.detect_context()
        self.assertEqual(cue.ci['service'], 'appveyor', "ci['service'] is {0} (expected: appveyor)"
                         .format(cue.ci['service']))
        self.assertEqual(cue.ci['os'], 'windows', "ci['os'] is {0} (expected: windows)"
                         .format(cue.ci['os']))
        self.assertEqual(cue.ci['compiler'], 'vs2017', "ci['compiler'] is {0} (expected: vs2017)"
                         .format(cue.ci['compiler']))
        self.assertEqual(cue.ci['platform'], 'x86', "ci['platform'] is {0} (expected: x86)"
                         .format(cue.ci['platform']))
        self.assertFalse(cue.ci['static'], "ci['static'] is True (expected: False)")
        self.assertFalse(cue.ci['debug'], "ci['debug'] is True (expected: False)")
        self.assertEqual(cue.ci['configuration'], 'shared-optimized',
                         "ci['configuration'] is {0} (expected: shared-optimized)"
                         .format(cue.ci['configuration']))
        self.assertIn('make', cue.ci['choco'], "'make' is not in ci['choco']")

    def test_WindowsVs2019None(self):
        cue.detect_context()
        self.assertEqual(cue.ci['service'], 'appveyor', "ci['service'] is {0} (expected: appveyor)"
                         .format(cue.ci['service']))
        self.assertEqual(cue.ci['os'], 'windows', "ci['os'] is {0} (expected: windows)"
                         .format(cue.ci['os']))
        self.assertEqual(cue.ci['compiler'], 'vs2019', "ci['compiler'] is {0} (expected: vs2019)"
                         .format(cue.ci['compiler']))
        self.assertEqual(cue.ci['platform'], 'x64', "ci['platform'] is {0} (expected: x64)"
                         .format(cue.ci['platform']))
        self.assertFalse(cue.ci['static'], "ci['static'] is True (expected: False)")
        self.assertFalse(cue.ci['debug'], "ci['debug'] is True (expected: False)")
        self.assertEqual(cue.ci['configuration'], 'shared-optimized',
                         "ci['configuration'] is {0} (expected: shared-optimized)"
                         .format(cue.ci['configuration']))
        self.assertIn('make', cue.ci['choco'], "'make' is not in ci['choco']")

    def test_StaticGetsWarning(self):
        os.environ['STATIC'] = 'YES'
        capturedOutput = getStringIO()
        sys.stdout = capturedOutput
        cue.detect_context()
        sys.stdout = sys.__stdout__
        self.assertRegexpMatches(capturedOutput.getvalue(), "Variable 'STATIC' not supported anymore")

    def test_MisspelledConfigurationGetsWarning(self):
        os.environ['CONFIGURATION'] = 'static-dubug'
        capturedOutput = getStringIO()
        sys.stdout = capturedOutput
        cue.detect_context()
        sys.stdout = sys.__stdout__
        self.assertRegexpMatches(capturedOutput.getvalue(), "Unrecognized build configuration setting")


class TestSetupForBuild(unittest.TestCase):
    args = Namespace(paths=[])
    cue.building_base = True
    if ci_os == 'windows':
        choco_installs = ['make']
        if ci_service != 'appveyor':
            choco_installs.append('strawberryperl')
        sp.check_call(['choco', 'install', '-ry'] + choco_installs)

    def setUp(self):
        if ci_service == 'appveyor':
            os.environ['CONFIGURATION'] = 'default'
        cue.detect_context()

    def tearDown(self):
        os.environ.pop('EPICS_HOST_ARCH', None)
        cue.clear_lists()

    def test_AddPathsOption(self):
        os.environ['FOOBAR'] = 'BAR'
        args = Namespace(paths=['/my/{FOOBAR}/dir', '/my/foobar'])
        cue.setup_for_build(args)
        self.assertTrue(re.search('/my/BAR/dir', os.environ['PATH']), 'Expanded path not in PATH')
        self.assertTrue(re.search('/foobar', os.environ['PATH']), 'Plain path not in PATH')
        os.environ.pop('FOOBAR', None)

    @unittest.skipIf(ci_os != 'windows', 'HostArchConfiguration test only applies to windows')
    def test_HostArchConfiguration(self):
        cue.ci['compiler'] = 'vs2017'
        for cue.ci['debug'] in [True, False]:
            for cue.ci['static'] in [True, False]:
                config_st = {True: 'static', False: 'shared'}
                config_db = {True: '-debug', False: '-optimized'}
                config = config_st[cue.ci['static']] + config_db[cue.ci['debug']]
                cue.setup_for_build(self.args)
                self.assertTrue('EPICS_HOST_ARCH' in os.environ,
                                'EPICS_HOST_ARCH is not set for Configuration={0}'.format(config))
                if cue.ci['static']:
                    self.assertTrue(re.search('-static$', os.environ['EPICS_HOST_ARCH']),
                                    'EPICS_HOST_ARCH is not -static for Configuration={0}'.format(config))
                    self.assertFalse(re.search('debug', os.environ['EPICS_HOST_ARCH']),
                                     'EPICS_HOST_ARCH is -debug for Configuration={0}'.format(config))
                elif cue.ci['debug']:
                    self.assertFalse(re.search('static', os.environ['EPICS_HOST_ARCH']),
                                     'EPICS_HOST_ARCH (found {0}) is -static for Configuration={1}'
                                     .format(os.environ['EPICS_HOST_ARCH'], config))
                    self.assertTrue(re.search('-debug$', os.environ['EPICS_HOST_ARCH']),
                                    'EPICS_HOST_ARCH (found {0}) is not -debug for Configuration={1}'
                                    .format(os.environ['EPICS_HOST_ARCH'], config))
                else:
                    self.assertFalse(re.search('static', os.environ['EPICS_HOST_ARCH']),
                                     'EPICS_HOST_ARCH is -static for Configuration={0}'.format(config))
                    self.assertFalse(re.search('debug', os.environ['EPICS_HOST_ARCH']),
                                     'EPICS_HOST_ARCH is -debug for Configuration={0}'.format(config))

    @unittest.skipIf(ci_os != 'windows', 'HostArchPlatform test only applies to windows')
    def test_HostArchPlatform(self):
        if ci_service == 'appveyor':
            platforms = ['x86', 'x64']
        else:
            platforms = ['x64']
        for platform in platforms:
            for cc in ['vs2019', 'gcc']:
                cue.ci['platform'] = platform
                cue.ci['compiler'] = cc
                cue.setup_for_build(self.args)
                self.assertTrue('EPICS_HOST_ARCH' in os.environ,
                                'EPICS_HOST_ARCH is not set for {0} / {1}'
                                .format(cc, cue.ci['platform']))
                if platform == 'x86':
                    self.assertTrue(re.search('^win32-x86', os.environ['EPICS_HOST_ARCH']),
                                    'EPICS_HOST_ARCH (found {0}) is not win32-x86 for {1} / {2}'
                                    .format(os.environ['EPICS_HOST_ARCH'], cc, platform))
                else:
                    self.assertTrue(re.search('^windows-x64', os.environ['EPICS_HOST_ARCH']),
                                    'EPICS_HOST_ARCH (found {0}) is not windows-x64 for {1} / {2}'
                                    .format(os.environ['EPICS_HOST_ARCH'], cc, platform))
                if cc == 'gcc':
                    self.assertTrue(re.search('-mingw$', os.environ['EPICS_HOST_ARCH']),
                                    'EPICS_HOST_ARCH (found {0}) is not -mingw for {1} / {2}'
                                    .format(os.environ['EPICS_HOST_ARCH'], cc, platform))
                    if ci_service == 'appveyor':
                        pattern = {'x86': 'mingw32', 'x64': 'mingw64'}
                        self.assertTrue(re.search(pattern[platform], os.environ['PATH']),
                                        'Binary location for {0} not in PATH (found PATH = {1})'
                                        .format(pattern[platform], os.environ['PATH']))

    @unittest.skipIf(ci_os != 'windows', 'Strawberry perl test only applies to windows')
    def test_StrawberryInPath(self):
        cue.setup_for_build(self.args)
        self.assertTrue(re.search('strawberry', os.environ['PATH'], flags=re.IGNORECASE),
                        'Strawberry Perl location not in PATH (found  PATH = {0})'
                        .format(os.environ['PATH']))

    def setBase314(self, yesno):
        cfg_base_version = os.path.join('configure', 'CONFIG_BASE_VERSION')
        fout = open(cfg_base_version, 'w')
        print('# test file for base version detection', file=fout)
        print('BASE_3_14={0}'.format(yesno), file=fout)
        fout.close()

    def setTestResultsTarget(self, target):
        rules_build = os.path.join('configure', 'RULES_BUILD')
        fout = open(rules_build, 'w')
        print('# test file for target detection', file=fout)
        print('{0}: something'.format(target), file=fout)
        fout.close()

    def test_DetectionBase314No(self):
        self.setBase314('NO')
        cue.setup_for_build(self.args)
        self.assertFalse(cue.is_base314, 'Falsely detected Base 3.14')

    def test_DetectionBase314Yes(self):
        self.setBase314('YES')
        cue.setup_for_build(self.args)
        self.assertTrue(cue.is_base314, 'Base 3.14 = YES not detected')

    def test_DetectionTestResultsTarget314No(self):
        self.setBase314('YES')
        self.setTestResultsTarget('nottherighttarget')
        cue.setup_for_build(self.args)
        self.assertFalse(cue.has_test_results, 'Falsely detected test-results target')

    def test_DetectionTestResultsTarget314Yes(self):
        self.setBase314('YES')
        self.setTestResultsTarget('test-results')
        cue.setup_for_build(self.args)
        self.assertFalse(cue.has_test_results, 'Falsely found test-results on Base 3.14')

    def test_DetectionTestResultsTargetNot314Yes(self):
        self.setBase314('NO')
        self.setTestResultsTarget('test-results')
        cue.setup_for_build(self.args)
        self.assertTrue(cue.has_test_results, 'Target test-results not detected')

    def test_ExtraMakeArgs(self):
        os.environ['EXTRA'] = 'bla'
        for ind in range(1,5):
            os.environ['EXTRA{0}'.format(ind)] = 'bla {0}'.format(ind)
        cue.setup_for_build(self.args)
        self.assertTrue(cue.extra_makeargs[0] == 'bla', 'Extra make arg [0] not set')
        for ind in range(1,5):
            self.assertTrue(cue.extra_makeargs[ind] == 'bla {0}'.format(ind),
                            'Extra make arg [{0}] not set (expected "bla {0}", found "{1}")'
                            .format(ind, cue.extra_makeargs[ind]))


class TestHooks(unittest.TestCase):
    location = os.path.join(cue.cachedir, 'hook_test')
    bla_file = os.path.join(location, 'bla.txt')
    new_file = os.path.join(location, 'dd', 'new.txt')

    def setUp(self):
        if os.path.exists(self.location):
            shutil.rmtree(self.location, onerror=cue.remove_readonly)
        try:
            os.makedirs(self.location)
        except:
            pass
        with open(self.bla_file, 'w') as f:
            f.write('''LINE1=YES
LINE2=NO''')

    def test_patchfile(self):
        hook = os.path.join(builddir, 'test.patch')
        cue.apply_patch(hook, cwd=self.location)
        line1_yes = False
        with open(self.bla_file) as f:
            if 'LINE1=YES' in f.read():
                line1_yes = True
        self.assertFalse(line1_yes, "Patch didn't change line in test file 'bla.txt'")
        self.assertTrue(os.path.exists(self.new_file), "patch didn't add new file")

    def test_archiveZip(self):
        hook = os.path.join(builddir, 'test.zip')
        cue.extract_archive(hook, cwd=self.location)
        self.assertTrue(os.path.exists(self.new_file), "archive extract didn't add new file")

    def test_archive7z(self):
        hook = os.path.join(builddir, 'test.7z')
        cue.extract_archive(hook, cwd=self.location)
        self.assertTrue(os.path.exists(self.new_file), "archive extract didn't add new file")


if __name__ == "__main__":
    if 'VV' in os.environ and os.environ['VV'] == '1':
        logging.basicConfig(level=logging.DEBUG)
        cue.silent_dep_builds = False

    cue.detect_context()
    cue.host_info()
    if sys.argv[1:] == ['env']:
        # testing with_vcvars
        [print(K, '=', V) for K, V in os.environ.items()]
    elif ci_os == 'windows' and sys.argv[1:] == ['findvs']:
        from fnmatch import fnmatch
        print('Available Visual Studio versions')
        for base in (r'C:\Program Files (x86)', r'C:\Program Files'):
            for root, dirs, files in os.walk(base):
                for fname in files:
                    if fnmatch(fname, 'vcvarsall.bat'):
                        print('Found', os.path.join(root, fname))
        sys.stdout.flush()
    else:
        unittest.main()
