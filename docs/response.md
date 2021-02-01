# Responses

An intent handler function can return three different types of objects. Any other returned object results in error.

## Response

*`skill_sdk.responses.Response`*

Any valid call of an intent handler may return `Response` type object. 
If a call of the intent is valid, the requested user action processed as intended. 
Furthermore, it covered any exception from the normal processing that is handled by notifying the client/user about the result. 
In other words: Everything that is not an unrecoverable error.

`Response` class has the following attributes:

- **type_**: Response type. Valid response types are `skill_sdk.responses.RESPONSE_TYPE_ASK`, `skill_sdk.responses.RESPONSE_TYPE_TELL` and `skill_sdk.responses.RESPONSE_TYPE_ASK_FREETEXT`.
- **text**: Text message that client reads out to the user. It can be a question if response is of `RESPONSE_TYPE_ASK`/`RESPONSE_TYPE_ASK_FREETEXT` types, or a statement if it is `RESPONSE_TYPE_TELL`. If the text is wrapped in a `<speak>` tag, it is interpreted as SSML.
- **card**: Response card. The card is sent to a user's companion app on the mobile device.
- **result**: Additional storage used for debug info and client [kits](use_kits_and_actions.md) activation. 

### Cards

Action cards deliver additional information to the user via the companion app on a smartphone.
A card is a graphical representation of a successful voice commands invoke.

#### Card Elements

Below is a list of card elements with their field names and descriptions. 
To get a better idea of field positions and their design, please refer to the samples section.

| Field |  Description  |
| -------- | ----------| 
|title_text | **Title**: this text is displayed as card title. If the filed is missing, the name of the related skill is displayed as card title. If the related skill is missing the title view is hidden.          
|type_description  | **Subtitle**: card subtitle. If the filed is missing, the subtitle view is hidden.   |
|prominent_text  | **Prominent Text**: card prominent text. If the filed is missing, the prominent text view is hidden.
|text  |  **Text**: card text. If the filed is missing, the text view is hidden.
|sub_text  |  **Subtext**: card subtext. If the filed is missing, the subtext view is hidden.
|icon_url  |  **Icon URL**: image that should be displayed inside the card view. Can be a valid url of an image e.g. cloudimage://picture.service/. If empty - a normal skill icon will be displayed as a fallback. If the skill is unknown, the image view will be hidden.
|list_sections  |  **List Sections**: a card can have a bullet-like list. Each list section contains items and title, title is optional. Each item contains iconUrl and title and iconUrl is optional.

Actions:

| Field |  Description  |
| -------- | ----------| 
|action  |  **Action**: action URL linked to action text or action prominent text. can be one of the internal deep links or an external url to a website. 
|action_text  |  **Action Text**: link text to access the given action. If the filed is missing, the link view is hidden. 
|action_prominent_text  |  **Action Prominent Text**: link prominent text to access the given action. f the filed is missing, the prominent link view is hidden.
#### Samples

- Sample card with title, subtitle, text and sub-text:
```python
from skill_sdk import Response
response = Response().with_card(
    title_text='Title',
    type_description='Subtitle',
    text='Text',
    sub_text='Subtext'
)
```
![capp_title](images/M-07-ACT-02.png)

- Prominent Text with link action:

```python
from skill_sdk import Response
response = Response().with_card(
    title_text='Title',
    type_description='Subtitle',
    prominent_text='Prominent Text',
    action='https://me-website',
    action_text='Action text'
)
```
![capp_title](images/M-07-ACT-07.png)

- Expandable list:

```python
from skill_sdk.responses import Response, ListSection, ListItem
response = Response().with_card(
    title_text='Title',
    type_description='Subtitle',
    text='Text',
    sub_text='Fine Print. Lorem dolor sit amet, consectetur adipiscing elit.',
    list_sections=[
        ListSection('Item Title', [
            ListItem('List item 1', 'cloudimage://picture.service/...'),
            ListItem('List item 2', 'cloudimage://picture.service/...')
        ]),
        ListSection('Item Title', [
            ListItem('List item 1', 'cloudimage://picture.service/...'),
            ListItem('List item 2', 'cloudimage://picture.service/...')
        ]),
        ListSection('Item Title', [
            ListItem('List item 1', 'cloudimage://picture.service/...'),
            ListItem('List item 2', 'cloudimage://picture.service/...')
        ]),
    ]
)
```
![capp_title](images/M-07-ACT-10-1.png)
![capp_title](images/M-07-ACT-10-2.png)


## Re-prompts

A re-prompt response is a special type of `RESPONSE_TYPE_ASK` response. It is implemented as a measure to limit a number of re-prompts.

Suppose your skill receives a number that must be in a range between 1 and 10. 
If user answers with a number outside of a range, you want to issue a re-prompt notifying user about erroneous input. 
If user again answers with a number outside, you issue a re-prompt once again.
If user's input is again invalid, you might want to give up and stop re-prompting.  

`Reprompt` response sets a number of re-prompts as a session value, increasing it with every prompt to user.
When the number of re-prompts reaches maximum, a simple `RESPONSE_TYPE_TELL` is returned with a `stop_text` that is set when creating an instance of `Reprompt` response.  

## ErrorResponse

*`skill_sdk.responses.ErrorResponse`*

An intent handler can return an `ErrorResponse` explicitly. If intent handler fails, the `ErrorResponse` is also returned.

The following combinations of an `ErrorResponse` are defined:

- **wrong intent**: `ErrorResponse(code=1, text="intent not found")` → *HTTP code: 404*
- **invalid token**: `ErrorResponse(code=2, text="invalid token")` → *HTTP code: 400*
- **locale,… missing**: `ErrorResponse(code=3, text="Bad request")` → *HTTP code: 400*
- **unhandled exception**: `ErrorResponse(code=999, text="internal error")` → *HTTP code: 500*

## String

If just a string is returned from the intent handler function, it is equivalent to returning `Response(text=the_returned_string)`.
As a result, the text is read out to user.
