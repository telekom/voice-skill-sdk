# Simple Intent Examples

## "Hello, World" 

`impl/hello.py`
```python
from skill_sdk import Context, Response, skill

@skill.intent_handler("SMALLTALK__GREETINGS")
def handle(context: Context) -> Response:
    return Response("Hello, World!")
```

## Weather example (this time with entities)

Here is a sample weather intent (because everybody likes weather):

`impl/main_intent.py`
```python
from skill_sdk import Card, Response, tell, ask, skill
from skill_sdk.entities import Location

@skill.intent_handler("WEATHER__CURRENT")
def weather(location: Location) -> Response:
    if not location:
        return ask("Please name a city")
    
    msg = f"It is awesome in {location.text}. At least I hope the sun is shining"
    card = Card(text=msg)
    return tell(msg, card=card)
```

## OAuth2 example

TBD
