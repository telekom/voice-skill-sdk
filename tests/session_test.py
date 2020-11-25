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

from skill_sdk.sessions import Session, SessionOversizeError, SessionInvalidKeyError


class TestSession(unittest.TestCase):

    # NOTE: We don't test the underlying dictionary!

    def setUp(self):
        self.s = Session('123456', True)

    def test_call_super(self):
        s = Session('123456', True, {'a': '123'})
        self.assertEqual(s['a'], '123')

    def test_get_storage_size_empty(self):
        self.assertEqual(self.s.get_storage_size(), 0)

    def test_get_storage_size_1_0(self):
        self.s['a'] = ''
        self.assertEqual(self.s.get_storage_size(), 1)

    def test_get_storage_size_3_4(self):
        self.s['abc'] = '1234'
        self.assertEqual(self.s.get_storage_size(), 7)

    def test_get_storage_size_two_keys(self):
        self.s['abc'] = '1234'
        self.s['def'] = '56789'
        self.assertEqual(self.s.get_storage_size(), 15)

    def test_setitem_int_as_key(self):
        self.s[1] = 'abc'
        self.assertEqual(list(self.s.keys()).pop(), '1')

    def test_setitem_int_as_value(self):
        self.s['abc'] = 1
        self.assertEqual(self.s['abc'], '1')

    def test_setitem_empty_key(self):
        with self.assertRaises(SessionInvalidKeyError):
            self.s[''] = '1'

    def test_setitem_oversize_empty_long_key(self):
        with self.assertRaises(SessionOversizeError):
            self.s[5000 * 'a'] = '1'

    def test_setitem_oversize_empty_long_value(self):
        with self.assertRaises(SessionOversizeError):
            self.s['abc'] = 5000 * 'a'

    def test_restore_old_value_on_oversize_error(self):
        self.s['abc'] = '123'
        try:
            self.s['abc'] = 5000 * 'a'
        except SessionOversizeError:
            pass
        self.assertEqual(self.s['abc'], '123')

    def test_update(self):
        self.s.update({'a': 'b'})
        self.assertEqual(self.s['a'], 'b')

    def test_update_existing_key(self):
        self.s['a'] = '1'
        self.s.update({'a': 'b'})
        self.assertEqual(self.s['a'], 'b')

    def test_update_kw(self):
        self.s.update(a='b')
        self.assertEqual(self.s['a'], 'b')

    def test_update_kw_existing_key(self):
        self.s['a'] = '1'
        self.s.update(a='b')
        self.assertEqual(self.s['a'], 'b')

    def test_update_dict_vs_kw(self):
        self.s['a'] = '1'
        self.s.update({'a': 'a'}, a='b')
        self.assertEqual(self.s['a'], 'b')

    def test_oversize_on_update(self):
        with self.assertRaises(SessionOversizeError):
            self.s.update({5000 * 'a': '1'})

    def test_oversize_on_update_kwargs(self):
        with self.assertRaises(SessionOversizeError):
            self.s.update(abc=5000 * '1')
