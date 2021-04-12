# Skill Invoke Request

Magenta Voice skill is invoked by Common Voice Interface (CVI), providing invoke data in [InvokeSkillRequestDto](https://htmlpreview.github.io/?https://raw.githubusercontent.com/telekom/voice-skill-sdk/blob/master/docs/skill-spi.html#_invokeskillrequestdto)

Skill invocation request consists of `spi_version` (string value specifying protocol version) and two object: 
request session ([SessionRequestDto](https://htmlpreview.github.io/?https://raw.githubusercontent.com/telekom/voice-skill-sdk/blob/master/docs/skill-spi.html#_sessionrequestdto))
and the context ([SkillContextDto](https://htmlpreview.github.io/?https://raw.githubusercontent.com/telekom/voice-skill-sdk/blob/master/docs/skill-spi.html#_skillcontextdto))

The session carries data that persists between user interactions while 
the context carries data about an intent being invoked (intent name, attributes, tokens, etc),   

Global `request` object is available within an intent handler scope and can be imported from `skill_sdk.intents` module.
If `request` attributes are accessed outside the intent handler, `None` is returned, 
and the error "Accessing request local object outside of the request-response cycle." is logged.

```python 
>>> from skill_sdk.intents import request
>>> request
<skill_sdk.intents.request.RequestContextVar object at 0x7eff512b9c10>
>>> request.spiVersion
Accessing request local object outside of the request-response cycle.
```

## Session Attributes

The `request.session` is dictionary-like key-value store where data can be stored and persists between user interactions.
Keys and values must be strings, otherwise `ValidationError` is raised.

Before the response is sent back to CVI, session attributes are collected and attached to the response, 
so the session data is persisting between invoke cycles.

This is valid only for **ASK** responses (when skill prompts for something and expects an answer). 
**TELL* response ends the session.    

## Context Attributes

`request.context` object has the following attributes:

- **intent**: The name of the intent that was called.
- **attributes_v2**: [Intent entities and attributes](entities.md).
- **attributes**: Attributes as simple value lists (for backward compatibility).
- **locale**: Requested language in two-letter ISO 639-1 format (for example `de`).
- **skill_id**: Optional skill ID.
- **client_type_name**: Optional client type (mini/premium/etc).
- **tokens**: Access tokens to authenticate to other services (*see below*).
- **user_profile_config**: Optional user profile configuration for the skill (*see below*).

### Translation functions

During `request.context` object instantiation, as list of available translations is requested from the skill. 

The translation that matches the request locale is injected into the `request` as `_trans` attribute, 
and the translation functions are injected into `request.context` object:

- `request.context._` is a synonym for `gettext` corresponding to requested locale. 


- `request.context._n` is a synonym for `ngettext` corresponding to requested locale. 


- `request.context._a` is a synonym for `getalltexts` correspondingly. 

### Timezone-aware datetime functions

If skill is configured to receive the device time zone, the invocation context contains at least the timezone name. 

Device timezone is tenant-specific string value representing the device location around the globe 
([IANA Time Zone Database](https://www.iana.org/time-zones)) and can contain values like "Europe/Berlin" or "Europe/Paris".

To get device-local date and time, the following shorthand methods are available:

- `request.context.now()` returns device-local date and time with timezone information.


- `request.context.today()` returns the current device-local date (current day at midnight).

Both methods return `datetime.datetime` value with `datetime.tzinfo`.

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

### Attribute "tokens"

Every intent invoke transmits existing tokens passing them as `request.context.tokens` dictionary to the intent handler.

The defined token name is the dictionary key. The token a string value.

**Example**

    {
        'all_access_token': 'PhoTwepUpwotketFoGribgiOtWumojCa',
        'external_service_token': 'TaglouvvattodcynipwenUcFatnirpilwikHomLawUvMojbienalAvNejNoupocs'
    }
    
### Attribute "user_profile_config"

Skill can define a number of configuration options that are exposed to end user via companion app.
These options must be defined in skill manifest. 

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
    "user_profile_config": [
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
    "attributes_v2": { ... },
    "attributes": { ... },
    "user_profile_config": {
      "favourite-team": ["1860"]
    },
    "locale":  "de",
    "tokens": {}
  },
  "session": { ... },
  "spi_version": "1.2"
}
```
