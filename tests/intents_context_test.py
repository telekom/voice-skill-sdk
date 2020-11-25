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
