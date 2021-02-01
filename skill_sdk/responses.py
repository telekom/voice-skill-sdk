#
#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

#
# Skill responses
#

from enum import Enum, EnumMeta
from functools import partial
from typing import Dict, List, NamedTuple, Optional, Text, Union
import json

from . import skill
from . import l10n
from .entities import snake_to_camel

# : the type for response cards that will ask for a missing attribute
RESPONSE_TYPE_ASK = 'ASK'

# : the type for response cards that will return information to the user
RESPONSE_TYPE_TELL = 'TELL'

# : response type to ask additional free text from the user
RESPONSE_TYPE_ASK_FREETEXT = 'ASK_FREETEXT'

# Supported card version
CARD_VERSION = 1

# The only card type available: "GENERIC_DEFAULT"
GENERIC_DEFAULT = 'GENERIC_DEFAULT'


class ListItem(NamedTuple):
    """
    List item in Card's list sections
    """
    title: Text
    icon_url: Optional[Text] = None


class ListSection(NamedTuple):
    """
    List section in a Card
    """
    title: Text
    items: List[ListItem]


class CardAction(str, Enum):
    """
    Card action link can be either one of internal "deep links" (enumerated below)
        or any external "http/https" URL

    """

    # Present skill details view
    INTERNAL_SKILLS = "internal://deeplink/skills"

    # Present overview of all devices
    INTERNAL_OVERVIEW = "internal://deeplink/speakeroverview"

    # Present device details page of the one device that was spoken into to generate this card
    INTERNAL_DETAILS = "internal://deeplink/speakerdetails"

    # Present feedback page in the app
    INTERNAL_FEEDBACK = "internal://deeplink/feedback"

    # Link to the news section of the app
    INTERNAL_NEWS = "internal://deeplink/news"

    # Present full text of the response in an overlay
    INTERNAL_RESPONSE_TEXT = "internal://showResponseText"

    # Initiate a call to the given phone number.
    INTERNAL_CALL = "internal://deeplink/call/{number}"

    # Open a specified app or the App Store if the app is not installed
    INTERNAL_OPEN_APP = "internal://deeplink/openapp?" \
                        "aos={aos_package_name}&" \
                        "iosScheme={ios_url_scheme}&" \
                        "iosAppStoreId={ios_app_store_id}"


class KitType(str, Enum):
    """
    Client kits available for cloud skills

    """
    AUDIO_PLAYER = "audio_player"
    CALENDAR = "calendar"
    SYSTEM = "system"
    TIMER = "timer"


class Kit(NamedTuple):
    """
    Client kit

    """
    kit_name: KitType
    action: str
    parameters: Optional[Dict]


class Command:
    """
    Generic client command

    """

    use_kit: Kit

    def __init__(self, kit_name, action, **kwargs):
        parameters = kwargs or None
        self.use_kit = Kit(
            kit_name,
            action,
            parameters=parameters)


class AudioPlayer(Command):
    """
    Kit for handling audio player/radio functions

    """

    class Action(str, Enum):
        PLAY_STREAM = "play_stream"
        PLAY_STREAM_BEFORE_TEXT = "play_stream_before_text"
        STOP = "stop"
        PAUSE = "pause"
        RESUME = "resume"

    class ContentType(str, Enum):
        RADIO = "radio"
        VOICEMAIL = "voicemail"

    def __init__(self, action, **kwargs):
        super().__init__(KitType.AUDIO_PLAYER, action, **kwargs)

    @staticmethod
    def play_stream(url: str) -> 'AudioPlayer':
        """
        Start playing a generic internet stream, specified by "url" parameter

        @param url:
        @return:
        """
        return AudioPlayer(AudioPlayer.Action.PLAY_STREAM, url=url)

    @staticmethod
    def play_stream_before_text(url: str) -> 'AudioPlayer':
        """
        Start playing a stream, before pronouncing the response

        @param url:
        @return:
        """
        return AudioPlayer(AudioPlayer.Action.PLAY_STREAM_BEFORE_TEXT, url=url)

    @staticmethod
    def stop(content_type: ContentType = None, text: str = None) -> 'AudioPlayer':
        """
        Stop currently playing media (voicemail, radio, content tts),
            optionally say text BEFORE stopping

        @param content_type:
        @param text:
        @return:
        """
        content_type = content_type or AudioPlayer.ContentType.RADIO
        text = text or ''

        return AudioPlayer(AudioPlayer.Action.STOP,
                           content_type=content_type,
                           notify=dict(not_playing=text))

    @staticmethod
    def pause(content_type: ContentType = None, text: str = None) -> 'AudioPlayer':
        """
        Pause playback, optionally say text AFTER playback paused

        @param content_type:
        @param text:
        @return:
        """
        content_type = content_type or AudioPlayer.ContentType.RADIO
        text = text or ''

        return AudioPlayer(AudioPlayer.Action.PAUSE,
                           content_type=content_type,
                           notify=dict(not_playing=text))

    @staticmethod
    def resume(content_type: ContentType = None) -> 'AudioPlayer':
        """
        Resume paused media, say response text before resuming

        @param content_type:
        @return:
        """
        content_type = content_type or AudioPlayer.ContentType.RADIO

        return AudioPlayer(AudioPlayer.Action.RESUME,
                           content_type=content_type)


class Calendar(Command):
    """
    Calendar kit: snooze calendar alarm, cancel snooze

    """

    class Action(str, Enum):
        SNOOZE_START = "snooze_start"
        SNOOZE_CANCEL = "snooze_cancel"

    def __init__(self, action, **kwargs):
        super().__init__(KitType.CALENDAR, action, **kwargs)

    @staticmethod
    def snooze_start(snooze_seconds: int = None) -> 'Calendar':
        """
        Snooze calendar alarm by optional number of seconds

        @param snooze_seconds:
        @return:
        """
        return Calendar(Calendar.Action.SNOOZE_START,
                        snooze_seconds=snooze_seconds)

    @staticmethod
    def snooze_cancel() -> 'Calendar':
        """
        Cancel current snooze

        @return:
        """
        return Calendar(Calendar.Action.SNOOZE_CANCEL)


class System(Command):
    """
    System functions kit

    """

    class Action(str, Enum):
        STOP = "stop"
        PAUSE = "pause"
        RESUME = "resume"
        NEXT = "next"
        PREVIOUS = "previous"
        SAY_AGAIN = "say_again"
        VOLUME_UP = "volume_up"
        VOLUME_DOWN = "volume_down"
        VOLUME_TO = "volume_to"

    class SkillType(str, Enum):
        TIMER = "Timer"
        CONVERSATION = "Conversation"
        MEDIA = "Media"

    def __init__(self, action, **kwargs):
        super().__init__(KitType.SYSTEM, action, **kwargs)

    @staticmethod
    def stop(skill_type: SkillType = None) -> 'System':
        """
        Send a `Stop` event: stops a foreground activity on the device.
        If there was another activity in background, it will gain focus.

        @param skill_type:  Stop a skill-related activity, or everything, if no skill specified
        @return:
        """
        return System(System.Action.STOP,
                      skill=skill_type)

    @staticmethod
    def pause() -> 'System':
        """
        Pause currently active content (if supported)

        @return:
        """
        return System(System.Action.PAUSE)

    @staticmethod
    def resume() -> 'System':
        """
        Resume media (if paused)

        @return:
        """
        return System(System.Action.RESUME)

    @staticmethod
    def next() -> 'System':
        """
        Switch to next item in content channel

        @return:
        """
        return System(System.Action.NEXT)

    @staticmethod
    def previous() -> 'System':
        """
        Switch to previous item in content channel

        @return:
        """
        return System(System.Action.PREVIOUS)

    @staticmethod
    def say_again() -> 'System':
        """
        Repeat last uttered sentence (from the dialog channel)

        @return:
        """
        return System(System.Action.SAY_AGAIN)

    @staticmethod
    def volume_up() -> 'System':
        """
        Increase the volume one notch

        @return:
        """
        return System(System.Action.VOLUME_UP)

    @staticmethod
    def volume_down() -> 'System':
        """
        Decrease the volume one notch

        @return:
        """
        return System(System.Action.VOLUME_DOWN)

    @staticmethod
    def volume_to(value: int = 0) -> 'System':
        """
        Set the volume to an absolute value (0-10)

        @return:
        """
        if value not in range(10):
            raise ValueError("Value %s in not in expected range (0 - 10)", repr(value))

        return System(System.Action.VOLUME_TO, value=value)


class Timer(Command):
    """
    Timer kit: start/stop Timer/Reminder/Alarm animation

        After animation started, it keeps running for max. 10 min if no user interaction happens

    """

    class Action(str, Enum):
        SET_TIMER = "set_timer"
        CANCEL_TIMER = "cancel_timer"

    def __init__(self, action, **kwargs):
        super().__init__(KitType.TIMER, action, **kwargs)

    @staticmethod
    def set_timer():
        """
        Fire up a "timer" animation

        @return:
        """
        return Timer(Timer.Action.SET_TIMER)

    @staticmethod
    def cancel_timer():
        """
        Cancel currently running "timer"

        @return:
        """
        return Timer(Timer.Action.CANCEL_TIMER)


class Card(NamedTuple):
    """
    Card to be sent to the companion app

    """

    # Type of action cards, only supported right now is GENERIC_DEFAULT
    #   NOTE: this parameter is left for backward compatibility and IS IGNORED
    type_: Optional[Text] = GENERIC_DEFAULT

    title_text: Optional[Text] = None
    type_description: Optional[Text] = None
    prominent_text: Optional[Text] = None
    text: Optional[Text] = None
    sub_text: Optional[Text] = None
    action: Optional[Text] = None
    action_text: Optional[Text] = None
    action_prominent_text: Optional[Text] = None
    icon_url: Optional[Text] = None
    list_sections: Optional[List[ListSection]] = None

    def with_action(
            self,
            action_text: Text,
            action: Union[CardAction, Text],
            action_prominent_text: Text = None,
            **kwargs
    ) -> 'Card':
        """
        Add action to card

        @param action_text:
        @param action:
        @param action_prominent_text:
        @param kwargs:
        @return:
        """
        return self._replace(action_text=action_text,
                             action_prominent_text=action_prominent_text,
                             action=action.format(**kwargs))

    def dict(self):
        """
        Export as dictionary

        :return:
        """
        card = {
            # Required properties
            'type': GENERIC_DEFAULT,
            'version': CARD_VERSION,

            # Optional properties
            'data': _serialize(self._replace(type_=None),
                               use_camel_case=True)
        }

        return card


class Result:
    """
    Result data to be sent to the device

    """

    def __init__(self, data, local=True, target_device_id=None, **kwargs):
        self.data = data or kwargs
        self.local = local
        self.target_device_id = target_device_id

    def __getitem__(self, *args):
        return self.data.__getitem__(*args)

    def __bool__(self):
        return any((self.data, self.target_device_id))

    def update(self, *args, **kwargs):
        """
        Update `data`

        :return:
        """
        return self.data.update(*args, **kwargs)

    def dict(self):
        """
        Export as dictionary

        :return:
        """
        result = {"data": _serialize(self.data), "local": self.local}

        # Optional properties
        if self.target_device_id:
            result['targetDeviceId'] = self.target_device_id

        return result

    def __repr__(self) -> str:
        """
        String representation

        :return:
        """
        return str(self.dict())


class Response:
    """
    Response to the server.

    This will carry all kind of information back to the device.
    The class will handle responses of the types :py:const:`RESPONSE_TYPE_ASK` and :py:const:`RESPONSE_TYPE_TELL`.
    For error responses see :py:class:`ErrorResponse`.

    :ivar text: text response to the user.
        This should be question for :py:const:`RESPONSE_TYPE_ASK` and a statement for :py:const:`RESPONSE_TYPE_TELL`.
    :ivar type_: the type of the response, can be :py:const:`RESPONSE_TYPE_ASK` or :py:const:`RESPONSE_TYPE_TELL`
    :ivar card: This can be ``None`` of any instance of :py:class:`SimpleCard` and it's subclasses.
        The card will be presented in the companion app of the user.
    :ivar result: the result in machine readable form. Can be ``None``, a dictionary with the key 'data' and 'local or
        a Result instance.

    """

    def __init__(self, text='', type_=RESPONSE_TYPE_TELL, card=None, result=None, **kwargs):

        if type_ not in (RESPONSE_TYPE_TELL,
                         RESPONSE_TYPE_ASK,
                         RESPONSE_TYPE_ASK_FREETEXT):
            raise ValueError(f'Type {type_} is not a valid type.')

        self.text = text
        self.type_ = type_
        self.card = card
        self.push_notification = None
        self.result = result if isinstance(result, Result) else Result(result, **kwargs)

    def dict(self, context):
        """
        Dump the request into JSON suitable to be returned to the dialog manager.

        :param context: the context of the request
        """

        # Required properties
        result = {
            'type': self.type_,
            'text': self.text,
        }

        # Export string key and format parameters from Message object
        if isinstance(self.text, l10n.Message):
            self.result = self.result or Result(None)
            self.result.update(key=self.text.key,
                               value=self.text.value,
                               args=self.text.args,
                               kwargs=self.text.kwargs)

        # Optional properties
        if self.card:
            result['card'] = self.card.dict()
        if self.result:
            result['result'] = self.result.dict()
        if self.push_notification:
            result['pushNotification'] = self.push_notification
        if context.session:
            result['session'] = {'attributes': context.session}

        return result

    def with_card(
            self,
            card: Card = None,
            title_text: Text = None,
            type_description: Text = None,
            prominent_text: Text = None,
            text: Text = None,
            sub_text: Text = None,
            action: Text = None,
            action_text: Text = None,
            action_prominent_text: Text = None,
            icon_url: Text = None,
            list_sections: List[ListSection] = None
    ) -> 'Response':
        """
        Attach Card to a response

        @param card:
        @param title_text:
        @param type_description:
        @param prominent_text:
        @param text:
        @param sub_text:
        @param action:
        @param action_text:
        @param action_prominent_text:
        @param icon_url:
        @param list_sections:
        @return:
        """
        self.card = card or Card(
            title_text=title_text,
            type_description=type_description,
            prominent_text=prominent_text,
            text=text,
            sub_text=sub_text,
            action=action,
            action_text=action_text,
            action_prominent_text=action_prominent_text,
            icon_url=icon_url,
            list_sections=list_sections
        )
        return self

    def with_command(self, command: Command):
        """
        Add a command to execute on the client

        @param command:
        @return:
        """
        self.result.update(command.__dict__)
        return self

    def as_response(self, context):
        """
        Converts the instance to an actual :py:class:HTTPResponse instance

        :param context: the request context
        """
        return skill.HTTPResponse(self.dict(context), 200, {'Content-type': 'application/json'})

    def __repr__(self) -> str:
        """
        String representation

        :return:
        """
        return str(self.__dict__)


def tell(*args, **kwargs):
    """
    Wrapper to return Response of RESPONSE_TYPE_TELL type

    :param args:
    :param kwargs:
    :return:
    """
    kwargs.update(type_=RESPONSE_TYPE_TELL)
    return Response(*args, **kwargs)


def ask(*args, **kwargs):
    """
    Wrapper to return Response of RESPONSE_TYPE_ASK type

    :param args:
    :param kwargs:
    :return:
    """
    kwargs.update(type_=RESPONSE_TYPE_ASK)
    return Response(*args, **kwargs)


def ask_freetext(*args, **kwargs):
    """
    Wrapper to return Response of RESPONSE_TYPE_ASK_FREETEXT type

    :param args:
    :param kwargs:
    :return:
    """
    kwargs.update(type_=RESPONSE_TYPE_ASK_FREETEXT)
    return Response(*args, **kwargs)


class Reprompt(Response):
    """
    Re-prompt response is sent to user as a measure to limit the number of re-prompts.

    """

    def __init__(self, text: str, stop_text: str = None, max_reprompts: int = 0, entity: str = None, **kwargs):
        """
        Set stop_text/max_reprompts/entity and pass the rest to parent

        :param text:            a re-prompt text
        :param stop_text:       stop text will be sent if number of re-prompts is higher than maximum number
        :param max_reprompts:   maximum number of re-prompts
        :param entity:          entity name if re-prompt is used for intent/entity
        :param kwargs:
        """
        self.stop_text = stop_text
        self.max_reprompts = max_reprompts
        self.entity = entity
        super().__init__(text, type_=RESPONSE_TYPE_ASK, **kwargs)

    def dict(self, context):
        """
        Get/set the number of re-prompts in session
        """

        # Name of the counter formatted as INTENT_ENTITY_reprompt_count
        name = f"{context.intent_name}{'_' + self.entity if self.entity else ''}_reprompt_count"

        try:
            reprompt_count = int(context.session.get(name, 0)) + 1
        except ValueError:
            reprompt_count = 1

        if reprompt_count > self.max_reprompts > 0:
            self.text = self.stop_text
            self.type_ = RESPONSE_TYPE_TELL
            context.session.pop(name, None)
        else:
            context.session[name] = reprompt_count

        return super().dict(context)


class ErrorResponse:
    """
    An error response
    It can be returned explicitly from the intent handler or will be returned if calling the intent handler fails.

    The following combinations are defined:

    **wrong intent**
      ``{"code": 1, "text": "intent not found"}`` HTTP code: *404*

    **invalid token**
      ``{"code": 2, "text": "invalid token"}`` HTTP code: *400*

    **version, locale,… missing**
      ``{"code": 3, "text": "Bad request"}`` HTTP code: *400*

    **time out**
      ``{"code": 4, "text": "Time out"}`` HTTP code: *504*

    **unhandled exception**
      ``{"code": 999, "text": "internal error"}`` HTTP code: *500*

    :ivar code: The error code
    :ivar text: the error text
    """
    code_map = {
        1: 404,
        2: 400,
        3: 400,
        4: 504,
        999: 500
    }

    def __init__(self, code, text):
        self.code = code
        self.text = text

    def json(self):
        """
        Serialize to JSON

        :return:
        """
        data = {"code": self.code, "text": self.text}
        return json.dumps(data)

    def as_response(self, context=None):
        """
        Send error as HTTP response

        :param context:
        :return:
        """
        return skill.HTTPResponse(self.json(), self.code_map.get(self.code, 500),
                                  {'Content-type': 'application/json'})


def _serialize(d, use_camel_case: bool = False):
    """
    Recursively serialize values

    @param d:
    @param use_camel_case:  Convert attribute names from "snake_case" to "camelCase"
    @return:
    """

    __iter = (getattr(d, '__slots__', None)
              or getattr(d, '_fields', None)
              # We don't want enum._EnumDict here (neither we want l10n.Message):
              or (not isinstance(type(d), EnumMeta) and not isinstance(d, str) and getattr(d, '__dict__', None))
              or isinstance(d, dict) and d)

    if __iter:
        __getter = partial(d.get) if isinstance(d, dict) else partial(getattr, d)
        return {snake_to_camel(slot) if use_camel_case else slot: _serialize(__getter(slot), use_camel_case)
                for slot in __iter if __getter(slot) is not None}

    if isinstance(d, (list, tuple)):
        return tuple([_serialize(v, use_camel_case) for v in d if v is not None])

    try:
        json.dumps(d)
        return d
    except (TypeError, OverflowError):
        return str(d)
