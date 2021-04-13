# Testing your Skill

## The Skill

Let's take a simple weather skill as an example. The skill receives location as a parameter, 
connects to an external service and returns the current weather in named location to the speaker:

```python
from skill_sdk import Response, skill, tell

# This is our fictive external service
async def current_weather(location):
    return "Here comes the weather forecast" 

@skill.intent_handler("WEATHER__STATUS")
async def weather__status_handler(location: str = None) -> Response:
    if not location:
        return tell("The weather on Earth is generally fine.")
    
    weather = await current_weather(location)
    return tell(f"The weather in {location} is: {weather}")

app = skill.init_app()
app.include(handler=weather__status_handler)
```  

We'll save this simple handler as `weather.py`.
  
## Unit Tests

To properly test our handler we need two tests: one test to ensure that if no location provided to the handler, 
the output is *"The weather on Earth is generally fine."*

Another is to ensure that `service.current_weather` is called with `location` parameter, if it provided to the handler.

Let's create our `weather_test.py`:

```python
from unittest.mock import patch
import pytest
from weather import app

@pytest.mark.asyncio
async def test_missing_location():
    response = await app.test_intent("WEATHER__STATUS")
    assert response.text == "The weather on Earth is generally fine."

@pytest.mark.asyncio
@patch("weather.current_weather", return_value="Great!")
async def test_weather_location(current_weather):
    response = await app.test_intent("WEATHER__STATUS", location="Berlin")
    assert response.text == "The weather in Berlin is: Great!"
    current_weather.assert_called_once_with("Berlin")
``` 

The first test case invokes "WEATHER__STATUS" intent handler and tests the response text to be equal to 
*"The weather on Earth is generally fine."*

The second case patches `weather.current_weather` function with a mock returning the string value *"Great!"*,
invokes "WEATHER__STATUS" intent handler and checks the response text. 
It does also test if the `weather.current_weather` was called with string value "Berlin" as parameter.

## Testing Intents

There are two basic ways to unit test your skill application:

1. Import your application object with included intent handlers, and use `test_intent` function to get the result.


2. Import your intent handler function and call it directly, 
   possibly wrapping the call into `utils.test_request` manager to simulate global request context.   


### Skill.test_intent

Awaiting the `test_intent` method of an application instance is the way we used in a previous example, 
when testing **WEATHER__STATUS** intent. The signature:

```python
async def test_intent(
    self,
    intent: Text,
    translation: i18n.Translations = None,
    session: Union[util.CamelModel, Dict[Text, Text]] = None,
    **kwargs,
) -> Response:
    ...
```

- **intent**: name of the intent to invoke
- **translation**: translations to use, will be initialized as NullTranslations if not set
- **session**: mocked session attributes (can be a session result of previous test invoke)
- **kwargs**: other intent attributes

> Please note that you should execute `test_intent` on **your** skill application instance 
> and include the intent handlers **before** calling this function.


This method is defined as _coroutine_ and must be _awaited_ (executed in an event loop).
To run the test in a synchronous context, such as inside the `unittest.TestCase` class, 
there is a backward-compatible function `skill_sdk.skill.test_intent`:

```python
def test_intent(
    intent: Text,
    translation: i18n.Translations = None,
    session: Union[util.CamelModel, Dict[Text, Text]] = None,
    **kwargs,
) -> Response:
    ...
```

This helper will create a default application instance 
(so you have to make sure to import your handlers **before** calling this helper) 
and executes `test_intent` in thread pool executor. 

Using this helper we can rewrite the previous tests using pure standard `unittest` module:

```python
import unittest
from unittest.mock import patch

from weather import skill

class TestWeather(unittest.TestCase):

    def test_missing_location(self):
        response = skill.test_intent("WEATHER__STATUS")
        self.assertEqual("The weather on Earth is generally fine.", response.text)

    @patch("weather.current_weather", return_value="Great!")
    def test_weather_location(self, current_weather):
        response = skill.test_intent("WEATHER__STATUS", location="Berlin")
        self.assertEqual("The weather in Berlin is: Great!", response.text)
        current_weather.assert_called_once_with("Berlin")
``` 

### utils.test_request

Another possibility is to import and directly call intent handler function during the test.
To simulate global request context and session attributes, there is a `utils.test_request` helper.

This function can be used in `with` statement to temporarily activate the request context, 
and deactivate it at the end of `with` block.

Alternatively, it can decorate a function/method, 
so that temporary request context is activated within the function scope.  

```python
def test_request(
    intent: Text,
    translation: i18n.Translations = None,
    session: Union[CamelModel, Dict[Text, Text]] = None,
    **kwargs,
):
    ...
```

The helper's parameters are identical to those of `skill_sdk.skill.test_intent`: 
intent name, translation, session and intent attributes. 

We can easily rewrite the previous tests using this helper:

```python
from unittest.mock import patch
import pytest

from skill_sdk import util
from weather import weather__status_handler

@pytest.mark.asyncio
@util.test_request("WEATHER__STATUS")
async def test_missing_location():
    response = await weather__status_handler()
    assert response.text == "The weather on Earth is generally fine."

@pytest.mark.asyncio
@patch("weather.current_weather", return_value="Great!")
async def test_weather_location(current_weather):
    with util.test_request("WEATHER__STATUS"):
        response = await weather__status_handler(location="Berlin")
        assert response.text == "The weather in Berlin is: Great!"
        current_weather.assert_called_once_with("Berlin")
``` 

### utils.create_request

Creates a skill invoke request with given intent name, locale (default to *"de"*), tokens, 
configurations and session parameters. The keyword arguments will be treated as attributes of context.

> **Note:** for use in unit tests. 

```python
def create_request(
    intent: Text, session: Union[CamelModel, Dict[Text, Text]] = None, **kwargs
):
    ...
```

**Example** 

`create_request("WEATHER__CURRENT", locale="de", location="Berlin")` 
creates a request for invoking "WEATHER__CURRENT" intent with German locale and location "Berlin".


### utils.create_context

Creates skill invocation context with attributes supplied as keyword arguments.

```python
def create_context(
    intent: Text,
    locale: Text = None,
    tokens: Dict[Text, Text] = None,
    configuration: Dict[Text, Dict] = None,
    **kwargs,
):
    ...
```

**Example** 

`create_context("WEATHER__CURRENT", locale="de", location="Berlin")` 
creates a context object for invoking "WEATHER__CURRENT" intent with German locale and location "Berlin".
