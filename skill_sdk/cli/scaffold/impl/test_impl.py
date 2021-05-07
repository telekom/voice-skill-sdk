#
# voice-skill-sdk
#
# (C) 2021, YOUR_NAME (YOUR COMPANY)
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#

"""Unit tests suite"""

import pytest
from skill_sdk import skill
from . import handler


@pytest.fixture
def app():
    """
    Pytest fixture to create an app for testing

    :return:
    """
    app = skill.init_app()
    app.include(handler=handler)
    return app


@pytest.mark.asyncio
async def test_intent_async(app):
    """
    This is a sample unit test of an intent in asynchronous context

    :param app:
    :return:
    """
    response = await app.test_intent("SMALLTALK__GREETINGS")
    assert response.text == "HELLOAPP_HELLO"


def test_intent_sync():
    """
    This is a sample unit test of an intent in sync context

    :return:
    """
    response = skill.test_intent("SMALLTALK__GREETINGS")
    assert response.text == "HELLOAPP_HELLO"
