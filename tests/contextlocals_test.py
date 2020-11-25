#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#
import datetime
import logging
import unittest
import threading
from unittest.mock import patch
from skill_sdk.intents import Context, context
from skill_sdk.test_helpers import create_context, mock_datetime_now


def run_thread(func):
    t = threading.Thread(target=func)
    t.start()
    t.join()


class TestThreadLocalContext(unittest.TestCase):
    now = datetime.datetime(year=2100, month=12, day=19, hour=23, minute=42,
                            tzinfo=datetime.timezone.utc)

    def setUp(self):

        @mock_datetime_now(self.now, datetime)
        def run():
            now = self.now.astimezone(datetime.timezone(datetime.timedelta(hours=1)))
            create_context("TELEKOM_Demo_Intent", timezone=['Europe/Berlin'])
            self.assertEqual(context.today().timestamp(), now.replace(hour=0, minute=0, tzinfo=None).timestamp())
            self.assertEqual(context.now().timestamp(), self.now.timestamp())

        run_thread(run)

    @mock_datetime_now(now, datetime)
    def test_thread_local_now(self):
        next_day = datetime.datetime(year=2100, month=12, day=20, hour=0, minute=0)
        create_context("TELEKOM_Demo_Intent", timezone=['Europe/Athens'])
        self.assertEqual(context.today().timestamp(), next_day.timestamp())
        self.assertEqual(context.now().timestamp(), self.now.timestamp())

    @patch.object(logging.Logger, 'error')
    def test_tread_local_context(self, err_mock):
        session = {'attributes': {"key-1": "value-1",
                                  "key-2": "value-2"}}
        ctx = create_context("TELEKOM_Demo_Intent", session=session)

        context.set_current(None)
        self.assertIsNone(context.intent_name)
        err_mock.assert_called_with('Accessing context outside of request.')
        context.intent_name = 'NoMore_Demo_Intent'
        err_mock.assert_called_with('Accessing context outside of request.')
        ctx = Context(ctx.request)
        self.assertEqual(context.intent_name, 'TELEKOM_Demo_Intent')
        self.assertEqual(context.session, {"key-1": "value-1", "key-2": "value-2"})
        self.assertEqual(context._('HELLO'), 'HELLO')
        self.assertEqual(context._n('HELLO', 'HOLA', 1), 'HELLO')
        self.assertEqual(context._a('HELLO'), ['HELLO'])
        context.intent_name = 'NoMore_Demo_Intent'
        self.assertEqual(context.intent_name, 'NoMore_Demo_Intent')
