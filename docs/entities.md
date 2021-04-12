# Intent Entities and Attributes

Natural language understanding tools use two basic concepts to translate human speech 
into a form that can be processed by computers: 

  - **intents**, that are classifying the user utterance.


  - **entities**, that are units of structured data extracted from the utterance.


Additionally, Common Voice Interface (CVI) can enrich this information with **attributes**, 
such as device data (location, name, time zone, etc.), raw text from ASR engine or entities from the conversational context.   


Due to their semantic (almost all entities may have multiple values), entity values are transmitted to the skill as **string lists**, 
and can be converted to a native Python representation using various converters defined in `skill_sdk.intents.entities` module.


Some entities might have the values that are nesting in or overlapping each other.
For example, the utterance "Turn on Super RTL" has two overlapping values for a `channel` entity: "RTL" and "Super RTL" 
(both are valid channel names).

To distinguish overlapping and nesting entities, skill receives entity values in `AttributeV2` format.
`AttributeV2` is a data structure that contains, along with the entity values, 
the unique index and pointers to other entities, that might contain or overlap this entity.

An example of two entity values for "Turn on Super RTL" utterance in `AttributeV2` format:
 
```json   
    "attributesV2": {
      "channel": [
        {
          "id": 1,
          "value": "super rtl",
          "nestedIn": [],
          "overlapsWith": []
        },
        {
          "id": 2,
          "value": "rtl",
          "nestedIn": [
            1
          ],
          "overlapsWith": []
        }
      ]
    }
```   

## Entity Types

Here is overview of the entity types included in SDK:


### Type: `datetime`

Date/time entities extract date and time values from the utterance. 
They are transmitted in ISO-8601 string format with time zone 
and can be converted to `datetime.date`/`datetime.time` or `datetime.datetime` objects.

#### Parsers

- `to_date`: converts an ISO-8601 formatted string to `datetime.date` value. If value is a `datetime.datetime`, 
  the time part is trimmed.


- `to_time`: converts an ISO-8601 formatted string to `datetime.time` value. If value is a `datetime.datetime`, 
  the date part is trimmed. If value is a `dateime.date` (no time part), simple "00:00" timestamp is returned.


- `to_datetime`: converts a string to `datetime.datetime` value with time zone info. If value is a `datetime.date`, 
  the datetime object is extended with "00:00" timestamp. If value is a `datetime.time`, 
  the object is extended with current date.


> Raise `ParserError` if string format is invalid.


> Missing year/month notified by double-dash "--" will be substituted with current date values.


#### Example

```
>>> from skill_sdk.intents.entities import to_date, to_time, to_datetime
>>> to_date("2106-12-31T12:30Z")
datetime.date(2106, 12, 31)
>>> to_time("2106-12-31T12:30Z")
datetime.time(12, 30)
>>> to_datetime("2106-12-31T12:30Z")
datetime.datetime(2106, 12, 31, 12, 30, tzinfo=tzutc())
>>> to_datetime("2106-12-")
Traceback (most recent call last):
  <skipped>
dateutil.parser._parser.ParserError: Unknown string format: 2106-12-
>>> to_datetime("---12-31T12:30Z")
datetime.datetime(2021, 12, 31, 12, 30, tzinfo=tzutc())
```

### Type: `timedelta`

Timedelta entities represent a time duration in ISO-8601 format. They can be converted to `datetime.timedelta` objects.

#### Parsers

- `to_timedelta`: converts an ISO-8601 duration string to `datetime.timedelta` value.

> Raise `ISO8601Error` if string format is invalid.

#### Example

```
>>> from skill_sdk.intents.entities import to_timedelta
>>> to_timedelta("PT10M")
datetime.timedelta(seconds=600)
>>> to_timedelta("--PT10M")
Traceback (most recent call last):
  <skipped>
isodate.isoerror.ISO8601Error: Unable to parse duration string '--PT10M'
```

### Type: `TimeRange`

Time range represents a period in time between timestamps ("starting last Wednesday 15:00 until this Friday 10:00").
It is transmitted as time interval in ISO-8601 format with start and end, separated by slash "/" symbol 
("2007-03-01T13:00:00Z/2008-05-11T15:30:00Z").

Time range can have an open start (then it begins on `datetime.datetime.min` timestamp) or open end 
(in this case, it ends on `datetime.datetime.max`).   

This type supports `in` operator, so you can check if a particular timestamp is **in** the time range.

Another useful function is `TimeRange.range` - it's a generator yielding datetime values within a particular timeframe, 
like hours/days/weeks/etc.   

#### Parsers

- `TimeRange`: converts an ISO-8601 interval string to `entities.TimeRange` object.

> Raise `ParserError` if string format is invalid.


#### Examples

```
>>> from skill_sdk.intents.entities import TimeRange
>>> interval = TimeRange("2007-03-01T13:00:00Z/2008-05-11T15:30:00Z")
>>> str(interval)
'<TimeRange begin="2007-03-01 13:00:00+00:00" end="2008-05-11 15:30:00+00:00">'
>>> TimeRange(None)
Traceback (most recent call last):
  <skipped>
dateutil.parser._parser.ParserError: Unknown string format: None
```

**in** operator:

```
>>> from skill_sdk.intents.entities import TimeRange
>>> interval = TimeRange("2007-03-01T13:00:00Z/2008-05-11T15:30:00Z")
>>> from dateutil.tz import tzutc
>>> datetime.datetime.now(tzutc()) in interval
False
```

`TimeRange.range`:

```
>>> from skill_sdk.intents.entities import TimeRange
>>> list(TimeRange("2019-02-08T12:27:20/2019-03-01T13:27:20").range("weeks"))
[datetime.datetime(2019, 2, 8, 12, 27, 20), datetime.datetime(2019, 2, 15, 12, 27, 20), datetime.datetime(2019, 2, 22, 12, 27, 20), datetime.datetime(2019, 3, 1, 12, 27, 20)]
```


### Type: `TimeSet`

Time set represents a recurring date/time event, such as "Every Monday at 8:00" 
and transmitted as ISO-8601 repeating interval ("XXXX-WXX-1T08:00Z").

Using `TimeSet.range` generator, you can yield recurring datetime values, 
limiting the number of events by `count` parameter, or setting the end date with `until` parameter. 

#### Parsers

- `TimeSet`: converts an ISO-8601 repeating interval to `entities.TimeSet` object.

> **Note:** Does not validate input string until `range` is called


#### Examples

```
>>> from skill_sdk.intents.entities import TimeSet
>>> t = TimeSet("invalid")
>>> str(t)
'<TimeSet timex="invalid" tz="tzutc()">'
>>> TimeRange(None)
Traceback (most recent call last):
  <skipped>
dateutil.parser._parser.ParserError: Unknown string format: None
```

`TimeSet.range`:

```
>>> from skill_sdk.intents.entities import TimeRange
>>> t = TimeSet("invalid")
>>> t.range(1)
Traceback (most recent call last):
  <skipped>
ValueError: Could not parse timex value: "invalid", Unknown string format: invalidT00:00
>>> list(TimeSet("T08:00").range(2))
[datetime.datetime(2021, 4, 13, 8, 0, tzinfo=tzutc()), datetime.datetime(2021, 4, 14, 8, 0, tzinfo=tzutc())]
>>> list(TimeSet("XXXX-WXX-1T08:00Z").range(2))
[datetime.datetime(2021, 4, 19, 8, 0, tzinfo=tzutc()), datetime.datetime(2021, 4, 26, 8, 0, tzinfo=tzutc())]
```


### Type: `bool`

Boolean entities represent logical states ("True"/"False") or state changes ("ON"/"OFF") and can be converted to `bool` objects.

#### Parsers

- `on_off_to_boolean`: convert boolean state string to `bool` value.

> Raise `ValueError` if string format is invalid.

#### Example

```
>>> from skill_sdk.intents.entities import on_off_to_boolean
>>> on_off_to_boolean("On")
True
>>> on_off_to_boolean("0")
False
>>> on_off_to_boolean("")
Traceback (most recent call last):
  <skipped>
ValueError: Cannot cast '' to boolean.
>>> 
```


### Built-in Types: `int`, `float`, `complex`, `str`

These entities extract correspondingly `int`, `float`, `complex`, `str` values from the utterance.

In case of `str` type, string entities are simply passed over to the handler function as a string, no conversion occurs. 

#### Parsers

- `convert`: Parse string value applying a function to convert the value to particular type.

> Raise `ValueError` if input string format is invalid.

#### Example

```
>>> from skill_sdk.intents.entities import convert
>>> convert(["0", "1", "2"], int)
>>> convert("2", int)
2
>>> convert("4.2", float)
4.2
>>> convert("4.2", complex)
(4.2+0j)
>>> convert("4.2", int)
Traceback (most recent call last):
  <skipped>
ValueError: invalid literal for int() with base 10: '4.2'
```


### Helper functions

* entities.get_entity(entities: List[Any]) -> Optional[Any]
    
    Silently returns first element from entities list. Will return unchanged value if passed parameter is not an instance of list or tuple.
    

* entities.convert(value: str, to_type: Union[bool, datetime, int, float, Callable]) -> Any
    
    Generic converter: converts value to one of primitive types or any other type if conversion function supplied as `to_type` parameter.
 

## Handling entities with decorator 

To simplify the entities parsing and conversion, use `@skill.intent_handler` decorator.

### @skill.intent_handler

The decorator `@intent_handler` uses type hints from the handler definition and converts the entities list into the specified type.
The following types are supported:
- `datetime.timedelta`
- `datetime.datetime` / `datetime.date` / `datetime.time`
- `entities.TimeRange`
- `entities.TimeSet`
- `int` / `float` / `complex` / `str`
- `bool`

**Examples**

To receive an entity converted to a single `datetime.timedelta` value:

   ```python
import datetime
from skill_sdk import skill

@skill.intent_handler('WEATHER__CURRENT')
def intent_handler_expecting_timedelta(timedelta: datetime.timedelta):
    ...
   ```

To receive a list of `datetime.date` values:

   ```python
import datetime
from skill_sdk import skill

@skill.intent_handler('WEATHER__CURRENT')
def intent_handler_expecting_dates_list(date_list: [datetime.date]):
    ...
   ```
   
By default, `intent_handler` decorator suppresses conversion errors and returns an instance of 
`EntityValueException` exception, if conversion error occurs. 

You may add your own error handler to the `intent_handler` decorator to handle exceptions yourself:

```python
import datetime
from skill_sdk import skill, tell


def date_error(name, value, exception):
    return tell(f"Wrong {name} value: {value}, exception {exception.__cause__}")

@skill.intent_handler('Test_Intent', error_handler=date_error)
def handler(date: datetime.date = None):
  ...
```

## Nested and overlapping entities

To receive the values in `AttributeV2` format, use the type hints when decorating your intent handler with `@intent_handler`.

If you want to receive a list of `AttributeV2` values:

```python
from typing import List
from skill_sdk import skill
from skill_sdk.intents.entities import AttributeV2

@skill.intent_handler('TV__INTENT')
def intent_handler_expecting_list_of_attributes_v2(channel: List[AttributeV2]):
    ...
```

To receive a single value (a first one from the list):

```python
from skill_sdk import skill
from skill_sdk.intents.entities import AttributeV2

@skill.intent_handler('TV__INTENT')
def intent_handler_expecting_single_attribute_v2(channel: AttributeV2):
    ...
```

To receive a list of `AttributeV2` that contain integer values: 

```python
from typing import List
from skill_sdk import skill
from skill_sdk.intents.entities import AttributeV2

@skill.intent_handler('TV__INTENT')
def intent_handler_expecting_single_attribute_v2(channel: List[AttributeV2[int]]):
    ...
```
