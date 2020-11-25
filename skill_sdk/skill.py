#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

#
# Wrapper around Bottle
#

import functools
from typing import Callable, Dict
import logging.config

import bottle
from bottle import install, get, post, route, error, request, response, tob, touni, app
from bottle import BaseRequest, HTTPResponse

from . import l10n
from . import intents
from . import responses
from . import decorators
from .config import config

logger = logging.getLogger(__name__)

# Fallback intent: called if no other implementation found
FALLBACK_INTENT = 'FALLBACK_INTENT'


def initialize(config_file: str = None, dev: bool = False, local: bool = False, cache: bool = True) -> 'Skill':
    """ Initialize the app

          * configure logging
          * load the intents
          * setup the routes
          * return default app

    :param config_file: read configuration from file
    :param dev:         initialize development mode
    :param local:       activate local proxy for services
    :param cache:       use local caches (False to deactivate)
    :return:
    """

    config.read_conf(config_file)

    from .caching import decorators
    decorators.CACHES_ACTIVE = cache

    from . import requests
    requests.USE_LOCAL_SERVICES = local

    max_request_size = config.getint('skill', 'max_request_size', fallback=0)
    if max_request_size:
        BaseRequest.MEMFILE_MAX = max_request_size

    from . import K8sChecks
    with K8sChecks('init'):
        configure_logging()

        skill = app()
        if not skill.get_intents():
            raise RuntimeError("No intent handlers loaded. Check the log messages for import errors...")

        if not l10n.translations:
            l10n.translations = l10n.load_translations()

        from . import routes      # Add standard routes
        from . import swagger     # Add swagger route

        set_dev_mode() if dev else setup_services()

        # Copy configuration to Skill instance
        skill.config.load_dict({section: dict(config.items(section)) for section in config.sections()})
        return skill


def configure_logging():
    """ Configure logging """

    from .tracing import initialize_tracer
    from . import log

    initialize_tracer()
    logging.config.dictConfig(log.conf[log.LOG_FORMAT])

    if log.LOG_FORMAT == 'gelf':
        config.set('http', 'logger_class', 'skill_sdk.log.GunicornLogger')

    # as bottle writes to stdout/stderr directly, patch it
    bottle_logger = logging.getLogger('bottle')
    bottle._stdout = lambda msg: bottle_logger.debug(msg)
    bottle._stderr = lambda msg: bottle_logger.info(msg)


def setup_services():
    """ Load optional cloud services:

    :return:
    """
    try:
        from .services import setup_services
        return setup_services()
    except ImportError:
        pass


def set_dev_mode():
    """ Setup `development` mode to run the skill """

    # Start builtin WSGIRefServer
    logger.warning("Starting bottle with WSGIRefServer. Do not use in production!")
    config.set('http', 'server', 'wsgiref')
    config.set('http', 'host', 'localhost')

    # Load swagger UI
    try:
        import swagger_ui
    except ModuleNotFoundError:
        logger.warning("Swagger UI not found, starting without...")


class Skill(bottle.Bottle):
    """ Simple bottle app """

    _intents: Dict[str, Callable] = {}

    def get_intent(self, name: str):
        return self._intents.get(name, self._intents.get(FALLBACK_INTENT))

    def get_intents(self):
        return self._intents

    def intent_handler(self, name: str, error_handler: Callable = None, **kwargs) -> Callable:
        """ Decorator to define intent implementation

        :param name: Intent name
        :param error_handler: Optional handler to call if conversion error occurs
        :return:
        """
        def decorator(func):    # NOSONAR
            kwargs.update(name=name)
            decorated = decorators.intent_handler(func, error_handler=error_handler)
            intent = intents.Intent(kwargs, decorated)
            if name in self._intents:
                raise ValueError(f'Duplicate intent {name} with handler {func}')
            self._intents[name] = intent
            return decorated
        return decorator

    def test_intent(self, name: str, **kwargs) -> responses.Response:
        """ Test an intent implementation

        :param name:    Intent name
        :param kwargs:  Intent's attributes
        :return:
        """
        from .test_helpers import invoke_intent
        return invoke_intent(name, skill=self, **kwargs)

    def run(self, **kwargs):
        """ Start the skill service

        :param kwargs:
        :return:
        """

        # Overwrite config arguments with function arguments
        kwargs = dict(config.items('http'), **kwargs)

        logger.info('Starting server')
        logger.debug('with arguments: %s', kwargs)

        super().run(**kwargs)


def run(config_file: str = None, dev: bool = False, local: bool = False, cache: bool = True, **kwargs):
    """ Init and start the skill service """

    skill = initialize(config_file=config_file, dev=dev, local=local, cache=cache)
    skill.run(**kwargs)


def make_default_app_wrapper(name):
    """ Decorator to apply a property to default bottle app """

    @functools.wraps(getattr(Skill, name))
    def wrapper(*args, **kwargs):   # NOSONAR
        return getattr(app(), name)(*args, **kwargs)
    return wrapper


intent_handler = make_default_app_wrapper('intent_handler')
test_intent = make_default_app_wrapper('test_intent')

app.push(Skill())
