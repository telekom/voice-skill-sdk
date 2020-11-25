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

from skill_sdk.responses import Result


class TestIntentsResult(unittest.TestCase):

    def test_result_empty(self):
        with self.assertRaises(TypeError):
            Result()  # Sorry for that Warning, but people seem to ignore it, so we raise an TypeError to catch it

    def test_result_local(self):
        result = Result({'a': 1}, True)
        self.assertEqual(result.data, {'a': 1})
        self.assertEqual(result.local, True)

    def test_result_local_false(self):
        result = Result({'a': 1}, False)
        self.assertEqual(result.data, {'a': 1})
        self.assertEqual(result.local, False)

    def test_result_local_missing(self):
        result = Result({'a': 1})
        self.assertEqual(result.data, {'a': 1})
        self.assertEqual(result.local, True)

    def test_dict(self):
        result = Result({'a': 1}, False)
        self.assertEqual(result.dict(), {'data': {'a': 1}, 'local': False})

    def test_result_empty_false(self):
        """ Make sure empty result evaluates to boolean False
        """
        result = Result(None)
        self.assertTrue(not result)
        result = Result({})
        self.assertTrue(not result)

    def test_bool_result_with_secondary_device(self):
        """ [HMPOP-273] TargetDeviceId is nullified if data is empty
        """
        result = Result(None)
        self.assertFalse(result)
        result.target_device_id = 'Target'
        self.assertTrue(result)

    def test_result_subscriptable(self):
        """ Ensure Result is subscriptable
        """
        result = Result({'a': 1})
        self.assertEqual(result['a'], 1)

    def test_result_updatable(self):
        """ Test if Result is updatable and `update` actually updates `data`
        """
        result = Result({'a': 0})
        result.update(a=1, b=2)
        self.assertEqual(result.data, {'a': 1, 'b': 2})

    def test_result_dict_is_serializable(self):
        """ Test `Result.dict` method returns serializable
        """
        import datetime
        result = Result({'date': datetime.datetime.now()}).dict()
        self.assertIsInstance(result['data']['date'], str)

    def test_target_device_id(self):
        """ Test target device id
        """
        self.assertIsNone(Result({'a': 1}).target_device_id)
        self.assertEqual(Result({'a': 1}, target_device_id='Primary').target_device_id, 'Primary')

    def test_result_repr(self):
        """ Test Result representation
        """
        result = Result({'a': 1}, target_device_id="Secondary")
        self.assertEqual("{'data': {'a': 1}, 'local': True, 'targetDeviceId': 'Secondary'}", repr(result))
