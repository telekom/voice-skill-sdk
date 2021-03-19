# Client Tasks *
<sup>* new in SPI version 1.4</sup>

A skill can send a scheduled or delayed task to be executed by the client.
To do so, add `ClientTask` object to a response using `Response.with_task` factory.

For example, to invoke "WEATHER__INTENT" after pronouncing "Weather forecast follows.":

```python
import datetime
from skill_sdk.responses import ClientTask, Response

response = Response("Weather forecast follows.").with_task(
    ClientTask.invoke("WEATHER__INTENT")
)
```

## Client Tasks Actions

The only supported client task's action is to invoke an intent by name, 
optionally providing the skill id during intent resolution.

```
@staticmethod
ClientTask.invoke(intent: str, skill_id: str = None, **kwargs) -> ClientTask
```

- **intent**: The name of the intent to invoke.
- **skill_id**: Optional skill id to be used during intent resolution.
- ****kwargs**: Key/values map that will be converted into attributes for intent invocation.

## Delayed Tasks

A task execution can be delayed relatively to a time anchor.  
These anchor references are:

- `ReferenceType.SPEECH_END`: speech end is the moment when the response text utterance is over (completed). 
  

- `ReferenceType.THIS_RESPONSE`: the moment when the response is received by the client 
  (before any text is uttered).

The delay is specified by the `offset` parameter of type `datetime.timedelta`. 

For example, to invoke "WEATHER__INTENT" in 10 seconds after pronouncing
"Weather forecast in 10 seconds.":

```python
import datetime
from skill_sdk.responses import ClientTask, Response

response = Response("Weather forecast in 10 seconds.").with_task(
    ClientTask.invoke("WEATHER__INTENT")
      .after(offset=datetime.timedelta(seconds=10))
)
```

## Scheduled Tasks

Tasks execution can be scheduled to a particular date/time using `ClientTask.at` factory.

> **Note**: to prevent possible time zones issues when scheduling tasks, 
> please avoid using time-zone naive date/times.     

Schedule a "WEATHER__INTENT" execution on 31 December 2120 at 22:00 UTC:

```python
import datetime
from skill_sdk.responses import ClientTask

task = ClientTask.invoke("WEATHER__INTENT").at(
    datetime.datetime(year=2120, month=12, day=31, hour=22, tzinfo=datetime.timezone.utc) 
)
```
