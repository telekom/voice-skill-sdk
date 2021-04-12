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

Both values be `None`, like if user has not filled the ZIP code field in the device configuration 
AND has uttered an intent without specifying the location
("What's the weather like outside?")

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
