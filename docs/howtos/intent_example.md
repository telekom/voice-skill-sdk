# Simple Intent Examples

## "Hello, World" 

```python
from skill_sdk import Response, skill

@skill.intent_handler("HELLO_WORLD__INTENT")
def handle() -> Response:
    return Response("Hello, World!")
```

## Current Weather

"WEATHER__CURRENT" intent receives a location specified in the utterance ("What is the weather in Bonn?"), 
and ZIP code from device configuration. 

Both values can be `None`, if user has not filled the ZIP code field in the device configuration 
AND has uttered an intent without specifying the location ("What's the weather like?")

```python
from skill_sdk import Response, tell, skill


@skill.intent_handler("WEATHER__CURRENT")
def weather(location: str = None, zip_code: str = None) -> Response:
    
    if not location and not zip_code:
        return tell("Please fill ZIP code in device configuration, or specify desired location.")
    
    if not location:
        # We have a ZIP code and tell weather for device location  
        msg = "It is awesome around you. At least I hope the sun is shining!"
        tell(msg).with_card(title_text="Current Weather", sub_text=zip_code, text=msg)

    msg = f"It is awesome in {location}. At least I hope the sun is shining!"
        
    return tell(msg).with_card(title_text="Current Weather", sub_text=location, text=msg)
```

## Guess the Number

This is a more comprehensive sample demonstrating the use of multiple intents, 
keeping the state between invokes in session attributes, and providing error handlers to incorrect user input.

The skill is going to randomly select an integer from 1 to 15 and let the user guess the number,
correcting them by telling each time if their guess was too high or too low.

First intent will be called when user utters "Let's play guess the number game!":


```python
from skill_sdk import Response, ask, skill


@skill.intent_handler("GUESS_NUMBER__INTENT")
def start() -> Response:
    
    return ask("Excellent! I chose a number between 1 and 15, guess what that could be?")
```

Second intent is called when user answers the question, trying to guess the number:

```python
from random import randint
from skill_sdk import Response, ask, tell, skill
from skill_sdk.intents import EntityValueException, request


def number_error(name, exception: EntityValueException) -> Response:
    """
    This function is called if exception is raised when converting user input to number

    :param name:        entity name
    :param exception:   EntityValueException
    :return:
    """
    return ask(f"Your guess {exception.value} does not look like a number. Please choose a number between 1 and 15.")


@skill.intent_handler("GUESS_NUMBER__NUMBER_INTENT", error_handler=number_error)
def game(number: int) -> Response:
    
    # Fetch the chosen number from the session
    chosen_number = int(request.session["chosen_number"]) or 0
    
    if 1 <= chosen_number <= 15:
        # choose a random number between 1 and 15, if it's a first run
        chosen_number = request.session["chosen_number"] = randint(1, 15)

    if number < chosen_number:
        return ask("Too low, try higher!")
    elif number > chosen_number:
        return ask("Too high, maybe lower?")
    else:
        return tell(f"Bingo! You did it, the number was {number}")
```
