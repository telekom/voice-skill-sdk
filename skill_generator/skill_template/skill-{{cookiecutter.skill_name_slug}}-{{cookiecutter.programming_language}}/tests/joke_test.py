#
# voice-skill-sdk
#
# (C) 2020, YOUR_NAME (YOUR COMPANY), Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#
import requests_mock
import unittest
import json

from impl.joke import skill


class TestMain(unittest.TestCase):

    @requests_mock.mock()
    def test_joke_handler(self, mock):
        """ Mock the request by providing data and ensure that implementation returns the joke
        """
        response = {
            'type': 'success',
            'value': {
                'id': 479,
                'joke': 'Chuck Norris does not need to know about class factory pattern. He can instantiate interfaces.',
                'categories': ['nerdy']
            }
        }
        mock.get('http://api.icndb.com/jokes/random', text=json.dumps(response))

        response = skill.test_intent('AMUSEMENT__JOKE')
        self.assertEqual(response.text.key, 'HELLOAPP_JOKE')

    @requests_mock.mock()
    def test_fail_joke_handler(self, mock):
        """ Mock the request to simulate remote server failure and ensure the implementation returns error message
        """
        mock.get('http://api.icndb.com/jokes/random', text='Failure', status_code=500, reason='Server Failure')

        response = skill.test_intent('AMUSEMENT__JOKE')
        self.assertEqual(response.text.key, 'HELLOAPP_REQUEST_ERROR')

    @requests_mock.mock()
    def test_fail_response_joke_handler(self, mock):
        """ Mock the request to simulate malformed response and ensure the implementation returns error message
        """
        mock.get('http://api.icndb.com/jokes/random', text=json.dumps({'jiberish': 'jiberish'}))

        response = skill.test_intent('AMUSEMENT__JOKE')
        self.assertEqual(response.text.key, 'HELLOAPP_RESPONSE_ERROR')
