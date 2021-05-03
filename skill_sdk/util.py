#
#
# voice-skill-sdk
#
# (C) 2021, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

"""Utility functions"""

import re
import time
import asyncio
import inspect
import datetime
import threading
import contextlib
import unittest.mock
from functools import partial
from contextvars import copy_context
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Awaitable, Callable, Dict, List, Mapping, Text, TypeVar, Union

import orjson
import pydantic
import nest_asyncio
from pydantic import root_validator, validator, ValidationError  # noqa
from pydantic.utils import lenient_issubclass
import uvicorn


T = TypeVar("T")


def camel_to_snake(name):
    """
    Convert CamelCase to snake_case

    :param name:
    :return:
    """
    name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()


def snake_to_camel(name):
    """
    Convert snake_case to CamelCase

    :param name:
    :return:
    """
    reg_ex = re.compile(r"_+[a-z0-9]")
    return reg_ex.sub(lambda x: x.group(0)[1].upper(), name)


def orjson_dumps(v, *, default):
    """
    orjson.dumps returns bytes, to match standard json.dumps we need to decode

    :param v:
    :param default:
    :return:
    """
    return orjson.dumps(v, default=default).decode()


class Server(uvicorn.Server):
    """Uvicorn server implementing "run_in_thread" context manager:

    >>> server = Server("app:app", port=4242)
    >>> with server.run_in_thread():
    >>>     # Server started.
    >>>     ...
    >>> # Server stopped

    """

    WAIT_TIME = 1e-3

    def __init__(self, *args, **kwargs):
        if "loop" not in kwargs:
            kwargs.update(dict(loop="asyncio"))
        config = uvicorn.Config(*args, **kwargs)
        super().__init__(config)

    @contextlib.contextmanager
    def run_in_thread(self):
        thread = threading.Thread(target=self.run)
        thread.start()
        try:
            while not self.started:
                time.sleep(Server.WAIT_TIME)
            yield
        finally:
            self.should_exit = True
            thread.join()


class ContextVarExecutor(ThreadPoolExecutor):
    """Copy existing contextVars before executing"""

    def submit(self, *args, **kwargs):
        ctx = copy_context()

        return super().submit(ctx.run, *args, **kwargs)


async def run_in_executor(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """
    Run a synchronous function in a thread pool to prevent blocking

    :param func:
    :param args:
    :param kwargs:
    :return:
    """
    loop = asyncio.get_running_loop()

    return await loop.run_in_executor(
        ContextVarExecutor(), partial(func, *args, **kwargs)
    )


def run_until_complete(func: Awaitable[T]) -> T:
    """
    Run an asynchronous function in synchronous context

    :param func:
    :return:
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        nest_asyncio.apply(loop)

    return loop.run_until_complete(func)


class BaseModel(pydantic.BaseModel):
    """
    Override Pydantic's BaseModel defaults:

        - use faster orjson for objects serialization

        - make all instances immutable
            (with an exception of `responses.Result` - that is mutable for backward compatibility)

        - allow objects population by the model attribute

        - use enum value instead of raw enums when populating properties

    """

    class Config:
        """Alter default config for base models"""

        # Use orjson to serialize
        json_dumps = orjson_dumps

        # Make all model instances "faux-immutable" by default
        allow_mutation = False

        # Allow objects population by the model attribute, as well as the alias
        allow_population_by_field_name = True

        # Populate models with the value property of enums, rather than the raw enum
        use_enum_values = True

    def dict(self, *args, **kwargs) -> Dict[Text, Any]:
        """
        Alter parent defaults when exporting:

            - exclude "None" values
            - export fields by alias

        """
        params = {
            "exclude_none": kwargs["exclude_none"]
            if "exclude_none" in kwargs
            else True,
            "by_alias": kwargs["by_alias"] if "by_alias" in kwargs else True,
        }

        return super().dict(*args, **{**kwargs, **params})


class CamelModel(BaseModel):
    """CamelModel will use camelCase aliases for snake_case fields"""

    class Config:
        """Set `snake_to_camel` as alias generator function"""

        alias_generator = snake_to_camel


def attrs_examples(intent: Callable) -> Dict[str, List]:
    """
    Create attribute samples for intent

    :param intent:
    :return:
    """

    from skill_sdk.intents import AttributeV2, Request

    # Extract parameter arguments from intent implementation
    parameters = {
        name: param
        for name, param in inspect.signature(intent).parameters.items()
        if not lenient_issubclass(param.annotation, Request)
    }

    # 'timezone' is always present
    if "timezone" not in parameters:
        parameters["timezone"] = inspect.Parameter(
            "timezone", inspect.Parameter.KEYWORD_ONLY, default="UTC"
        )

    def value(param):
        """Try to set value to an attribute"""
        return (
            param.default
            if param.default and param.default != inspect.Parameter.empty
            else "value"
        )

    attrs_v2 = {
        name: [AttributeV2(value=value(param), id=0).dict()]
        for name, param in parameters.items()
    }

    return attrs_v2


#
#   Helpers for Swagger UI/Redoc
#


def intent_examples(intents: Mapping[Text, Callable]) -> Dict[str, Dict]:
    """
    Create example intent calls

    :param intents: List of intents
    :return:
    """
    examples = {
        f"{snake_to_camel(name)}Example": {
            "summary": name,
            "value": {
                "context": {
                    "intent": name,
                    "attributesV2": attrs_examples(intent),
                    "configuration": {},
                    "locale": "de",
                    "tokens": {},
                },
                "session": {
                    "id": 123,
                    "new": True,
                    "attributes": {"attr-1": 1, "attr-2": "2"},
                },
            },
        }
        for name, intent in intents.items()
    }

    return examples


def populate_intent_examples(intents: Mapping[Text, Callable]):
    """
    Create intent invoke examples for Swagger UI

    :param intents:
    :return:
    """
    from skill_sdk.intents import Context

    Context.__config__.schema_extra = {"examples": intent_examples(intents)}


#
#   Unit test helpers:
#

datetime_class = datetime.datetime


def mock_datetime_now(target, dt):
    """
    Patch datetime.datetime.now with __instancecheck__
    """

    class DatetimeSubclassMeta(type):
        """Metaclass to mock __instancecheck__"""

        @classmethod
        def __instancecheck__(mcs, obj):  # NOSONAR
            return isinstance(obj, datetime_class)

    class BaseMockedDatetime(datetime_class):
        """Patch the original datetime.datetime.now"""

        @classmethod
        def now(cls, tz=None):
            return target.replace(tzinfo=tz)

        @classmethod
        def utcnow(cls):
            return target

    dt_mock = DatetimeSubclassMeta("datetime", (BaseMockedDatetime,), {})
    return unittest.mock.patch.object(dt, "datetime", dt_mock)


def create_request(
    intent: Text, session: Union[CamelModel, Dict[Text, Text]] = None, **kwargs
):
    """
    Skill invoke request factory: used in unit tests to mock a skill invoke request

    :param intent:      Intent name
    :param session:     Session (or session attributes)
    :param kwargs:      Keyword arguments are forwarded to create_context factory
    :return:
    """

    from skill_sdk.__version__ import __spi_version__
    from skill_sdk.intents import Request, Session
    from skill_sdk.responses import SessionResponse

    example: Dict = Session.Config.schema_extra["example"]
    if isinstance(session, Session):
        _session = session.copy()
    elif isinstance(session, SessionResponse):
        _session = Session(
            **{
                **dict(id=example["id"], new=False),
                **dict(attributes=session.attributes),
            }
        )
    elif isinstance(session, Dict):
        _session = Session(
            **{**dict(id=example["id"], new=example["new"]), **dict(attributes=session)}
        )
    else:
        _session = Session(**example)

    return Request(
        context=create_context(intent=intent, **kwargs),
        session=_session,
        spi_version=__spi_version__,
    )


def test_request(
    intent: Text,
    session: Union[CamelModel, Dict[Text, Text]] = None,
    translation=None,  # noqa: don't want to import i18n for type hinting `Translations`
    **kwargs,
):
    """
    Context manager to setup global request object for unit tests

    :param intent:      Intent name for the test request
    :param session:     Session attributes
    :param translation: Optional translations
    :param kwargs:      The rest of kwargs goes to `create_context`

    :return:
    """
    from skill_sdk.i18n import Translations
    from skill_sdk.intents.request import RequestContextVar

    translations = kwargs.pop("translation", Translations())

    request = create_request(intent, session=session, **kwargs).with_translation(
        translations
    )

    return RequestContextVar(request=request)


def create_context(
    intent: Text,
    locale: Text = None,
    tokens: Dict[Text, Text] = None,
    configuration: Dict[Text, Dict] = None,
    **kwargs,
):
    """
    Intent invoke context factory:
    Creates skill invocation context with attributes supplied as keyword arguments.

    :param intent:  Intent name
    :param locale:  Request locale
    :param tokens:  Intent tokens (if requires)
    :param configuration:  Skill configuration
    :param kwargs:  Attributes(V2)
    :return:
    """

    from skill_sdk.intents import Context, AttributeV2

    def parse(_: Any) -> AttributeV2:
        """Try to create AttributeV2 from any string"""

        try:
            attr_v2: AttributeV2 = AttributeV2(_)
        except (AttributeError, TypeError, ValidationError, ValueError):
            attr_v2 = AttributeV2({"id": 0, "value": _})
        return attr_v2

    attributes_v2 = {
        key: [parse(each) for each in value]
        if isinstance(value, (list, tuple))
        else [parse(value)]
        for key, value in kwargs.items()
        if value is not None
    }

    # 'timezone' is always present
    if "timezone" not in attributes_v2:
        attributes_v2["timezone"] = [parse("Europe/Berlin")]

    # Create `attributes` dict for backward compatibility
    attributes: Dict[Text, List] = {
        key: [item.value for item in value] for key, value in attributes_v2.items()
    }

    return Context(
        attributes=attributes or {},
        attributes_v2=attributes_v2 or {},
        configuration=configuration or {},
        intent=intent,
        locale=locale or "de",
        tokens=tokens or {},
    )
