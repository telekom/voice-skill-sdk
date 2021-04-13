#
#
# voice-skill-sdk
#
# (C) 2021, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

"""Skill responses"""

from typing import Text

from skill_sdk.responses.info import SkillInfoResponse

from skill_sdk.responses.error import (
    ErrorCode,
    ErrorResponse,
)

from skill_sdk.responses.card import (
    Card,
    CardAction,
    ListItem,
    ListSection,
)

from skill_sdk.responses.command import (
    Command,
    AudioPlayer,
    Calendar,
    System,
    Timer,
)

from skill_sdk.responses.result import Result

from skill_sdk.responses.response import (
    SkillInvokeResponse,
    SkillInvokeResponse as Response,
    ResponseType,
    SessionResponse,
    _enrich,
)

from skill_sdk.responses.reprompt import Reprompt

from skill_sdk.responses.task import ClientTask, DelayedClientTask


def tell(text: Text, **kwargs) -> Response:
    """
    Wrapper to return Response of TELL type

    :param text:
    :param kwargs:
    :return:
    """
    return Response(**{**kwargs, **dict(text=text, type=ResponseType.TELL)})


def ask(text: Text, **kwargs) -> Response:
    """
    Wrapper to return Response of ASK type

    :param text:
    :param kwargs:
    :return:
    """
    return Response(**{**kwargs, **dict(text=text, type=ResponseType.ASK)})


def ask_freetext(text: Text, **kwargs) -> Response:
    """
    Wrapper to return Response of ASK_FREETEXT type

    :param text:
    :param kwargs:
    :return:
    """
    return Response(**{**kwargs, **dict(text=text, type=ResponseType.ASK_FREETEXT)})
