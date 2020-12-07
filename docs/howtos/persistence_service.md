# How to use Persistence Service

Persistence Service is an internal key/value cloud storage
that you can use to keep an intermediate skill state. The data sent to the service persists between device sessions or skill restarts and re-deployments.

> Persistence service requires a service token for authentication. 
> How to request a token using [skill manifest](skill_manifest.md)

## API

Python Skill SDK provides an easy to use interface to the service:

 **services.persistence.PersistenceService.set**

`set(data: {}, replace: bool = True) -> Response` saves the skill data specified by the `data` parameter to persistent store.

If the `replace` parameter is set to `False`, existing data keys will not be overwritten. 

**services.persistence.PersistenceService.get**

`get() -> services.persistence.Hasher` retrieves the current skill data.

The data is returned as a dictionary-like Hasher object. This is a small wrapper on top of the standard Python dictionary to safely traverse a dictionary. You can traverse it like `Hasher()['key1']['key2']` or `Hasher().get('key1').get('key2')` without raising KeyError or AttributeError, if the requested key is not in the dictionary.

**services.persistence.PersistenceService.get_all**

`get_all() -> services.persistence.Hasher` retrieves all data for specific user that may contain other skills storage.

The data is returned as Hasher object with the following structure:
```json
{
  "skill-id": {
    "attr-1": "value-1",
    "attr-2": "value-2"
  }
}
``` 

## Configuration

The persistence service is configured in `[service-persistence]` section of `skill.conf`:

- **[service-persistence] → active**: Boolean value to activate/deactivate the persistence service (default is `true` ).
- **[service-persistence] → url**: The persistence services endpoint URL.

```ini
[service-persistence]
url = https://api.voiceui.telekom.net/svh/services/persistence/
```

## Examples

Suppose you're writing a greeting skill that wants to keep the owners name and greet him personally by his name. 
You want to save the owners name and keep it indefinitely despite device restarts or blackouts in your data center.

We start with defining two intents for our skill. One intent will be activated when the user says "Hello", we name it "HELLO_INTENT".
The other intent will save the users name and greet him, we name it "HELLO_INTENT_REPROMPT".

`skill.py` defines the implementation:
```python
from skill_sdk import Context, ask_freetext, skill
from skill_sdk.services.persistence import PersistenceService

@skill.intent_handler('HELLO_INTENT')
def hello(ctx: Context):
    name = PersistenceService().get()['name']
    if name:
        return f"Hello, {name}! It's awesome today!"
    else:
        return ask_freetext(f"Oh, we haven't met yet. What's your name?")

@skill.intent_handler('HELLO_INTENT_REPROMPT')
def hello_reprompt(ctx: Context, name: str):
    PersistenceService().set({'name': name})
    return hello(ctx)
```
