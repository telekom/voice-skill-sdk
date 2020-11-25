#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#
import time
import unittest
from unittest.mock import patch

from skill_sdk.caching.exceptions import KeyNotFoundException
from skill_sdk.caching.local import (LocalCacheItem, BaseLocalCache, LocalFIFOCache, LocalLRUCache,
                                     LocalTimeoutCache, LocalSoftTimeoutCache, CacheControlLocalLRUCache)


class TestLocalCacheItem(unittest.TestCase):

    def test_payload_none(self):
        self.assertEqual(LocalCacheItem(None).payload, None)

    def test_payload_int(self):
        self.assertEqual(LocalCacheItem(-3).payload, -3)

    def test_payload_string(self):
        self.assertEqual(LocalCacheItem('abcdef').payload, 'abcdef')

    def test_payload_bytes(self):
        self.assertEqual(LocalCacheItem(b'12345').payload, b'12345')

    def test_payload_dict(self):
        self.assertEqual(LocalCacheItem({'a': 1}).payload, {'a': 1})

    def test_created_last_read(self):
        time_before = time.time()
        time.sleep(0.1)
        item = LocalCacheItem(None)
        time.sleep(0.1)
        time_after = time.time()
        self.assertTrue(time_before < item.created < time_after)
        self.assertTrue(time_before < item.last_read)

    @patch('time.time', return_value=100.0)
    def test_age(self, *_):
        item = LocalCacheItem(None)
        item.created = 0.0
        self.assertEqual(item.age, 100)

    @patch('time.time', return_value=100.0)
    def test_not_read_for(self, *_):
        item = LocalCacheItem(None)
        item.last_read = 0.0
        self.assertEqual(item.not_read_for, 100)

    # TODO fix test/code
    def test_touch(self):
        item = LocalCacheItem(None)
        time_after = time.time()
        item.touch()

    #    self.assertTrue(item.last_read < time_after)

    def test_payload_touch(self):
        item = LocalCacheItem(None)
        time_after = time.time()
        item.payload
    #    self.assertTrue(item.last_read > time_after)


class TestBaseLocalCache(unittest.TestCase):

    def setUp(self):
        self.cache = BaseLocalCache()

    def test_init(self):
        self.assertEqual(self.cache.data, {})

    def test_len(self):
        self.assertEqual(len(self.cache), 0)
        self.cache.data['a'] = None
        self.assertEqual(len(self.cache), 1)

    def test_bool(self):
        self.assertFalse(self.cache)
        self.cache.set('a', 1)
        self.assertTrue(self.cache)

    def test_get_miss(self):
        with self.assertRaises(KeyNotFoundException):
            self.cache.get('a')

    def test_get_no_conditions_miss(self):
        with self.assertRaises(KeyNotFoundException):
            self.cache.get_no_conditions('a')

    def test_get_hit(self):
        self.cache.set('a', 1)
        self.assertEqual(self.cache.get('a'), 1)

    def test_get_no_conditions_hit(self):
        self.cache.set('a', 1)
        self.assertEqual(self.cache.get_no_conditions('a'), 1)

    def test_get_and_should_be_updated(self):
        self.cache.set('a', 1)
        self.assertEqual(self.cache.get_and_should_be_updated('a'), (1, False))

    def test_set(self):
        self.cache.set('a', 1)
        self.assertEqual(self.cache.data['a'].payload, 1)

    def test_set_cache_item(self):
        self.cache.set('a', LocalCacheItem(1))
        self.assertEqual(self.cache.data['a'].payload, 1)

    def test_delete_miss(self):
        self.cache.set('a', 1)
        self.cache.delete('b')
        self.assertEqual(len(self.cache), 1)

    def test_delete_hit(self):
        self.cache.set('a', 1)
        self.cache.delete('a')
        self.assertEqual(len(self.cache), 0)

    def test_touch(self):
        self.cache.set('a', 1)
        self.cache.data['a'].last_read = 1.0
        self.cache.touch('a')
        self.assertTrue(self.cache.data['a'].last_read > 1000.0)

    def test_touch_miss(self):
        self.cache.set('a', 1)
        with self.assertRaises(KeyNotFoundException):
            self.cache.touch('b')

    def test_purge(self):
        for index, value in enumerate('abcdefg'):
            self.cache.set(value, index)
        self.assertEqual(len(self.cache), 7)
        self.cache.purge()
        self.assertEqual(len(self.cache), 0)

    def test_validate(self):
        self.cache.validate()

    def test_name(self):
        self.assertIn(self.cache.__class__.__name__, self.cache.name)

    @patch('skill_sdk.caching.local.CLEAN_UP_INTERVAL', 2)
    def test_validate_called_interval(self):
        with patch.object(self.cache, 'validate') as validate_mock:  # @UndefinedVariable
            self.cache.set('a', 1)
            self.cache.set('b', 2)
            validate_mock.assert_any_call()


class TestLocalFIFOCache(TestBaseLocalCache):

    def setUp(self):
        self.cache = LocalFIFOCache(10)

    def test_set_overflow(self):
        for index, value in enumerate('1234567890'):
            self.cache.set(value, index)
        self.assertEqual(len(self.cache), 10)
        self.cache.set('a', 'a')
        self.assertEqual(len(self.cache), 10)
        self.assertEqual(list(self.cache.data.keys()), list('234567890a'))

    def test_validate_too_long(self):
        for index, value in enumerate('1234567890'):
            self.cache.set(value, index)
        self.cache.data['a'] = LocalCacheItem('a')
        self.assertEqual(len(self.cache), 11)
        self.cache.validate()
        self.assertEqual(len(self.cache), 10)


class TestLocalLRUCache(TestBaseLocalCache):

    def setUp(self):
        self.cache = LocalLRUCache(10)

    def test_moved_to_end_on_access(self):
        for index, value in enumerate('1234567890'):
            self.cache.set(value, index)
        self.cache.get('1')
        self.assertEqual(list(self.cache.data.keys()), list('2345678901'))


class TestCacheControlLocalLRUCache(TestLocalLRUCache):

    def setUp(self):
        self.cache = CacheControlLocalLRUCache(10)

    def test_get_miss(self):
        self.assertIsNone(self.cache.get('a'))

    def test_bool(self):
        self.assertTrue(self.cache)
        self.cache.set('a', 1)
        self.assertTrue(self.cache)

    def test_moved_to_end_on_access(self):
        for index, value in enumerate('1234567890'):
            self.cache.set(value, index)
        self.cache.get('1')
        self.assertEqual(list(self.cache.data.keys()), list('2345678901'))


class TestLocalTimoutCache(TestBaseLocalCache):

    def setUp(self):
        self.cache = LocalTimeoutCache(60)

    def test_get_hit_timeout(self):
        self.cache.set('a', 1)
        self.cache.data['a'].created = 1.0
        with self.assertRaises(KeyNotFoundException):
            self.cache.get('a')

    def test_get_and_should_be_updated_hit_timeout(self):
        self.cache.set('a', 1)
        self.cache.data['a'].created = 1.0
        with self.assertRaises(KeyNotFoundException):
            self.cache.get_and_should_be_updated('a')

    def test_validate(self):
        self.cache.set('a', 1)
        self.cache.set('b', 1)
        self.assertEqual(len(self.cache), 2)
        self.cache.data['a'].created = 1.0
        self.cache.validate()
        self.assertEqual(len(self.cache), 1)
        with patch.object(self.cache, 'delete', side_effect=KeyError()):
            self.cache.data['b'].created = 1.0
            self.cache.validate()
            self.assertEqual(len(self.cache), 1)


class TestLocalSoftTimoutCache(TestLocalTimoutCache):

    def setUp(self):
        self.cache = LocalSoftTimeoutCache(60, 0.5)

    def test_init_bad_thresholds(self):
        with self.assertRaises(ValueError):
            LocalSoftTimeoutCache(60, 1.5)
        with self.assertRaises(ValueError):
            LocalSoftTimeoutCache(60, 0.0)

    def test_hit_soft_timeout(self):
        self.cache.set('a', 1)
        self.cache.data['a'].created = time.time() - 45.0
        self.assertEqual(self.cache.get_and_should_be_updated('a'), (1, True))
