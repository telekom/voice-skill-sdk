#
# voice-skill-sdk
#
# (C) 2020, YOUR_NAME (YOUR COMPANY), Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#
from random import randint
from skill_sdk import skill, Response, ask, tell
from skill_sdk.l10n import _


#
# This implementation demonstrates a basic sample of "Guess Number" game:
#   user gives a number from 1 to 10 and we answer if we had it in mind :)
#


# The said number comes as a list of strings
# We'll use `intent_handler` decorator and type hints to convert it to integer value
@skill.intent_handler('MINIGAMES__GUESS_NUMBER')
def handler(number: int) -> Response:
    """ The implementation

    :param number:
    :return:            Response
    """
    try:
        # We check if value is in range of 1 to 10
        assert 1 <= number <= 10
        # We get a random number
        if number == randint(1, 10):
            # ... and congratulate the winner!
            msg = _('HELLOAPP_NUMBER_SUCCESS_MESSAGE')
        else:
            # ... or encourage them to keep trying
            msg = _('HELLOAPP_NUMBER_WRONG_MESSAGE')
        response = tell(msg)
    except (AssertionError, TypeError, ValueError):
        msg = _('HELLOAPP_NO_NUMBER_MESSAGE')
        # We create a response with NO_NUMBER_MESSAGE and ask to repeat the number
        response = ask(msg)
    return response
