#
# voice-skill-sdk
#
# (C) 2020, YOUR_NAME (YOUR COMPANY), Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#
import unittest

from impl.hello import skill


class TestMain(unittest.TestCase):

    def test_hello_handler(self):
        """ A simple test case to ensure that our implementation returns 'Hello'
        """
        response = skill.test_intent('SMALLTALK__GREETINGS')
        self.assertEqual(response.text.key, 'HELLOAPP_HELLO')
