#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#
import json
import time
import unittest
from unittest.mock import MagicMock

from skill_sdk.caching import decorators
from skill_sdk.caching.decorators import CallCache
from skill_sdk.caching.local import LocalFIFOCache


class TestCallCache(unittest.TestCase):

    def setUp(self):
        decorators.CACHES_ACTIVE = True

    def tearDown(self):
        decorators.CACHES_ACTIVE = False

    def test_init_no_cache_chain(self):
        with self.assertRaises(ValueError):
            CallCache()

    def test_init_cache_chain_no_list(self):
        with self.assertRaises(ValueError):
            CallCache(1)

    def test_init_cache_chain_no_items(self):
        with self.assertRaises(ValueError):
            CallCache([])

    def test_time_10_times(self):
        @CallCache([LocalFIFOCache(1)])
        def _get_time():
            return time.time()

        results = [_get_time() for _ in range(10)]
        self.assertEqual(len(set(results)), 1)

    def test_complex_arguments(self):
        @CallCache([LocalFIFOCache(1)])
        def _complex_arguments(*args, **kwargs):
            return json.dumps((time.time(), args, kwargs))

        results = [_complex_arguments(1, 2, 3, a='1', b=None) for _ in range(10)]
        self.assertEqual(len(set(results)), 1)

    def test_complex_arguments_different(self):
        @CallCache([LocalFIFOCache(2)])
        def _complex_arguments(*args, **kwargs):
            return json.dumps((time.time(), args, kwargs))

        results1 = [_complex_arguments(1, 2, 3, a='1', b=None) for _ in range(10)]
        results2 = [_complex_arguments(1, 2, 3, a='2', b=None) for _ in range(10)]
        self.assertEqual(len(set(results1)), 1)
        self.assertEqual(len(set(results2)), 1)
        self.assertNotEqual(results1.pop(), results2.pop())

    def test_fifo_push_out(self):
        @CallCache([LocalFIFOCache(1)])
        def _complex_arguments(*args, **kwargs):
            return json.dumps((time.time(), args, kwargs))

        result1 = _complex_arguments(1, 2, 3, a='1', b=None)
        result2 = _complex_arguments(1, 2, 3, a='2', b=None)
        result3 = _complex_arguments(1, 2, 3, a='1', b=None)
        self.assertNotEqual(result1, result2)
        self.assertNotEqual(result1, result3)

    def test_ignore_first_argument_on(self):
        c = CallCache([LocalFIFOCache(1)], ignore_first_argument=True)
        c.key_generator = MagicMock(return_value=b'test_key')

        @c
        def _test_method(a, b, c):
            return None

        _test_method(1, 2, 3)
        self.assertEqual(c.key_generator.call_args[0][1], (2, 3))

    def test_ignore_first_argument_off(self):
        c = CallCache([LocalFIFOCache(1)], ignore_first_argument=False)
        c.key_generator = MagicMock(return_value=b'test_key')

        @c
        def _test_method(a, b, c):
            return None

        _test_method(1, 2, 3)
        self.assertEqual(c.key_generator.call_args[0][1], (1, 2, 3))

    def test_store_upstream(self):
        l1 = LocalFIFOCache(1)
        l2 = LocalFIFOCache(1)

        @CallCache([l1, l2])
        def _get_time():
            return time.time()

        _get_time()
        self.assertEqual(len(l1), 1)
        self.assertEqual(len(l2), 1)

    def test_store_downstream(self):
        l1 = LocalFIFOCache(1)
        l2 = LocalFIFOCache(1)

        @CallCache([l1, l2])
        def _get_time():
            return time.time()

        a = _get_time()
        self.assertEqual(len(l1), 1)
        self.assertEqual(len(l2), 1)
        l1.purge()
        self.assertEqual(len(l1), 0)
        self.assertEqual(len(l2), 1)
        b = _get_time()
        self.assertEqual(a, b)
        self.assertEqual(len(l1), 1)
        self.assertEqual(len(l2), 1)

    def test_no_store_upstream_or_cached_value(self):
        l1 = LocalFIFOCache(1)
        l2 = LocalFIFOCache(1)

        @CallCache([l1, l2])
        def _get_time():
            return time.time()

        a = _get_time()
        self.assertEqual(len(l1), 1)
        self.assertEqual(len(l2), 1)
        l2.purge()
        self.assertEqual(len(l2), 0)
        b = _get_time()
        self.assertEqual(a, b)
        self.assertEqual(len(l1), 1)
        self.assertEqual(len(l2), 0)

    def test_raise_on_exception_do_not_cache(self):
        l1 = LocalFIFOCache(1)

        @CallCache([l1])
        def _get_time():
            raise ValueError(time.time())

        with self.assertRaises(ValueError):
            _get_time()
        with self.assertRaises(ValueError):
            _get_time()
        self.assertEqual(len(l1), 0)

    def test_call_cache_lazy_call(self):
        """ Make sure decorated wrapper is evaluated at runtime """
        from skill_sdk.tracing import initialize_tracer
        initialize_tracer()

        @CallCache([LocalFIFOCache(1)])
        def _get_time():
            return time.perf_counter()

        decorators.CACHES_ACTIVE = False
        results = [_get_time() for _ in range(10)]
        self.assertEqual(len(set(results)), 10)

        decorators.CACHES_ACTIVE = True
        results = [_get_time() for _ in range(10)]
        self.assertEqual(len(set(results)), 1)
