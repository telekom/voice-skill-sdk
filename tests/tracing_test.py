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
from skill_sdk.tracing import initialize_tracer, set_global_tracer, start_span, start_active_span


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
