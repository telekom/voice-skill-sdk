#
# voice-skill-sdk
#
# (C) 2020, YOUR_NAME (YOUR COMPANY), Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#
from skill_sdk import skill, Response, tell
from skill_sdk.l10n import _


@skill.intent_handler('SMALLTALK__GREETINGS')
def handler() -> Response:
    """ A very basic handler of SMALLTALK__GREETINGS intent,
        SMALLTALK__GREETINGS intent is activated when user says 'Hello'
        returns translated 'Hello' greeting

    :return:        Response
    """
    # We get a translated message
    msg = _('HELLOAPP_HELLO')
    # We create a simple response
    response = tell(msg)
    # We return the response
    return response
