#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#

import os
import time
import unittest
from unittest.mock import patch
from types import SimpleNamespace

import requests
import requests_mock

from skill_sdk.services import prometheus


class TestPrometheus(unittest.TestCase):

    @patch('skill_sdk.services.prometheus.active_count', return_value=3)
    def test_update_stats(self, *mocks):
        prometheus.update_stats()
        self.assertEqual(prometheus.thread_count._value._value, 3.0)

    @patch('skill_sdk.services.prometheus.update_stats')
    def test_metrics(self, update_mock):
        result = prometheus.metrics()
        self.assertIn(b'\ninprogress_requests ', result)
        self.assertIn(b'\nthread_count ', result)
        self.assertIn(b' http_server_requests_seconds_count', result)
        # self.assertIn(b'\nprocess_max_fds ', result)
        update_mock.assert_called_with()

    @patch('os.environ', new={'prometheus_multiproc_dir': '/tmp'})
    @patch('skill_sdk.services.prometheus.update_stats')
    def test_log_message(self, update_mock):
        """ Test log message in multiprocessing mode """
        with patch('skill_sdk.services.prometheus.logger') as log_mock:
            prometheus.metrics()
            log_mock.debug.assert_called_with('Collecting from %s', "'/tmp'")

    def test_prometheus_middleware(self):
        from skill_sdk.routes import api_base

        def callback():
            self.assertIn(b'\ninprogress_requests 1.0', prometheus.metrics())
            return SimpleNamespace(status_code=200)

        self.assertIn(b'\ninprogress_requests 0.0', prometheus.metrics())
        with patch('skill_sdk.services.prometheus.request') as request:
            request.path = api_base()
            prometheus.prometheus(callback)()

        self.assertIn(b'\ninprogress_requests 0.0', prometheus.metrics())

    def test_prometheus_latency(self):
        from skill_sdk.routes import api_base

        @prometheus.prometheus_latency('Latency Test')
        def callback():
            time.sleep(0.025)
            return SimpleNamespace(status_code=200)

        self.assertIn(b'\ninprogress_requests 0.0', prometheus.metrics())
        with patch('skill_sdk.services.prometheus.request') as request:
            request.path = api_base()
            prometheus.prometheus(callback)()

        metrics = prometheus.metrics()
        self.assertIn(b'le="0.025",operation="Latency Test",version="0.1"} 0.0', metrics)
        self.assertIn(b'le="0.05",operation="Latency Test",version="0.1"} 1.0', metrics)

    def test_prometheus_partner(self):
        with requests_mock.Mocker() as m:
            m.get('http://fohf_partner_call.com', text='resp', status_code=404)
            m.get('http://working_partner_call.com', text='', status_code=200)

            with prometheus.partner_call(requests.get, 'partner-call') as get:
                [get('http://fohf_partner_call.com') for _ in range(0, 15)]
                [get('http://working_partner_call.com') for _ in range(0, 10)]

        result = prometheus.metrics()
        self.assertIn(b'partner_name="partner-call",status="404"} 15.0', result)
        self.assertIn(b'partner_name="partner-call",status="200"} 10.0', result)

    def test_prometheus_partner_with_circuit_breaker(self):
        from skill_sdk.requests import CircuitBreakerSession, BadHttpResponseCodeException
        from skill_sdk.services.prometheus import count_partner_calls, http_partner_request_count_total

        http_partner_request_count_total.clear()

        with requests_mock.Mocker() as m:
            m.get("http://httpbin.org/status/404", text='', status_code=404)
            m.get("http://httpbin.org/status/500", text='', status_code=500)

            with CircuitBreakerSession(response_hook=count_partner_calls('partner-call')) as session:
                with self.assertRaises(BadHttpResponseCodeException):
                    [session.get("http://httpbin.org/status/404") for _ in range(1, 15)]
                with self.assertRaises(BadHttpResponseCodeException):
                    [session.get("http://httpbin.org/status/500") for _ in range(1, 15)]

        result = prometheus.metrics()
        self.assertIn(b'partner_name="partner-call",status="404"} 1.0', result)
        self.assertIn(b'partner_name="partner-call",status="500"} 1.0', result)

    @patch.object(prometheus.config, 'getint', return_value=2)
    @patch.object(prometheus.multiprocess, 'MultiProcessCollector')
    def test_setup_service(self, mpc_mock, *args):
        with patch('skill_sdk.services.prometheus.mkdtemp', return_value='/tmp'):
            prometheus.setup_service()
            self.assertEqual(os.environ['prometheus_multiproc_dir'], '/tmp')
            mpc_mock.assert_called_once_with(prometheus.core.REGISTRY)
        with patch('skill_sdk.services.prometheus.mkdtemp') as mkd_mock:
            prometheus.setup_service()
            mkd_mock.assert_not_called()
