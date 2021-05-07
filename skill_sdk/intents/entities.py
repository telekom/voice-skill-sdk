#
# voice-skill-sdk
#
# (C) 2021, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

"""Intent entities and conversion functions"""

import re
import logging
import datetime
import functools
from typing import Any, Callable, Dict, Generic, List, Optional, Text, TypeVar, Union
from dateutil import parser, rrule
from dateutil.tz import tzutc, gettz
import isodate
from pydantic import root_validator

from skill_sdk.util import CamelModel


logger = logging.getLogger(__name__)
T = TypeVar("T")


def get_entity(entities: List[Any]) -> Optional[Any]:
    """Silently return first element of a list, or unchanged value otherwise"""
    return (
        next(iter(entities), None) if isinstance(entities, (list, tuple)) else entities
    )


@functools.singledispatch
def to_datetime(value) -> datetime.datetime:
    """Parse datetime string"""
    return parser.parse(value)


@functools.singledispatch
def to_date(value) -> datetime.date:
    """Parse datetime and return date component"""
    return to_datetime(value).date()


@functools.singledispatch
def to_time(value) -> datetime.time:
    """Parse datetime and return time component"""
    return to_datetime(value).time()


@functools.singledispatch
def to_timedelta(value) -> datetime.timedelta:
    """Parse duration string and return timedelta"""
    return isodate.parse_duration(value)


@to_timedelta.register(datetime.timedelta)
def __to_timedelta(value: datetime.timedelta):
    """No-op if already converted"""
    return value


def on_off_to_boolean(value: str) -> bool:
    """
    Converts ON_OFF entity value to boolean
    The value might be any string of ``0``, ``1``, ``on``, ``off``, ``true``, ``false``, case insensitive.

    :param value: the entity value
    """
    logger.debug("converting value %s to bool", repr(value))
    if not isinstance(value, str):
        raise ValueError(f"The value {value.__repr__()} is not a string.")
    if value.lower() in ("on", "true", "yes", "1"):
        return True
    if value.lower() in ("off", "false", "no", "0"):
        return False
    raise ValueError(f"{value} is not a proper on/off value.")


class TimeRange:
    """
    Date/Time range representation
    """

    __slots__ = ("begin", "end")

    begin: Optional[datetime.datetime]
    end: Optional[datetime.datetime]

    def __init__(self, value: str):
        self.begin, self.end = [
            parser.parse(v) if v else None for v in value.split("/")
        ]

    def __contains__(
        self, value: Union[datetime.datetime, datetime.date, datetime.time]
    ) -> bool:

        begin = self.begin or datetime.datetime.min
        end = self.end or datetime.datetime.max

        if isinstance(value, datetime.time):
            return begin.time() <= value <= end.time()
        elif isinstance(value, datetime.datetime):
            return begin <= value <= end
        elif isinstance(value, datetime.date):
            return begin.date() <= value <= end.date()

        raise TypeError("Can't compare TimeRange to %s", type(value).__name__)

    def __eq__(self, other):
        try:
            return (
                self.__slots__ == other.__slots__
                and self.begin == other.begin
                and self.end == other.end
            )
        except AttributeError:
            return False

    def range(self, frame: str):
        """
        Generator yielding datetime values within a particular frame: hours/days/weeks/etc

        :param frame:
        :return:
        @throws:        OverflowError in open-end datetime case
        """

        current = self.begin or datetime.datetime.now()
        end = self.end or datetime.datetime.max

        while current <= end:
            yield current
            current += datetime.timedelta(**{frame: 1})

    def __str__(self):
        return f'<TimeRange begin="{self.begin}" end="{self.end}">'


class TimeSet:
    """
    Recurring DateTimeV2 set
    """

    __slots__ = ("timex", "tz")

    timex: str  # Unparsed (original) value from NLU
    tz: datetime.tzinfo  # Time zone

    MAX: datetime.datetime = (
        datetime.datetime.max
    )  # Maximum allowed date/time to stop iteration

    def __init__(self, timex: str, tz=tzutc()):
        if not isinstance(tz, datetime.tzinfo):
            tz = gettz(tz)

        self.tz = tz
        self.timex = timex

    def range(self, count: int = None, until: str = None):
        until_date: Optional[datetime.datetime]
        if until is not None:
            if count is not None:
                logger.debug(
                    '"count" and "until" should not be used together, setting "count" to "None"'
                )
                count = None
            until_date = parser.parse(until)
            if until_date.tzinfo is None:
                until_date = until_date.replace(tzinfo=self.tz)
        else:
            until_date = None if count else self.MAX.replace(tzinfo=self.tz)

        try:

            rule = _parse_timex(self.timex)
            if rule["dtstart"].tzinfo is None:
                rule["dtstart"] = rule["dtstart"].replace(tzinfo=self.tz)

            if rule["dtstart"] < datetime.datetime.now(self.tz):
                rule["dtstart"] += datetime.timedelta(days=1)

            return rrule.rrule(**{**rule, **dict(count=count, until=until_date)})

        except (TypeError, ValueError) as ex:
            raise ValueError(f'Could not parse timex value: "{self.timex}", {ex}')

    def __str__(self):
        return f'<TimeSet timex="{self.timex}" tz="{self.tz}">'


class AttributeV2(CamelModel, Generic[T]):
    """
    Attribute V2: indicates the nested and overlapping entities

        Sample usage:

        >>>import datetime
        >>>from skill_sdk import skill, responses
        >>>from skill_sdk.intents import AttributeV2

        >>>@skill.intent_handler('Intent')
        >>>def handler(date: AttributeV2[str]) -> responses.Response:
        >>>    ...

    """

    # Attribute ID (int32)
    id: int

    # Attribute value
    value: T

    # List of attribute IDs this attribute is nested in
    nested_in: List[int] = []

    # List of attribute IDs this attribute overlaps with
    overlaps_with: List[int] = []

    # Extra information for skills. e.g. literal value
    extras: Optional[Dict[Text, Text]]

    class Config:
        """Sample values for Swagger UI"""

        schema_extra = {
            "example": {
                "id": 1,
                "value": "value",
                "nested_in": [],
                "overlaps_with": [],
                "extras": {},
            }
        }

    @root_validator(pre=True)
    def remove_none_values(cls, values: Dict):  # pylint: disable=E0213
        return {k: v for k, v in values.items() if v is not None}

    def __init__(
        self,
        value: Union[Dict, "AttributeV2", Text],
        mapping: Callable[[Any], Any] = None,
        **data: Any,
    ) -> None:
        """
        Create AttributeV2 object optionally converting the value to required type

        :param value:   Value dictionary
        :param mapping: Conversion function
        """
        if isinstance(value, type(self)):
            __value = value.dict()
        elif isinstance(value, dict):
            __value = value.copy()
        else:
            __value = dict(value=value, **data)

        if mapping:
            try:
                __value["value"] = mapping(__value["value"])
            except (KeyError, TypeError):
                pass

        super().__init__(**__value)


def rank(value: str) -> int:
    """
    Convert GENERIC_ORDER NLU concept to an index value.
    The GENERIC_ORDER concept return a string that can be "max", "min", "succ", "prec", "0", "1", ...<br>
        "max" -> -1<br>
        "min" -> 0<br>
        "1" -> 0<br>
        "2" -> 1<br>
        ...<br>
    The "succ" value is not handled and should not be used in the intent samples.<br>
    Please see https://developer.nuance.com/mix/documentation/nlu/#nuance_generic_order

    :param value:   GENERIC_ORDER concept value.
    :return: index
    """
    _ = {
        "min": 0,
        "max": -1,
        "prec": -2,
    }
    try:
        return _[value]
    except KeyError:
        return int(value) - 1


def converter(to_type) -> Callable[[str], Any]:
    """
    Returns conversion function

    :param to_type: type or callable
    :return:
    """
    _ = {
        datetime.timedelta: to_timedelta,
        datetime.datetime: to_datetime,
        datetime.date: to_date,
        datetime.time: to_time,
        bool: on_off_to_boolean,
    }

    conversion_func = to_type if callable(to_type) else lambda a: a
    return _.get(to_type, conversion_func)


def convert(value: str, to_type=None):
    """
    Convert value to type defined in conversion table or using a conversion function provided in `to_type` param
    returns converted value or the value itself if conversion function not defined

    :param value:   value to convert
    :param to_type: type or callable
    :return:
    """
    return converter(to_type)(value)


@to_datetime.register(datetime.date)
def date_to_datetime(value: datetime.date) -> datetime.datetime:
    """Date to datetime with time set to 00:00"""
    return datetime.datetime.combine(value, datetime.time(0, 0))


@to_datetime.register(datetime.time)
def time_to_datetime(value: datetime.time) -> datetime.datetime:
    """Time to datetime with date set to today"""
    return datetime.datetime.combine(datetime.datetime.now().date(), value)


@to_datetime.register(list)
def list_to_datetime(entities: List) -> datetime.datetime:
    """Parse first list element and return datetime"""
    value = get_entity(entities)
    return to_datetime(value) if value else datetime.datetime.min


@to_date.register(datetime.datetime)
def datetime_to_date(value: datetime.datetime) -> datetime.date:
    """Parse datetime and return date component"""
    return to_datetime(value).date() if value else datetime.date.min


@to_date.register(list)
def list_to_date(entities: List) -> datetime.date:
    """Parse first list element and return date component"""
    value = get_entity(entities)
    return to_date(value) if value else datetime.date.min


@to_time.register(datetime.datetime)
def datetime_to_time(value: datetime.datetime) -> datetime.time:
    """Parse datetime and return time component"""
    return value.time()


@to_time.register(list)
def list_to_time(entities: List) -> datetime.time:
    """Parse first list element and return time component"""
    value = get_entity(entities)
    return to_time(value) if value else datetime.time.min


WEEK_TIMEX = re.compile(
    r"^(?:(?P<year>[X\d]+)-)?" r"W(?:(?P<week>[X\d]+)-)?" r"(?:(?P<day>\d+))?$"
)


def _parse_timex(timex: str) -> Dict:
    """
    Parse "timex" value from NLU
    Currently covers the following cases:

        - "every day at ...":           "T%HH:%MM"
        - "every Monday at ...":        "XXXX-WXX-1T%HH:%MM"
        - "every Monday to Wednesday":  "(XXXX-WXX-1,XXXX-WXX-3,P2D)"
        - "every Monday ... to ...":    "(XXXX-WXX-1T14,XXXX-WXX-1T18,PT4H)"

    :param timex:
    :return:
    """
    weekday = None
    freq = rrule.DAILY

    timex_tuple = _parse_timex_tuple(timex)
    if timex_tuple:
        return timex_tuple

    if "T" in timex:
        date_part, time_part = timex.split("T")
        # if Timex ends with 'Txx', we want to add ':00' to specify that it's a time expression
        if ":" not in time_part:
            time_part = f"{time_part}:00"
    else:
        date_part = timex
        time_part = "00:00"

    if "W" in date_part:
        result = WEEK_TIMEX.search(date_part)
        if result:
            year, week, day = result.groupdict().values()
            freq = rrule.WEEKLY
            weekday = int(day) - 1  # rrule says Monday is 0
            date_part = ""

    return {
        "dtstart": parser.parse("T".join((date_part, time_part))),
        "freq": freq,
        "byweekday": weekday,
    }


def _parse_timex_tuple(timex: str) -> Optional[Dict]:
    """
    Try to parse duration tuple: (begin,end,duration)

    :param timex:
    :return:
    """
    try:
        begin, end, duration = timex.strip("()").split(",")
        start_args = _parse_timex(begin)
        end_args = _parse_timex(end)
        delta = isodate.parse_duration(duration)
        if delta.days:
            return {
                "dtstart": start_args["dtstart"],
                "freq": rrule.WEEKLY,
                "byweekday": range(start_args["byweekday"], end_args["byweekday"] + 1),
            }
        elif delta.seconds:
            return {
                "dtstart": start_args["dtstart"],
                "freq": rrule.WEEKLY,
                "byweekday": start_args["byweekday"],
                # For weekly recurrence, time part of `dtstart` is ignored
                "byhour": range(
                    start_args["dtstart"].hour, end_args["dtstart"].hour + 1
                ),
            }
        else:
            raise NotImplementedError(f"Cannot parse value {timex} (yet)")
    except ValueError:
        return None
