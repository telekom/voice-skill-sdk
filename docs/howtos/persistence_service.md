# How to use Persistence Service

Persistence Service is an internal key/value cloud storage that you can use to keep an intermediate skill state. 
Stored data persists between device sessions or skill restarts and re-deployments.

> **Note:** Persistence service requires a service token for authentication. 
> How to request a token using [skill manifest](skill_manifest.md)

## API

Python Skill SDK provides an easy-to-use interface adapter:

 **services.persistence.PersistenceService.set**

`async def set(self, data: Dict[str, Any]) -> Response` saves the skill data specified by the `data` parameter to persistent storage.

**services.persistence.PersistenceService.get**

`async def get(self) -> Dict[Text, Any]` retrieves the current skill data.

**services.persistence.PersistenceService.get_all**

`async def get_all(self) -> Dict[Text, Any]` retrieves all data for specific user that may contain other skills' storage.

The data is returned as dictionary object with the following structure:

```json
{
  "skill-id": {
    "attr-1": "value-1",
    "attr-2": "value-2"
  }
}
``` 

**services.persistence.PersistenceService.delete**

`async def delete(self) -> Response` deletes the data from the storage.


## Configuration

The persistence service may be configured in `[service-persistence]` section of `skill.conf`:

- **[service-persistence] → url**: The persistence services endpoint URL.

```ini
[service-persistence]
url = https://api.voiceui.telekom.net/svh/services/persistence/
```

## Examples

Suppose you're writing a greeting skill that wants to keep the owners name and greet him personally by his name. 
You want to save the owners name and keep it indefinitely despite device restarts.

We start with defining two intents for our skill. One intent will be activated when the user says "Hello", we name it "HELLO_INTENT".
The other intent will save the users name and greet him, we name it "HELLO_INTENT_REPROMPT".

```python
from skill_sdk import ask_freetext, skill
from skill_sdk.config import settings
from skill_sdk.services.persistence import PersistenceService

SERVICE_URL = settings.SERVICE_PERSISTENCE_URL or "https://api.voiceui.telekom.net/svh/services/persistence/" 

@skill.intent_handler('HELLO_INTENT')
async def hello():
    data = await PersistenceService(SERVICE_URL).get()
    if 'name' in data:
        return f"Hello, {data['name']}! It's awesome today!"
    else:
        return ask_freetext(f"Oh, we haven't met yet. What's your name?")

@skill.intent_handler('HELLO_INTENT_REPROMPT')
def hello_reprompt(name: str):
    await PersistenceService(SERVICE_URL).set({'name': name})
    return await hello()
```
