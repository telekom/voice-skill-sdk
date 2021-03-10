#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#
import logging
import threading
import unittest
from configparser import ConfigParser
from unittest.mock import patch, Mock

from skill_sdk import tracing
from skill_sdk.services import zipkin
from skill_sdk.services.zipkin import QUEUE
from skill_sdk.requests import CircuitBreakerSession
from skill_sdk.services.zipkin import setup_service, queued_transport, zipkin_report_worker, B3Codec, SpanContext
from py_zipkin.zipkin import ZipkinAttrs, zipkin_span
from requests.sessions import Session

from requests.exceptions import ConnectionError

test_config = ConfigParser()
test_config['zipkin'] = {'server_url': 'http://localhost:9411/api/v1/spans'}


class TestTransport(unittest.TestCase):

    @patch('skill_sdk.services.zipkin.config', new=test_config)
    @patch('skill_sdk.services.zipkin.ZIPKIN_API_URL', 'http://localhost:9411/api/v1/spans')
    @patch('requests.post')
    def test_queued_transport(self, request_mock):
        threading.Thread(target=zipkin_report_worker, daemon=True).start()
        queued_transport(b'demodata')
        QUEUE.join()
        request_mock.assert_called_once_with(
            url='http://localhost:9411/api/v1/spans',
            data=b'demodata',
            headers={'Content-Type': 'application/x-thrift'}
        )
        with patch.object(zipkin.QUEUE, 'put') as put_mock, patch.object(zipkin, 'ZIPKIN_API_URL', new=None):
            queued_transport(b'wont send')
            put_mock.assert_not_called()

    @patch('skill_sdk.services.zipkin.config', new=test_config)
    @patch('skill_sdk.services.zipkin.ZIPKIN_API_URL', 'http://localhost:9411/api/v1/spans')
    @patch.object(zipkin.QUEUE, 'task_done', side_effect=StopIteration)
    @patch('requests.post')
    def test_transport_handler(self, request_mock, task_done):
        with patch.object(zipkin.QUEUE, 'get', return_value='<spam span/>'):
            with self.assertRaises(StopIteration):
                zipkin_report_worker()
            request_mock.assert_called_once_with(
                url='http://localhost:9411/api/v1/spans',
                data='<spam span/>',
                headers={'Content-Type': 'application/x-thrift'}
            )

            with patch.object(logging.Logger, 'error') as log_mock:
                request_mock.side_effect = ConnectionError()
                with self.assertRaises(StopIteration):
                    zipkin_report_worker()
                log_mock.assert_any_call('Zipkin reporter failed for service [%s]: %s', 'unnamed_service', 'ConnectionError()')


class TestZipkin(unittest.TestCase):

    def setUp(self):
        test_config = ConfigParser()
        test_config['zipkin'] = {'server_url': 'http://localhost:9411/api/v1/spans'}
        with patch('skill_sdk.config.config', new=test_config):
            setup_service()
        self.request = Mock()
        self.request.headers = {
            'X-B3-TraceId': '430ee1c3e2deccfa',
            'X-B3-ParentSpanId': '01e97311cfec540a',
            'X-B3-SpanId': 'd4aeec01e3c43faa',
            'X-B3-Sampled': '1',
            'X-B3-Debug': '0',
            'X-Testing': '1'
        }

    @patch('py_zipkin.zipkin.generate_random_64bit_string', return_value='0123456789abcdef')
    def test_init(self, *args):
        scope = tracing.start_active_span('span', self.request)
        ctx = scope.span.context
        self.assertEqual(ctx.trace_id, '430ee1c3e2deccfa')
        self.assertEqual(ctx.span_id, '0123456789abcdef')
        self.assertEqual(ctx.parent_id, 'd4aeec01e3c43faa')
        self.assertEqual(ctx.flags, 5)

    @patch('py_zipkin.zipkin.generate_random_64bit_string', return_value='0123456789abcdef')
    def test_init_no_headers(self, *args):
        request = Mock()
        request.headers = {}
        scope = tracing.start_active_span('span', request)
        ctx = scope.span.context
        self.assertEqual('0123456789abcdef', ctx.span_id)
        self.assertEqual('0123456789abcdef', ctx.trace_id)
        self.assertEqual(0, ctx.flags)

    def test_span(self):
        scope = tracing.start_active_span('span', self.request)
        span = scope.span.tracer.start_span('testspan')
        self.assertEqual(span.operation_name, 'testspan')
        self.assertEqual(span._span.sample_rate, 100.0)
        self.assertEqual(span._span.transport_handler, queued_transport)

    def test_new_span(self):
        with tracing.start_active_span('active span', self.request) as scope:
            with scope.span.tracer.start_span('inner span') as span:
                self.assertEqual(span.operation_name, 'inner span')
                span.set_operation_name('new_span')
                self.assertEqual(span.operation_name, 'new_span')
                span.log_kv({'key': 'value'}, 123456789)
                self.assertEqual(span._span.annotations, {'{"key": "value"}': 123456789})

    @patch('py_zipkin.zipkin.create_attrs_for_span', return_value=ZipkinAttrs(
        trace_id='430ee1c3e2deccfc',
        span_id='d4aeec01e3c43fac',
        parent_span_id=None,
        flags='0',
        is_sampled=True,
    ))
    @patch.object(Session, 'request', return_value=Mock(status_code=200))
    def test_request_headers_propagation(self, request_mock, *mocks):
        with tracing.start_span("operation"):
            with CircuitBreakerSession(internal=True) as s:
                s.get('http://localhost/')
                request_mock.assert_any_call(s, 'GET', 'http://localhost/', timeout=5, allow_redirects=True,
                                             headers={'X-B3-TraceId': '430ee1c3e2deccfc',
                                                      'X-B3-SpanId': 'd4aeec01e3c43fac'})

    @patch('py_zipkin.zipkin.generate_random_64bit_string', return_value='0123456789abcdef')
    @patch.object(Session, 'request', return_value=Mock(status_code=200))
    def test_testing_header_propagation(self, request_mock, *mocks):
        with tracing.start_active_span("operation", self.request):
            with CircuitBreakerSession(internal=True) as s:
                s.get('http://localhost/')
                request_mock.assert_any_call(s, 'GET', 'http://localhost/', timeout=5, allow_redirects=True,
                                             headers={'X-B3-TraceId': '430ee1c3e2deccfa',
                                                      'X-B3-SpanId': '0123456789abcdef',
                                                      'X-B3-ParentSpanId': '0123456789abcdef',
                                                      'X-B3-Sampled': '1',
                                                      'X-Testing': '1'})

    def test_extract_inject_exceptions(self):
        tracer = tracing.global_tracer()
        with self.assertRaises(tracing.UnsupportedFormatException):
            tracer.extract(tracing.Format.BINARY, {})
        ctx = tracing.SpanContext(None, None, None)
        with self.assertRaises(tracing.UnsupportedFormatException):
            tracer.inject(ctx, tracing.Format.BINARY, {})


class TestB3Codec(unittest.TestCase):
    def test_b3_extract(self):
        codec = B3Codec()

        with self.assertRaises(tracing.InvalidCarrierException):
            codec.extract([])

        # Implicit case insensitivity testing
        carrier = {'X-b3-SpanId': 'a2fb4a1d1a96d312', 'X-B3-ParentSpanId': '0020000000000001',
                   'X-B3-traceId': '463ac35c9f6413ad48485a3953bb6124', 'X-B3-flags': '1'}

        span_context = codec.extract(carrier)
        assert span_context.span_id == 'a2fb4a1d1a96d312'
        assert span_context.trace_id == '463ac35c9f6413ad48485a3953bb6124'
        assert span_context.parent_id == '0020000000000001'
        assert span_context.flags == 0x02

        # validate that missing parentspanid does not cause an error
        carrier.pop('X-B3-ParentSpanId')
        span_context = codec.extract(carrier)
        assert span_context.parent_id is None

        carrier.update({'X-b3-sampled': '1'})

        span_context = codec.extract(carrier)
        assert span_context.flags == 0x03

        carrier.pop('X-B3-flags')
        span_context = codec.extract(carrier)
        assert span_context.flags == 0x01

        carrier.update({'X-Testing': '1'})
        span_context = codec.extract(carrier)
        assert span_context.baggage == {'testing': '1'}
        assert span_context.flags == 0x05

    def test_b3_inject(self):
        codec = B3Codec()

        with self.assertRaises(tracing.InvalidCarrierException):
            codec.inject(None, [])

        ctx = SpanContext(
            trace_id='463ac35c9f6413ad48485a3953bb6124',
            span_id='a2fb4a1d1a96d312',
            parent_id='0020000000000001',
            flags=6
        )
        carrier = {}
        codec.inject(ctx, carrier)
        self.assertEqual(carrier, {'X-B3-SpanId': 'a2fb4a1d1a96d312',
                                   'X-B3-ParentSpanId': '0020000000000001',
                                   'X-B3-TraceId': '463ac35c9f6413ad48485a3953bb6124',
                                   'X-B3-Flags': '1',
                                   'X-Testing': '1',
                                   })
