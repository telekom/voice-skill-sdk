#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#

########################################################################################################################
#                                                                                                                      #
#   Full functional test:                                                                                              #
#                                                                                                                      #
#   This test starts the web server in a separate thread and tries to reach two endpoints:                             #
#       - GET /v1/test/info                                                                                            #
#       - POST /v1/test                                                                                                #
#                                                                                                                      #
#   If you attempt to run it along with the other unit tests, it will most probably fail,                              #
#   because they pollute the global `config` object. The test should be run in isolation                               #
#                                                                                                                      #
########################################################################################################################

""" Monkey-patch as early as possible  """
import skill_sdk

import sys
import gevent
import requests
import unittest
import importlib
from typing import List
import requests_mock

from unittest.mock import patch
from skill_sdk import intents, l10n, log, skill
from skill_sdk.__version__ import __version__, __spi_version__
from skill_sdk.l10n import _
from skill_sdk.config import Config
from skill_sdk import test_helpers

l10n.translations = {'de': l10n.Translations(), 'en': l10n.Translations()}
l10n.translations['de']._catalog['HELLO'] = 'Hallo Welt!'
l10n.translations['en']._catalog['HELLO'] = 'Hello World!'


@skill.intent_handler('HELLO_INTENT')
def hello():
    return _('HELLO')


@skill.intent_handler('DRAGONS_INTENT')
def dragons(dragon_list: List[str]):
    return _('DRAGONS')


@skill.intent_handler(skill.FALLBACK_INTENT)
def fallback(ctx: intents.Context):
    return f'Python Skill SDK v{__version__} Fallback Handler: {ctx.attributes}'


config = Config()

config.read_dict({
    'skill': {
        'name': 'test',
        'id': 'test',
        'version': '1',
        'debug': 'no'
    },
    'http': {
        'server': 'gunicorn',
    }
})

SKILL_URL = 'http://localhost:4242/v1/test'


class TestRunnerFunctions(unittest.TestCase):

    @patch('skill_sdk.config.config', new=config)
    @patch('skill_sdk.skill.config', new=config)
    @patch('gevent.spawn', side_effect=ModuleNotFoundError())
    @patch.dict('sys.modules', {'skill_sdk.services': ModuleNotFoundError()})
    @patch.dict('sys.modules', {'skill_sdk.services.prometheus': ModuleNotFoundError()})
    @patch.dict('sys.modules', {'skill_sdk.services.k8s': ModuleNotFoundError()})
    def test_setup_services_module_not_found(self, *args):
        """ This unit test is used just to cover ModuleNotFoundError exceptions

        """
        from skill_sdk.skill import initialize
        initialize(dev=False)


class TestRunnerDev(unittest.TestCase):

    bottle: gevent.Greenlet

    @staticmethod
    @patch('skill_sdk.config.config', new=config)
    @patch('skill_sdk.skill.config', new=config)
    def bottle_run():
        from skill_sdk import skill
        skill.run(dev=True, local=False)

    @classmethod
    def setUpClass(cls):
        cls.bottle = gevent.spawn(cls.bottle_run)
        gevent.sleep(0)

    @classmethod
    def tearDownClass(cls):
        while not cls.bottle.dead:
            cls.bottle.kill(exception=KeyboardInterrupt)
            gevent.sleep(0)

    def test_info_response(self):
        """ Get an "info" response
        """
        response = requests.get(f'{SKILL_URL}/info')
        self.assertTrue(response.ok)
        self.assertEqual(response.json(), {
            'skillId': 'test',
            'skillSpiVersion': __spi_version__,
            'skillVersion': f'1 {__version__}',
            'supportedLocales': ['de', 'en']
        })

    def test_not_found_response(self):
        """ Get 404 response to wrong request
        """
        response = requests.get('http://localhost:4242/path/that/do/not/exists')
        self.assertFalse(response.ok)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {'code': 1, 'text': 'Not Found!'})

    def test_intent_invoke_response(self):
        """ Check response to HELLO_INTENT invocation
        """
        payload = {"context": {"intent": "HELLO_INTENT", "locale": "de"}}
        response = requests.post(SKILL_URL, json=payload)
        self.assertTrue(response.ok)
        self.assertEqual(response.json()['text'], 'Hallo Welt!')
        payload = {"context": {"intent": "HELLO_INTENT", "locale": "en"}}
        response = requests.post(SKILL_URL, json=payload)
        self.assertTrue(response.ok)
        self.assertEqual(response.json()['text'], 'Hello World!')

    def test_fallback_intent_invoke_response(self):
        """ Get response to FALLBACK_INTENT
        """
        payload = test_helpers.create_context("UNKNOWN_INTENT", arg1=["arg1"], arg2=["arg2"]).request.json
        response = requests.post(SKILL_URL, json=payload)
        self.assertTrue(response.ok)
        self.assertEqual(response.json()['text'],
                         f"Python Skill SDK v{__version__} Fallback Handler: "
                         f"{{'arg1': ['arg1'], 'arg2': ['arg2'], 'timezone': ['Europe/Berlin']}}")


@unittest.skipIf(sys.platform.startswith("win"), "Windows cannot gunicorn")
class TestRunnerProd(TestRunnerDev):

    req_mock: requests_mock.Mocker

    @staticmethod
    @patch('skill_sdk.config.config', new=config)
    @patch('skill_sdk.skill.config', new=config)
    def bottle_run():
        config['service-text'] = {'update-interval': 0.5}
        from skill_sdk import skill
        with patch.dict('sys.modules', swagger_ui=None), requests_mock.Mocker(real_http=True) as req_mock:
            req_mock.get('http://service-text-service:1555/v1/text/info/scope/test',
                         text='{"supportedLanguages": [{"code": "de"}, {"code": "en"}]}')
            req_mock.get('http://service-text-service:1555/v1/text/de/test',
                         text='[{"locale": "de","scope": "test",'
                              '"sentences": ["Hallo Welt!"],'
                              '"tag": "HELLO"}]')
            req_mock.get('http://service-text-service:1555/v1/text/en/test',
                         text='[{"locale": "en","scope": "test",'
                              '"sentences": ["Hello World!"],'
                              '"tag": "HELLO"}]')
            TestRunnerProd.req_mock = req_mock
            l10n.translations = {}
            skill.run(dev=False, local=False, cache=False)

    def test_prometheus_response(self):
        """ Check response prometheus metrics request
        """
        response = requests.get('http://localhost:4242/prometheus')
        self.assertTrue(response.ok)

    def test_text_service_reload(self):
        payload = {"context": {"intent": "DRAGONS_INTENT", "locale": "de"}}
        response = requests.post(SKILL_URL, json=payload)
        self.assertTrue(response.ok)
        self.assertEqual(response.json()['text'], 'DRAGONS')

        self.req_mock.get('http://service-text-service:1555/v1/text/de/test',
                          text='[{"locale": "de","scope": "test",'
                               '"sentences": ["Hallo Welt!"],'
                               '"tag": "HELLO"}, '
                               ' {"locale": "de", "scope": "test",'
                               '"sentences": ["Here be the dragons"],"tag": "DRAGONS"}]')

        gevent.sleep(0.5)
        response = requests.post(SKILL_URL, json=payload)
        self.assertTrue(response.ok)
        self.assertEqual(response.json()['text'], 'Here be the dragons')


class TestRunnerCrash(unittest.TestCase):

    @patch('skill_sdk.services.text.load_translations_from_server', return_value=None)
    @patch('skill_sdk.config.config', new=config)
    def test_crash_if_no_location_services_available(self, *args):
        """ Check if runner raises exception and does not start if text services are requested and no available
        """
        config.update({'service-text': {'active': True, 'load': 'startup'}})

        with self.assertRaises(l10n.TranslationError), \
                patch('os.environ', new={'LOG_LEVEL': 'CRITICAL'}):     # suppress error message
            importlib.reload(skill_sdk.log)
            from skill_sdk import skill
            skill.run(dev=False, local=False)


class TestZFunctionalTest(unittest.TestCase):
    """ Intentionally named with "Z" to run last:
            the test executes test_helpers.FunctionalTest and runs bottle instance in a thread,
            and we can't kill the bottle thread after the test

    """

    @patch('skill_sdk.config.config', new=config)
    @patch('skill_sdk.skill.config', new=config)
    def test(self):
        import unittest.loader as loader
        config['skill']['auth'] = 'basic'
        config['skill']['api_key'] = 'basic'
        config.update({
            'tests': {'freetext': "'a', ['b']"}
        })
        importlib.reload(skill_sdk.test_helpers)
        func_suite = loader.findTestCases(test_helpers, prefix='default')
        tests = func_suite.countTestCases()
        test_runner = unittest.TextTestRunner()
        result = test_runner.run(func_suite)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.failures, [])
        self.assertEqual(result.skipped, [])
        self.assertEqual(result.testsRun, tests)
