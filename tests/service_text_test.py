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
import logging
from unittest.mock import patch
from configparser import ConfigParser

from skill_sdk import l10n
from skill_sdk.services import base
from skill_sdk.services.text import TextService, MultiStringTranslation, DelayedTranslation, setup_service
from skill_sdk.services.text import load_translations_from_server, translation_reload_worker
from skill_sdk import requests
from requests import exceptions
import requests_mock


class TestSetupService(unittest.TestCase):

    @requests_mock.mock()
    @patch.object(logging.Logger, 'debug')
    @patch('skill_sdk.services.text.config', new_callable=ConfigParser)
    def test_setup_services(self, req_mock, config_mock, log_mock):
        from skill_sdk.services.text import translation_reload_worker, load_translations_from_server
        config_mock['service-text'] = {'load': 'startup'}
        with patch('skill_sdk.services.text.load_translations_from_server', return_value=True):
            with patch('skill_sdk.services.text.threading.Thread') as thread_mock:
                setup_service()
                thread_mock.assert_called_once_with(args=({},), target=translation_reload_worker, daemon=True)

        with patch('skill_sdk.services.text.load_translations_from_server', return_value=None):
            with self.assertRaises(l10n.TranslationError):
                setup_service()

        config_mock['service-text'] = {'load': 'auto'}
        with patch('skill_sdk.services.text.threading.Thread') as thread_mock:
            setup_service()
            thread_mock.assert_any_call(target=load_translations_from_server, args=({},), daemon=True)
            thread_mock.assert_called_with(target=translation_reload_worker, args=({},), daemon=True)

        config_mock['service-text'] = {'load': 'delayed'}
        with patch('skill_sdk.services.text.l10n') as l10n_mock:
            l10n_mock.get_locales.return_value = ['de', 'fr']
            setup_service()
            self.assertIsInstance(l10n_mock.translations['de'], DelayedTranslation)
            self.assertIsInstance(l10n_mock.translations['fr'], DelayedTranslation)


class TestTextService(unittest.TestCase):

    @requests_mock.mock()
    def test_supported_locales(self, req_mock):
        req_mock.get('http://service-text-service:1555/v1/text/info/scope/unnamed-skill',
                     text='{"supportedLanguages": [{"code": "de"}, {"code": "en"}]}')

        service = TextService()
        result = service.supported_locales()
        self.assertEqual(result, ['de', 'en'])

    @requests_mock.mock()
    def test_supported_locales_empty_response(self, req_mock):
        req_mock.get('http://service-text-service:1555/v1/text/info/scope/unnamed-skill', text='{}')
        service = TextService()
        result = service.supported_locales()
        self.assertEqual(result, [])

    @requests_mock.mock()
    def test_supported_locales_invalid_response(self, req_mock):
        req_mock.get('http://service-text-service:1555/v1/text/info/scope/unnamed-skill', text='')
        service = TextService()
        result = service.supported_locales()
        self.assertEqual(result, [])

    @requests_mock.mock()
    def test_supported_locales_requests_exception(self, req_mock):
        req_mock.get('http://service-text-service:1555/v1/text/info/scope/unnamed-skill',
                     exc=exceptions.RequestException)
        service = TextService()
        result = service.supported_locales()
        self.assertEqual(result, [])

    @requests_mock.mock()
    def test_get_translation_catalog_exception(self, req_mock):
        from skill_sdk import requests
        from collections import defaultdict
        req_mock.get('http://service-text-service:1555/v1/text/en/unnamed-skill',
                     exc=requests.BadHttpResponseCodeException(500))
        service = TextService()
        result = service.get_translation_catalog('en')
        self.assertEqual(result, defaultdict(list))

    @patch.object(logging.Logger, 'error')
    @patch('skill_sdk.services.text.config', new_callable=ConfigParser)
    @requests_mock.mock()
    def test_headers(self, config_mock, log_mock, req_mock):
        config_mock['service-text'] = {'auth_header': 'true'}
        service = TextService()

        req_mock.get('http://service-text-service:1555/v1/text/info/scope/unnamed-skill',
                     request_headers={'Accept': 'application/json', 'Content-Type': 'application/json'},
                     text='{"supportedLanguages": [{"code": "aa"}, {"code": "bb"}]}')

        self.assertEqual(['aa', 'bb'], service.supported_locales())
        log_mock.assert_called_once_with(
            'Authorization header is requested, but no CVI token found in the current request.')


    @patch.object(logging.Logger, 'debug')
    @patch('skill_sdk.services.text.config', new_callable=ConfigParser)
    @requests_mock.mock()
    def test_auth_header(self, config_mock, log_mock, req_mock):
        config_mock['service-text'] = {'auth_header': 'true'}
        req_mock.get('http://service-text-service:1555/v1/text/info/scope/unnamed-skill',
                     request_headers={'Accept': 'application/json', 'Content-Type': 'application/json',
                                      'Authorization': 'Bearer eyJ123'})

        with patch('skill_sdk.services.base.request') as r:
            r.json = {"context": {
                "attributes": {'location': 'Berlin'},
                "intent": "TELEKOM_Demo_Intent",
                "locale": "de",
                "tokens": {"cvi": "eyJ123"},
                "clientAttributes": {}
            }}
            TextService().supported_locales()
        log_mock.assert_any_call('Adding CVI token to authorization header.')

    @patch.object(logging.Logger, 'debug')
    @patch('skill_sdk.services.text.config', new_callable=ConfigParser)
    @requests_mock.mock()
    def test_additional_headers(self, config_mock, log_mock, req_mock):
        service = TextService(headers={"Authorization": "Bearer eyJ123"})
        req_mock.get('http://service-text-service:1555/v1/text/info/scope/unnamed-skill',
                     request_headers={'Authorization': 'Bearer eyJ123'},
                     text='{"supportedLanguages": [{"code": "aa"}, {"code": "bb"}]}')

        self.assertEqual(['aa', 'bb'], service.supported_locales())
        log_mock.assert_any_call("Additional headers: {'Authorization': '*****'}")

    @patch.object(TextService, 'supported_locales', return_value=['de', 'fr'])
    @requests_mock.mock()
    def test_load_translations_from_server_ok(self, ts_mock, req_mock):
        req_mock.get('http://service-text-service:1555/v1/text/de/unnamed-skill',
                     text='[{"locale": "de","scope": "unnamed-skill",'
                          '"sentences": ["KEY1", "KEY2"],'
                          '"tag": "KEY"}]')
        req_mock.get('http://service-text-service:1555/v1/text/fr/unnamed-skill',
                     text='[{"locale": "de","scope": "unnamed-skill",'
                          '"sentences": ["KEYA", "KEYB"],'
                          '"tag": "KEY"}]')
        ts = load_translations_from_server(l10n.translations)
        self.assertEqual(ts['de']._catalog['KEY'], ['KEY1', 'KEY2'])
        self.assertEqual(ts['fr']._catalog['KEY'], ['KEYA', 'KEYB'])

    @patch.object(TextService, 'supported_locales', return_value=['de', 'fr'])
    @requests_mock.mock()
    def test_load_translations_from_server_fail(self, ts_mock, req_mock):
        req_mock.get('http://service-text-service:1555/v1/text/de/unnamed-skill',
                     exc=l10n.TranslationError)
        req_mock.get('http://service-text-service:1555/v1/text/fr/unnamed-skill',
                     exc=exceptions.ConnectTimeout)
        with self.assertRaises(l10n.TranslationError):
            load_translations_from_server(l10n.translations)

    @patch.object(TextService, 'supported_locales', return_value=['de'])
    @requests_mock.mock()
    def test_load_translations_from_server_reload_if_exists(self, ts_mock, req_mock):
        req_mock.get('http://service-text-service:1555/v1/text/de/unnamed-skill',
                     text='[{"locale": "de","scope": "unnamed-skill",'
                          '"sentences": ["KEY1", "KEY2"],'
                          '"tag": "KEY"}]')
        import importlib
        import skill_sdk
        importlib.reload(skill_sdk.l10n)
        from skill_sdk.l10n import translations
        ts = load_translations_from_server(translations)
        self.assertEqual(ts['de']._catalog['KEY'], ['KEY1', 'KEY2'])
        self.assertEqual(translations['de']._catalog['KEY'], ['KEY1', 'KEY2'])
        req_mock.get('http://service-text-service:1555/v1/text/de/unnamed-skill',
                     text='[{"locale": "de","scope": "unnamed-skill",'
                          '"sentences": ["SCHLÜSSEL1", "SCHLÜSSEL2"],'
                          '"tag": "KEY"}]')
        load_translations_from_server(translations)
        self.assertEqual(translations['de']._catalog['KEY'], ['SCHLÜSSEL1', 'SCHLÜSSEL2'])

    @patch('skill_sdk.services.text.MultiStringTranslation.reload')
    @patch.object(TextService, 'supported_locales', return_value=['de', 'fr'])
    @requests_mock.mock()
    def test_load_translations_from_server_ready_locks(self, mst_mock, ts_mock, req_mock):
        from skill_sdk.services.k8s import K8sChecks
        self.assertTrue(K8sChecks.ready())
        load_translations_from_server(l10n.translations)
        self.assertTrue(K8sChecks.ready())

    @patch.object(TextService, 'supported_locales')
    @requests_mock.mock()
    def test_load_translations_from_server_full_reload(self, ts_mock, req_mock):
        import importlib
        import skill_sdk
        importlib.reload(skill_sdk.l10n)
        from skill_sdk.l10n import translations

        ts_mock.return_value = []
        load_translations_from_server(translations)
        self.assertEqual(translations, {})

        req_mock.get('http://service-text-service:1555/v1/text/de/unnamed-skill',
                     text='[{"locale": "de","scope": "unnamed-skill",'
                          '"sentences": ["KEY1", "KEY2"],'
                          '"tag": "KEY"}]')

        ts_mock.return_value = ['de']
        load_translations_from_server(translations, reload=True)
        self.assertEqual(translations['de']._catalog['KEY'], ['KEY1', 'KEY2'])

        tr = translations['de']
        load_translations_from_server(translations, reload=True)
        self.assertNotEqual(translations['de'], tr)


class TestMultiStringTranslation(unittest.TestCase):

    def test_init_no_conf(self):
        t = MultiStringTranslation('zh')
        self.assertEqual(t.locale, 'zh')
        self.assertEqual(t._catalog, {})

    @patch('skill_sdk.services.text.config', new_callable=ConfigParser)
    def test_init_only_skill_name(self, config_mock):
        config_mock['skill'] = {'name': 'testingskill'}
        t = MultiStringTranslation('zh')
        self.assertEqual(t.locale, 'zh')
        self.assertEqual(t._catalog, {})

    @patch('skill_sdk.services.text.config', new_callable=ConfigParser)
    def test_init_i18n_scope_name(self, config_mock):
        config_mock['i18n'] = {'scope': 'testingskill'}
        t = MultiStringTranslation('zh')
        self.assertEqual(t.locale, 'zh')
        self.assertEqual(t._catalog, {})

    def test_markgettext(self):
        t = MultiStringTranslation('de')
        t._catalog['KEY'] = ['äöü']
        self.assertEqual(t.markgettext('KEY'), 'KEY')

    def test_lgettext(self):
        t = MultiStringTranslation('de')
        t._catalog['KEY'] = ['äöü']
        self.assertEqual(t.lgettext('KEY'), b'\xc3\xa4\xc3\xb6\xc3\xbc')

    def test_lngettext(self):
        t = MultiStringTranslation('de')
        t._catalog['KEY'] = ['üöä']
        t._catalog['KEY_PLURAL'] = ['äöü']
        self.assertEqual(t.lngettext('KEY', 'KEY_PLURAL', 2), b'\xc3\xa4\xc3\xb6\xc3\xbc')

    def test_gettext_empty_catalog(self):
        t = MultiStringTranslation('de')
        self.assertEqual(t.gettext('ABC'), 'ABC')

    def test_gettext(self):
        t = MultiStringTranslation('de')
        t._catalog['KEY'] = ['VALUE1', 'VALUE2', 'VALUE3']
        self.assertIn(t.gettext('KEY'), ['VALUE1', 'VALUE2', 'VALUE3'])

    def test_ngettext_0(self):
        t = MultiStringTranslation('de')
        t._catalog['KEY'] = ['VALUE1', 'VALUE2', 'VALUE3']
        t._catalog['KEY_PLURAL'] = ['VALUEA', 'VALUEB', 'VALUEC']

        self.assertIn(t.ngettext('KEY', 'KEY_PLURAL', 0), ['VALUEA', 'VALUEB', 'VALUEC'])

    def test_ngettext_1(self):
        t = MultiStringTranslation('de')
        t._catalog['KEY'] = ['VALUE1', 'VALUE2', 'VALUE3']
        t._catalog['KEY_PLURAL'] = ['VALUEA', 'VALUEB', 'VALUEC']

        self.assertIn(t.ngettext('KEY', 'KEY_PLURAL', 1), ['VALUE1', 'VALUE2', 'VALUE3'])

    def test_getalltexts_empty_catalog(self):
        t = MultiStringTranslation('de')
        self.assertEqual(t.getalltexts('ABC'), ['ABC'])

    def test_getalltexts(self):
        t = MultiStringTranslation('de')
        t._catalog['KEY'] = ['VALUE1', 'VALUE2', 'VALUE3']
        self.assertEqual(t.getalltexts('KEY'), ['VALUE1', 'VALUE2', 'VALUE3'])
        from skill_sdk.l10n import _a
        l10n.set_current_locale(t)
        self.assertEqual(_a('KEY'), ['VALUE1', 'VALUE2', 'VALUE3'])

    @requests_mock.mock()
    def test_reload(self, req_mock):
        req_mock.get('http://service-text-service:1555/v1/text/de/unnamed-skill',
                     text='[{"locale": "de","scope": "unnamed-skill",'
                          '"sentences": ["SCHLÜSSEL1", "SCHLÜSSEL2"],'
                          '"tag": "KEY"}]')
        t = MultiStringTranslation('de')
        t.reload()
        self.assertEqual(t._catalog['KEY'], ['SCHLÜSSEL1', 'SCHLÜSSEL2'])

    @requests_mock.mock()
    def test_reload_no_data(self, req_mock):
        req_mock.get('http://service-text-service:1555/v1/text/de/unnamed-skill',
                     text='[]')
        t = MultiStringTranslation('de')
        with self.assertRaises(l10n.TranslationError):
            t.reload()


class TestDelayedTranslation(unittest.TestCase):

    def tearDown(self):
        l10n.translations.clear()

    @requests_mock.mock()
    @patch.object(logging.Logger, 'debug')
    @patch('skill_sdk.services.text.config', new_callable=ConfigParser)
    def test_gettext(self, req_mock, config_mock, log_mock):
        config_mock['service-text'] = {'load': 'delayed'}
        req_mock.get('http://service-text-service:1555/v1/text/info/scope/unnamed-skill',
                     text='{"supportedLanguages": [{"code": "en"}, {"code": "de"}]}')
        req_mock.get('http://service-text-service:1555/v1/text/en/unnamed-skill',
                     text='[{"locale": "en","scope": "unnamed-skill",'
                          '"sentences": ["KEY1", "KEY2"],'
                          '"tag": "KEY"}]')
        req_mock.get('http://service-text-service:1555/v1/text/de/unnamed-skill',
                     text='[{"locale": "de","scope": "unnamed-skill",'
                          '"sentences": ["SCHLÜSSEL1", "SCHLÜSSEL2"],'
                          '"tag": "KEY"}, '
                          ' {"locale": "de", "scope": "unnamed-skill",'
                          '"sentences": ["Die Arzte"],"tag": "KEY_PLURAL"}]')
        t = DelayedTranslation('de')
        self.assertIn(t.gettext('KEY'), ["SCHLÜSSEL1", "SCHLÜSSEL2"])
        log_mock.assert_any_call('Catalog for de is empty. Loading translations...')
        log_mock.assert_called_with("2 candidates: ['SCHLÜSSEL1', 'SCHLÜSSEL2']")
        self.assertEqual(t.getalltexts('KEY'), ["SCHLÜSSEL1", "SCHLÜSSEL2"])
        self.assertEqual(t.getalltexts('KEY'), ["SCHLÜSSEL1", "SCHLÜSSEL2"])
        self.assertEqual(t.ngettext('KEY', 'KEY_PLURAL', 2), 'Die Arzte')

    @requests_mock.mock()
    @patch.object(logging.Logger, 'warning')
    @patch('skill_sdk.services.text.config', new_callable=ConfigParser)
    def test_gettext_exception(self, req_mock, config_mock, log_mock):
        config_mock['service-text'] = {'load': 'delayed'}
        req_mock.get('http://service-text-service:1555/v1/text/info/scope/unnamed-skill',
                     exc=requests.BadHttpResponseCodeException(500))
        t = DelayedTranslation('de')
        self.assertEqual(t.gettext('KEY'), 'KEY')
        log_mock.assert_any_call('No translations found for de.')
        log_mock.assert_called_with('No translation for key: KEY')

        req_mock.get('http://service-text-service:1555/v1/text/info/scope/unnamed-skill',
                     text='{"supportedLanguages": [{"code": "en"}]}')
        req_mock.get('http://service-text-service:1555/v1/text/en/unnamed-skill',
                     text='[{"locale": "en","scope": "unnamed-skill",'
                          '"sentences": ["KEY1", "KEY2"],'
                          '"tag": "KEY"}]')
        t = DelayedTranslation('de')
        self.assertEqual(t.gettext('KEY'), 'KEY')
        log_mock.assert_any_call('No translations found for de.')
        log_mock.assert_called_with('No translation for key: KEY')

    @requests_mock.mock()
    @patch.object(logging.Logger, 'debug')
    @patch('skill_sdk.services.text.config', new_callable=ConfigParser)
    def test_reload(self, req_mock, config_mock, log_mock):
        import time
        config_mock['service-text'] = {'load': 'delayed'}
        req_mock.get('http://service-text-service:1555/v1/text/info/scope/unnamed-skill',
                     text='{"supportedLanguages": [{"code": "en"}, {"code": "de"}]}')
        req_mock.get('http://service-text-service:1555/v1/text/en/unnamed-skill',
                     text='[{"locale": "en","scope": "unnamed-skill",'
                          '"sentences": ["KEY1", "KEY2"],'
                          '"tag": "KEY"}]')
        req_mock.get('http://service-text-service:1555/v1/text/de/unnamed-skill',
                     text='[{"locale": "de","scope": "unnamed-skill",'
                          '"sentences": ["SCHLÜSSEL1", "SCHLÜSSEL2"],'
                          '"tag": "KEY"}]')
        t = DelayedTranslation('de')
        self.assertIn(t.gettext('KEY'), ["SCHLÜSSEL1", "SCHLÜSSEL2"])
        t.update_interval = 0.05
        req_mock.get('http://service-text-service:1555/v1/text/de/unnamed-skill',
                     text='[{"locale": "de","scope": "unnamed-skill",'
                          '"sentences": ["CHUCK", "NORRIS"],'
                          '"tag": "KEY"}]')
        time.sleep(0.1)
        self.assertIn(t.gettext('KEY'), ["CHUCK", "NORRIS"])
        log_mock.assert_any_call("Reloading translations for en.")
        log_mock.assert_any_call("Reloading translations for de.")

        req_mock.get('http://service-text-service:1555/v1/text/de/unnamed-skill', text='')
        time.sleep(0.1)
        self.assertIn(t.gettext('KEY'), ["CHUCK", "NORRIS"])


class TestReloadWorker(unittest.TestCase):

    def tearDown(self):
        import importlib
        import skill_sdk
        importlib.reload(skill_sdk.l10n)

    @requests_mock.mock()
    @patch('skill_sdk.services.text.config', new_callable=ConfigParser)
    def test_reload(self, req_mock, config_mock):
        from skill_sdk.l10n import translations
        req_mock.get('http://service-text-service:1555/v1/text/info/scope/unnamed-skill',
                     text='{"supportedLanguages": [{"code": "en"}, {"code": "de"}]}')
        req_mock.get('http://service-text-service:1555/v1/text/en/unnamed-skill',
                     text='[{"locale": "en","scope": "unnamed-skill",'
                          '"sentences": ["KEY1", "KEY2"],'
                          '"tag": "KEY"}]')
        req_mock.get('http://service-text-service:1555/v1/text/de/unnamed-skill',
                     text='[{"locale": "de","scope": "unnamed-skill",'
                          '"sentences": ["SCHLÜSSEL1", "SCHLÜSSEL2"],'
                          '"tag": "KEY"}]')
        config_mock['service-text'] = {'update-interval': 0.00001}

        def _break():
            """ Stop infinite `while` loop on the second call to `gevent.sleep`
            """
            counter = 0

            def wrapper(*a, **kw):
                nonlocal counter
                if counter:
                    raise Exception('Break')
                counter += 1
            return wrapper

        with patch('skill_sdk.services.text.time.sleep', new_callable=_break):
            with self.assertRaises(Exception):
                translation_reload_worker(translations)

        self.assertIn(translations['de'].gettext('KEY'), ['SCHLÜSSEL1', 'SCHLÜSSEL2'])
        self.assertEqual(translations['de'].gettext('KEY_PLURAL'), 'KEY_PLURAL')

        req_mock.get('http://service-text-service:1555/v1/text/de/unnamed-skill',
                     text='[{"locale": "de","scope": "unnamed-skill",'
                          '"sentences": ["SCHLÜSSEL1", "SCHLÜSSEL2"],'
                          '"tag": "KEY"}, '
                          ' {"locale": "de", "scope": "unnamed-skill",'
                          '"sentences": ["Die Ärzte"],"tag": "KEY_PLURAL"}]')

        with patch('skill_sdk.services.text.time.sleep', new_callable=_break):
            with self.assertRaises(Exception):
                translation_reload_worker(translations)

        self.assertEqual(translations['de'].gettext('KEY_PLURAL'), 'Die Ärzte')

        with patch('skill_sdk.services.text.time.sleep', new_callable=_break), \
             patch('skill_sdk.services.text.load_translations_from_server', side_effect=l10n.TranslationError()):
            with self.assertRaises(Exception):
                translation_reload_worker(translations)

        self.assertEqual(translations['de'].gettext('KEY_PLURAL'), 'Die Ärzte')
