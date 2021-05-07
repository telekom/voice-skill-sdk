"""
Automatically rendered runner for the intents:

    - "Test_Intent"
    - "Another_Test_Intent"

"""

from skill_sdk import skill
from impl import (
    handle_test_intent,
    handle_another_test_intent
)

app = skill.init_app(develop=True)
app.include("Test_Intent", handler=handle_test_intent)
app.include("Another_Test_Intent", handler=handle_another_test_intent)
