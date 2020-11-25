#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#
import unittest


def test_suite():
    test_loader = unittest.TestLoader()
    return test_loader.discover('tests', pattern='*_test.py')
