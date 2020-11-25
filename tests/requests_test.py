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
from unittest.mock import patch, Mock

import requests_mock
from circuitbreaker import CircuitBreaker, STATE_CLOSED
from requests.sessions import Session

from skill_sdk import requests
from skill_sdk.circuit_breaker import DEFAULT_CIRCUIT_BREAKER
from skill_sdk.requests import BadHttpResponseCodeException, CircuitBreakerSession, DEFAULT_REQUEST_TIMEOUT
from skill_sdk.caching.local import LocalFIFOCache


class TestBadHttpResponseCodeException(unittest.TestCase):

    def test_init(self):
        shrce = BadHttpResponseCodeException(500)
        self.assertEqual(shrce.status_code, 500)

    def test_str(self):
        shrce = BadHttpResponseCodeException(500)
        self.assertEqual(str(shrce), 'BadHttpResponseCodeException 500')


class TestCircuitBreakerSession(unittest.TestCase):

    def tearDown(self):
        DEFAULT_CIRCUIT_BREAKER._failure_count = 0
        DEFAULT_CIRCUIT_BREAKER._state = STATE_CLOSED

    def test_init(self):
        zcbs = CircuitBreakerSession(cache=LocalFIFOCache())
        self.assertEqual(zcbs.internal, False)
        self.assertEqual(zcbs.circuit_breaker, DEFAULT_CIRCUIT_BREAKER)
        self.assertTrue(isinstance(zcbs, Session))

    def test_init_with_circuit_breaker(self):
        cb = CircuitBreaker()
        zcbs = CircuitBreakerSession(circuit_breaker=cb)
        self.assertEqual(zcbs.internal, False)
        self.assertEqual(zcbs.circuit_breaker, cb)
        self.assertTrue(isinstance(zcbs, Session))

    def test_init_with_internal_false(self):
        zcbs = CircuitBreakerSession(internal=False)
        self.assertEqual(zcbs.internal, False)
        self.assertEqual(zcbs.circuit_breaker, DEFAULT_CIRCUIT_BREAKER)
        self.assertTrue(isinstance(zcbs, Session))

    def test_init_with_internal_true(self):
        zcbs = CircuitBreakerSession(internal=True)
        self.assertEqual(zcbs.internal, True)
        self.assertEqual(zcbs.circuit_breaker, DEFAULT_CIRCUIT_BREAKER)
        self.assertTrue(isinstance(zcbs, Session))

    @patch.object(Session, 'request')
    def test_request_timeout_to_default(self, request_mock):
        with CircuitBreakerSession() as s:
            s.get('http://localhost/')
            request_mock.assert_called_once_with(s, 'GET', 'http://localhost/',
                                                 allow_redirects=True, timeout=DEFAULT_REQUEST_TIMEOUT)

    @patch.object(Session, 'request')
    def test_request_timeout_if_set(self, request_mock):
        with CircuitBreakerSession(timeout=6.6) as s:
            s.get('http://localhost/')
            request_mock.assert_called_once_with(s, 'GET', 'http://localhost/', allow_redirects=True, timeout=6.6)

    @patch.object(Session, 'request')
    @patch.object(requests.CircuitBreakerSession, 'DEFAULT_TIMEOUT', 10)
    def test_request_timeout_from_config(self, request_mock):
        with CircuitBreakerSession() as s:
            s.get('http://localhost/')
            request_mock.assert_called_once_with(s, 'GET', 'http://localhost/', allow_redirects=True, timeout=10)

    @patch.object(requests, 'global_tracer')
    @requests_mock.mock()
    def test_http_error_500(self, tracer_mock, req_mock):
        req_mock.get('http://localhost/', status_code=500)
        with self.assertRaises(BadHttpResponseCodeException):
            with CircuitBreakerSession() as s:
                s.get('http://localhost/')
        tracer_mock().start_span().__enter__().log_kv.assert_called_once_with(
            {'error': 'BadHttpResponseCodeException 500'})

    def test_check_status_code_default_ok(self):
        response = Mock()
        response.status_code = 200
        self.assertEqual(CircuitBreakerSession()._check_status_code(response), None)

    def test_check_status_code_default_500(self):
        response = Mock()
        response.status_code = 500
        with self.assertRaises(Exception):
            CircuitBreakerSession()._check_status_code(response)

    def test_check_status_code_200_ok(self):
        response = Mock()
        response.status_code = 200
        self.assertEqual(CircuitBreakerSession(good_codes=(200,))._check_status_code(response), None)

    def test_check_status_code_200_500(self):
        response = Mock()
        response.status_code = 500
        with self.assertRaises(Exception):
            CircuitBreakerSession(good_codes=(200,))._check_status_code(response)

    def test_check_status_code_range2xx_ok(self):
        response = Mock()
        response.status_code = 200
        self.assertEqual(CircuitBreakerSession(good_codes=range(200, 300))._check_status_code(response), None)

    def test_check_status_code_range2xx_500(self):
        response = Mock()
        response.status_code = 500
        with self.assertRaises(Exception):
            CircuitBreakerSession(good_codes=range(200, 300))._check_status_code(response)

    def test_check_status_code_range2xx_only_ok(self):
        response = Mock()
        response.status_code = 200
        self.assertEqual(CircuitBreakerSession(good_codes=range(200, 300))._check_status_code(response), None)

    def test_check_status_code_range2xx_only_500(self):
        response = Mock()
        response.status_code = 500
        with self.assertRaises(Exception):
            CircuitBreakerSession(good_codes=range(200, 300))._check_status_code(response)

    def test_check_status_code_int_range_ok(self):
        response = Mock()
        response.status_code = 200
        self.assertEqual(CircuitBreakerSession(good_codes=(200, 300))._check_status_code(response),
                         None)

    def test_check_status_code_int_range_found(self):
        response = Mock()
        response.status_code = 302
        self.assertEqual(CircuitBreakerSession(good_codes=range(300, 400))._check_status_code(response),
                         None)

    def test_check_status_code_int_range_500(self):
        response = Mock()
        response.status_code = 500
        with self.assertRaises(Exception):
            CircuitBreakerSession(good_codes=range(200, 400))._check_status_code(response)

    def test_check_status_code_string(self):
        response = Mock()
        response.status_code = 500
        with self.assertRaises(Exception):
            CircuitBreakerSession(good_codes='200')._check_status_code(response)

    def test_check_status_code_range_and_int(self):
        response = Mock()
        response.status_code = 404
        try:
            CircuitBreakerSession(good_codes=(range(200, 400), 404), bad_codes=range(400, 600))._check_status_code(response)
        except BadHttpResponseCodeException:
            self.fail('BadHttpResponseCodeException should not be raised')

    @patch.object(Session, 'request')
    def test_request_proxy_on_service(self, req_mock):
        requests.USE_LOCAL_SERVICES = True
        with CircuitBreakerSession() as session:
            session.get('http://service-test-service')
        self.assertEqual(req_mock.call_args_list[0][1]['proxies'], {'http': 'http://localhost:8888'})
        requests.USE_LOCAL_SERVICES = False

    @patch.object(Session, 'request')
    def test_request_proxy_off_service(self, req_mock):
        requests.USE_LOCAL_SERVICES = False
        with CircuitBreakerSession() as session:
            session.get('http://service-test-service')
        self.assertEqual(req_mock.call_args_list[0][1].get('proxies'), None)
        requests.USE_LOCAL_SERVICES = False

    @patch.object(Session, 'request')
    def test_request_proxy_on_no_service(self, req_mock):
        requests.USE_LOCAL_SERVICES = True
        with CircuitBreakerSession() as session:
            session.get('http://test')
        self.assertEqual(req_mock.call_args_list[0][1].get('proxies'), None)
        requests.USE_LOCAL_SERVICES = False

    @patch.object(Session, 'request')
    def test_request_proxy_off_no_service(self, req_mock):
        requests.USE_LOCAL_SERVICES = False
        with CircuitBreakerSession() as session:
            session.get('http://test')
        self.assertEqual(req_mock.call_args_list[0][1].get('proxies'), None)
        requests.USE_LOCAL_SERVICES = False


class TestCaching(unittest.TestCase):

    def test_cache_class_can_validate(self):
        with CircuitBreakerSession() as session:
            for url in ('http://example.com/', 'https://example.com/'):
                adapter = session.get_adapter(url)
                self.assertTrue(hasattr(adapter.cache, 'validate'))
