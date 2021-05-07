"""
Automatically rendered handlers for the intents:

    - "Test_Intent"
    - "Another_Test_Intent"

"""

from datetime import date
from skill_sdk import skill, Response


@skill.intent_handler("Test_Intent")
async def handle_test_intent(
    name: str = "World"
) -> Response:
    """
    "Test_Intent" handler implementation

    :param name:
    :return:
    """
    return Response("Hello from Test_Intent")


@skill.intent_handler("Another_Test_Intent")
async def handle_another_test_intent(
    date: date,
    name: str = "World"
) -> Response:
    """
    "Another_Test_Intent" handler implementation

    :param date:
    :param name:
    :return:
    """
    return Response("Hello from Another_Test_Intent")
