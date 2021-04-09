#
# voice-skill-sdk
#
# (C) 2021, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#

import os
import time
import logging
import datetime
import threading
import unittest
from unittest.mock import patch
from dateutil import tz
import pytest

from pydantic import ValidationError
from skill_sdk.intents import RequestContextVar, request
from skill_sdk.util import (
    create_context,
    create_request,
    mock_datetime_now,
    run_in_executor,
)
from skill_sdk.i18n import Translations

logger = logging.getLogger(__name__)

TEST_INTENT = "Test__Intent"


def test_session():
    r = create_request(TEST_INTENT, session={'key-1': 'value-1', 'key-2': 'value-2'})
    assert r.session.attributes == {'key-1': 'value-1', 'key-2': 'value-2'}
    with pytest.raises(ValidationError):
        create_request(TEST_INTENT, session={'non-string': datetime.datetime(year=2100, month=1, day=1)})


class TestContext(unittest.TestCase):
    def setUp(self):
        self.ctx = create_context(TEST_INTENT)

    def test_tz_functions(self):
        now = datetime.datetime(
            year=2100, month=12, day=19, hour=23, minute=42, tzinfo=tz.tzutc()
        )

        self.assertEqual("CET", self.ctx.gettz().tzname(now))
        ctx = create_context(TEST_INTENT, timezone="Mars")
        with patch.object(logging.Logger, "error") as log:
            self.assertEqual("UTC", ctx.gettz().tzname(now))
            self.assertEqual(log.call_count, 1)

        with mock_datetime_now(now, datetime):
            # Make sure timezone is set to "Europe/Berlin"
            self.assertEqual(self.ctx.attributes.get("timezone"), ["Europe/Berlin"])
            self.assertEqual(self.ctx.gettz().tzname(now), "CET")
            ctx = create_context(TEST_INTENT, timezone="Europe/Athens")
            self.assertIsInstance(ctx.gettz(), datetime.tzinfo)

            with patch.dict(os.environ, {"TZ": "UTC"}):
                time.tzset()
                local_now = ctx.now()
                self.assertEqual(local_now, now)
                self.assertEqual(local_now.day, 20)
                self.assertEqual(local_now.hour, 1)

                local_today = ctx.today()
                self.assertEqual(local_today.day, 20)
                self.assertEqual(local_today.hour, 0)
                self.assertEqual(local_today.minute, 0)

    def test_missing_attribute(self):
        self.assertEqual("Value", self.ctx._get_attr_value("Non-existing", "Value"))


def run_thread(func):
    t = threading.Thread(target=func)
    t.start()
    t.join()


class TestContextLocal(unittest.TestCase):
    now = datetime.datetime(
        year=2100, month=12, day=19, hour=23, minute=42, tzinfo=datetime.timezone.utc
    )

    def setUp(self):
        req = create_request(TEST_INTENT, timezone=["Europe/Berlin"])

        @mock_datetime_now(self.now, datetime)
        def run():
            now = self.now.astimezone(datetime.timezone(datetime.timedelta(hours=1)))
            with RequestContextVar(request=req):
                self.assertEqual(
                    request.context.today().timestamp(),
                    now.replace(hour=0, minute=0, tzinfo=None).timestamp(),
                )
                self.assertEqual(
                    request.context.now().timestamp(), self.now.timestamp()
                )

        run_thread(run)

    @mock_datetime_now(now, datetime)
    def test_context_local_now(self):
        req = create_request(TEST_INTENT, timezone=["Europe/Athens"])
        next_day = datetime.datetime(year=2100, month=12, day=20, hour=0, minute=0)
        with RequestContextVar(request=req):
            self.assertEqual(request.context.today().timestamp(), next_day.timestamp())
            self.assertEqual(request.context.now().timestamp(), self.now.timestamp())

    @patch.object(logging.Logger, "error")
    def test_context_local_context(self, err_mock):
        self.assertIsNone(request.context)
        err_mock.assert_called_with(
            "Accessing request local object outside of the request-response cycle."
        )
        req = create_request(
            "TELEKOM_Demo_Intent", session={"key-1": "value-1", "key-2": "value-2"}
        )
        with RequestContextVar(request=req):
            self.assertEqual(request.context.intent, "TELEKOM_Demo_Intent")
            self.assertEqual(
                {
                    "id": "123",
                    "attributes": {"key-1": "value-1", "key-2": "value-2"},
                    "new": True,
                },
                request.session.dict(),
            )

        with RequestContextVar(request=req.with_translation(Translations())):
            self.assertEqual("HELLO", request.context._("HELLO"))
            self.assertEqual("HELLO", request.context._n("HELLO", "HOLA", 1))
            self.assertEqual(["HELLO"], request.context._a("HELLO"))


@pytest.mark.asyncio
async def test_context_local_session():
    def one(_):
        with RequestContextVar(request=_):
            del request.session["key-1"]
            del request.session["key-2"]
            assert request.session.dict() == {
                "id": "123",
                "attributes": {},
                "new": True,
            }

    def init(_):
        with RequestContextVar(request=_):
            with pytest.raises(TypeError):
                request.context.locale = "de"  # noqa: attempt to modify "read-only" context (to raise TypeError)

            assert request.session.dict() == {
                "id": "123",
                "attributes": {"key-1": "value-1", "key-2": "value-2"},
                "new": True,
            }

    def two(_):
        with RequestContextVar(request=_):
            request.session["key-1"] = "value-12"
            request.session["key-2"] = "value-22"
            assert request.session.dict() == {
                "id": "123",
                "attributes": {"key-1": "value-12", "key-2": "value-22"},
                "new": True,
            }

    req = create_request(
        "TELEKOM_Demo_Intent", session={"key-1": "value-1", "key-2": "value-2"}
    )

    await run_in_executor(init, req)
    await run_in_executor(one, req)
    await run_in_executor(init, req)
    await run_in_executor(two, req)
