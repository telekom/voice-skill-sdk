#
# voice-skill-sdk
#
# (C) 2021, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#

import unittest
import datetime
from datetime import timedelta
from dateutil import parser
from dateutil.tz import tzutc, tzoffset

from skill_sdk.intents import entities
from skill_sdk.intents.entities import (
    TimeRange,
    TimeSet,
    AttributeV2,
    on_off_to_boolean,
    convert,
)
from skill_sdk.util import mock_datetime_now


class TestEntityOnOff(unittest.TestCase):
    def test_values_on(self):
        for value in ("on", "ON", "On", "true", "TRUE", "True", "1"):
            self.assertEqual(on_off_to_boolean(value), True)

    def test_values_off(self):
        for value in ("off", "OFF", "Off", "false", "FALSE", "False", "0"):
            self.assertEqual(on_off_to_boolean(value), False)

    def test_values_bad(self):
        for value in (" on", "ON ", "", None, "\x00", True, False):
            with self.assertRaises(ValueError):
                on_off_to_boolean(value)


class TestEntityTimeRange(unittest.TestCase):
    def test_init(self):
        r = TimeRange("2019-02-08T12:27:20Z/2019-02-08T13:27:20Z")
        self.assertEqual(
            r.begin,
            datetime.datetime(
                year=2019, month=2, day=8, hour=12, minute=27, second=20, tzinfo=tzutc()
            ),
        )
        self.assertEqual(
            r.end,
            datetime.datetime(
                year=2019, month=2, day=8, hour=13, minute=27, second=20, tzinfo=tzutc()
            ),
        )
        self.assertEqual(TimeRange("2019-02-08T12:27:20Z/2019-02-08T13:27:20Z"), r)
        self.assertNotEqual(r, 1)

        with self.assertRaises(parser.ParserError):
            TimeRange("")

    def test_contains(self):
        r = TimeRange("2019-02-08T12:27:20/2019-02-08T13:27:20")
        self.assertTrue(
            datetime.datetime(year=2019, month=2, day=8, hour=12, minute=28) in r
        )
        self.assertFalse(datetime.datetime(year=2019, month=2, day=8, hour=12) in r)
        self.assertTrue(datetime.time(hour=13) in r)
        self.assertTrue(datetime.date(year=2019, month=2, day=8) in r)

        with self.assertRaises(TypeError):
            (2 in r)

        # can't compare offset-naive and offset-aware datetimes
        with self.assertRaises(TypeError):
            r = TimeRange("2019-02-08T12:27:20Z/2019-02-08T13:27:20Z")
            self.assertFalse(
                datetime.datetime(year=2019, month=2, day=8, hour=12, minute=28) in r
            )

    def test_range(self):
        weeks = list(
            TimeRange("2019-02-08T12:27:20/2019-03-01T13:27:20").range("weeks")
        )
        self.assertEqual(
            weeks,
            [
                datetime.datetime(
                    year=2019, month=2, day=8, hour=12, minute=27, second=20
                ),
                datetime.datetime(
                    year=2019, month=2, day=15, hour=12, minute=27, second=20
                ),
                datetime.datetime(
                    year=2019, month=2, day=22, hour=12, minute=27, second=20
                ),
                datetime.datetime(
                    year=2019, month=3, day=1, hour=12, minute=27, second=20
                ),
            ],
        )
        days = list(TimeRange("2019-02-08T12:27:20/2019-02-09T13:27:20").range("days"))
        self.assertEqual(
            days,
            [
                datetime.datetime(
                    year=2019, month=2, day=8, hour=12, minute=27, second=20
                ),
                datetime.datetime(
                    year=2019, month=2, day=9, hour=12, minute=27, second=20
                ),
            ],
        )
        hours = list(
            TimeRange("2019-02-08T12:27:20/2019-02-08T15:48:20").range("hours")
        )
        self.assertEqual(
            hours,
            [
                datetime.datetime(
                    year=2019, month=2, day=8, hour=12, minute=27, second=20
                ),
                datetime.datetime(
                    year=2019, month=2, day=8, hour=13, minute=27, second=20
                ),
                datetime.datetime(
                    year=2019, month=2, day=8, hour=14, minute=27, second=20
                ),
                datetime.datetime(
                    year=2019, month=2, day=8, hour=15, minute=27, second=20
                ),
            ],
        )

    def test_range_open(self):
        """Test datetime range with open begin/end"""

        open_start = TimeRange("/2019-12-31T23:59:59")
        self.assertTrue(
            datetime.datetime(year=2019, month=12, day=31, hour=23, minute=59)
            in open_start
        )
        self.assertFalse(
            datetime.datetime(year=2020, month=1, day=1, hour=12) in open_start
        )
        self.assertTrue(datetime.time(hour=13) in open_start)
        self.assertTrue(datetime.date(year=2019, month=2, day=8) in open_start)

        with mock_datetime_now(
            datetime.datetime(year=2019, month=12, day=29, hour=15), datetime
        ):
            days = list(open_start.range("days"))
            self.assertEqual(
                days,
                [
                    datetime.datetime(year=2019, month=12, day=29, hour=15),
                    datetime.datetime(year=2019, month=12, day=30, hour=15),
                    datetime.datetime(year=2019, month=12, day=31, hour=15),
                ],
            )

        open_end = TimeRange("2019-12-31T23:59:59/")
        self.assertTrue(
            datetime.datetime(
                year=2019, month=12, day=31, hour=23, minute=59, second=59
            )
            in open_end
        )
        self.assertFalse(
            datetime.datetime(
                year=2019, month=12, day=31, hour=23, minute=59, second=58
            )
            in open_end
        )
        self.assertTrue(datetime.time(hour=23, minute=59, second=59) in open_end)
        self.assertTrue(datetime.date(year=2020, month=1, day=1) in open_end)

        weeks = open_end.range("weeks")
        self.assertEqual(
            datetime.datetime(
                year=2019, month=12, day=31, hour=23, minute=59, second=59
            ),
            next(weeks),
        )
        self.assertEqual(
            datetime.datetime(year=2020, month=1, day=7, hour=23, minute=59, second=59),
            next(weeks),
        )

        with self.assertRaises(OverflowError):
            list(weeks)

    def test_str(self):
        r = TimeRange("2019-02-08T12:27:20/2019-03-01T13:27:20")
        self.assertEqual(
            str(r), '<TimeRange begin="2019-02-08 12:27:20" end="2019-03-01 13:27:20">'
        )


@mock_datetime_now(
    datetime.datetime(year=2019, month=10, day=31, hour=15, tzinfo=tzutc()), datetime
)
class TestEntityTimeSet(unittest.TestCase):
    def test_init(self):
        self.assertEqual('<TimeSet timex="T08" tz="tzutc()">', str(TimeSet("T08")))
        timex = TimeSet("T08", tz="Europe/Berlin")
        self.assertIsInstance(timex.tz, datetime.tzinfo)

        with self.assertRaises(ValueError):
            TimeSet("Hello").range()

    def test_range(self):
        # Test rrule string representation
        self.assertEqual(
            "DTSTART:20191031T150000\nRRULE:FREQ=DAILY;UNTIL=99991231T235959",
            str(TimeSet("T15").range()),
        )
        self.assertEqual(
            "DTSTART:20191101T080000\nRRULE:FREQ=DAILY;UNTIL=99991231T235959",
            str(TimeSet("T08").range()),
        )

        # Jeden Tag um 8 Uhr
        result = list(TimeSet("T08:00+02:00").range(5, until="2019-11-05T12:00Z"))
        dt_test = datetime.datetime(
            year=2019, month=11, day=1, hour=8, tzinfo=tzoffset(None, 7200)
        )
        self.assertEqual(
            result,
            [
                dt_test,
                dt_test + timedelta(days=1),
                dt_test + timedelta(days=2),
                dt_test + timedelta(days=3),
                dt_test + timedelta(days=4),
            ],
        )

        # Jeden Freitag um 10 Uhr
        result = list(TimeSet("XXXX-WXX-5T10:00Z").range(until="2019-11-30"))
        dt_test = datetime.datetime(year=2019, month=11, day=1, hour=10, tzinfo=tzutc())
        self.assertEqual(
            result,
            [
                dt_test,
                dt_test + timedelta(days=7),
                dt_test + timedelta(days=14),
                dt_test + timedelta(days=21),
                dt_test + timedelta(days=28),
            ],
        )

        with self.assertRaises(ValueError):
            list(TimeSet("-W").range(until="2019-11-30"))

        # Jeden Montag bis Freitag
        result = list(TimeSet("(XXXX-WXX-1,XXXX-WXX-5,P4D)").range(8))
        self.assertEqual(
            result,
            [
                datetime.datetime(year=2019, month=11, day=1, tzinfo=tzutc()),
                datetime.datetime(year=2019, month=11, day=4, tzinfo=tzutc()),
                datetime.datetime(year=2019, month=11, day=5, tzinfo=tzutc()),
                datetime.datetime(year=2019, month=11, day=6, tzinfo=tzutc()),
                datetime.datetime(year=2019, month=11, day=7, tzinfo=tzutc()),
                datetime.datetime(year=2019, month=11, day=8, tzinfo=tzutc()),
                datetime.datetime(year=2019, month=11, day=11, tzinfo=tzutc()),
                datetime.datetime(year=2019, month=11, day=12, tzinfo=tzutc()),
            ],
        )

        # Jeden Montag 14 bis 18 Uhr '(XXXX-WXX-1T14,XXXX-WXX-1T18,PT4H)'
        result = list(TimeSet("(XXXX-WXX-1T14,XXXX-WXX-1T18,PT4H)").range(6))
        self.assertEqual(
            result,
            [
                datetime.datetime(year=2019, month=11, day=4, hour=14, tzinfo=tzutc()),
                datetime.datetime(year=2019, month=11, day=4, hour=15, tzinfo=tzutc()),
                datetime.datetime(year=2019, month=11, day=4, hour=16, tzinfo=tzutc()),
                datetime.datetime(year=2019, month=11, day=4, hour=17, tzinfo=tzutc()),
                datetime.datetime(year=2019, month=11, day=4, hour=18, tzinfo=tzutc()),
                datetime.datetime(year=2019, month=11, day=11, hour=14, tzinfo=tzutc()),
            ],
        )


class TestEntityAttributeV2(unittest.TestCase):
    def test_init(self):
        attr = AttributeV2(
            {
                "id": 0,
                "value": "super rtl",
                "extras": {"literal": "super rtl"},
                "nestedIn": None,
                "overlapsWith": None,
            }
        )
        self.assertEqual("super rtl", attr.value)
        self.assertEqual([], attr.nested_in)
        self.assertEqual([], attr.overlaps_with)
        self.assertEqual({"literal": "super rtl"}, attr.extras)

    def test_init_with_mapper(self):
        attr = AttributeV2(
            {"id": 0, "value": "123456", "nestedIn": [], "overlapsWith": []}, int
        )
        self.assertEqual(attr.value, 123456)

    def test_init_with_self(self):
        attr = AttributeV2(
            {"id": 0, "value": "123456", "nestedIn": [], "overlapsWith": []}, int
        )
        self.assertEqual(attr, AttributeV2(attr))

    def test_init_with_kwargs(self):
        attr = AttributeV2("123456", int, id=0, nested_in=[1], overlaps_with=[2])
        self.assertEqual(
            "AttributeV2(id=0, value=123456, nested_in=[1], overlaps_with=[2], extras=None)",
            repr(attr),
        )

    def test_equal(self):
        attr = AttributeV2(
            {
                "id": 1,
                "value": "123456",
                "extras": {"literal": "123456"},
                "nestedIn": [1, 2],
                "overlapsWith": [3],
            },
            int,
        )
        self.assertEqual(
            attr,
            AttributeV2(
                {
                    "id": 1,
                    "value": "123456",
                    "extras": {"literal": "123456"},
                    "nestedIn": [1, 2],
                    "overlapsWith": [3],
                },
                int,
            ),
        )
        self.assertNotEqual(attr, 1)

    def test_repr(self):
        attr = AttributeV2(
            {"id": 1, "value": "123456", "nestedIn": [1, 2], "overlapsWith": [3]}, int
        )
        self.assertEqual(
            "AttributeV2(id=1, value=123456, nested_in=[1, 2], overlaps_with=[3], extras=None)",
            repr(attr),
        )


class TestConverter(unittest.TestCase):
    def test_converter(self):
        self.assertEqual(
            convert("2106-12-31T12:30", datetime.date), datetime.date(2106, 12, 31)
        )
        self.assertEqual(
            convert("2106-12-31T12:30", datetime.datetime),
            datetime.datetime(2106, 12, 31, 12, 30, 00),
        )
        self.assertEqual(
            convert("2106-12-31T12:30", datetime.time), datetime.time(12, 30, 00)
        )
        self.assertEqual(convert("2106-12-31T12:30", str), "2106-12-31T12:30")
        self.assertEqual(convert("12.30", float), 12.3)
        self.assertEqual(convert("off", bool), False)
        self.assertEqual(convert("1", bool), True)
        self.assertEqual(convert("ja", "str"), "ja")

        self.assertEqual(
            convert("PT1H5M6S", datetime.timedelta),
            datetime.timedelta(hours=1, minutes=5, seconds=6),
        )
        delta = convert("PT1H5M6S", datetime.timedelta)
        self.assertEqual(convert(delta, datetime.timedelta), delta)

        with self.assertRaises(ValueError):
            convert("Something", datetime.time)
        with self.assertRaises(ValueError):
            convert("12.30", int)
        with self.assertRaises(ValueError):
            convert("Ja", bool)
        with self.assertRaises(ValueError):
            convert(1, bool)

    def test_datetime(self):
        self.assertEqual(
            entities.to_datetime("2106-12-31T12:30"),
            datetime.datetime(2106, 12, 31, 12, 30, 00),
        )
        self.assertEqual(
            entities.to_datetime(datetime.date(2106, 12, 31)),
            datetime.datetime(2106, 12, 31, 00, 00, 00),
        )

        now = datetime.datetime.now()
        self.assertEqual(
            entities.to_datetime(datetime.time(12, 30)),
            datetime.datetime(now.year, now.month, now.day, 12, 30, 00),
        )

        self.assertEqual(
            entities.to_datetime(["2106-12-31T12:30"]),
            datetime.datetime(2106, 12, 31, 12, 30, 00),
        )
        self.assertEqual(
            entities.to_datetime(["2106-12-31T12:30", "2116-12-31T12:30"]),
            datetime.datetime(2106, 12, 31, 12, 30, 00),
        )

        self.assertEqual(
            entities.to_datetime(["--12-31"]),
            datetime.datetime(datetime.datetime.now().year, 12, 31, 00, 00),
        )
        self.assertEqual(
            entities.to_datetime(["--12-31T12:30"]),
            datetime.datetime(datetime.datetime.now().year, 12, 31, 12, 30),
        )

        self.assertEqual(entities.to_datetime([]), datetime.datetime.min)

    def test_date(self):
        self.assertEqual(
            entities.to_date("2106-12-31T12:30"), datetime.date(2106, 12, 31)
        )
        self.assertEqual(
            entities.to_date(datetime.datetime(2106, 12, 31, 12, 30, 00)),
            datetime.date(2106, 12, 31),
        )

        self.assertEqual(
            entities.to_date(["2106-12-31T12:30"]), datetime.date(2106, 12, 31)
        )
        self.assertEqual(
            entities.to_date(["2106-12-31T12:30", "2116-12-31T12:30"]),
            datetime.date(2106, 12, 31),
        )

        self.assertEqual(
            entities.to_date(["--12-31"]),
            datetime.date(datetime.datetime.now().year, 12, 31),
        )
        self.assertEqual(
            entities.to_date(["--12-31T12:30"]),
            datetime.date(datetime.datetime.now().year, 12, 31),
        )

        self.assertEqual(entities.to_date([]), datetime.date.min)

    def test_time(self):
        self.assertEqual(entities.to_time("2106-12-31T12:30"), datetime.time(12, 30))
        self.assertEqual(
            entities.to_time(datetime.datetime(2106, 12, 31, 12, 30, 00)),
            datetime.time(12, 30),
        )

        self.assertEqual(entities.to_time(["2106-12-31T12:30"]), datetime.time(12, 30))
        self.assertEqual(
            entities.to_time(["2106-12-31T12:30", "2116-12-31T15:30"]),
            datetime.time(12, 30),
        )

        self.assertEqual(entities.to_time(["--12-31"]), datetime.time(0, 0))
        self.assertEqual(entities.to_time(["--12-31T12:30"]), datetime.time(12, 30))

        self.assertEqual(entities.to_time([]), datetime.time.min)
