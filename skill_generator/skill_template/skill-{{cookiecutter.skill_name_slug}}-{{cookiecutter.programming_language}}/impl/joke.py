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

import requests


@skill.intent_handler('AMUSEMENT__JOKE')
def handler() -> Response:
    """ A sample handler of AMUSEMENT__JOKE intent,
        AMUSEMENT__JOKE intent is activated when user asks to tell him a joke
        returns a random joke from Chuck Norris jokes database: http://api.icndb.com/jokes/random

    :return:        Response
    """
    try:
        # We request a random joke from icndb with time-out set to 10 seconds
        response = requests.get('http://api.icndb.com/jokes/random', timeout=10)
        # We parse the response json or raise exception if unsuccessful
        response.raise_for_status()
        data = response.json()
        # We get the joke from the response data
        joke = data['value']['joke'] if data.get('type') == 'success' else None
        # We format our response to user or ask for an excuse
        if joke:
            msg = _('HELLOAPP_JOKE', joke=joke)
        else:
            msg = _('HELLOAPP_RESPONSE_ERROR')
    except requests.exceptions.RequestException as err:
        msg = _('HELLOAPP_REQUEST_ERROR', err=err)

    # We create a response with either joke or error message
    return tell(msg)
