#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#
import gc
import gevent
import unittest
from configparser import ConfigParser
from unittest.mock import patch, Mock

from skill_sdk import tracing
from skill_sdk.services.jaeger import setup_service
from jaeger_client.tracer import Tracer
from jaeger_client.span import Span

test_config = ConfigParser()
test_config['jaeger'] = {}


class TestJaeger(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        with patch('skill_sdk.services.jaeger.config', new=test_config):
            setup_service()

    @classmethod
    def tearDownClass(cls) -> None:
        [obj.kill() for obj in gc.get_objects() if isinstance(obj, gevent.Greenlet)]

    def setUp(self):
        self.request = Mock()
        self.request.headers = {
            'X-B3-TraceId': '430ee1c3e2deccfa',
            'X-B3-ParentSpanId': '01e97311cfec540a',
            'X-B3-SpanId': 'd4aeec01e3c43faa',
            'X-B3-Sampled': '1',
            'X-B3-Debug': '0'}

    @patch.object(Tracer, '_random_id', return_value=16362748281808618186)
    def test_init(self, *args):
        with tracing.start_active_span('span', self.request) as scope:
            span = scope.span
            self.assertEqual(f"{span.parent_id:x}", 'd4aeec01e3c43faa')
            self.assertEqual(f"{span.trace_id:x}", '430ee1c3e2deccfa')
            self.assertEqual(f"{span.span_id:x}", 'e31428de665602ca')
            self.assertEqual(span.is_sampled(), True)
            self.assertEqual(span.flags, 1)

    def test_init_no_headers(self):
        request = Mock()
        request.headers = {}
        with tracing.start_active_span('span', request) as scope:
            span = scope.span
            self.assertEqual(False, span.is_sampled())
            self.assertEqual(span.flags, 0)

    @patch.object(Span, 'finish')
    def test_new_span(self, stop_span):
        with tracing.start_active_span('active span', self.request) as scope:
            with scope.span.tracer.start_span('inner span') as span:
                self.assertEqual(span.tracer.service_name, 'unnamed-skill')
                self.assertEqual(span.operation_name, 'inner span')
                span.set_operation_name('new_span')
                self.assertEqual(span.operation_name, 'new_span')
                span.log_kv({'key': 'value'}, 123456789)
                self.assertEqual(span.logs[0].fields[0].__dict__, dict(key='key', vType=0, vStr='value',
                                                                       vDouble=None, vBool=None, vLong=None,
                                                                       vBinary=None))
        # Ensure both spans are finished when out of scope
        self.assertEqual(stop_span.call_count, 2)
