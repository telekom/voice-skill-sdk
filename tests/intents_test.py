#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#
import random
import logging
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import skill_sdk
from skill_sdk import l10n
from skill_sdk.intents import Intent, Context
from skill_sdk.responses import RESPONSE_TYPE_TELL, Response, ErrorResponse
from skill_sdk.test_helpers import create_context
from skill_sdk.tracing import Tracer

from circuitbreaker import CircuitBreakerError, CircuitBreaker
from requests.exceptions import RequestException

l10n.translations = {'de': l10n.Translations()}
logger = logging.getLogger(__name__)


class TestIntent(unittest.TestCase):

    def setUp(self):
        request = SimpleNamespace()
        request.json = {"context": {"attributes": {},
                                    "intent": "TELEKOM_Demo_Intent",
                                    "locale": "de",
                                    "tokens": {}},
                        "session": {"new": True,
                                    "id": "12345",
                                    "attributes": {"key-1": "value-1",
                                                   "key-2": "value-2"}},
                        }
        request.headers = {}
        self.ctx = Context(request)
        self.ctx.tracer = Tracer(request)

    @patch.object(logging.Logger, 'warning')
    def test_init_exceptions(self, warn_mock):
        with self.assertRaises(TypeError):
            Intent({})
        with self.assertRaises(ValueError):
            Intent('', None)
        with self.assertRaises(ValueError):
            Intent('demo_intent', 'random.does_not_exist')

    @patch('random.randint', return_value=1)
    def test_call_bad_return_type(self, mock_gde):
        mock_gde.__name__ = 'mock_gde'
        intent = Intent('TELEKOM_Demo_Intent', random.randint)
        with self.assertRaises(ValueError):
            intent(self.ctx).dict(self.ctx)

    @patch('random.randint', return_value=ErrorResponse(999, 'some error'))
    def test_call_error_999(self, mock_gde):
        mock_gde.__name__ = 'mock_gde'
        intent = Intent('TELEKOM_Demo_Intent', random.randint)
        self.assertIsInstance(intent(self.ctx), ErrorResponse)

    @patch('random.randint', side_effect=RequestException())
    def test_call_requests_error(self, mock_gde):
        mock_gde.__name__ = 'mock_gde'
        intent = Intent('TELEKOM_Demo_Intent', random.randint)
        response = intent(self.ctx)
        self.assertIsInstance(response, Response)
        self.assertEqual(response.text, 'GENERIC_HTTP_ERROR_RESPONSE')

    @patch('random.randint', side_effect=CircuitBreakerError(CircuitBreaker()))
    def test_call_circuit_breaker_open(self, mock_gde):
        mock_gde.__name__ = 'mock_gde'
        intent = Intent('TELEKOM_Demo_Intent', random.randint)
        response = intent(self.ctx)
        self.assertIsInstance(response, Response)
        self.assertEqual(response.text, 'GENERIC_HTTP_ERROR_RESPONSE')

    @patch('random.randint', return_value=Response(text='some text', type_=RESPONSE_TYPE_TELL))
    def test_append_push_messages_empty(self, mock_gde):
        mock_gde.__name__ = 'mock_gde'
        context = create_context('TELEKOM_Demo_Intent')
        intent = Intent('TELEKOM_Demo_Intent', random.randint)
        response = intent(context)
        response = intent._append_push_messages(context, response)
        self.assertEqual(response.push_notification, None)

    @patch('random.randint', return_value=Response(text='some text', type_=RESPONSE_TYPE_TELL))
    def test_append_push_messages_one(self, mock_gde):
        mock_gde.__name__ = 'mock_gde'
        context = create_context('TELEKOM_Demo_Intent')
        intent = Intent('TELEKOM_Demo_Intent', random.randint)
        response = intent(context)
        context.push_messages = {'device': [{'payload': 1}]}
        response = intent._append_push_messages(context, response)
        self.assertEqual(response.push_notification,
                         {'targetName': 'device', 'messagePayload': {'payload': 1}})

    @patch('random.randint', return_value=Response(text='some text', type_=RESPONSE_TYPE_TELL))
    def test_append_push_messages_two_messages(self, mock_gde):
        mock_gde.__name__ = 'mock_gde'
        context = create_context('TELEKOM_Demo_Intent')
        intent = Intent('TELEKOM_Demo_Intent', random.randint)
        response = intent(context)
        context.push_messages = {'device': [{'payload': 1}, {'payload': 2}]}
        with self.assertRaises(ValueError):
            _ = intent._append_push_messages(context, response)

    @patch('random.randint', return_value=Response(text='some text', type_=RESPONSE_TYPE_TELL))
    def test_append_push_messages_two_devices(self, mock_gde):
        mock_gde.__name__ = 'mock_gde'
        context = create_context('TELEKOM_Demo_Intent')
        intent = Intent('TELEKOM_Demo_Intent', random.randint)
        response = intent(context)
        context.push_messages = {'device': [{'payload': 1}], 'device2': [{'payload': 2}]}
        with self.assertRaises(ValueError):
            _ = intent._append_push_messages(context, response)

    def test_repr(self):
        self.assertIn('TELEKOM_Demo_Intent', repr(Intent('TELEKOM_Demo_Intent', random.randint)))

    def test_response_returns_message(self):
        """ Test if context._ returns l10n.Message
        """
        l10n.translations = {'de': l10n.Translations()}
        context = create_context('TELEKOM_Demo_Intent')
        with patch('random.randint', return_value=Response(text=context._('some text'))) as mock_gde:
            mock_gde.__name__ = 'mock_gde'
            intent = Intent('TELEKOM_Demo_Intent', random.randint)
            response = intent(context)
            self.assertIsInstance(response.text, l10n.Message)
