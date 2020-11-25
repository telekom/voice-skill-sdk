#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from skill_sdk.config import config, Config, logger


class TestConfig(unittest.TestCase):

    @patch('sys.argv', new=['python'])
    @patch.object(Config, 'read')
    def test_read_conf(self, config_mock):
        config.read_conf()
        config_mock.assert_called_once_with([Path('skill.conf'), Path('../skill.conf'), Path('/skill.conf'), Path('~/skill.conf')])

    @patch('os.environ', new={'SKILL_CONF': '1.conf'})
    @patch.object(Config, 'read')
    def test_read_conf_arg(self, config_mock):
        config.read_conf()
        config_mock.assert_called_once_with([Path('1.conf'), Path('../1.conf'), Path('/1.conf'), Path('~/1.conf')])

    def test_resolve_glob(self):
        with tempfile.TemporaryDirectory() as tmp:
            locale_dir = Path(tmp) / 'locale'
            locale_dir.mkdir(), (locale_dir / 'a.bb').touch(), (locale_dir / 'b.bb').touch()
            with patch.object(Config, 'read', return_value=[tmp + '/skill.conf']):
                config.read_conf()
                lst = list(config.resolve_glob(Path('locale/*.bb')))
                self.assertIn(Path(tmp) / 'locale/b.bb', lst)
                self.assertIn(Path(tmp) / 'locale/a.bb', lst)


class TestToken(unittest.TestCase):

    def setUp(self):
        config.tokens.clear()

    @patch('builtins.open')
    @patch('skill_sdk.config.json.load')
    def test_read_tokens_ok(self, token_mock, mock_open):
        mock_open.return_value.__enter__.return_value.name = None
        token_mock.return_value = {
            "tokens": [
                {"id": "mytokenid",
                 "parameter": {"type": "OAUTH2_AUTHORIZATION_CODE",
                               "authorizationUrl": "authorizationUrl",
                               "tokenUrl": "tokenUrl",
                               "scopes": ["scope-1"],
                               "clientId": "client-id",
                               "clientSecret": "client-secret"
                               }}]}
        config.read_tokens()
        self.assertEqual(config.get_tokens()[0]["id"], 'mytokenid')

    @patch.object(logger, 'exception')
    @patch('builtins.open', side_effect=OSError('Not found.'))
    def test_read_tokens_os_error(self, mock_open, log_mock):
        config.read_tokens()
        self.assertEqual(log_mock.call_count, 1)

    @patch.object(Path, 'is_file', return_value=False)
    def test_read_tokens_no_file(self, isfile_mock):
        tokens = config.read_tokens()
        self.assertEqual(tokens, {})

    def tearDown(self):
        config.tokens.clear()


class TestEnvironment(unittest.TestCase):

    #
    #   Test overwriting the config with environment variables
    #

    def setUp(self):
        self.config = Config()

    @patch('os.environ', new={'SERVICE_TEXT_URL': 'http://service-text-service'})
    def test_service_text_url(self):
        self.config.read_environment(*('SERVICE_TEXT_URL', 'service-text', 'url'))
        self.assertEqual(self.config.get("service-text", "url"), "http://service-text-service")

    @patch('os.environ', new={'SERVICE_LOCATION_URL': 'http://service-location-service'})
    def test_service_location_url(self):
        self.config.read_environment(*('SERVICE_LOCATION_URL', 'service-location', 'url'))
        self.assertEqual(self.config.get("service-location", "url"), "http://service-location-service")

    def test_expand_vars(self):
        config_data = """
        [section]
        key = ${ENV_VAR:default}
        key1 = ${ENV_VAR_NOT_SET}
        """
        the_config = Config()
        the_config.read_string(config_data)
        self.assertIsNone(the_config['section']['key1'])
        self.assertEqual(the_config['section']['key'], 'default')
        with patch('os.environ', new={'ENV_VAR': 'environment_variable'}):
            self.assertEqual(the_config['section']['key'], 'environment_variable')
