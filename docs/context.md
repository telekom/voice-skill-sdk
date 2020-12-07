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

TODO: Check whether the configuration attribute internal doc can be exposed.

The `configuration` is a dictionary of lists that contains items of the types defined in the [Generic Skill Configuration](https://gard.telekom.de/gardwiki/display/SH/Generic+skill+configuration).

**Example**

    {
        'key1': ['abc'],
        'setting_a': [1, 2, 3]
    }

A user can set a given set of preference variables as defined in the skill manifest. These values are made available in the `context.configuration` and passed with every skill invoke.
