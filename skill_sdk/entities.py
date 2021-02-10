#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

#
# Intent entities and conversion functions
#

import re
import logging
import datetime
import functools
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar, Union
from dateutil import parser, rrule
from dateutil.tz import tzutc, gettz
import isodate

from .l10n import nl_strip

logger = logging.getLogger(__name__)
T = TypeVar('T')


def get_entity(entities: List[Any]) -> Optional[Any]:
    """ Silently return first element of a list, or unchanged value otherwise
    """
    return next(iter(entities), None) if isinstance(entities, (list, tuple)) else entities


def snake_to_camel(name):
    """ Convert snake_case to CamelCase

    :param name:
    :return:
    """
    reg_ex = re.compile(r'_+[a-z0-9]')
    return reg_ex.sub(lambda x: x.group(0)[1].upper(), name)


def camel_to_snake(name):
    """ Convert CamelCase to snake_case

    :param name:
    :return:
    """
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()


@functools.singledispatch
def to_datetime(value) -> datetime.datetime:
    """ Parse datetime string """
    return parser.parse(value)


@functools.singledispatch
def to_date(value) -> datetime.date:
    """ Parse datetime and return date component """
    return to_datetime(value).date()


@functools.singledispatch
def to_time(value) -> datetime.time:
    """ Parse datetime and return time component """
    return to_datetime(value).time()


@functools.singledispatch
def to_timedelta(value) -> datetime.timedelta:
    """ Parse duration string and return timedelta  """
    return isodate.parse_duration(value)


@to_timedelta.register(datetime.timedelta)
def __to_timedelta(value: datetime.timedelta):
    """ No-op if already converted """
    return value


def on_off_to_boolean(value: str) -> bool:
    """ Converts ON_OFF entity value to boolean
    The value might be any string of ``0``, ``1``, ``on``, ``off``, ``true``, ``false``, case insensitive.

    :param value: the entity value
    """
    logger.debug(f'converting value {value} to bool')
    if not isinstance(value, str):
        raise ValueError(f'The value {value.__repr__()} is not a string.')
    if value.lower() in ('on', 'true', 'yes', '1'):
        return True
    if value.lower() in ('off', 'false', 'no', '0'):
        return False
    raise ValueError(f'{value} is not a proper on/off value.')


class Location:
    """ Location entity placeholder

    """

    def __init__(self, location_text=None, **kwargs):
        if not (location_text or any(
                [arg in kwargs for arg in ('coordinates', 'language', 'city', 'country', 'postalcode')])):
            raise ValueError('At least one of location_text or coordinated has to be given.')

        self._text = location_text
        self._coordinates = kwargs.get('coordinates')
        self._timezone = kwargs.get('timezone')
        self._city = kwargs.get('city')
        self._country = kwargs.get('country')
        self._language = kwargs.get('language')
        self._postalcode = kwargs.get('postalcode')

    def __eq__(self, other):
        if isinstance(other, Location):
            return self._text == other.text and self._coordinates == other._coordinates
        else:
            return False

    @property
    def text(self):
        return self._text

    @property
    def coordinates(self):
        return self._coordinates

    @property
    def timezone(self):
        return self._timezone

    def __str__(self):
        return '<Location text="{}" coords={}>'.format(self._text, self._coordinates)


@functools.singledispatch
def to_location(location_text=None, **kwargs) -> Location:
    """ Create Location object from text """
    return Location(location_text, **kwargs)


@to_location.register(Location)
def __to_location(value: Location):
    """ No-op, if already converted """
    return value


class Device:
    """ Represents a user device, can be a smart speaker or a companion app.
    """

    def __init__(self, name):
        self.name = name

    def send_push_message(self, context, payload):
        context.push_messages[self.name].append(payload)


class TimeRange:
    """ Date/Time range representation
    """

    __slots__ = ('begin', 'end')

    begin: Optional[datetime.datetime]
    end: Optional[datetime.datetime]

    def __init__(self, value: str):
        self.begin, self.end = [parser.parse(v) if v else None for v in value.split('/')]

    def __contains__(self, value) -> bool:

        begin = self.begin or datetime.datetime.min
        end = self.end or datetime.datetime.max

        if isinstance(value, datetime.time):
            return begin.time() <= value <= end.time()
        if isinstance(value, datetime.datetime):
            return begin <= value <= end
        if isinstance(value, datetime.date):
            return begin.date() <= value <= end.date()
        return False

    def __eq__(self, other):
        try:
            return self.__slots__ == other.__slots__ and self.begin == other.begin and self.end == other.end
        except AttributeError:
            return False

    def range(self, frame: str):
        """ Generator yielding datetime values within a particular frame: hours/days/weeks/etc

        @param frame:
        @return:
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
    """ Recurring DateTimeV2 set """

    __slots__ = ('timex', 'tz')

    timex: str                                              # Unparsed (original) value from NLU
    tz: datetime.tzinfo                                     # Time zone

    MAX: datetime.datetime = datetime.datetime.max          # Maximum allowed date/time to stop iteration

    def __init__(self, timex: str, tz=tzutc()):
        if not isinstance(tz, datetime.tzinfo):
            tz = gettz(tz)

        self.tz = tz
        self.timex = timex

    def range(self, count: int = None, until: str = None):
        until_date = self.MAX.replace(tzinfo=self.tz)

        if until is not None:
            if count is not None:
                logger.debug('"count" and "until" should not be used together, setting "count" to "None"')
                count = None
            until_date = parser.parse(until)
            if until_date.tzinfo is None:
                until_date = until_date.replace(tzinfo=self.tz)

        try:

            rule = _parse_timex(self.timex)
            if rule['dtstart'].tzinfo is None:
                rule['dtstart'] = rule['dtstart'].replace(tzinfo=self.tz)

            if rule['dtstart'] < datetime.datetime.now(self.tz):
                rule['dtstart'] += datetime.timedelta(days=1)

            rule.update(dict(count=count, until=until_date))
            return rrule.rrule(**rule)

        except (TypeError, ValueError) as ex:
            raise ValueError(f'Could not parse timex value: "{self.timex}", {ex}')

    def __str__(self):
        return f'<TimeSet timex="{self.timex}" tz="{self.tz}">'


class AttributeV2(Generic[T]):
    """ Attribute V2: indicates the nested and overlapping entities

        Sample usage:
        ```python

        import datetime
        from skill_sdk import skill, responses
        from skill_sdk.entities import AttributeV2

        @skill.intent_handler('Intent')
        def handler(date: AttributeV2[str]) -> responses.Response:
            ...
        ```
    """

    __slots__ = ('id', 'value', 'extras', 'nested_in', 'overlaps_with')

    def __init__(self, value: Union[Dict, 'AttributeV2'], mapping: Callable[[Any], Any] = None) -> None:
        """ Create AttributeV2 object optionally converting the value to required type

        :param value:   Value dictionary
        :param mapping: Conversion function
        """
        self.id = value.get('id', 0)
        self.value = mapping(value.get('value')) if mapping is not None else value.get('value')
        self.extras = value.get('extras') or {}
        self.nested_in = value.get('nestedIn') or []
        self.overlaps_with = value.get('overlapsWith') or []

    def __eq__(self, other):
        try:
            return self.__slots__ == other.__slots__ and all(self.get(item) == other.get(item)
                                                             for item in self.__slots__)
        except AttributeError:
            return False

    def get(self, key, default=None):
        return getattr(self, key, default)

    def dict(self):
        return {
            'id': self.id,
            'value': self.value,
            'extras': self.extras,
            'nestedIn': self.nested_in,
            'overlapsWith': self.overlaps_with,
        }

    def __repr__(self):
        return f'<AttributeV2 id="{self.id}" value="{type(self.value)} {self.value}" extras="{self.extras}" '\
               f'nested_in="{self.nested_in}" overlaps_with="{self.overlaps_with}">'


def rank(value: str) -> int:
    """ Convert GENERIC_ORDER NLU concept to an index value.
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
        'min': 0,
        'max': -1,
        'prec': -2,
    }
    try:
        return _[value]
    except KeyError:
        return int(value) - 1


def converter(to_type) -> Callable[[str], Any]:
    """ Returns conversion function
    :param to_type: type or callable
    :return:
    """
    _ = {
        datetime.timedelta: to_timedelta,
        datetime.datetime: to_datetime,
        datetime.date: to_date,
        datetime.time: to_time,
        bool: on_off_to_boolean,
        Location: to_location,
    }

    conversion_func = to_type if callable(to_type) else lambda a: a
    return _.get(to_type, conversion_func)


def convert(value: str, to_type=None):
    """ Convert value to type defined in conversion table or using a conversion function provided in `to_type` param
        returns converted value or the value itself if conversion function not defined

    :param value:   value to convert
    :param to_type: type or callable
    :return:
    """
    return converter(to_type)(value)


@to_datetime.register(datetime.date)
def date_to_datetime(value: datetime.date) -> datetime.datetime:
    """ Date to datetime with time set to 00:00 """
    return datetime.datetime.combine(value, datetime.time(0, 0))


@to_datetime.register(datetime.time)
def time_to_datetime(value: datetime.time) -> datetime.datetime:
    """ Time to datetime with date set to today """
    return datetime.datetime.combine(datetime.datetime.now().date(), value)


@to_datetime.register(list)
def list_to_datetime(entities: List) -> datetime.datetime:
    """ Parse first list element and return datetime """
    value = get_entity(entities)
    return to_datetime(value) if value else datetime.datetime.min


@to_date.register(datetime.datetime)
def datetime_to_date(value: datetime.datetime) -> datetime.date:
    """ Parse datetime and return date component """
    return to_datetime(value).date() if value else datetime.date.min


@to_date.register(list)
def list_to_date(entities: List) -> datetime.date:
    """ Parse first list element and return date component """
    value = get_entity(entities)
    return to_date(value) if value else datetime.date.min


@to_time.register(datetime.datetime)
def datetime_to_time(value: datetime.datetime) -> datetime.time:
    """ Parse datetime and return time component """
    return value.time()


@to_time.register(list)
def list_to_time(entities: List) -> datetime.time:
    """ Parse first list element and return time component """
    value = get_entity(entities)
    return to_time(value) if value else datetime.time.min


WEEK_TIMEX = re.compile(r'^(?:(?P<year>[X\d]+)-)?'
                        r'W(?:(?P<week>[X\d]+)-)?'
                        r'(?:(?P<day>\d+))?$')


def _parse_timex(timex: str) -> Dict:
    """ Parse "timex" value from NLU
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

    if 'T' in timex:
        date_part, time_part = timex.split('T')
        # if Timex ends with 'Txx', we want to add ':00' to specify that it's a time expression
        if ':' not in time_part:
            time_part = f"{time_part}:00"
    else:
        date_part = timex
        time_part = "00:00"

    if 'W' in date_part:
        result = WEEK_TIMEX.search(date_part)
        if result:
            year, week, day = result.groupdict().values()
            freq = rrule.WEEKLY
            weekday = int(day) - 1      # rrule says Monday is 0
            date_part = ''

    return {
        'dtstart': parser.parse('T'.join((date_part, time_part))),
        'freq': freq,
        'byweekday': weekday
    }


def _parse_timex_tuple(timex: str) -> Optional[Dict]:
    """ Try to parse duration tuple: (begin,end,duration)

    :param timex:
    :return:
    """
    try:
        begin, end, duration = timex.strip('()').split(',')
        start_args = _parse_timex(begin)
        end_args = _parse_timex(end)
        delta = isodate.parse_duration(duration)
        if delta.days:
            return {
                'dtstart': start_args['dtstart'],
                'freq': rrule.WEEKLY,
                'byweekday': range(start_args['byweekday'], end_args['byweekday'] + 1)
            }
        elif delta.seconds:
            return {
                'dtstart': start_args['dtstart'],
                'freq': rrule.WEEKLY,
                'byweekday': start_args['byweekday'],
                # For weekly recurrence, time part of `dtstart` is ignored
                'byhour': range(start_args['dtstart'].hour, end_args['dtstart'].hour + 1)
            }
        else:
            raise NotImplementedError(f"Cannot parse value {timex} (yet)")
    except ValueError:
        return None

# Helper Methods for handling multiple Dates - Start:


def to_integer(dt_time: datetime.date):
    """ convert the date to a human readable int
    """
    return 10000 * dt_time.year + 100 * dt_time.month + dt_time.day


def filter_date_list(datelist: List[datetime.date],
                     after: datetime.date = datetime.date.min,
                     before: datetime.date = datetime.date.max) -> List[datetime.date]:
    """ filter a list of dates to a list of dates to be limited within a range and order it at once
    """
    return sorted((d for d in datelist if after < d < before), key=to_integer)


def closest_next_date(datelist: List[datetime.date], date: datetime.date) -> datetime.date:
    """ get the closest future date from a list to a given date
        if no future date is found, the given date is returned.
    """
    _future_dates = filter_date_list(datelist, after=date)
    if len(_future_dates) > 0:
        return _future_dates[0]
    else:
        return date


def closest_previous_date(datelist: List[datetime.date], date: datetime.date) -> datetime.date:
    """ get the closest past date from a list to a given date
        if no past date is found, the given date is returned.
    """
    _past_dates = filter_date_list(datelist, before=date)
    if len(_past_dates) > 0:
        return _past_dates[-1]
    else:
        return date


def is_text_including_words(text: str, words: List[str]) -> bool:
    """ is any word of the list included in the text
        a word needs to be exact and lonely
        "i lived in duisburg"
        neither include the words 'live' nor the word 'burg'
        but once 'i' at the beginning
    """
    if text:
        _text = nl_strip(text).lower()
        stripped = _text.split(' ')
        return any(_ in stripped for _ in words)
    else:
        return False


# Helper Methods for handling multiple Dates - End!
