"""Unit tests suite"""

import pytest
from skill_sdk import skill
from . import (
    handle_test_intent,
    handle_another_test_intent
)


@pytest.fixture
def app():
    """Pytest fixture to create an app for testing"""

    app = skill.init_app()
    app.include("Test_Intent", handler=handle_test_intent)
    app.include("Another_Test_Intent", handler=handle_another_test_intent)
    return app


@pytest.mark.asyncio
async def test_handle_test_intent(app):
    response = await app.test_intent("Test_Intent")
    assert response.text == "Hello from Test_Intent"


@pytest.mark.asyncio
async def test_handle_another_test_intent(app):
    response = await app.test_intent("Another_Test_Intent")
    assert response.text == "Hello from Another_Test_Intent"
