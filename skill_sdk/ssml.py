#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

#
# SSML tag wrappers (Nuance vocalizer)
#

import re
from typing import List
from functools import reduce

DURATION = r"^(\d*\.?\d+)(s|ms)$"
STRENGTH = ("none", "x-weak", "weak", "medium", "strong", "x-strong")
LEVEL = ("strong", "moderate", "reduced")
LOCALE = ("de", "en", "fr")
DEFAULT_LOCALE = "de"


class SSMLException(Exception):
    """Exception raised if an SSML tag or entity is incorrect"""


def escape(text: str) -> str:
    """
    Escape special characters

    @param text:
    @return:
    """

    # List of text characters to replace
    _ = (
        ('&', 'and'),
        ('<', ''),
        ('>', ''),
        ('\"', ''),
        ('\'', '')
    )

    return reduce(lambda t, repl: t.replace(*repl), _, text)


def validate_locale(locale: str) -> None:
    """
    Validate locale

    @param locale:
    @return:

    @throws SSMLException  if locale is not supported
    """

    if locale not in LOCALE:
        raise SSMLException(f"Locale {repr(locale)} is invalid. Must be one of {LOCALE}")


def validate_duration(duration: str):
    """
    Parse and validate duration [0 - 10000ms]

    @param duration:
    @return:
    @throws SSMLException  if duration cannot be parsed or is not in the range
    """

    try:
        matcher = re.search(DURATION, duration)
        assert matcher is not None, "Invalid format"

        break_scale = str(matcher.group(2))
        break_duration = int(matcher.group(1))

        if break_scale == "s":
            assert 0 <= break_duration <= 10, 'Duration length must be between 0 and 10 seconds'

        if break_scale == "ms":
            assert 0 <= break_duration <= 10000, 'Duration length must be between 0 and 10000 milliseconds'

    except (AssertionError, AttributeError, TypeError, ValueError) as ex:
        raise SSMLException(f"Cannot parse duration value {repr(duration)}: {repr(ex)}")


def pause(text: str = None, duration: str = None, strength: str = None):
    """
    Insert <break/> tag

    @param text:
    @param duration:
    @param strength:
    @return:
    """
    text = text or ''

    if duration:
        validate_duration(duration)
        return f'<break time="{duration}"/>{text}'

    elif strength:
        if strength in STRENGTH:
            return f'<break strength="{strength}"/>{text}'
        else:
            raise SSMLException(f"Invalid strength value {repr(strength)}. Must be one of {STRENGTH}")

    else:
        raise SSMLException('Please set one of "duration"/"strength" parameters when setting a break')


def paragraph(text: str) -> str:
    """
    Insert paragraph <p/> tag

    @param text:
    @return:
    """
    return f"<p>{text}</p>"


def sentence(text: str) -> str:
    """
    Insert sentence <s/> tag

    @param text:
    @return:
    """
    return f"<s>{text}</s>"


def spell(text: str) -> str:
    """
    Insert say-as/spell-out tag to spell the text

    @param text:
    @return:
    """
    return f'<say-as interpret-as="spell-out">{text}</say-as>'


def phone(text: str) -> str:
    """
    Insert say-as/phone tag

    @param text:
    @return:
    """
    return f'<say-as interpret-as="phone">{text}</say-as>'


def ordinal(text: str) -> str:
    """
    Insert say-as/ordinal tag

    @param text:
    @return:
    """
    return f'<say-as interpret-as="ordinal">{text}</say-as>'


def emphasis(text: str, level: str = "moderate") -> str:
    """
    Insert emphasis tag: <emphasis/>

    @param text:
    @param level:
    @return:
    """
    if level.lower() not in LEVEL:
        raise SSMLException(f"Emphasis level {repr(level)} is invalid. Must be one of {repr(LEVEL)}")

    return f'<emphasis level="{level}">{text}</emphasis>'


def lang(text: str, locale: str = DEFAULT_LOCALE) -> str:
    """
    Insert language <lang/> tag

    @param text:
    @param locale:
    @return:
    """
    if locale not in LOCALE:
        raise SSMLException(f"Locale {repr(locale)} is invalid. Must be one of {LOCALE}")

    return f'<lang xml:lang="{locale}">{text}</lang>'


def audio(src: str) -> str:
    """
    Insert audio tag

        The tag is currently not supported by Nuance, please use `audio_player` kit:
        docs/use_kits_and_actions.md

    :param src:
    :return:
    """
    return f'<audio src="{src}"/>'


def speak(*text: str) -> str:
    """
    Wrap text in <speak/> tag

    @param text:
    @return:
    """
    return f'<speak>{"".join(text)}</speak>'


class Speech:
    """SSML speech"""

    content: List[str]
    locale: str

    def __init__(self, text: str = None, locale: str = DEFAULT_LOCALE) -> None:
        validate_locale(locale)
        self.content = []
        self.locale = locale
        if text:
            self.say(text)

    def say(self, text: str) -> 'Speech':
        self.content.append(text)
        return self

    def paragraph(self, text: str) -> 'Speech':
        return self.say(paragraph(text))

    def pause(self, text: str = None, duration: str = None, strength: str = None) -> 'Speech':
        return self.say(pause(text, duration=duration, strength=strength))

    def sentence(self, text: str) -> 'Speech':
        return self.say(sentence(text))

    def spell(self, text: str) -> 'Speech':
        return self.say(spell(text))

    def emphasis(self, text: str, level: str = "moderate") -> 'Speech':
        return self.say(emphasis(text, level))

    def lang(self, text: str, locale: str = DEFAULT_LOCALE) -> 'Speech':
        return self.say(lang(text, locale))

    def __str__(self) -> str:
        return speak(lang(''.join(self.content), locale=self.locale))
