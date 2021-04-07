#
# voice-skill-sdk
#
# (C) 2021, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

import time
import unittest
from types import SimpleNamespace

import respx
import httpx
from httpx import Response

from skill_sdk.middleware.prometheus import (
    Prometheus,
    count_partner_calls,
    handle_metrics,
    partner_call,
    prometheus_latency,
)

from skill_sdk.requests import Client


class TestPrometheus(unittest.TestCase):
    def test_prometheus_middleware(self):
        Prometheus.requests_latency()
        Prometheus.partner_requests_count()
        r = SimpleNamespace()
        metrics = handle_metrics(r).body
        self.assertIn(b"http_requests_latency_seconds", metrics)
        self.assertIn(b"http_partner_request_count_total", metrics)

    def test_prometheus_latency(self):
        r = SimpleNamespace()

        @prometheus_latency("Latency Test")
        def callback():
            time.sleep(0.025)
            return SimpleNamespace(status_code=200)

        callback()
        metrics = handle_metrics(r).body
        self.assertIn(
            b'http_requests_latency_seconds_bucket{job="skill-noname",'
            b'le="0.025",operation="Latency Test",version="1"} 0.0',
            metrics,
        )
        self.assertIn(
            b'http_requests_latency_seconds_bucket{job="skill-noname",'
            b'le="0.05",operation="Latency Test",version="1"} 1.0',
            metrics,
        )

    @respx.mock
    def test_prometheus_partner(self):

        Prometheus.partner_requests_count().clear()

        respx.get("http://fohf_partner_call.com").mock(
            return_value=Response(404, text="resp")
        )
        respx.get("http://working_partner_call.com").mock(
            return_value=Response(200, text="")
        )

        with partner_call("partner-call", httpx.get) as get:
            [get("http://fohf_partner_call.com") for _ in range(0, 15)]
            [get("http://working_partner_call.com") for _ in range(0, 10)]

        metrics = handle_metrics(SimpleNamespace()).body
        self.assertIn(b'partner_name="partner-call",status="404"} 15.0', metrics)
        self.assertIn(b'partner_name="partner-call",status="200"} 10.0', metrics)

    @respx.mock
    def test_partner_call_with_circuit_breaker(self):
        Prometheus.partner_requests_count().clear()

        respx.get("http://httpbin.org/status/404").mock(
            return_value=Response(404, text="")
        )
        respx.get("http://httpbin.org/status/500").mock(
            return_value=Response(500, text="")
        )

        with Client(response_hook=count_partner_calls("partner-call")) as client:
            with self.assertRaises(httpx.HTTPError):
                [client.get("http://httpbin.org/status/404") for _ in range(1, 15)]
            with self.assertRaises(httpx.HTTPError):
                [client.get("http://httpbin.org/status/500") for _ in range(1, 15)]

        metrics = handle_metrics(SimpleNamespace()).body
        self.assertIn(b'partner_name="partner-call",status="404"} 1.0', metrics)
        self.assertIn(b'partner_name="partner-call",status="500"} 1.0', metrics)
