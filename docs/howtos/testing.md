# Testing your Skill

## The Skill

Let's take a simple weather skill as an example. The skill receives location as a parameter, 
connects to an external service and returns the current weather in named location to the speaker:

```python
from skill_sdk import Response, skill, tell

# This is our external service 
from service import current_weather

@skill.intent_handler("WEATHER__STATUS")
def weather__status_handler(location: str = None) -> Response:
    """ WEATHER__STATUS handler
        
    :param location: str = None
    :return:
    """
    if not location:
        return tell("The weather on Earth is generally fine.")
    
    return tell(f"The weather in {location} is following: {current_weather(location)}")
```  

We'll save this simple handler as `weather.py`.
  
## Unit Tests

To properly test our handler we need two tests: one test to ensure that if no location provided to the handler, 
the output is *"The weather on Earth is generally fine."*

Another is to ensure that `service.current_weather` is called with `location` parameter, if it provided to the handler.

Let's create our `weather_test.py`:

```python
import unittest
from unittest.mock import patch
from weather import skill


class TestMain(unittest.TestCase):

    def test_missing_location(self):
        response = skill.test_intent('WEATHER__STATUS')
        self.assertEqual("The weather on Earth is generally fine.", response.text)

    @patch('weather.current_weather', return_value='Great!')
    def test_weather_location(self, current_weather):
        response = skill.test_intent('WEATHER__STATUS', location='Berlin')
        self.assertEqual("The weather in Berlin is following: Great!", response.text)
        current_weather.assert_called_once_with('Berlin')
``` 

The first test case invokes "WEATHER__STATUS" intent handler and tests the response text to be equal to 
*"The weather on Earth is generally fine."*

The second case patches `weather.current_weather` function with a mock returning the string value *"Great!"*,
invokes "WEATHER__STATUS" intent handler and checks the response text. 
It does also tests if the `weather.current_weather` was called with string value "Berlin" as parameter.

## Test Helpers

Skill SDK provides a number of helpers to test your skill simulating a skill invocation context and a user session.
Test helpers are defined in [test_helpers.py](../../skill_sdk/test_helpers.py) module:

### `create_context`

```python
def create_context(intent: str,
                   locale: str = None,
                   tokens: Dict[str, str] = None,
                   configuration: Dict[str, Dict] = None,
                   session: Dict[str, Union[bool, str, Dict]] = None,
                   **kwargs) -> Context
```

Creates a skill invocation context for testing with given intent name, locale (default to *"de"*), tokens, 
configurations and session parameters. The keyword arguments will be treated as attributes of context.

**Example** 

`create_context('WEATHER__CURRENT', locale='de', location='Berlin')` creates a context for invoking "WEATHER__CURRENT" 
intent with German locale in Berlin.

### `invoke_intent`

```python
def invoke_intent(intent_name: str, skill: Skill = None, **kwargs)
```

Calls handler of an intent, specified by `intent_name`, the keyword arguments are passed over to create 
the skill invocation context (`create_context` function from above).

If `skill` arguments is not specified, it will try to get a current default app from the stack. 
That basically means, you have to import the intent handlers **before** calling this function or 
supply your skill with intent handlers as an argument. 

### `skill.test_intent`

A shorthand function to call `invoke_intent` that will use your skill as `skill` parameter.
  
**Example**

```python
from impl.main import skill

response = skill.test_intent('WEATHER__CURRENT', location='Berlin')
```

> Please note that you should execute `test_intent` on **your** skill application instance, 
> i.e. import the intent handlers **before** calling this function.


### `test_context` context manager and decorator

`create_context` function sets global [`context`](../context.md) object as a side effect, thus leaving a permanent trace
that might be unwanted in certain situations. To eliminate the trace, please use the `test_context` manager. 
This is a `with` statement context manager: it will save global `context` when entering the statement 
and restore it when leaving. 

The unit tests from above example can be rewritten with `test_context` manager: 

```python
import unittest
from unittest.mock import patch
from skill_sdk.test_helpers import test_context
from weather import weather__status_handler


class TestMain(unittest.TestCase):

    def test_missing_location(self):
        with test_context('WEATHER__STATUS'):
            response = weather__status_handler()
            self.assertEqual("The weather on Earth is generally fine.", response.text)

    @test_context('WEATHER__STATUS', location='Berlin')
    @patch('weather.current_weather', return_value='Great!')
    def test_weather_location(self, current_weather):
        response = weather__status_handler('Berlin')
        self.assertEqual("The weather in Berlin is following: Great!", response.text)
        current_weather.assert_called_once_with('Berlin')
``` 

`test_context` manager can be used in both `with` statements and as a decorator to temporary apply testing context
during test method execution.

This way of writing unit tests has no visible advantage vs. using the `test_intent` helper.
It may be beneficial however, if your intent handler makes extensive use of the global `context` object or 
if if you often switching the context during the unit test run.


## Functional Tests

Skill SDK for Python includes a basic testing framework that can execute the unit tests and
perform a number of functional tests to check skill responses to various entity values.

### How to run

To execute the supplied unit tests in your skill, issue the command `python manage.py test`.

To execute the functional tests, issue the command `python manage.py test -f` or `python manage.py test --functional`.

Adding the `-f` or `--functional` parameter will tell the SDK to execute the functional tests as well:

`python manage.py test -f`

### What it does

The functional test parses the skill intents, starts the skill in development mode and reads the skill responses supplying
different (both correct and incorrect) entity values.

Here are the default values that are used for various entity types:
```python
# Testing values with defaults
DEFAULT_VALUES = {
    'FREETEXT': ('', ['a'], 'None', [None], 'Chuck Norris', ['Chuck Norris']),
    'RANK': ('', ['a'], 'None', [None], ['max'], ['min'], ['prec'], 0, 1, [0, 1]),
    'TIMEZONE': ('', ['a'], 'None', [None], 'Europe/Berlin', ['Europe/Berlin'], ['Africa/Abidjan', 'US/Pacific']),
    'ZIP_CODE': ('', ['a'], 'None', [None], '1234', ['12345']),
    'ISO_DURATION': ('', ['a'], 'None', [None], ['P1Y2M10DT2H30M']),
    'CITY': ('', ['a'], 'None', [None], 'Bonn', ['Bonn', 'Berlin']),
}
```

You can also override the default values in `[tests]` section of your `skill.conf`.
For example, to test the skill with FREETEXT entity values `[None], ['Schlafzimmer'], ['Haupteingang']`, add this line to `skill.conf`:
```
[tests]
FREETEXT = [None], ['Schlafzimmer'], ['Haupteingang']
```

### How to read test output

Functional test expects the skill responses to be in `HTTP 2xx` range and will log an error otherwise.
It's up to developer to decide whether this is a real issue or not.

Sometimes your skill would expect integer values as FREETEXT entities, and it is totally ok if skill fails to respond
correctly when value ['a'] could not be converted to an integer. Such error can be safely ignored, unless your skill should
also handle incorrect values from a user.

Test failures will be logged in a following format:
```
======================================================================
FAIL: test_invoke_response (skill_sdk.test_helpers.FunctionalTest) (intent='SMARTHOME__DIM_CHANGE', payload={'context': {'intent': 'SMARTHOME__DIM_CHANGE', 'locale': 'de', 'attributes': {'room': ['a']}}})
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/vadim/PycharmProjects/skill-smarthome-python/.venv/lib/python3.7/site-packages/skill_sdk/test_helpers.py", line 146, in get_intent_invoke_response
    self.assertTrue(response.ok, json)
AssertionError: False is not true : {'code': 999, 'text': "error inside impl.dim_change.handle_dim_change while handling SMARTHOME__DIM_CHANGE. Exception-type <class 'KeyError'> Args: ('cvi',) \nPlease, check logs for details."}
```

This message means that an intent `SMARTHOME__DIM_CHANGE` would fail if the attribute `room` has value `['a']` and was invoked with German locale.

If we read the exception cause further, it appears that the actual failure would happen when a CVI token is read from requests context:

`Exception-type <class 'KeyError'> Args: ('cvi',) `

>Again if it's up to a developer to decide whether the issue when CVI token is missing should be handled by the skill, or safely ignored.

## Testing your Skill: Example

Now let's perform a functional test against a real skill and analyze the results.

- Clone the skill:
```
vadim@speedy:~/PycharmProjects $ git clone https://smarthub-wbench.wesp.telekom.net/gitlab/smarthub_skills/skill-shopping-list-python.git
Cloning into 'skill-shopping-list-python'...
remote: Enumerating objects: 1591, done.
remote: Counting objects: 100% (1591/1591), done.
remote: Compressing objects: 100% (510/510), done.
remote: Total 1591 (delta 1080), reused 1573 (delta 1067)
Receiving objects: 100% (1591/1591), 229.99 KiB | 463.00 KiB/s, done.
Resolving deltas: 100% (1080/1080), done.
```

- Create and activate virtual environment:
```
vadim@speedy:~/PycharmProjects $ cd skill-shopping-list-python/
vadim@speedy:~/PycharmProjects/skill-shopping-list-python (master)$ export PIPENV_VENV_IN_PROJECT=1
vadim@speedy:~/PycharmProjects/skill-shopping-list-python (master)$ pipenv --python 3.7
Creating a virtualenv for this project…
Pipfile: /home/vadim/PycharmProjects/skill-shopping-list-python/Pipfile
Using /usr/bin/python3.7m (3.7.3) to create virtualenv…
⠹ Creating virtual environment...Using base prefix '/usr'
New python executable in /home/vadim/PycharmProjects/skill-shopping-list-python/.venv/bin/python3.7m
Also creating executable in /home/vadim/PycharmProjects/skill-shopping-list-python/.venv/bin/python
Installing setuptools, pip, wheel...
done.
Running virtualenv with interpreter /usr/bin/python3.7m

✔ Successfully created virtual environment!
Virtualenv location: /home/vadim/PycharmProjects/skill-shopping-list-python/.venv
requirements.txt found, instead of Pipfile! Converting…
✔ Success!
vadim@speedy:~/PycharmProjects/skill-shopping-list-python (master)$ pipenv shell
Launching subshell in virtual environment…
vadim@speedy:~/PycharmProjects/skill-shopping-list-python (master)$  . /home/vadim/PycharmProjects/skill-shopping-list-python/.venv/bin/activate
(skill-shopping-list-python) vadim@speedy:~/PycharmProjects/skill-shopping-list-python (master)$ pip install -r requirements.txt
```

- Run the tests:
```
(skill-shopping-list-python) vadim@speedy:~/PycharmProjects/skill-shopping-list-python (master)$ python manage.py test -f
......................................
----------------------------------------------------------------------
Ran 38 tests in 0.063s

OK
```

These were the results of supplied unit tests. Let's scroll down to the functional test results:

```
----------------------------------------------------------------------
Ran 4 tests in 0.709s

FAILED (failures=9, skipped=1)
```

We've got 9 failures in total. Most of them are related to integer conversion, when entity value that is expected to be an integer cannot be converted to int:
```
AssertionError: False is not true : {'code': 999, 'text': 'error inside impl.shopping_list_delete.handle_delete while handling SHOPPING_LIST__DELETE. Exception-type <class \'ValueError\'> Args: ("invalid literal for int() with base 10: \'Chuck Norris\'",) \nPlease, check logs for details.'}
```
Those issues should have been handled by CVI-core and can be safely ignored.

The functional test also output the following other errors:
```
======================================================================
FAIL: test_invoke_response (skill_sdk.test_helpers.FunctionalTest) (intent='SHOPPING_LIST_REPROMPT__YES', payload={'context': {'intent': 'SHOPPING_LIST_REPROMPT__YES', 'locale': 'de', 'attributes': {}}})
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/vadim/PycharmProjects/skill-shopping-list-python/.venv/lib/python3.7/site-packages/skill_sdk/test_helpers.py", line 146, in get_intent_invoke_response
    self.assertTrue(response.ok, json)
AssertionError: False is not true : {'code': 999, 'text': "error inside impl.yes_reprompt.yes_reprompt while handling SHOPPING_LIST_REPROMPT__YES. Exception-type <class 'KeyError'> Args: ('action',) \nPlease, check logs for details."}
```

Let's take a look at the failed source and we'll see a potential problem:
```python
def yes_reprompt(context) -> Response:
    if context.session['action'] == 'DELETE':
        return delete_some_items(context, eval(context.session['items']))

    return Response(text="")
```

If there is no `action` key in session dictionary, our skill would fail and return an incorrect value.
Not to mention that `session['items']` value is resolved with `eval` function and can be used to execute arbitrary code objects,
thus leaving a potential security hole inside the skill.

