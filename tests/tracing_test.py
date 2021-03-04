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
from unittest.mock import patch
from skill_sdk.tracing import (
    global_tracer,
    initialize_tracer,
    set_global_tracer,
    start_span,
    Codec,
    Format,
    InvalidCarrierException,
    SpanContext,
    UnsupportedFormatException,
)


class TestTracing(unittest.TestCase):

    def setUp(self):
        initialize_tracer()

    def test_start_span(self):
        with self.assertRaises(ValueError):
            set_global_tracer(None)

        with start_span('test_span') as span:
            self.assertEqual(span.tracer.service_name, 'unnamed-skill')
            self.assertEqual(span.operation_name, 'test_span')
            with start_span('another_one', child_of=span) as child_span:
                self.assertEqual(child_span.span_name, 'another_one')
                self.assertEqual(child_span.context, span.context)

    @patch('skill_sdk.tracing.Tracer.start_span')
    def test_start_span_decorator(self, start_mock):
        @start_span('test_span')
        def decorated_func():
            return True

        decorated_func()
        start_mock.assert_called_once_with('test_span')


class TestNoopCodec(unittest.TestCase):

    def setUp(self):
        initialize_tracer()

    def test_extract(self):
        codec = Codec()

        with self.assertRaises(InvalidCarrierException):
            codec.extract([])

        # Implicit case insensitivity testing
        carrier = {'X-b3-SpanId': 'a2fb4a1d1a96d312',
                   'X-B3-traceId': '463ac35c9f6413ad48485a3953bb6124',
                   'X-Testing': '1'}

        span_context = codec.extract(carrier)
        assert span_context.span_id == 'a2fb4a1d1a96d312'
        assert span_context.trace_id == '463ac35c9f6413ad48485a3953bb6124'
        assert span_context.testing == '1'

    def test_b3_inject(self):
        codec = Codec()

        with self.assertRaises(InvalidCarrierException):
            codec.inject(None, [])

        ctx = SpanContext(trace_id='463ac35c9f6413ad48485a3953bb6124', span_id='a2fb4a1d1a96d312', testing='1')
        carrier = {}
        codec.inject(ctx, carrier)
        self.assertEqual({'X-B3-SpanId': 'a2fb4a1d1a96d312',
                          'X-B3-TraceId': '463ac35c9f6413ad48485a3953bb6124', 'X-Testing': '1'}, carrier)

    def test_extract_inject_exceptions(self):
        tracer = global_tracer()
        with self.assertRaises(UnsupportedFormatException):
            tracer.extract(Format.BINARY, {})
        ctx = SpanContext(None, None, None)
        with self.assertRaises(UnsupportedFormatException):
            tracer.inject(ctx, Format.BINARY, {})
