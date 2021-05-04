#
# voice-skill-sdk
#
# (C) 2021, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#

import asyncio
import inspect
import unittest.mock
import datetime
from contextvars import ContextVar
from typing import List
import pytest

from skill_sdk import Response
from skill_sdk.intents import (
    intent_handler,
    AttributeV2,
    Context,
    EntityValueException,
)
from skill_sdk import util
from skill_sdk.util import create_request, mock_datetime_now


class TestHandlerDecorator(unittest.TestCase):
    def test_handler_no_type_hints(self):
        """Throw exception if no type hints"""
        with self.assertRaises(ValueError):

            @intent_handler
            def decorated_test(context, param):
                return None

    def test_handler_no_type_hints_param(self):
        """Throw exception if no type hints"""
        with self.assertRaises(ValueError):

            @intent_handler
            def decorated_test(param):
                return None

    def test_handler_context(self):
        @intent_handler
        def decorated_test(context: Context, timezone: str):
            return context, timezone

        r = create_request("TEST_CONTEXT")
        result = decorated_test(r)
        self.assertEqual(result, (r.context, "Europe/Berlin"))

    def test_handler_array(self):
        """Check simple usage with no conversion"""

        @intent_handler
        def decorated_test(arr: List[str]):
            return arr

        r = create_request(
            "TEST_CONTEXT",
            arr=[
                "31-12-2001",
                "31-12-1001",
            ],
        )
        result = decorated_test(r)
        self.assertEqual(
            result,
            [
                "31-12-2001",
                "31-12-1001",
            ],
        )

    def test_handler_dates(self):
        """Check handler usage with date conversion"""

        @intent_handler
        def decorated_test(date_str: str = None, date_date: datetime.date = None):
            return date_str, date_date

        r = create_request(
            "TEST_CONTEXT",
            date_str=[
                "2001-12-31",
                "2001-12-31",
            ],
            date_date=[
                "2001-12-31",
                "1001-12-31",
            ],
        )
        result = decorated_test(r)
        self.assertEqual(result, ("2001-12-31", datetime.date(2001, 12, 31)))

    def test_handler_date_array(self):
        """Check usage with date array"""

        @intent_handler
        def decorated_test(date_arr: [datetime.date]):
            return date_arr

        r = create_request(
            "TEST_CONTEXT",
            date_arr=[
                "2001-12-31",
                "1001-12-31",
            ],
        )
        result = decorated_test(r)
        self.assertEqual(
            result, [datetime.date(2001, 12, 31), datetime.date(1001, 12, 31)]
        )

    def test_handler_date_fail(self):
        """Test date conversion of invalid date"""

        @intent_handler(False)
        def decorated_test(date: datetime.date):
            return date

        r = create_request("TEST_CONTEXT", date=["not a date"])
        with self.assertRaises(EntityValueException):
            result = decorated_test(r)

    def test_handler_fail_silent(self):
        """Test date conversion of invalid date in "silent" mode"""

        @intent_handler
        def date_test(date: datetime.date):
            return date

        r = create_request("TEST_CONTEXT", date=["not a date"])
        result = date_test(r)
        self.assertIsInstance(result, EntityValueException)

        @intent_handler
        def int_test(integer: int):
            return integer

        r = create_request("TEST_CONTEXT", integer=["not a number"])
        result = int_test(r)
        self.assertIsInstance(result, EntityValueException)

    def test_stacked_decorators(self):
        import functools

        m = unittest.mock.MagicMock()

        @intent_handler
        @functools.lru_cache(2)
        def test(date: datetime.date):
            m(date)

        r = create_request("TEST_CONTEXT", date=["2012-12-12"])
        test(r)
        test(r)
        r = create_request("TEST_CONTEXT", date=["2012-12-14"])
        test(r)
        test(r)
        self.assertEqual(m.call_count, 2)

    def test_with_error_handler(self):
        """Test conversion failure if error_handler provided"""
        from skill_sdk.intents import ErrorHandlerType

        error_handler: ErrorHandlerType

        def error_handler(name, exception):
            return name, exception.value, str(exception.__cause__)

        @intent_handler(error_handler=error_handler)
        def date_test(date: datetime.date):
            return None

        result = date_test(create_request("TEST_CONTEXT", date=["not a date"]))
        self.assertEqual(
            result,
            (
                "date",
                "not a date",
                str(ValueError("Unknown string format: not a date")),
            ),
        )
        self.assertIsNone(date_test(create_request("TEST_CONTEXT", date=[])))

    def test_handler_direct_call(self):
        """Test direct call: no conversion"""

        @intent_handler
        def decorated_test(date: datetime.date):
            return date

        result = decorated_test(date="2001-12-31")
        self.assertEqual(result, "2001-12-31")

        @intent_handler
        def decorated_test(date: datetime.date, date_arr: [datetime.date]):
            return date, date_arr

        result = decorated_test(
            "2001-12-31",
            [
                "2001-12-31",
                "1001-12-31",
            ],
        )
        self.assertEqual(
            result,
            (
                "2001-12-31",
                [
                    "2001-12-31",
                    "1001-12-31",
                ],
            ),
        )

    @mock_datetime_now(
        datetime.datetime(year=2100, month=12, day=31, hour=15), datetime
    )
    def test_multiple_date_values(self):
        """Improve LUIS weekday parsing"""
        from dateutil.tz import tzutc

        @intent_handler
        def date_test(date: [datetime.datetime]):
            return tuple(date)

        r = create_request("TEST_CONTEXT", date=["2100-12-31", "T13:00:00Z"])
        self.assertEqual(
            (
                datetime.datetime(2100, 12, 31, 0, 0),
                datetime.datetime(2100, 12, 31, 13, 0, tzinfo=tzutc()),
            ),
            date_test(r),
        )


class TestAttributesV2(unittest.TestCase):

    attr_v2 = {"id": 1, "value": "value", "nestedIn": [], "overlapsWith": []}
    request = create_request("TEST_CONTEXT", attr=attr_v2)

    def test_attributesV2(self):
        """Test conversions to AttributesV2"""

        @intent_handler
        def attr_v2_test(attr: AttributeV2):
            return attr

        self.assertEqual(attr_v2_test(self.request), AttributeV2(self.attr_v2))

    def test_attributesV2_list(self):
        """Test conversions to List of AttributesV2"""

        @intent_handler
        def attr_v2_test(attr: [AttributeV2]):
            return attr[0]

        self.assertEqual(attr_v2_test(self.request), AttributeV2(self.attr_v2))

        @intent_handler
        def attr_v2_test(attr: List[AttributeV2]):
            return attr[0]

        self.assertEqual(attr_v2_test(self.request), AttributeV2(self.attr_v2))

    def test_attributesV2_subtypes(self):
        # Test conversions of AttributesV2 with subtypes
        attr_v2 = {"id": 1, "value": "123456", "nestedIn": [], "overlapsWith": []}
        context = create_request("TEST_CONTEXT", attr=attr_v2)

        @intent_handler
        def attr_v2_test(attr: AttributeV2[int]):
            return attr

        self.assertEqual(attr_v2_test(context), AttributeV2(attr_v2, int))

    def test_attributesV2_list_subtypes(self):
        # Test conversion of List of AttributesV2 with subtypes
        attr_v2 = {"id": 1, "value": "123456", "nestedIn": [], "overlapsWith": []}
        context = create_request("TEST_CONTEXT", attr=attr_v2)

        @intent_handler
        def attr_v2_test(attr: List[AttributeV2[int]]):
            return attr

        result = attr_v2_test(context)
        self.assertEqual(result, [AttributeV2(attr_v2, int)])


@pytest.mark.asyncio
async def test_async_decorator():
    from skill_sdk.intents.handlers import get_inner

    @intent_handler
    def sync_handler():  # noqa
        pass

    assert inspect.iscoroutinefunction(get_inner(sync_handler)) is False
    assert inspect.iscoroutinefunction(sync_handler) is False

    @intent_handler
    async def async_handler():  # noqa
        return None

    assert inspect.iscoroutinefunction(async_handler) is True
    assert inspect.iscoroutinefunction(get_inner(async_handler)) is True

    @intent_handler(silent=False)
    async def async_handler():  # noqa
        return None

    assert inspect.iscoroutinefunction(async_handler) is True
    assert inspect.iscoroutinefunction(get_inner(async_handler)) is True


@pytest.mark.asyncio
async def test_async_error_handler():
    def sync_error_handler(name, exception) -> Response:
        return Response(str(exception.__cause__))

    async def error_handler(name, exception) -> Response:
        return Response(str(exception.__cause__))

    with pytest.raises(ValueError):

        @intent_handler(error_handler=sync_error_handler)
        async def async_handler():
            return None

    @intent_handler(error_handler=error_handler)
    async def async_handler():
        return None


@pytest.mark.asyncio
async def test_handler_array_async():
    @intent_handler
    def decorated_test(arr: List[str]):
        return arr

    r = create_request(
        "TEST_CONTEXT",
        arr=[
            "31-12-2001",
            "31-12-1001",
        ],
    )
    result = decorated_test(r)
    assert result == [
        "31-12-2001",
        "31-12-1001",
    ]


def test_context_vars_executor():

    ctx = ContextVar("Var")

    def handler():
        with pytest.raises(LookupError):
            ctx.get()

    def same_context_handler():
        assert ctx.get() == {"a": 1}
        return ctx.get()

    async def main(*, loop):
        ctx.set({"a": 1})

        ret = await loop.run_in_executor(None, handler)
        assert ret is None

        ret = await util.run_in_executor(same_context_handler)
        assert ret == {"a": 1}

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop=loop))
