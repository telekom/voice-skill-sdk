#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#
import sys
import unittest
from json import loads
from logging import makeLogRecord, INFO
from unittest.mock import patch

from skill_sdk import tracing
from skill_sdk import log

test_context = tracing.SpanContext('abcd', '1234', '1')


class TestSmartHubGELFFormatter(unittest.TestCase):

    def setUp(self):
        # Re-init the tracer to reset a current span, that might have been activated by previous tests
        tracing.initialize_tracer()

        self.record = makeLogRecord({
            'levelno': INFO,
            'levelname': 'INFO',
            'thread': '123456',
            'name': 'demo.logger',
            'msg': 'testmessage',
            'audience': 'development',
        })

    def test_format(self):
        data = loads(log.SmartHubGELFFormatter().format(self.record))
        self.assertGreater(data['@timestamp'], 1490000000000)
        self.assertIn('process', data)
        self.assertEqual(data['tenant'], 'unnamed-skill')
        self.assertEqual(data['thread'], '123456')
        self.assertEqual(data['message'], 'testmessage')
        self.assertEqual(data['level'], "INFO")
        self.assertNotIn('audience', data)
        self.assertEqual(data['logger'], 'demo.logger')
        self.assertNotIn('intention', data)
        self.assertEqual(data['traceId'], None)
        self.assertEqual(data['spanId'], None)

    def test_format_exception(self):
        self.record.exc_info = True
        try:
            1 / 0
        except:
            data = loads(log.SmartHubGELFFormatter().format(self.record))
            self.assertIn('ZeroDivisionError', data['_traceback'])


class TestLogLevels(unittest.TestCase):

    def setUp(self):
        if 'skill_sdk.services.log' in sys.modules:
            del sys.modules['skill_sdk.services.log']

    def test_log_level_environment_not_set(self):
        from skill_sdk.services.log import LOG_LEVEL
        self.assertEqual(LOG_LEVEL, "ERROR")

    @patch('os.environ', new={'SPAN_TAG_ENVIRONMENT': 'prod'})
    def test_log_level_unknown(self):
        from skill_sdk.services.log import LOG_LEVEL
        self.assertEqual(LOG_LEVEL, "ERROR")

    @patch('os.environ', new={'SPAN_TAG_ENVIRONMENT': 'skill-edge'})
    def test_log_level_skill_edge(self):
        from skill_sdk.services.log import LOG_LEVEL
        self.assertEqual(LOG_LEVEL, "DEBUG")

    @patch('os.environ', new={'SPAN_TAG_ENVIRONMENT': 'staging'})
    def test_log_level_staging(self):
        from skill_sdk.services.log import LOG_LEVEL
        self.assertEqual(LOG_LEVEL, "DEBUG")

    @patch('os.environ', new={'SPAN_TAG_ENVIRONMENT': 'integration'})
    def test_log_level_integration(self):
        from skill_sdk.services.log import LOG_LEVEL
        self.assertEqual(LOG_LEVEL, "DEBUG")


class TestHelperFunctions(unittest.TestCase):

    def test_get_logger(self):
        import logging
        logger = log.get_logger('test')
        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, 'test')
        logger = log.get_logger()
        self.assertEqual(logger.name, __name__.split('.')[-1])

    @unittest.skipIf(sys.platform.startswith("win"), "Windows cannot gunicorn")
    def test_gunicorn_logger(self):
        from types import SimpleNamespace
        from skill_sdk.log import GunicornLogger, SmartHubGELFFormatter
        logger = GunicornLogger(SimpleNamespace(errorlog='-'))
        self.assertIsInstance(logger, GunicornLogger)
        self.assertEqual(logger.error_log.name, 'gunicorn')
        [self.assertIsInstance(handler.formatter, SmartHubGELFFormatter) for handler in logger.error_log.handlers]
        [self.assertIsInstance(handler.formatter, SmartHubGELFFormatter) for handler in logger.access_log.handlers]

    def test_prepare_for_logging(self):
        from skill_sdk.log import prepare_for_logging, LOG_ENTRY_MAX_STRING
        request_json = {
            "context": {
                "attributes": {'location': ['A' * 1000, 'B' * 1000]},
                "attributesV2": {'location': [{'value': 'A' * 1000}, {'value': 'B' * 1000}]},
            },
        }

        request = prepare_for_logging(request_json)
        self.assertEqual(request['context']['attributes']['location'],
                         ['A' * LOG_ENTRY_MAX_STRING + '...', 'B' * LOG_ENTRY_MAX_STRING + '...'])
        self.assertEqual(request['context']['attributesV2']['location'],
                         [{'value': 'A' * LOG_ENTRY_MAX_STRING + '...'}, {'value': 'B' * LOG_ENTRY_MAX_STRING + '...'}])

    def test_hide_tokens(self):
        from skill_sdk.log import prepare_for_logging
        original = {
            "context": {
                "tokens": {'cvi': 'eyJblablabla'},
            },
        }
        request = prepare_for_logging(original)
        self.assertEqual(original, {"context": {"tokens": {"cvi": "eyJblablabla"}}})
        self.assertEqual(request, {"context": {"tokens": {"cvi": "*****"}}})
        self.assertEqual(prepare_for_logging(dict(value='Immutable Chuck Norris')), dict(value='Immutable Chuck Norris'))
