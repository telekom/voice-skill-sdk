#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#
import unittest.mock
import datetime
from typing import List

from skill_sdk import l10n, intents, entities
from skill_sdk.intents import Context
from skill_sdk.test_helpers import create_context, mock_datetime_now
from skill_sdk.decorators import intent_handler

l10n.translations = {'de': l10n.Translations()}


class TestHandlerDecorator(unittest.TestCase):

    def test_handler_no_type_hints(self):
        """ Throw exception if no type hints """
        with self.assertRaises(ValueError):
            @intent_handler
            def decorated_test(context, param):
                return None

    def test_handler_no_type_hints_param(self):
        """ Throw exception if no type hints """
        with self.assertRaises(ValueError):
            @intent_handler
            def decorated_test(context: Context, param):
                return None

    def test_handler_context(self):
        @intent_handler
        def decorated_test(context: Context, timezone: str):
            return context, timezone

        ctx = create_context('TEST_CONTEXT')
        result = decorated_test(ctx)
        self.assertEqual(result, (ctx, 'Europe/Berlin'))

    def test_handler_array(self):
        """ Check simple usage with no conversion """

        @intent_handler
        def decorated_test(context: Context, arr: List[str]):
            return arr

        ctx = create_context('TEST_CONTEXT', arr=['31-12-2001', '31-12-1001', ])
        result = decorated_test(ctx)
        self.assertEqual(result, ['31-12-2001', '31-12-1001', ])

    def test_handler_dates(self):
        """ Check handler usage with date conversion """

        @intent_handler
        def decorated_test(context: Context, date_str: str = None, date_date: datetime.date = None):
            return date_str, date_date

        ctx = create_context('TEST_CONTEXT', date_str=['2001-12-31', '2001-12-31', ],
                             date_date=['2001-12-31', '1001-12-31', ])
        result = decorated_test(ctx)
        self.assertEqual(result, ('2001-12-31', datetime.date(2001, 12, 31)))

    def test_handler_date_array(self):
        """ Check usage with date array """

        @intent_handler
        def decorated_test(context: Context, date_arr: [datetime.date]):
            return date_arr

        ctx = create_context('TEST_CONTEXT', date_arr=['2001-12-31', '1001-12-31', ])
        result = decorated_test(ctx)
        self.assertEqual(result, [datetime.date(2001, 12, 31), datetime.date(1001, 12, 31)])

    def test_handler_date_fail(self):
        """ Test date conversion of invalid date """
        @intent_handler(False)
        def decorated_test(context: Context, date: datetime.date):
            return date

        ctx = create_context('TEST_CONTEXT', date=['not a date'])
        with self.assertRaises(intents.EntityValueException):
            result = decorated_test(ctx)

    def test_handler_fail_silent(self):
        """ Test date conversion of invalid date in "silent" mode """
        @intent_handler
        def date_test(context: Context, date: datetime.date):
            return date

        ctx = create_context('TEST_CONTEXT', date=['not a date'])
        result = date_test(ctx)
        self.assertIsInstance(result, intents.EntityValueException)

        @intent_handler
        def int_test(context: Context, integer: int):
            return integer

        ctx = create_context('TEST_CONTEXT', integer=['not a number'])
        result = int_test(ctx)
        self.assertIsInstance(result, intents.EntityValueException)

    def test_stacked_decorators(self):
        import functools

        m = unittest.mock.MagicMock()

        @intent_handler
        @functools.lru_cache(2)
        def test(date: datetime.date):
            m(date)

        ctx = create_context('TEST_CONTEXT', date=['2012-12-12'])
        test(ctx)
        test(ctx)
        ctx = create_context('TEST_CONTEXT', date=['2012-12-14'])
        test(ctx)
        test(ctx)
        self.assertEqual(m.call_count, 2)

    def test_with_error_handler(self):
        """ Test conversion failure if error_handler supplied """
        def error_handler(name, exception):
            return name, exception.value, str(exception.__cause__)

        @intent_handler(error_handler=error_handler)
        def date_test(context: Context, date: datetime.date):
            return None

        result = date_test(create_context('TEST_CONTEXT', date=['not a date']))
        self.assertEqual(result, ('date', 'not a date', str(ValueError('Unknown string format: not a date'))))
        self.assertIsNone(date_test(create_context('TEST_CONTEXT', date=[])))

    def test_handler_direct_call(self):
        """ Test direct call: no conversion """

        @intent_handler
        def decorated_test(date: datetime.date):
            return date

        result = decorated_test(date='2001-12-31')
        self.assertEqual(result, '2001-12-31')

        @intent_handler
        def decorated_test(date: datetime.date, date_arr: [datetime.date]):
            return date, date_arr

        result = decorated_test('2001-12-31', ['2001-12-31', '1001-12-31', ])
        self.assertEqual(result, ('2001-12-31', ['2001-12-31', '1001-12-31', ]))

    @mock_datetime_now(datetime.datetime(year=2100, month=12, day=31, hour=15), datetime)
    def test_multiple_date_values(self):
        """ Improve LUIS weekday parsing """
        from dateutil.tz import tzutc

        @intent_handler
        def date_test(date: [datetime.datetime]):
            return tuple(date)

        ctx = create_context('TEST_CONTEXT', date=['2100-12-31', 'T13:00:00Z'])
        self.assertEqual((datetime.datetime(2100, 12, 31, 0, 0),
                          datetime.datetime(2100, 12, 31, 13, 0, tzinfo=tzutc())), date_test(ctx))


class TestAttributesV2(unittest.TestCase):

    attr_v2 = {"id": 1, "value": "value", "nestedIn": [], "overlapsWith": []}
    context = create_context('TEST_CONTEXT', attr=attr_v2)

    def test_attributesV2(self):
        """ Test conversions to AttributesV2
        """
        @intent_handler
        def attr_v2_test(attr: entities.AttributeV2):
            return attr

        self.assertEqual(attr_v2_test(self.context), entities.AttributeV2(self.attr_v2))

    def test_attributesV2_list(self):
        """ Test conversions to List of AttributesV2
        """

        @intent_handler
        def attr_v2_test(attr: [entities.AttributeV2]):
            return attr[0]

        self.assertEqual(attr_v2_test(self.context), entities.AttributeV2(self.attr_v2))

        @intent_handler
        def attr_v2_test(attr: List[entities.AttributeV2]):
            return attr[0]

        self.assertEqual(attr_v2_test(self.context), entities.AttributeV2(self.attr_v2))

    def test_attributesV2_subtypes(self):
        """ Test conversions of AttributesV2 with subtypes
        """
        attr_v2 = {"id": 1, "value": "123456", "nestedIn": [], "overlapsWith": []}
        context = create_context('TEST_CONTEXT', attr=attr_v2)

        @intent_handler
        def attr_v2_test(attr: entities.AttributeV2[int]):
            return attr

        self.assertEqual(attr_v2_test(context), entities.AttributeV2(attr_v2, int))

    def test_attributesV2_list_subtypes(self):
        """ Test conversion of List of AttributesV2 with subtypes
        """
        attr_v2 = {"id": 1, "value": "123456", "nestedIn": [], "overlapsWith": []}
        context = create_context('TEST_CONTEXT', attr=attr_v2)

        @intent_handler
        def attr_v2_test(attr: List[entities.AttributeV2[int]]):
            return attr

        result = attr_v2_test(context)
        self.assertEqual(result, [entities.AttributeV2(attr_v2, int)])
