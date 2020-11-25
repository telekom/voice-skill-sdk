#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#
import unittest
from skill_sdk import ssml


class TestSsmlFunctions(unittest.TestCase):

    def test_escape(self):
        self.assertEqual('', ssml.escape('<>"\'<>"\''))
        self.assertEqual('Ricchi and Poveri', ssml.escape('<Ricchi>" \'&<>" \'Poveri'))

    def test_validate_locale(self):
        ssml.validate_locale('de')
        with self.assertRaises(ssml.SSMLException):
            ssml.validate_locale('de-DE')

    def test_validate_duration(self):
        ssml.validate_duration("100ms")
        ssml.validate_duration("10s")
        with self.assertRaises(ssml.SSMLException):
            ssml.validate_duration('50000ms')
        with self.assertRaises(ssml.SSMLException):
            ssml.validate_duration('20s')
        with self.assertRaises(ssml.SSMLException):
            ssml.validate_duration('1h')
        with self.assertRaises(ssml.SSMLException):
            ssml.validate_duration('-1')

    def test_pause(self):
        self.assertEqual('<break strength="medium"/>Hola', ssml.pause('Hola', strength='medium'))
        with self.assertRaises(ssml.SSMLException):
            ssml.pause(strength='whateva')
        with self.assertRaises(ssml.SSMLException):
            ssml.pause()

    def test_simple_wrappers(self):
        self.assertEqual('<p>Hallo</p>', ssml.paragraph('Hallo'))
        self.assertEqual('<s>Hallo</s>', ssml.sentence('Hallo'))
        self.assertEqual('<say-as interpret-as="spell-out">Hallo</say-as>', ssml.spell('Hallo'))
        self.assertEqual('<say-as interpret-as="phone">Hallo</say-as>', ssml.phone('Hallo'))
        self.assertEqual('<say-as interpret-as="ordinal">Hallo</say-as>', ssml.ordinal('Hallo'))
        self.assertEqual('<emphasis level="moderate">Hallo</emphasis>', ssml.emphasis('Hallo'))
        with self.assertRaises(ssml.SSMLException):
            ssml.emphasis('Hallo', level='None')
        self.assertEqual('<lang xml:lang="de">Hallo</lang>', ssml.lang('Hallo'))
        with self.assertRaises(ssml.SSMLException):
            ssml.lang('Hallo', locale='AA')
        self.assertEqual('<audio src="Hallo"/>', ssml.audio('Hallo'))

    def test_speech(self):
        text = ssml.Speech("Hello, World", "en").pause(duration="500ms").say("is in").emphasis("English")
        self.assertEqual('<speak><lang xml:lang="en">Hello, World<break time="500ms"/>'
                         'is in<emphasis level="moderate">English</emphasis></lang></speak>', str(text))

        text = ssml.Speech("Hallo, Welt").pause(duration="500ms").say("ist auf").emphasis("Deutsch")
        self.assertEqual('<speak><lang xml:lang="de">Hallo, Welt<break time="500ms"/>'
                         'ist auf<emphasis level="moderate">Deutsch</emphasis></lang></speak>', str(text))

        text = ssml.Speech().paragraph('Hallo').sentence(ssml.lang(ssml.spell('World'), locale="en"))
        self.assertEqual('<speak><lang xml:lang="de"><p>Hallo</p><s><lang xml:lang="en">'
                         '<say-as interpret-as="spell-out">World</say-as></lang></s></lang></speak>', str(text))

        text = ssml.Speech('Hallo').lang('World', locale="en").pause(duration="500ms").spell('WORLD')
        self.assertEqual('<speak><lang xml:lang="de">Hallo<lang xml:lang="en">World</lang><break time="500ms"/>'
                         '<say-as interpret-as="spell-out">WORLD</say-as></lang></speak>', str(text))
