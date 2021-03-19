#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

#
# Intent/context definition
#

import logging
import datetime
import importlib
from warnings import warn
from threading import local
from typing import Any, Dict, Callable
from collections import defaultdict
from dateutil.tz import tz

from .l10n import _, get_translation, set_current_locale
from .tracing import start_span
from .responses import ErrorResponse, Response
from .sessions import Session

logger = logging.getLogger(__name__)


class InvalidTokenError(Exception):
    """
    Error type raised in case an invalid token has been received.
    """


class AttributeMissingError(Exception):
    """
    Error type raised when an attribute is missing and the reaction "error" is defined.
    """


# Backward compatibility
ArgumentMissingError = AttributeMissingError


class EntityValueException(Exception):
    """
    Entity values conversion exception
    """

    def __init__(self, ex, value=None, func=None, *args):
        self.__cause__ = ex
        self.value = value
        self.func = func
        super().__init__(*args)


class Context:
    """
    A Context passed to the intent implementation callable with all kind of useful objects.

    :ivar intent_name: name of the intent that was called
    :ivar locale: the language code for this request
    :ivar translation: a :py:class:gettext.Translation instance related to the locale
    :ivar _: a shortcut to :py:function:self.translation.gettext
    :ivar _n: a shortcut to :py:function:self.translation.ngettext
    :ivar _a: a shortcut to :py:function:self.translation.getalltexts
    :ivar tokens: the tokens transmitted with the request
    :ivar session: the session data
    :ivar attributes: the raw version of the attributes as received in the request
    :ivar attributesV2: the raw version of attributesV2 values in the request

    :ivar version: skill SPI version
    """

    def __init__(self, request):
        self.request = request
        request_data = request.json
        request_context = request_data.get('context')
        self.skill_id = request_context.get('skillId')
        self.intent_name = request_context.get('intent')
        self.spi_version = request_context.get('spiVersion')
        self.client_type_name = request_context.get('clientTypeName')
        self.user_profile_config = request_context.get('userProfileConfig')
        self.locale = {'language': request_context.get('locale')}
        logger.debug('Language: %s', self.locale)
        self.translation = get_translation(self.locale['language'])
        self._ = self.translation.gettext
        self._n = self.translation.ngettext
        self._a = self.translation.getalltexts if hasattr(self.translation, 'getalltexts') else lambda m: [m]

        # Expose nl_join/nl_build method if available for locale
        self.nl_join = self.translation.nl_join if hasattr(self.translation, 'nl_join') else None
        self.nl_build = self.translation.nl_build if hasattr(self.translation, 'nl_build') else None

        self.tokens = request_context.get('tokens', {})
        self.configuration = request_context.get('configuration', {})

        session = request_data.get('session')
        if session:
            new = session['new']
            id_ = session['id']
            logger.debug('Found session with id %s', id_)
            attrs = session.get('attributes', {})
            self.session = Session(id_, new, attrs)
        else:

            logger.debug('No session found. Creating new one.')
            self.session = Session(None, True)

        self.attributesV2 = request_context.get('attributesV2', {})
        self.push_messages = defaultdict(list)

        # Backward compatibility:
        self.attributes = {name: [value.get('value') for value in items] for name, items in self.attributesV2.items()}

        set_current_locale(self.translation)
        context.set_current(self)

    def _get_attribute(self, attr, default=None):
        """ Silently return first item from attributes array """
        return next(iter(self.attributes.get(attr, [])), default)

    def dict(self) -> Dict:
        """
        Export as dictionary

        :return:
        """
        return dict(
            intent_name=self.intent_name,
            locale=self.locale,
            tokens=self.tokens,
            session=self.session,
            configuration=self.configuration,
            attributesV2=self.attributesV2,
            clientTypeName=self.client_type_name,
            userProfileConfig=self.user_profile_config,
            spi_version=self.spi_version,
        )

    def __repr__(self) -> str:
        """ String representation

        :return:
        """
        return str(self.dict())

    def gettz(self) -> datetime.tzinfo:
        """
        Get device timezone from context attributes

        :return:
        """
        _tz = self._get_attribute('timezone')
        timezone = tz.gettz(_tz)

        if timezone is None:
            logger.error("Device timezone not present or invalid: %s. Defaulting to UTC", repr(_tz))
            timezone = tz.tzutc()

        return timezone

    def today(self) -> datetime.datetime:
        """
        Get `datetime.datetime` object representing the current day at midnight

        :return:
        """
        dt = self.now()
        return datetime.datetime.combine(dt.date(), datetime.time(0))

    def now(self) -> datetime.datetime:
        """ Get current device date/time with timezone info

        :return:
        """
        timezone = self.gettz()
        return datetime.datetime.now(datetime.timezone.utc).astimezone(timezone)


class LocalContext(Context):
    """ Thread-local Context object """

    _thread_locals = local()

    def __init__(self):
        self._thread_locals.context = None

    def __setattr__(self, key, value):
        try:
            return setattr(self._thread_locals.context, key, value)
        except AttributeError:
            logger.error('Accessing context outside of request.')

    def __getattr__(self, item):
        try:
            return getattr(self._thread_locals.context, item)
        except AttributeError:
            logger.error('Accessing context outside of request.')

    @classmethod
    def get_current(cls):
        return cls._thread_locals.context

    @classmethod
    def set_current(cls, ctx: Context):
        cls._thread_locals.context = ctx


context = LocalContext()


class Intent:
    """
    An intent as loaded from the JSON file

    """
    name: str
    implementation: Callable[..., Any]

    def __init__(self, name, implementation: Callable[..., Any]):
        if not name:
            raise ValueError('Intent name is required.')
        if not implementation or not callable(implementation):
            raise ValueError('Implementation is required.')

        self.name = name
        self.implementation = implementation    # type: ignore

    @staticmethod
    def _append_push_messages(_context, response):
        messages = []
        for name, payload_list in _context.push_messages.items():
            for payload in payload_list:
                messages.append((name, payload))
        if not messages:
            logger.debug('No push messages to append.')
            return response
        message = messages.pop()
        response.push_notification = {"targetName": message[0], "messagePayload": message[1]}
        if messages:
            logger.debug('More than one push messages to append.')
            raise ValueError('Multiple push messages are not supported yet.')
        logger.debug('Push messages appended: %s', response.push_notification)
        return response

    def _log_return_value(self, result):
        """
        Log intent handler result or raise ValueError.

        :param result:
        :return:
        """
        if isinstance(result, Response):
            logger.debug('Result is of type %s. Returning it.', type(result))
            return self._append_push_messages(context, result)
        if isinstance(result, ErrorResponse):
            logger.debug('Error result is of type %s. Returning it.', type(result))
            return result
        if isinstance(result, str):
            logger.debug('Result is a string. Returning it as a TELL response.')
            return self._append_push_messages(context, Response(result))
        else:
            logger.error('Unknown return type %s when calling implementation of intent.', type(result))
            raise ValueError('Unknown return value')

    def __call__(self, _context: Context):
        """
        Call the implementation of the intent with context argument.

        :param _context:
        """
        from requests.exceptions import RequestException
        from urllib3.exceptions import HTTPError
        from circuitbreaker import CircuitBreakerError

        with start_span(f'intent_call: {self.name}') as span:
            logger.info('Calling intent: %s', repr(self.name))

            logger.debug('Calling %s with context: %s', repr(self.implementation.__name__), repr(_context))
            try:
                result = self.implementation(_context)
                span.log_kv({'intent_handler_result': repr(result)})
                return self._log_return_value(result)

            except (RequestException, HTTPError, CircuitBreakerError) as ex:
                span.log_kv({'error': repr(ex)})
                logger.exception('Exception while calling %s: %s', repr(self.name), repr(ex))
                return self._append_push_messages(_context, Response(_('GENERIC_HTTP_ERROR_RESPONSE')))

            except Exception as ex:
                span.log_kv({'error': repr(ex)})
                logger.exception('Exception in %s while handling %s', repr(self.implementation.__name__), repr(self.name))
                raise

    def dict(self) -> Dict:
        """
        Export as dictionary

        :return:
        """
        return dict(
            name=self.name,
            implementation=self.implementation.__name__,
        )

    def __repr__(self) -> str:
        """ String representation

        :return:
        """
        return str(self.dict())


def _get_implementation(dotted_name: str) -> Callable:      # pragma: no cover
    """ **DEPRECATED**: Get the callable represented by `dotted_name`.

    The function is left for backward compatibility with existing unit tests

    :param dotted_name: The dotted name to the function to retrieve.
           e.g. ``'intents.weather.get_weather'`` → ``get_weather`` in ``intents/weather.py``.
    """
    module, _, name = dotted_name.rpartition('.')
    warn(f'_get_implementation is deprecated. Please use direct import: "from {module} import {name}"',
         DeprecationWarning, stacklevel=2)

    return getattr(importlib.import_module(module), name)
