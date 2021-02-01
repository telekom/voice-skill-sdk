#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

#
# Bottle route definitions
#

import json
import base64
import logging
import traceback
from json import dumps, JSONDecodeError

from .__version__ import __version__, __spi_version__
from .config import config
from .intents import Context, InvalidTokenError
from .l10n import TranslationError, get_locales
from .responses import ErrorResponse
from .skill import app, error, get, post, request, response, tob, touni, HTTPResponse

from . import log, tracing

logger = logging.getLogger(__name__)


def api_base():
    """Get API base"""
    return config.get('skill', 'api_base', fallback=f"/v1/{config.get('skill', 'name')}")


def debug():
    return config.getboolean('skill', 'debug', fallback=False)


def authenticate(req, password):
    """
    Authenticate the request

    :param req:
    :param password:
    :return:    True if authorized
    """
    logger.debug('Processing basic authentication.')
    auth = req.headers.get('Authorization')

    try:
        method, data = auth.split(None, 1)
        if method.lower() == 'basic':
            # Get user:password from "Authorization" header
            user, pwd = touni(base64.b64decode(tob(data))).split(':', 1)

            authorized = (user.lower() == 'cvi' and pwd == password)
            logger.debug(f"Basic auth decoded: {user}/{pwd}. {'Authorized' if authorized else 'NOT authorized'}.")
            return authorized

        logger.warning(f"Authorization [{method}] is not accepted.")
    except (AttributeError, KeyError, TypeError, ValueError) as ex:
        logger.debug(f'Error authenticating request: {ex}')
        return None


def auth_basic(check, text="Access denied"):
    """
    Decorator to [optionally] require basic auth

    :param check:
    :param text:
    :return:        function to authenticate the request (if configured)
    """
    def decorator(func):
        """ Check skill config and return either inner wrapper requesting basic auth,
            or the original (undecorated) function otherwise
        """

        auth = config.get('skill', 'auth', fallback='None')
        api_key = config.get('skill', 'api_key', fallback=None)
        if auth == 'basic' and api_key:
            logger.debug(f'Basic authentication requested for {func.__name__}, api-key: {api_key}.')

            def wrapper(*args, **kwargs):
                """ Inner wrapper """
                if not check(request, api_key):
                    logger.warning('401 raised, returning: access denied.')
                    return HTTPResponse(json.dumps({'text': text}), 401, {'Content-type': 'application/json'})

                return func(*args, **kwargs)
            return wrapper

        # If authentication requested but no api_key found in config, log a warning
        if auth == 'basic' and not api_key:
            logger.warning('Please set api_key in skill.conf! Proceeding without authentication....')

        return func
    return decorator


@get(f'{api_base()}/info')
@auth_basic(authenticate)
def info():
    """
    Get skill info endpoint

    returns basic skill info to CVI:
        - skill id
        - supported SPI version
        - skill and SDK versions
        - supported locales
    """

    with tracing.start_active_span('info', request):
        logger.debug('Handling info request.')

        try:
            response.content_type = 'application/json'
            data = {
                'skillId': config.get('skill', 'id', fallback=config.get('skill', 'name')),
                'skillSpiVersion': __spi_version__,
                'skillVersion': f"{config.get('skill', 'version')} {__version__}",
                'supportedLocales': [
                    lang.split('-', 1).pop().lower() for lang in get_locales()
                ],
            }
            logger.debug('Info request result: %s', data)
            return dumps(data)

        except BaseException as ex:
            logger.exception('Internal error: %s', repr(ex))
            return ErrorResponse(999, 'internal error').as_response()


@post(api_base())
@auth_basic(authenticate)
def invoke():
    """
    Invoke intent endpoint:

    returns intent call result or ErrorResponse
    """

    with tracing.start_active_span('invoke', request) as scope:
        logger.debug('Handling intent call request.')

        try:
            logger.debug('Request data: %s', log.prepare_for_logging(request.json))
            context = Context(request)
            context.tracer = scope.span.tracer
            intent = app().get_intent(context.intent_name)
            if intent:
                result = intent(context).as_response(context)
                logger.debug('Intent call result: %s', result.body)
            else:
                result = ErrorResponse(1, 'intent not found').as_response()
                logger.error('Intent not found: %s', context.intent_name)

        except InvalidTokenError:
            logger.exception('Invalid token.')
            result = ErrorResponse(2, 'invalid token').as_response()
        except (TranslationError, JSONDecodeError, AttributeError, KeyError, TypeError) as ex:
            logger.exception('Bad request: %s', repr(ex))
            exc_msg = f'Exception in "invoke": {repr(ex)}. {traceback.format_exc()}' if debug() else 'Bad request'
            result = ErrorResponse(3, exc_msg).as_response()
        except BaseException as ex:
            logger.exception('Exception in "invoke": %s', repr(ex))
            exc_msg = f'Exception in "invoke": {repr(ex)}. {traceback.format_exc()}' if debug() else 'internal error'
            result = ErrorResponse(999, exc_msg).as_response()

    return result


@error(400)
def json_400(err):
    """Bad request"""

    logger.warning('400 raised, returning: bad request.')
    logger.debug('Error: %s', err)
    return ErrorResponse(3, 'Bad request!').as_response()


@error(404)
def json_404(err):
    """Not found"""

    logger.warning('404 raised, returning: not found.')
    logger.debug('Error: %s', err)
    return ErrorResponse(1, 'Not Found!').as_response()


@error(500)
def json_500(err):
    """Internal server error"""

    logger.warning('500 error raised, returning: internal error.')
    logger.debug('Error: %s', err)
    return ErrorResponse(999, 'internal error').as_response()
