#!/usr/bin/env python
"""Module ci-scripts AppVeyor unit tests
"""

# SET=test00 in .appveyor.yml runs the tests in this script
# all other jobs are started as compile jobs

import sys, os
import unittest

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
        try:
            do.source_set('test01')
        except NameError:
            return
        self.fail('source_set did not throw on empty SETUP_DIRS')

    def test_InvalidSetupName(self):
        try:
            do.source_set('xxdoesnotexistxx')
        except NameError:
            return
        self.fail('source_set did not throw on invalid file name')

    def test_ValidSetupName(self):
        do.source_set('test01')
        self.assertEqual(do.setup['BASE'], '7.0', 'BASE was not set to \'7.0\'')

    def test_SetupDoesNotOverridePreset(self):
        os.environ['BASE'] = 'foo'
        do.source_set('test01')
        self.assertEqual(do.setup['BASE'], 'foo',
                         'Preset BASE was overridden by test01 setup (expected \'foo\' got {0})'
                         .format(do.setup['BASE']))

    def test_IncludeSetupFirstSetWins(self):
        do.source_set('test02')
        self.assertEqual(do.setup['BASE'], 'foo',
                         'BASE set in test02 was overridden by test01 setup (expected \'foo\' got {0})'
                         .format(do.setup['BASE']))
        self.assertEqual(do.setup['FOO'], 'bar', 'Setting of single word does not work')
        self.assertEqual(do.setup['FOO2'], 'bar bar2', 'Setting of multiple words does not work')
        self.assertEqual(do.setup['FOO3'], 'bar bar2', 'Indented setting of multiple words does not work')
        self.assertEqual(do.setup['SNCSEQ'], 'R2-2-7', 'Setup test01 was not included')






if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSourceSet)
    unittest.TextTestRunner(verbosity=2).run(suite)
#    unittest.main()
