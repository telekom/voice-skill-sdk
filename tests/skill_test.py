#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#
import types
import bottle
import logging
import datetime
import unittest
import importlib
from unittest.mock import patch

import skill_sdk
from skill_sdk import l10n, log
from skill_sdk.config import Config
from skill_sdk.skill import intent_handler, configure_logging, test_intent
from skill_sdk.test_helpers import create_context

import requests_mock

test_config = Config()
test_config['http'] = {'port': 4242}

l10n.translations = {'de': l10n.Translations()}


# Dummy intent handler to prevent RuntimeError
@intent_handler('dummy')
def dummy():
    ...


class TestPatch(unittest.TestCase):

    def test_patch_bottle(self):
        configure_logging()
        self.assertIsInstance(bottle._stdout, types.LambdaType)
        self.assertIsInstance(bottle._stderr, types.LambdaType)
        self.assertEqual(bottle._stdout('Test'), None)
        self.assertEqual(bottle._stderr('Test'), None)
        with patch('skill_sdk.log.LOG_FORMAT', new='human'):
            configure_logging()


class TestSkill(unittest.TestCase):

    def test_initialize(self, *args):
        from skill_sdk.skill import initialize, set_dev_mode
        with patch('skill_sdk.skill.set_dev_mode') as dev_mock, patch('skill_sdk.l10n.translations', new=None):
            initialize(dev=True, local=True, cache=True)
            from skill_sdk.caching import decorators
            self.assertTrue(decorators.CACHES_ACTIVE)
            from skill_sdk import requests
            self.assertTrue(requests.USE_LOCAL_SERVICES)
            dev_mock.assert_called_once()

        with patch('skill_sdk.services.setup_services') as serv_mock:
            initialize(dev=False, local=False, cache=False)
            from skill_sdk.caching import decorators
            self.assertFalse(decorators.CACHES_ACTIVE)
            from skill_sdk import requests
            self.assertFalse(requests.USE_LOCAL_SERVICES)
            serv_mock.assert_called_once()

        with patch('skill_sdk.services.setup_services', side_effect=ModuleNotFoundError):
            initialize(dev=False, local=False, cache=False)

        with patch('builtins.__import__', side_effect=ModuleNotFoundError()), \
             patch.object(logging.Logger, 'warning') as warn_mock:
            set_dev_mode()
            warn_mock.assert_any_call('Starting bottle with WSGIRefServer. Do not use in production!')
            warn_mock.assert_called_with('Swagger UI not found, starting without...')

        with patch.object(skill_sdk.skill.Skill, 'get_intents', return_value=0):
            with self.assertRaises(RuntimeError):
                initialize(dev=False, local=False, cache=False)

    def test_max_request_size(self):
        self.assertEqual(bottle.BaseRequest.MEMFILE_MAX, 102400)

        max_request_size_config = Config()
        max_request_size_config['skill']['max_request_size'] = '1'
        max_request_size_config.merge_intents = lambda *a: True
        with patch('skill_sdk.skill.set_dev_mode'), patch('skill_sdk.services.setup_services'):
            with patch('skill_sdk.skill.config', new=max_request_size_config):
                from skill_sdk.skill import initialize
                initialize()
                self.assertEqual(bottle.BaseRequest.MEMFILE_MAX, 1)

    def test_intent_handler(self):

        # Test single decorator
        @intent_handler('Test_Intent')
        def decorated_test(date_str: str = None, date_date: datetime.date = None):
            return date_str, date_date

        ctx = create_context('Test_Intent',
                             date_str=['2001-12-31', '2001-12-31', ], date_date=['2001-12-31', '1001-12-31', ])
        result = decorated_test(ctx)
        self.assertEqual(result, ('2001-12-31', datetime.date(2001, 12, 31)))

        # Test stacked decorators
        @intent_handler('Test_Intent1')
        @intent_handler('Test_Intent2')
        @intent_handler('Test_Intent3')
        def decorated_test(date: datetime.date = None):
            return date
        ctx = create_context('Test_Intent1', date=['2001-12-31'])
        result = decorated_test(ctx)
        self.assertEqual(result, datetime.date(2001, 12, 31))

        from skill_sdk.services.location import Location
        @intent_handler('Test_Intent4')
        def decorated_test(on_off: bool = False, date: datetime.date = None, location: Location = None):
            return f"It is {on_off} in {location.text} at {location.coordinates} on {date.strftime('%c')}"

        ctx = create_context('Test_Intent4', on_off=['Yes', 'No'], date=['2012-12-31', '2022-01-31'], location=['Berlin'])
        with requests_mock.Mocker() as req_mock:
            req_mock.get('http://service-location-service:1555/v1/location/geo',
                         text='{"lat": 50.0, "lng": 8.0, "timeZone": "Europe/Berlin"}')
            result = decorated_test(ctx)
            self.assertEqual(result, 'It is True in Berlin at (50.0, 8.0) on Mon Dec 31 00:00:00 2012')

        # Duplicate intent handler: should raise ValueError
        with self.assertRaises(ValueError):
            @intent_handler('Test_Intent4')
            def dummy():
                pass

    def test_test_intent_helper(self):

        @intent_handler('Test_Another_Intent')
        def decorated_test(date_str: str = None):
            return date_str

        result = test_intent('Test_Another_Intent', date_str=['2001-12-31', '2012-12-31', ])
        self.assertEqual(result.text, '2001-12-31')

    @patch('skill_sdk.skill.config', new=test_config)
    def test_run(self, *args):
        from skill_sdk.skill import Skill, configure_logging
        with patch.object(Skill, 'run') as run_mock:
            from skill_sdk.skill import run
            run(dev=False, local=False, cache=False, host='here-be-the-dragons')
            run_mock.assert_called_once_with(host='here-be-the-dragons')

        from bottle import Bottle
        with patch('os.environ', new={'LOG_FORMAT': 'gelf'}), patch.object(Bottle, 'run') as run_mock:
            importlib.reload(skill_sdk.log)
            configure_logging()
            from skill_sdk.skill import run
            run(host='here-be-the-dragons')
            run_mock.assert_called_once_with(host='here-be-the-dragons', port='4242',
                                             logger_class='skill_sdk.log.GunicornLogger')
