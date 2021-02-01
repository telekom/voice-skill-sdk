# Context

Skill invocation request consists of two data transfer object (DTO): a request context and request session.
The context carries data about an intent being invoked (intent name, attributes, tokens, etc), 
while the session carries data that persists between user interactions.   

Before calling an intent handler function, SDK injects the `context` object into the global address space.
Global `context` object is importable from `skill_sdk.intents` module (this is a thread-safe instance referring 
to currently running request's context):

```python 
>>> from skill_sdk.intents import context
>>> context
<skill_sdk.intents.LocalContext object at 0x7faa1bc75910>
```

## Attributes of the context object

The `context` object has the following attributes:

- **intent_name**: The name of the intent that was called.
- **attributesV2**: Raw version of the attributes received in the request.
- **attributes**: Attributes as simple value lists (for backward compatibility).
- **session**: A session object (see below).
- **locale**: Dictionary with information of the clients location and language:
  - **language**: Requested language in two-letter ISO 639-1 format (for example `de`).
- **translation**: `gettext.Translation` instance bound to the current request `locale`.
- **tokens**: Access tokens to authenticate to other services (*see below*).
- **configuration**: User configuration for the skill (*see below*).

## Timezone-aware datetime functions

Skill invocation context object contains at least one required attribute: the device time zone name.
Device timezone is tenant-specific string value representing the device location around the globe 
([IANA Time Zone Database](https://www.iana.org/time-zones)) and can contain values like "Europe/Berlin" or "Europe/Paris".

To get device-local date and time, the following shorthand methods are available:

- `Context.now()`: returns device-local date and time with timezone information
- `Context.today()`: returns the current device-local date (current day at midnight)

Both methods return `datetime.datetime` value with `datetime.tzinfo`

The timezone must be provided by as an attribute to the intent, which can be automated in the intent configuration like this:

**Example**

CVI configuration for minimum MYINTENT intent getting timezone of the device as a parameter.

```json
    {
      "name": "MYINTENT",
      "entityFiller": "",
      "entities": [
        {
          "name": "timezone",
          "type": "TIMEZONE",
          "fillPolicy": [
            "device"
          ],
          "useFromSession": true
        }
      ],
      "prompts": [],
      "requiredTokens": [],
      "errors": []
    }
```

 
## Detailed information about specific attributes

### Attribute "session"

The `session` attribute is a key value store where information can be stored inside a user interaction session.
With few limitations, it acts like a dictionary:

- Keys and values must be strings. If they are not, they are casted.
- Keys must not be an empty string.
- The sum of lengths of all keys and values must not exceed `MAX_SESSION_STORAGE_SIZE` which is 4096 at the time of writing.

If the maximum session size is exceeded, a `SessionOversizeError` raises.

### Attribute "tokens"

You can define the type of `tokens` in the `tokens.json` file. 

Every intent invoke transmits existing tokens passes them as `context.tokens` dictionary to the intent handler.

The defined token name is the key of the dictionary. The token has strings as values.

**Example**

    {
        'all_access_token': 'PhoTwepUpwotketFoGribgiOtWumojCa',
        'external_service_token': 'TaglouvvattodcynipwenUcFatnirpilwikHomLawUvMojbienalAvNejNoupocs'
    }
    
### Attribute "configuration"

Skill can define a number of configuration options that are exposed to end user via companion app.
These options must be defined in skill manifest. Their values are made available in the `context.configuration` and passed with every skill invoke.

A configuration option must be defined with the attributes below:
  - name
  - localized label
  - localized description
  - data type (string, int number, float number, boolean, list)
  - required flag
  - localized list values - only if the data type is a list. Every list value has a canonical id which is stored and sent to the skill on invocation.
  - list display (radiobox, dropdown, etc.) - only if the data type is a list
  - multiselect: If true, the user can select more than one list value,

**Example**

Configuration option sample of a skill, that can store user's favorite football team:

```json
{
    "configuration": [
        {
            "name": "favourite-team",
            "label": {
                "de": "Lieblingsmannschaft",
                "en": "Favourite team"
            },
            "description": {
                "de": "Ihre Lieblingsmannschaft",
                "en": "Your favourite team"
            },
            "type": "string",
            "required": true,
            "list": {
                "values": [
                    {
                        "id":"bayern",
                        "label": {
                            "de": "FC Bayern München",
                            "en": "FC Bayern München"   
                        }
                    },
                    {
                        "id": "1860",
                        "label": {
                            "de": "1860 München",
                            "en": "1860 München"   
                        }
                    }
                ],
                "display": "dropdown",
                "multiselect": false
            }
        }
    ]
}
```
where:

| field | description   | allowed value |
|-------|-----------|------:|
| name | Name of the configuration entry. Must be unique.   |  a-Z A-Z 0-9 dash underscore |
| type | Data type of the configuration entry.  |  string, int, float, boolean, date, time, datetime, list    |
| label | 	Localized label which gets displayed to the user.  | Dictionary from locale → string     |
| description    | Localized description which gets displayed to the user.  |  Dictionary from locale → string    |
| required      | 	Flag to mark required entries.  |  true, false    |
| list.values      | 	Selectable values. Ignored if data type is not "list"  |  Array of values.    |
| list.values.id   | Canonical value for that list item. This id is sent to the skill on invocation.  |   *  |
| list.values.label      | 	Localized label of the list item  | Every value is a dictionary from locale → string     |
| list.display      | Selects how a list is displayed. Ignored if data type is not "list"  |   "dropdown", "radiobox", "checkbox". Only "checkbox" is allowed if multiselect is true.   |
| list.multiselect      | 	Flag to enable to select more than one list item.  |  true, false    |

CVI Core supplies configuration values to skill on invoke:

```json
{
  "context": {
    "intent": "...",
    "attributes": { ... },
    "configuration": {
      "favourite-team": ["1860"]
    }
  },
  "session": { ... }
}
```
