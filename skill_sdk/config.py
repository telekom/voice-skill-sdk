#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

#
# Read skill configuration file
#

import os
import re
import json
import logging
import configparser
from pathlib import Path
from typing import Dict, List

#
#   This is a default configuration
#   Loaded when config instantiated
#

DEFAULT_VALUES = {
    'skill': {
        'name': 'unnamed-skill',
        'version': 0.1,
    },
    'http': {
        'host': '0.0.0.0',
        'port': 4242,
        'server': 'gunicorn',
        'workers': 1,
        'threads': 1,
        'worker_class': 'gevent',
        'keepalive': 30,
    }
}

# Name of default config file
DEFAULT_CONFIG_FILE = 'skill.conf'

# Name of default tokens file
DEFAULT_TOKENS_FILE = 'tokens.json'

# Filesystem paths to look for config and tokens
SEARCH_PATH = [Path('./'), Path('../'), Path('/'), Path('~')]

ENV_VAR_TEMPLATE = re.compile(r'\${([^}^{]+)\}')

logger = logging.getLogger(__name__)


def get_config_file():
    """ Read config file name from environment """
    return os.environ.get('SKILL_CONF', DEFAULT_CONFIG_FILE)


def get_token_file():
    """ Read token file name from environment """
    return os.environ.get('TOKENS_JSON', DEFAULT_TOKENS_FILE)


class EnvVarInterpolation(configparser.BasicInterpolation):
    """ Interpolation to expand environment variables in the format:

            [section]
            key = ${ENV_VAR:default}

    """

    def before_get(self, parser, section, option, value, defaults):
        match = ENV_VAR_TEMPLATE.match(value)
        if not match:
            return os.path.expandvars(value)

        match = match.group(1)
        env_var, default = match.split(':', 1) if ':' in match else (match, None)
        value = os.getenv(env_var)
        if value:
            logger.debug("Read %s from environment: %s", env_var, value)
        elif default:
            logger.debug("%s is empty, setting to default: %s", env_var, default)
        return value or default


class Config(configparser.ConfigParser):
    """ Here is our configuration that holds:
           - WSGI server config
           - service config
           - tokens

    """

    tokens: Dict = {}
    # The config files that were successfully loaded, we'll use it to determine relative paths for intents loading
    config_files: List = []

    def __init__(self):
        super().__init__(interpolation=EnvVarInterpolation())
        self.read_dict(DEFAULT_VALUES)  # Read default config
        self.read_conf()                # Read config from `skill.conf`
        self.read_tokens()              # Read tokens

    def read_conf(self, config_file: str = None) -> 'Config':
        """ Read the configuration file

        :param config_file: Path to config file
        :return:    self
        """
        config_file = config_file or get_config_file()
        logger.info(f"Reading configuration from {config_file}")

        self.config_files = self.read([path.joinpath(config_file) for path in SEARCH_PATH])
        if not self.config_files:
            logger.info(f"Can't read configuration from {config_file}...")

        return self

    def read_tokens(self, token_file: str = None) -> Dict:
        """ Read the tokens

        :param token_file:  Path to tokens file
        :return:    dict
        """
        token_file = token_file or get_token_file()
        logger.info(f"Reading tokens from {token_file}")

        try:
            with open(token_file) as file:
                self.tokens.update(json.load(file))
        except FileNotFoundError:
            logger.info(f"{token_file} does not exist. Skipping...")
        except Exception as ex:
            logger.exception(f"Can't read tokens from {token_file}: %s", ex)

        return self.tokens

    def read_environment(self, env: str, section: str, option: str) -> 'Config':
        """ Read the environment variables and overwrite config values

        :param env:         environment variable
        :param section:     config section
        :param option:      config option to get from environment
        :return:
        """
        value = os.environ.get(env)
        if value:
            self.read_dict({section: {option: value}})
        return self

    def active(self, service: str) -> bool:
        """ Returns True is service is activated in skill configuration

        :return:
        """
        return self.has_section(service) and self.getboolean(service, "active", fallback=True)

    def get_tokens(self):
        """ Get tokens defined in `token.json`

        :return:
        """
        return self.tokens.get('tokens')

    def resolve_glob(self, glob_to_resolve: Path):
        """ Resolve glob pattern relative to the path where config files were found

        :param glob_to_resolve:
        :return:
        """
        if glob_to_resolve.is_absolute():
            return glob_to_resolve.parent.glob(glob_to_resolve.name)

        conf_file_found_in = [Path(file_name).resolve().parent for file_name in self.config_files] or [Path('.')]
        return (file for path in conf_file_found_in for file in path.glob(str(glob_to_resolve)))


config = Config()
