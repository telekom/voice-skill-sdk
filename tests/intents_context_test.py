#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#
import os
import time
import logging
import datetime
import unittest
import importlib
from unittest.mock import patch
from types import SimpleNamespace
from gettext import NullTranslations
from dateutil import tz

from skill_sdk import l10n
from skill_sdk.intents import Context
from skill_sdk.test_helpers import create_context, mock_datetime_now

l10n.translations = {'de': NullTranslations()}

logger = logging.getLogger(__name__)


class TestIntentsContext(unittest.TestCase):
    ctx: Context

    def setUp(self):
        configuration = {'a': ['123'],
                         'b': [1, 2, 3]}
        session = {'attributes': {"key-1": "value-1",
                                  "key-2": "value-2"}}
        self.ctx = create_context('TELEKOM_Clock_GetTime', configuration=configuration, session=session)

    def test_check_prerequisite(self):
        logger.info(self.ctx)
        self.assertEqual(self.ctx.intent_name, 'TELEKOM_Clock_GetTime')
        self.assertEqual(self.ctx.locale, {'language': 'de'})
        self.assertEqual(self.ctx.session.new_session, True)
        self.assertEqual(self.ctx.session.session_id, '12345')
        self.assertEqual(self.ctx.configuration, {'a': ['123'],
                                              'b': [1, 2, 3]})

    def test_no_translations(self):
        from unittest import mock
        with mock.patch('skill_sdk.l10n.logger') as fake_log:
            self.ctx = create_context('TELEKOM_Clock_GetTime', locale='fr')
            fake_log.error.assert_called_with('A translation for locale %s is not available.', 'fr')

    def test_init_no_session(self):
        request = SimpleNamespace()
        request.json = {
            "context": {
                "attributes": {...},
                "intent": "TELEKOM_Clock_GetTime",
                "locale": "de",
                "tokens": {},
            },
            "version": 1
        }
        request.headers = {}
        ctx = Context(request)

        self.assertEqual(ctx.session.new_session, True)
        self.assertEqual(ctx.session.session_id, None)
        self.assertEqual(len(ctx.session), 0)

    def test_no_user_config(self):
        request = SimpleNamespace()
        request.json = {
            "context": {
                "attributes": {...},
                "intent": "TELEKOM_Clock_GetTime",
                "locale": "de",
                "tokens": {},
            },
            "version": 1
        }
        request.headers = {}
        ctx = Context(request)

        self.assertEqual(ctx.configuration, {})

    def test_tz_functions(self):
        now = datetime.datetime(year=2100, month=12, day=19, hour=23, minute=42, tzinfo=tz.tzutc())

        self.assertEqual('CET', self.ctx.gettz().tzname(now))
        with patch.dict(self.ctx.attributes, {'timezone': ["Mars"]}), patch.object(logging.Logger, 'error') as log:
            self.assertEqual('UTC', self.ctx.gettz().tzname(now))
            self.assertEqual(log.call_count, 1)

        with mock_datetime_now(now, datetime):
            # Make sure timezone is set to "Europe/Berlin"
            self.assertEqual(self.ctx.attributes.get('timezone'), ["Europe/Berlin"])
            self.assertEqual(self.ctx.gettz().tzname(now), 'CET')
            self.ctx.attributes['timezone'] = ['Europe/Athens']
            self.assertIsInstance(self.ctx.gettz(), datetime.tzinfo)

            with patch.dict(os.environ, {'TZ': 'UTC'}):
                time.tzset()
                local_now = self.ctx.now()
                self.assertEqual(local_now, now)
                self.assertEqual(local_now.day, 20)
                self.assertEqual(local_now.hour, 1)

                local_today = self.ctx.today()
                self.assertEqual(local_today.day, 20)
                self.assertEqual(local_today.hour, 0)
                self.assertEqual(local_today.minute, 0)

    def test_previous_date_functions(self):
        self.ctx.attributes["date"] = [datetime.date(year=1980, month=2, day=27),
                                               datetime.date(year=1980, month=1, day=27),
                                               datetime.date(year=1980, month=2, day=28),
                                               datetime.date(year=1980, month=3, day=27),
                                               datetime.date(year=1981, month=2, day=27),
                                               datetime.date(year=1979, month=2, day=27)]

        now = datetime.datetime(year=1980, month=2, day=26, hour=23, minute=42, tzinfo=tz.tzutc())
        with mock_datetime_now(now, datetime):
            with patch.dict(os.environ, {'TZ': 'UTC'}):
                self.assertEqual(self.ctx.attributes.get('timezone'), ["Europe/Berlin"])
                self.assertEqual(self.ctx.gettz().tzname(now), 'CET')
                #not 1980-2-27, because 23h UTC will become next day CET
                self.assertEqual(self.ctx.closest_previous_date(),datetime.date(year=1980, month=1, day=27))
                #check fall back to today
                self.ctx.attributes["date"] = []
                self.assertEqual(self.ctx.closest_previous_date(), self.ctx.now().date())

    def test_next_date_functions(self):
        self.ctx.attributes["date"] = [datetime.date(year=1980, month=2, day=27),
                                               datetime.date(year=1980, month=1, day=27),
                                               datetime.date(year=1980, month=2, day=28),
                                               datetime.date(year=1980, month=3, day=27),
                                               datetime.date(year=1981, month=2, day=27),
                                               datetime.date(year=1979, month=2, day=27)]

        now = datetime.datetime(year=1980, month=2, day=27, hour=23, minute=42, tzinfo=tz.tzutc())
        with mock_datetime_now(now, datetime):
            with patch.dict(os.environ, {'TZ': 'UTC'}):
                self.assertEqual(self.ctx.attributes.get('timezone'), ["Europe/Berlin"])
                self.assertEqual(self.ctx.gettz().tzname(now), 'CET')
                #not 1980-2-28, because 23h UTC will become next day CET
                self.assertEqual(self.ctx.closest_next_date(),datetime.date(year=1980, month=3, day=27))
                #check fall back to today
                self.ctx.attributes["date"] = []
                self.assertEqual(self.ctx.closest_next_date(), self.ctx.now().date())

    def test_is_text_including_words(self):
        self.ctx.attributes["stt_text"] = ["Welches Datum war am Montag?"]
        self.assertEqual(self.ctx.is_text_including_words(["war","gewesen"]), True)
        self.ctx.attributes["stt_text"] = ["Welches Datum ist am Montag gewesen?"]
        self.assertEqual(self.ctx.is_text_including_words(["war", "gewesen"]), True)
        self.ctx.attributes["stt_text"] = ["Gestern gabe es eine Warnung"]
        self.assertEqual(self.ctx.is_text_including_words(["war", "gewesen"]), False)
        self.ctx.attributes["stt_text"] = ["Wir waren gestern im Kino"]
        self.assertEqual(self.ctx.is_text_including_words(["war", "gewesen"]), False)
