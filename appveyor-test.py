#!/usr/bin/env python
"""Module ci-scripts AppVeyor unit tests
"""

# SET=test00 in .appveyor.yml runs the tests in this script
# all other jobs are started as compile jobs

import sys, os, fileinput
import unittest

def getStringIO():
    if (sys.version_info > (3, 0)):
        import io
        return io.StringIO()
    else:
        import StringIO
        return StringIO.StringIO()

sys.path.append('appveyor')
import do

class TestSourceSet(unittest.TestCase):

    def setUp(self):
        os.environ['SETUP_PATH'] = '.:appveyor'
        if 'BASE' in os.environ:
            del os.environ['BASE']
        do.clear_lists()

    def test_EmptySetupDirsPath(self):
        del os.environ['SETUP_PATH']
        self.assertRaisesRegexp(NameError, '\(SETUP_PATH\) is empty', do.source_set, 'test01')

    def test_InvalidSetupName(self):
        self.assertRaisesRegexp(NameError, 'does not exist in SETUP_PATH', do.source_set, 'xxdoesnotexistxx')

    def test_ValidSetupName(self):
        capturedOutput = getStringIO()
        sys.stdout = capturedOutput
        do.source_set('test01')
        sys.stdout = sys.__stdout__
        self.assertEqual(do.setup['BASE'], '7.0', 'BASE was not set to \'7.0\'')

    def test_SetupDoesNotOverridePreset(self):
        os.environ['BASE'] = 'foo'
        capturedOutput = getStringIO()
        sys.stdout = capturedOutput
        do.source_set('test01')
        sys.stdout = sys.__stdout__
        self.assertEqual(do.setup['BASE'], 'foo',
                         'Preset BASE was overridden by test01 setup (expected \'foo\' got {0})'
                         .format(do.setup['BASE']))

    def test_IncludeSetupFirstSetWins(self):
        capturedOutput = getStringIO()
        sys.stdout = capturedOutput
        do.source_set('test02')
        sys.stdout = sys.__stdout__
        self.assertEqual(do.setup['BASE'], 'foo',
                         'BASE set in test02 was overridden by test01 setup (expected \'foo\' got {0})'
                         .format(do.setup['BASE']))
        self.assertEqual(do.setup['FOO'], 'bar', 'Setting of single word does not work')
        self.assertEqual(do.setup['FOO2'], 'bar bar2', 'Setting of multiple words does not work')
        self.assertEqual(do.setup['FOO3'], 'bar bar2', 'Indented setting of multiple words does not work')
        self.assertEqual(do.setup['SNCSEQ'], 'R2-2-7', 'Setup test01 was not included')

    def test_DoubleIncludeGetsIgnored(self):
        capturedOutput = getStringIO()
        sys.stdout = capturedOutput
        do.source_set('test03')
        sys.stdout = sys.__stdout__
        self.assertRegexpMatches(capturedOutput.getvalue(), 'Ignoring already included setup file')

class TestUpdateReleaseLocal(unittest.TestCase):

    release_local = os.path.join(do.cachedir, 'RELEASE.local')

    def setUp(self):
        if os.path.exists(self.release_local):
            os.remove(self.release_local)

    def test_SetModule(self):
        do.update_release_local('MOD1', '/foo/bar')
        found = 0
        for line in fileinput.input(self.release_local, inplace=1):
            if 'MOD1=' in line:
                self.assertEqual(line.strip(), 'MOD1=/foo/bar', 'MOD1 not set correctly')
                found += 1
        fileinput.close()
        self.assertEqual(found, 1, 'MOD1 not written once to RELEASE.local (found {0})'.format(found))

    def test_SetBaseAndMultipleModules(self):
        do.update_release_local('EPICS_BASE', '/bar/foo')
        do.update_release_local('MOD1', '/foo/bar')
        do.update_release_local('MOD2', '/foo/bar2')
        do.update_release_local('MOD1', '/foo/bar1')
        found = {}
        foundat = {}
        for line in fileinput.input(self.release_local, inplace=1):
            if 'MOD1=' in line:
                self.assertEqual(line.strip(), 'MOD1=/foo/bar1',
                                 'MOD1 not set correctly (expected \'MOD1=/foo/bar1\' found \'{0}\')'
                                 .format(line))
                found['mod1'] += 1
                foundat['mod1'] = fileinput.filelineno()
            if 'MOD2=' in line:
                self.assertEqual(line.strip(), 'MOD2=/foo/bar2',
                                 'MOD2 not set correctly (expected \'MOD2=/foo/bar2\' found \'{0}\')'
                                 .format(line))
                found['mod2'] += 1
                foundat['mod2'] = fileinput.filelineno()
            if 'EPICS_BASE=' in line:
                self.assertEqual(line.strip(), 'EPICS_BASE=/bar/foo',
                                 'EPICS_BASE not set correctly (expected \'EPICS_BASE=/bar/foo\' found \'{0}\')'
                                 .format(line))
                found['base'] += 1
                foundat['base'] = fileinput.filelineno()
        fileinput.close()
        self.assertEqual(found['mod1'], 1, 'MOD1 does not appear once in RELEASE.local (found {0})'.format(found['mod1']))
        self.assertEqual(found['mod2'], 1, 'MOD2 does not appear once in RELEASE.local (found {0})'.format(found['mod2']))
        self.assertEqual(found['base'], 1, 'EPICS_BASE does not appear once in RELEASE.local (found {0})'.format(found['base']))
        self.assertGreater(foundat['base'], foundat['mod2'],
                           'EPICS_BASE (line {0}) appears before MOD2 (line {1})'.format(foundat['base'], foundat['mod2']))
        self.assertGreater(foundat['mod2'], foundat['mod1'],
                           'MOD2 (line {0}) appears before MOD1 (line {1})'.format(foundat['mod2'], foundat['mod1']))




if __name__ == "__main__":
#    suite = unittest.TestLoader().loadTestsFromTestCase(TestSourceSet)
#    suite = unittest.TestLoader().loadTestsFromTestCase(TestUpdateReleaseLocal)
#    unittest.TextTestRunner(verbosity=2).run(suite)
    unittest.main()
