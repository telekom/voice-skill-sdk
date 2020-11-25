#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#
import io
import logging
import pathlib
import tempfile
import unittest
from unittest import mock
from unittest.mock import patch

from skill_sdk.manage import manage, import_module, ARG_RUN, ARG_TEST, ARG_VERSION, ARG_TRANSLATE

import requests_mock
from skill_sdk.config import Config

config = Config()
config['skill'] = {'version': '1', 'intents': 'intents/*.json'}


class TestManage(unittest.TestCase):

    @patch('sys.argv', new=['manage.py'])
    def test_no_args_should_give_help(self):
        with mock.patch('sys.stdout', new=io.StringIO()) as fake_out:
            with self.assertRaises(SystemExit):
                manage()
            self.assertIn('usage: manage.py', fake_out.getvalue())

    @patch('sys.argv', new=['manage.py', '--help'])
    def test_help_should_give_help(self):
        with mock.patch('sys.stdout', new=io.StringIO()) as fake_out:
            with self.assertRaises(SystemExit):
                manage()
            self.assertIn('usage: manage.py', fake_out.getvalue())

    @patch('sys.argv', new=['manage.py', ARG_RUN, '--help'])
    def test_run_help_should_give_run_help(self):
        with mock.patch('sys.stdout', new=io.StringIO()) as fake_out:
            with self.assertRaises(SystemExit):
                manage()
            self.assertIn('Run the HTTP server as configured to handle requests', fake_out.getvalue())

    @patch('sys.argv', new=['manage.py', ARG_RUN])
    @patch('skill_sdk.skill.run')
    def test_run_should_run_runner(self, main_mock):
        manage()
        main_mock.assert_called_with(dev=False, local=False, cache=True)

    @patch('sys.argv', new=['manage.py', '-l', ARG_RUN])
    @patch('skill_sdk.skill.run')
    def test_run_with_l(self, main_mock):
        manage()
        main_mock.assert_called_with(dev=False, local=True, cache=True)

    @patch('sys.argv', new=['manage.py', '--local', ARG_RUN])
    @patch('skill_sdk.skill.run')
    def test_run_with_l_removed(self, main_mock):
        """ Make sure "--local" param is stripped from arguments list before being passed to Gunicorn
        """
        manage()
        import sys
        self.assertNotIn('--local', sys.argv)

    @patch('sys.argv', new=['manage.py', '-t', ARG_RUN])
    @patch('skill_sdk.skill.run')
    def test_run_with_t(self, main_mock):
        manage()
        main_mock.assert_called_with(local=False, dev=True, cache=True)

    @patch('sys.argv', new=['manage.py', ARG_TEST, '-c'])
    @patch('coverage.Coverage.start')
    @patch('coverage.Coverage.report', return_value=0)
    @patch('unittest.TextTestRunner.run')
    @patch('sys.exit')
    def test_test(self, exit_mock, test_mock, report_mock, cov_mock):
        manage()
        test_mock.assert_called_once()
        report_mock.assert_called_once()
        cov_mock.assert_called_once()

    @patch('coverage.Coverage.start')
    @patch('coverage.Coverage.report', return_value=0)
    @patch('unittest.TextTestRunner.run')
    def test_run_tests(self, test_mock, report_mock, cov_mock):
        from skill_sdk.manage import run_tests, run_func_tests
        self.assertTrue(run_func_tests())
        self.assertEqual(run_tests(cover=True), 0)
        self.assertEqual(run_tests(cover=False), 0)
        with patch('skill_sdk.manage.Coverage.report', return_value=40):
            self.assertEqual(run_tests(cover=50), '\nFAIL: expected 50% coverage')
        with patch('skill_sdk.manage.run_unit_tests', return_value=False):
            self.assertEqual(run_tests(), 'FAIL: unit tests')
        with patch('skill_sdk.manage.run_func_tests', return_value=False):
            self.assertEqual(run_tests(functional=True), 'FAIL: functional tests')

    @patch('sys.argv', new=['manage.py', ARG_VERSION])
    @patch('skill_sdk.manage.config', new=config)
    def test_version(self):
        with mock.patch('sys.stdout', new=io.StringIO()) as fake_out:
            manage()
            self.assertIn('1', fake_out.getvalue())
            self.assertNotIn(' ', fake_out.getvalue())

    def test_import_module(self):
        with patch('importlib.import_module') as imp_mock:
            import_module('main.py')
            imp_mock.assert_called_once_with('main')
        with patch('importlib.import_module') as imp_mock, \
                patch.object(pathlib.Path, 'is_dir', return_value=True), \
                patch.object(pathlib.Path, 'is_file', return_value=True), \
                patch.object(pathlib.Path, 'iterdir', return_value=[pathlib.Path('impl/a.py'), pathlib.Path('impl/b.py')]):
            import_module('impl')
            imp_mock.assert_any_call('impl')
            imp_mock.assert_any_call('.a', 'impl')
            imp_mock.assert_any_call('.b', 'impl')
        with patch('importlib.import_module') as imp_mock, \
                patch.object(pathlib.Path, 'is_dir', return_value=False):
            import_module('impl')
            imp_mock.assert_called_once_with('impl')
        # Check if error message logged
        with patch('importlib.import_module', side_effect=ModuleNotFoundError), \
                patch.object(logging.Logger, 'error') as log:
            import_module('main.py')
            log.assert_called_once()

    @patch('sys.argv', new=['manage.py', ARG_TRANSLATE])
    @patch('skill_sdk.manage.translate_modules', return_value='ok')
    def test_manage_translate(self, *args):
        with patch('sys.exit') as exit_mock:
            manage()
            exit_mock.assert_called_once_with('ok')

    @requests_mock.mock()
    @patch('skill_sdk.manage.config', new=config)
    def test_translate_modules(self, req_mock):
        from skill_sdk.manage import translate_modules
        req_mock.get('http://service-text-service:1555/v1/text/info/locale',
                     text='{"supportedLanguages": [{"code": "de"}, {"code": "en"}]}')
        req_mock.get('http://service-text-service:1555/v1/text/scope/unnamed-skill',
                     text='[{"locale": "de","scope": "unnamed-skill",'
                          '"sentences": ["SCHLÜSSEL1", "SCHLÜSSEL2"],'
                          '"tag": "KEY"}, '
                          '{"locale": "en","scope": "unnamed-skill",'
                          '"sentences": ["KEY1", "KEY2"],'
                          '"tag": "KEY"}]')
        with tempfile.TemporaryDirectory() as tmp:
            with patch('skill_sdk.l10n.LOCALE_DIR', tmp), \
                    patch('skill_sdk.l10n.init_locales', return_value=True) as init_mock, \
                    patch('skill_sdk.l10n.translate_locale', return_value=['msgid "KEY1" \n',
                                                                              'msgstr "Test Translation"', '\n',
                                                                              ' msgid "KEY2" \n', '  msgstr "" \n']):

                with patch('skill_sdk.l10n.extract_translations', return_value=f'{tmp}/messages.pot'):
                    self.assertEqual(translate_modules(['impl'], download_url='http://'), 0)
                    self.assertEqual(translate_modules(['impl'], download_url='http://service-text-service:1555'), 0)

                    self.assertTrue((pathlib.Path(tmp) / 'en.po').exists())
                    self.assertTrue((pathlib.Path(tmp) / 'en.mo').exists())
                    self.assertTrue((pathlib.Path(tmp) / 'de.po').exists())
                    self.assertTrue((pathlib.Path(tmp) / 'de.mo').exists())

                    with patch.dict('sys.modules', {'skill_sdk.services.text': ModuleNotFoundError()}):
                        self.assertNotEqual(translate_modules(['impl'], download_url='http://'), 0)
                    with patch.dict(config._sections, {'service-text': {'active': 'false'}}):
                        self.assertEqual(translate_modules(['impl']), 'No "download_url" specified')

                with patch('skill_sdk.l10n.extract_translations', return_value=None):
                    self.assertEqual(translate_modules(['impl']), 'Failed to extract translations')

    @patch('skill_sdk.manage.config', new=config)
    def test_patch(self):
        """ Test monkey patching the standard libraries """

        from skill_sdk.manage import patch as monkey_patch
        with patch('gevent.monkey.patch_all') as m:
            # Make sure default is to call gevent.monkey.patch_all
            monkey_patch()
            m.assert_called_once()
        config['http']['worker_class'] = "eventlet"
        eventlet = unittest.mock.MagicMock()
        with patch.dict('sys.modules', {'eventlet': eventlet}):
            # Ensure setting worker_class to empty string, removes the value from config
            monkey_patch()
            eventlet.monkey_patch.assert_called_once()

        # For coverage sake
        config['http']['worker_class'] = "meinheld#gunicorn_worker"
        monkey_patch()
