#
# voice-skill-sdk
#
# (C) 2021, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#

import asyncio
import unittest

import pytest
from fastapi.testclient import TestClient
from skill_sdk import init_app
from skill_sdk.util import camel_to_snake, snake_to_camel, Server, run_until_complete


class TestUtils(unittest.TestCase):
    def test_snake_to_camel(self):
        self.assertEqual(snake_to_camel("abc"), "abc")
        self.assertEqual(snake_to_camel("a_b_c"), "aBC")
        self.assertEqual(snake_to_camel("ab_2"), "ab2")
        self.assertEqual(snake_to_camel("a_bc"), "aBc")
        self.assertEqual(snake_to_camel("snake_case"), "snakeCase")
        with self.assertRaises(TypeError):
            snake_to_camel(123)

    def test_camel_to_snake(self):
        self.assertEqual(camel_to_snake("Simple"), "simple")
        self.assertEqual(camel_to_snake("SnakeCase"), "snake_case")
        with self.assertRaises(TypeError):
            snake_to_camel(123)

    def test_camel_to_camel(self):
        """
        Make sure camelCased attribute names remain camelCased

        @return:
        """
        self.assertEqual("camelCase", snake_to_camel("camelCase"))

    def test_run_async_from_sync(self):
        assert run_until_complete(async_sleep())


def test_server_run_in_thread():
    app = init_app()
    client = TestClient(app)

    with Server(app).run_in_thread():
        openapi = client.get("/openapi.json").json()
        assert openapi["info"] == {
            "title": "skill-noname",
            "description": "Magenta Voice Skill SDK for Python",
            "version": "1",
        }


async def async_sleep():
    await asyncio.sleep(0.1)
    return True


def test_run_async_from_sync():
    assert asyncio.iscoroutine(async_sleep())
    assert run_until_complete(async_sleep())


@pytest.mark.asyncio
async def test_run_sync_from_async():
    assert await async_sleep()
    # This would raise "RuntimeError: This event loop is already running"
    assert run_until_complete(async_sleep())
