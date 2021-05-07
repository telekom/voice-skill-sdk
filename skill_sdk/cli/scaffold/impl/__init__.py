#
# voice-skill-sdk
#
# (C) 2021, YOUR_NAME (YOUR COMPANY)
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#

"""Your intent handlers"""

from skill_sdk import Response, skill, tell
from skill_sdk.i18n import _


@skill.intent_handler("SMALLTALK__GREETINGS")
async def handler() -> Response:
    """
    A handler of SMALLTALK__GREETINGS intent.

        SMALLTALK__GREETINGS intent is activated when user says 'Hello'
        returns translated 'Hello' greeting

    :return:        Response
    """

    # Get a translated message
    msg = _("HELLOAPP_HELLO")

    # Create a simple response
    response = tell(msg)

    # Return the response
    return response
