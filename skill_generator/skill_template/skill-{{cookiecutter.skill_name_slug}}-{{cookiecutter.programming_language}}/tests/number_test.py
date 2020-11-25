#
# voice-skill-sdk
#
# (C) 2020, YOUR_NAME (YOUR COMPANY), Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#
from unittest import mock
import unittest

from impl.number import skill


class TestMain(unittest.TestCase):

    @mock.patch('impl.number.randint', return_value=5)
    def test_number_game_won(self, m):
        """ Mock random number to return 5 and ensure we won the game
        """
        response = skill.test_intent('MINIGAMES__GUESS_NUMBER', number=[5])
        self.assertEqual(response.text.key, 'HELLOAPP_NUMBER_SUCCESS_MESSAGE')

    @mock.patch('impl.number.randint', return_value=1)
    def test_number_game_lost(self, m):
        """ Mock random number to return 1 and ensure we lost the game
        """
        response = skill.test_intent('MINIGAMES__GUESS_NUMBER', number=[5])
        self.assertEqual(response.text.key, 'HELLOAPP_NUMBER_WRONG_MESSAGE')

    def test_fail_number(self):
        """ Supply a non-numerical value and ensure the implementation returns the error
        """
        response = skill.test_intent('MINIGAMES__GUESS_NUMBER', number=['not-a-number'])
        self.assertEqual(response.text.key, 'HELLOAPP_NO_NUMBER_MESSAGE')
