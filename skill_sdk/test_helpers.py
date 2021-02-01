#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

#
# Unit testing helpers
#

import ast
import sys
import base64
import gettext
import inspect
import logging
import datetime
import contextlib
import configparser
import unittest.mock
from functools import partial
from threading import Thread
from typing import Any, Dict, List, Union
from types import SimpleNamespace

from .__version__ import __spi_version__
from .config import config
from .intents import Context
from .entities import AttributeV2
from .skill import initialize
from .responses import RESPONSE_TYPE_ASK, RESPONSE_TYPE_TELL, RESPONSE_TYPE_ASK_FREETEXT

# Load swagger UI
try:
    import swagger_ui        # noqa: F401
except ModuleNotFoundError:  # pragma: no cover
    pass

logger = logging.getLogger()
datetime_class = datetime.datetime


def mock_datetime_now(target, dt):
    """ Patch datetime.datetime.now with __instancecheck__ """

    class DatetimeSubclassMeta(type):
        """ Metaclass to mock __instancecheck__ """
        @classmethod
        def __instancecheck__(mcs, obj):    # NOSONAR
            return isinstance(obj, datetime_class)

    class BaseMockedDatetime(datetime_class):
        """ Patch the original datetime.datetime.now """
        @classmethod
        def now(cls, tz=None):
            return target.replace(tzinfo=tz)

        @classmethod
        def utcnow(cls):
            return target

    dt_mock = DatetimeSubclassMeta('datetime', (BaseMockedDatetime,), {})
    return unittest.mock.patch.object(dt, 'datetime', dt_mock)


def set_translations(translations: Union[gettext.NullTranslations, Dict] = None):
    """ Set all globally available translations.

        `set_translations(None)` will set the translations to NullTranslations for use in the unit tests,
        so that you can test the output of translation `l10n._`/`l10n._n`/`l10n._a` functions like:

            `self.assertEqual(_('KEY'), 'KEY')`

    :param translations:
    :return:
    """
    from . import l10n

    translations = translations or gettext.NullTranslations()

    if isinstance(translations, gettext.NullTranslations):
        l10n.translations = {locale: translations for locale in l10n.translations}
    elif isinstance(translations, Dict):
        l10n.translations = {locale: _translation for locale, _translation in translations.items()}
    else:
        raise TypeError("Wrong translations value: %s", repr(translations))


def create_context(intent: str,
                   locale: str = None,
                   tokens: Dict[str, str] = None,
                   configuration: Dict[str, Dict] = None,
                   session: Dict[str, Any] = None,
                   **kwargs) -> Context:
    """ Create skill invocation context

    :param intent:  Intent name
    :param locale:  Request locale
    :param tokens:  Intent tokens (if requires)
    :param configuration:  Skill configuration
    :param session: Test session
    :param kwargs:  Attributes(V2)
    :return:
    """

    def parse(_: Any) -> Dict:
        """ Try to create AttributeV2 from any string """
        try:
            attr_v2: AttributeV2 = AttributeV2(_)
        except (AttributeError, TypeError, ValueError):
            attr_v2 = AttributeV2({'value': _})
        return attr_v2.dict()

    attributes_v2 = {key: [parse(each) for each in value] if isinstance(value, (list, tuple)) else [parse(value)]
                     for key, value in kwargs.items()
                     if value is not None}

    # 'timezone' is always present
    if 'timezone' not in attributes_v2:
        attributes_v2['timezone'] = [parse('Europe/Berlin')]

    # Create `attributes` dict for backward compatibility
    attributes: Dict[str, List] = {key: [item.get('value') for item in value] for key, value in attributes_v2.items()}

    # Prepare session attributes
    session = session or {}
    session_attrs = {key: value for key, value in session.items() if key not in ('id', 'new', 'attributes')}
    _session = {
        'id': session.get('id', '12345'),
        'new': session.get('new', True),
        'attributes': {**session.get('attributes', {}), **session_attrs}
    }

    # Mock request.json
    request = SimpleNamespace()
    request.json = {
        "context": {
            "intent": intent,
            "tokens": tokens or {},
            "locale": locale or "de",
            "attributes": attributes or {},
            "attributesV2": attributes_v2 or {},
            "configuration": configuration or {}
        },
        "session": _session,
    }
    request.headers = {}

    ctx = Context(request)
    return ctx


@contextlib.contextmanager
def test_context(intent: str,
                 locale: str = None,
                 tokens: Dict[str, str] = None,
                 configuration: Dict[str, Dict] = None,
                 session: Dict[str, Union[bool, str, Dict]] = None,
                 **kwargs):
    """ Context manager for `create_context`: will save and restore thread-local context object """

    from .intents import context

    ctx = context.get_current()
    try:
        yield create_context(intent, locale=locale, tokens=tokens,
                             configuration=configuration, session=session, **kwargs)
    finally:
        context.set_current(ctx)


def invoke_intent(intent_name: str, skill=None, **kwargs):
    """ Invoke intent by name, **kwargs are passed over to create_context

    :param intent_name: Intent name
    :param skill:
    :param kwargs:
    :return:
    """
    from bottle import app

    # If skill not supplied with arguments, get the current default app from stack
    skill = skill or app()

    try:
        intent = skill.get_intents()[intent_name]
    except KeyError:
        raise KeyError(f"Intent {intent_name} not found")

    with test_context(intent, **kwargs) as ctx:
        return intent(ctx)


# Testing values with defaults
DEFAULT_VALUES = {
    'str': ('', ['a'], 'None', [None], 'Chuck Norris', ['Chuck Norris']),
    'rank': ('', ['a'], 'None', [None], ['max'], ['min'], ['prec'], 0, 1, [0, 1]),
    'datetime.timedelta': ('', ['a'], 'None', [None], ['P1Y2M10DT2H30M']),
    'Location': ('', ['a'], 'None', [None], 'Bonn', ['Bonn', 'Berlin']),
    'Context': {'locale': 'de'}
}


class FunctionalTest(unittest.TestCase):
    """ Functional test class: starts the default app and bombards it with requests from separate greenlet
    """

    # Skill settings
    name: str = config.get('skill', 'name')
    skill_id: str = config.get('skill', 'id', fallback=name)
    version: str = config.get('skill', 'version')
    auth: str = config.get('skill', 'auth', fallback='None')
    api_key: str = config.get('skill', 'api_key', fallback='')
    host: str = 'http://localhost'
    port: str = config.get('http', 'port')
    locales: List[str] = []

    values: Dict = DEFAULT_VALUES

    # Bottle Thread
    bottle: Thread

    def __init__(self, methodName='runTest'):
        # Delay loading requests
        import requests
        self._post = partial(requests.post, headers=self._headers())
        self._get = partial(requests.get, headers=self._headers())

        super().__init__(methodName=methodName)

    @classmethod
    def setUpClass(cls) -> None:
        """ Create and start app instance

        :return:
        """

        # Try to parse testing values from config
        for etype in cls.values:
            try:
                cls.values[etype] = ast.literal_eval(config.get('tests', etype.lower()))
            except (AttributeError, ValueError, TypeError, configparser.Error):
                pass

        test_skill = initialize(dev=True, local=False)
        cls.bottle = Thread(target=test_skill.run, daemon=True)
        cls.bottle.start()

    @classmethod
    def setLocales(cls, locales: list) -> None:
        cls.locales = locales

    def _headers(self):
        headers = {}
        if self.auth == 'basic':
            auth = base64.b64encode(b"cvi:" + self.api_key.encode('utf-8'))
            headers['Authorization'] = f"Basic {auth.decode('utf-8', 'strict')}"
        return headers

    def create_payload(self, intent, locale=None, **kwargs):
        """ Create json payload form attribute values

        :param intent:  intent name
        :param locale:  requested locale
        :param kwargs:  attribute values
        :return:
        """
        locale = locale or next(iter(self.locales), None) or "de"

        # Add keyword arguments as context attributes
        attributes = {key: value if isinstance(value, (list, tuple)) else [value, ]
                      for key, value in kwargs.items()
                      if key != 'attributesV2'}

        # Duplicate attributes as AttributesV2
        attributes_v2 = {
            key: [AttributeV2({'value': v}).dict() for v in value] if isinstance(value, (list, tuple))
            else [AttributeV2({'value': value}).dict(), ]
            for key, value in kwargs.items()
            if key != 'attributesV2'
        }

        # Add specific AttributesV2, if in keyword arguments
        try:
            attributes_v2 = {**attributes_v2, **{key: value for key, value in kwargs['attributesV2'].items()}}
        except (AttributeError, KeyError, TypeError):
            pass

        return {"context": {
            "intent": intent,
            "locale": locale,
            "attributes": attributes,
            "attributesV2": attributes_v2
        }}

    def invoke(self, intent, locale=None, json=None, **kwargs):
        """ Invoke intent

        :param intent:  intent name
        :param locale:  requested locale
        :param json:    json payload, if missing will be created from attribute values
        :param kwargs:  attribute values
        :return:
        """
        payload = json or self.create_payload(intent, locale, **kwargs)
        response = self._post(f"{self.host}:{self.port}/v1/{self.name}", json=payload)
        self.assertTrue(response.ok)

        return response.json()

    def get_intent_invoke_response(self, intent, locale, **kwargs):
        """ Invoke intent and perform basic check

        :param intent:  intent name
        :param locale:  requested locale
        :param kwargs:  attribute values
        :return:
        """
        payload = self.create_payload(intent, locale, **kwargs)
        with self.subTest(intent=intent, payload=payload):
            json = self.invoke(intent, json=payload)
            self.assertIn(json['type'], (RESPONSE_TYPE_TELL, RESPONSE_TYPE_ASK, RESPONSE_TYPE_ASK_FREETEXT))
            self.assertIsInstance(json['text'], str)
            self.assertTrue(json['text'])
            return json, payload

    #
    # We name our self-test methods 'default_*_test' not to interfere with custom unit tests
    #

    def default_info_response_test(self, *args, **kwargs):   # pragma: no cover
        """ Get an "info" response
        """
        response = self._get(f"{self.host}:{self.port}/v1/{self.name}/info")

        self.assertTrue(response.ok)
        json = response.json()
        self.assertEqual(json['skillId'], f"{self.skill_id}")
        self.assertEqual(json['skillSpiVersion'], __spi_version__)
        self.assertIsInstance(json['supportedLocales'], list)
        self.setLocales(json['supportedLocales'])

    def default_swagger_json_test(self, *args, **kwargs):
        """ Get an "info" response
        """
        response = self._get(f'{self.host}:{self.port}/v1/swagger.json')
        self.assertTrue(response.ok)
        json = response.json()
        self.assertEqual(json['info']['title'], f"{self.name}")
        self.assertEqual(json['info']['version'], self.version)

    # Only makes sense if SDK installed in development mode
    @unittest.skipUnless('swagger_ui' in sys.modules, "requires swagger_ui")
    def default_swagger_ui_test(self, *args, **kwargs):
        """ Ping Swagger UI
        """
        response = self._get(f'{self.host}:{self.port}/swagger-ui/')
        self.assertTrue(response.ok)

    def default_invoke_response_test(self, *args, **kwargs):
        from .skill import app
        for name, intent in app().get_intents().items():
            for locale in self.locales:
                # Get response without attributes
                self.get_intent_invoke_response(name, locale)

                # Get response with AttributeV2
                self.get_intent_invoke_response(name, locale, attributesV2={'test': {}})

                # Get over the defined attributes
                for ename, entity in inspect.signature(intent.implementation).parameters.items():
                    type_ = (entity.annotation.__name__
                             if hasattr(entity.annotation, '__name__')
                             else str(entity.annotation))
                    for value in self.values.get(type_, []):
                        self.get_intent_invoke_response(name, locale, **{ename: value})
