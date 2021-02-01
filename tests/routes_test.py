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
import pathlib
import unittest
import importlib
import configparser
from io import StringIO
from json import loads, JSONDecodeError
from types import SimpleNamespace
from unittest.mock import patch, mock_open
from bottle import HTTPResponse
from opentracing.scope import Scope
import requests_mock

import skill_sdk
from skill_sdk import l10n
from skill_sdk.__version__ import __version__, __spi_version__
from skill_sdk.routes import info
from skill_sdk.config import Config

test_config = Config()
test_config['skill'] = {'name': 'testingskill',
                        'intents': 'intents/*.json',
                        'version': 1,
                        'auth': 'basic',
                        'api_key': '0123456789'}


def token_error_intent(context, location=None):
    from skill_sdk.intents import InvalidTokenError
    raise InvalidTokenError()


def error_intent(context, location):
    raise OSError()


class TestInfo(unittest.TestCase):

    @patch('skill_sdk.config.config', new=test_config)
    def setUp(self):
        from skill_sdk import routes
        importlib.reload(skill_sdk.routes)
        self.request = SimpleNamespace()
        self.request.headers = {'Authorization': 'Basic Q1ZJOjAxMjM0NTY3ODk='}

    @patch('skill_sdk.l10n.translations', {'de': None})
    def test_info(self, *_):
        with patch('skill_sdk.routes.request', new=self.request):
            result = loads(info())
            self.assertEqual(result, {"skillId": "testingskill", "skillVersion": f"1 {__version__}", "skillSpiVersion": __spi_version__, 'supportedLocales': ['de']})
            with patch.object(skill_sdk.routes.config, 'get', side_effect=configparser.NoOptionError('skill', 'version')):
                result = info()
                self.assertEqual(result.status_code, 500)
                data = loads(result.body)
                self.assertEqual(data['code'], 999)
                self.assertEqual(data['text'], 'internal error')

    @patch('skill_sdk.l10n.translations', {'en': None})
    @patch('skill_sdk.routes.config', new=test_config)
    def test_info_two_letter_locale(self, *_):
        with patch('skill_sdk.routes.request', new=self.request):
            from skill_sdk.routes import info
            result = loads(info())
            self.assertEqual(result, {"skillId": "testingskill", "skillVersion": f"1 {__version__}", "skillSpiVersion": __spi_version__, 'supportedLocales': ['en']})

    @patch('skill_sdk.routes.config', new=test_config)
    def test_info_wrong_authentication(self):
        from skill_sdk.routes import info

        self.request.headers = {'Authorization': 'Basic Y3ZpOjEyMzQ1Njc4OTA='}
        with patch('skill_sdk.routes.request', new=self.request), \
             patch('skill_sdk.routes.logger.warning') as log_warning, \
             patch('skill_sdk.routes.logger.debug') as log_debug:
            result = info()
            self.assertIsInstance(result, HTTPResponse)
            self.assertEqual(result.status_code, 401)
            log_debug.assert_called_with('Basic auth decoded: cvi/1234567890. NOT authorized.')
            log_warning.assert_called_with('401 raised, returning: access denied.')

        self.request.headers = {'Authorization': 'Basic 92736r87263r87263r8'}
        with patch('skill_sdk.routes.request', new=self.request), \
             patch('skill_sdk.routes.logger.debug') as log_debug:
            result = info()
            self.assertIsInstance(result, HTTPResponse)
            self.assertEqual(result.status_code, 401)
            log_debug.assert_any_call('Error authenticating request: Incorrect padding')

        self.request.headers = {'Authorization': 'Digest Y3ZpOjEyMzQ1Njc4OTA='}
        with patch('skill_sdk.routes.request', new=self.request), \
             patch('skill_sdk.routes.logger.warning') as log_warning:
            result = info()
            self.assertIsInstance(result, HTTPResponse)
            self.assertEqual(result.status_code, 401)
            log_warning.assert_any_call('Authorization [Digest] is not accepted.')

    @patch('skill_sdk.routes.config', new=test_config)
    def test_api_base_config(self):
        from skill_sdk.routes import api_base
        self.assertEqual(api_base(), '/v1/testingskill')
        test_config['skill']['api_base'] = '/new/base'
        with patch.object(skill_sdk.routes, 'config', new=test_config):
            self.assertEqual(api_base(), '/new/base')

    @requests_mock.mock()
    @patch.object(logging.Logger, 'debug')
    @patch('skill_sdk.routes.config', new=test_config)
    def test_reported_locales(self, req_mock, log_mock):
        """ https://gard.telekom.de/gard/browse/HMPOP-253: incorrect locales reported """

        l10n.translations = {}
        self.assertEqual({"skillId": "testingskill", "skillVersion": f"1 {__version__}",
                          "skillSpiVersion": __spi_version__, 'supportedLocales': []}, loads(info()))

        from tests.l10n_test import EMPTY_MO_DATA

        with patch('skill_sdk.l10n.pathlib.Path.open', mock_open(read_data=EMPTY_MO_DATA), create=True), \
                patch('skill_sdk.l10n.config.resolve_glob', return_value=[pathlib.Path('zh.mo')]):
            l10n.translations = l10n.load_translations()

        self.assertEqual({"skillId": "testingskill", "skillVersion": f"1 {__version__}",
                          "skillSpiVersion": __spi_version__, 'supportedLocales': ['zh']}, loads(info()))


class TestInvoke(unittest.TestCase):

    @patch('random.randint', return_value='answer')
    def setUp(self, mock_gde):
        mock_gde.__name__ = 'mock_gde'
        from skill_sdk import routes
        from skill_sdk.intents import Intent
        importlib.reload(skill_sdk.routes)

        self.request = SimpleNamespace()
        self.request.headers = {'Authorization': 'Basic Q1ZJOjAxMjM0NTY3ODk='}
        self.request.json = {
            "context": {
                "attributes": {'location': 'Berlin'},
                "intent": "TELEKOM_Demo_Intent",
                "locale": "de",
                "tokens": {},
                "clientAttributes": {}
            },
            "session": {
                "new": True,
                "id": "12345",
                "attributes": {
                    "key-1": "value-1",
                    "key-2": "value-2"
                }
            },
            "version": 1
        }
        self.intent = Intent("TELEKOM_Demo_Intent", random.randint)

    def test_invoke(self):
        with patch('skill_sdk.routes.request', new=self.request), \
                patch.object(skill_sdk.skill.Skill, '_intents', new={'TELEKOM_Demo_Intent': self.intent}):
            from skill_sdk.routes import invoke
            result = invoke()
        self.assertEqual(result.status_code, 200)

    def test_invoke_invalid_token(self):
        intent = self.intent
        intent.implementation = token_error_intent
        with patch('skill_sdk.routes.request', new=self.request), \
                patch.object(skill_sdk.skill.Skill, '_intents', new={'TELEKOM_Demo_Intent': intent}):
            from skill_sdk.routes import invoke
            result = invoke()
        self.assertEqual(result.status_code, 400)

    def test_invoke_other_error(self):
        intent = self.intent
        intent.implementation = error_intent
        with patch('skill_sdk.routes.request', new=self.request), \
                patch.object(skill_sdk.skill.Skill, '_intents', new={'TELEKOM_Demo_Intent': intent}):
            from skill_sdk.routes import invoke
            result = invoke()
        self.assertEqual(result.status_code, 400)

    def test_invoke_no_context(self):
        intent = self.intent
        intent.implementation = error_intent
        self.request.json = ''
        with patch('skill_sdk.routes.request', new=self.request), \
                patch.object(skill_sdk.skill.Skill, '_intents', new={'TELEKOM_Demo_Intent': intent}):
            from skill_sdk.routes import invoke
            result = invoke()
        self.assertEqual(result.status_code, 400)

    def test_invoke_json_decode_error(self):
        intent = self.intent
        intent.implementation = error_intent
        with patch('skill_sdk.routes.request', new=self.request), \
                patch('skill_sdk.log.prepare_for_logging', side_effect=JSONDecodeError('', '', 0)), \
                patch.object(skill_sdk.skill.Skill, '_intents', new={'TELEKOM_Demo_Intent': intent}):
            from skill_sdk.routes import invoke
            result = invoke()
        self.assertEqual(result.status_code, 400)

    @patch('skill_sdk.l10n.translations', {})
    def test_invoke_translation_error(self):
        with patch('skill_sdk.routes.request', new=self.request), patch('skill_sdk.l10n.logger') as fake_log:
            from skill_sdk.routes import invoke
            result = invoke()
            self.assertEqual(result.status_code, 404)
            fake_log.error.assert_called_with('A translation for locale %s is not available.', 'de')

    def test_invoke_intent_not_found(self):
        self.request.json = {
            "context": {
                "attributes": {...},
                "intent": "TELEKOM_Demo_Intent",
                "locale": "de",
                "tokens": {},
                "clientAttributes": {}
            },
            "session": {
                "new": True,
                "id": "12345",
                "attributes": {
                    "key-1": "value-1",
                    "key-2": "value-2"
                }
            },
            "version": 1
        }
        with patch('skill_sdk.routes.request', new=self.request):
            from skill_sdk.routes import invoke
            result = invoke()
        self.assertEqual(result.status_code, 404)

    def test_invoke_exception(self):
        with patch('skill_sdk.routes.Context', side_effect=SyntaxError), \
             patch('skill_sdk.routes.request', new=self.request):
            from skill_sdk.routes import invoke
            result = invoke()
        self.assertEqual(result.status_code, 500)

    @patch('skill_sdk.routes.logger')
    def test_no_token_logging(self, logger_mock):
        self.request.json['context']['tokens'] = {"demotoken": "abcdefg"}
        with patch('skill_sdk.routes.request', new=self.request), \
                patch.object(skill_sdk.skill.Skill, '_intents', new={'TELEKOM_Demo_Intent': self.intent}):
            from skill_sdk.routes import invoke
            invoke()
        log = StringIO()
        [log.write(str(i)) for i in logger_mock.debug.call_args_list]
        self.assertNotIn('abcdefh', log.getvalue())
        self.assertIn('*****', log.getvalue())
        self.assertEqual(self.request.json['context']['tokens'], {"demotoken": "abcdefg"})

    @patch.object(Scope, 'close')
    def test_invoke_close_tracing_scope(self, close_scope):
        """ Ensure tracing scope is closed when invoke is complete """

        with patch('skill_sdk.routes.request', new=self.request), \
                patch.object(skill_sdk.skill.Skill, '_intents', new={'TELEKOM_Demo_Intent': self.intent}):
            from skill_sdk.routes import invoke
            result = invoke()

        close_scope.assert_called_once()


class TestErrors(unittest.TestCase):

    def test_error_400(self):
        from skill_sdk.routes import json_400
        result = json_400(None)
        self.assertIsInstance(result, HTTPResponse)
        data = loads(result.body)
        self.assertEqual(data['code'], 3)
        self.assertEqual(data['text'], 'Bad request!')

    def test_error_404(self):
        from skill_sdk.routes import json_404
        result = json_404(None)
        self.assertIsInstance(result, HTTPResponse)
        data = loads(result.body)
        self.assertEqual(data['code'], 1)
        self.assertEqual(data['text'], 'Not Found!')

    def test_error_500(self):
        from skill_sdk.routes import json_500
        result = json_500(None)
        self.assertIsInstance(result, HTTPResponse)
        data = loads(result.body)
        self.assertEqual(data['code'], 999)
        self.assertEqual(data['text'], 'internal error')

    @patch.object(logging.Logger, 'warning')
    def test_auth_warning(self, warn_mock):
        conf = Config()
        conf['skill'] = {'name': 'testingskill',
                        'intents': 'intents/*.json',
                        'version': 1,
                        'auth': 'basic'}
        with patch('skill_sdk.config.config', new=conf):
            from skill_sdk import routes
            importlib.reload(skill_sdk.routes)
            warn_mock.assert_called_with('Please set api_key in skill.conf! Proceeding without authentication....')
