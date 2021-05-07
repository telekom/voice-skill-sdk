#
# voice-skill-sdk
#
# (C) 2021, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

import json
import asyncio
import datetime
from datetime import date

import pytest
from fastapi.testclient import TestClient

from skill_sdk.skill import init_app
from skill_sdk import ui, util


LOCALHOST = "http://localhost"


@pytest.fixture
def client():
    app = init_app(develop=True)
    return TestClient(app)


def test_list_intents_empty(client):
    r = client.get("/intents")
    assert r.status_code == 200
    assert r.json() == []


def test_models(monkeypatch):
    param = ui.Parameter(**dict(name="Parameter", type="str", values=None))
    assert json.loads(param.json()) == {
        "name": "Parameter",
        "type": "str",
        "required": False,
        "sample": None,
        "values": [],
    }

    intent = ui.Intent(**dict(name="Intent"))
    assert json.loads(intent.json()) == {
        "name": "Intent",
        "implementation": ["impl", "handle_Intent"],
        "parameters": [],
    }

    def handle(i: int, t: str, f: float, dt: date):
        ...

    with util.mock_date_today(datetime.date(2100, 12, 31)):
        intent = ui.Intent.from_callable("Test_Intent", handle)
    assert json.loads(intent.json()) == {
        "name": "Test_Intent",
        "implementation": ["test_ui", "handle"],
        "parameters": [
            {"name": "i", "type": "int", "required": True, "sample": 42, "values": []},
            {
                "name": "t",
                "type": "str",
                "required": True,
                "sample": "string value",
                "values": [],
            },
            {
                "name": "f",
                "type": "float",
                "required": True,
                "sample": 42.0242,
                "values": [],
            },
            {
                "name": "dt",
                "type": "date",
                "required": True,
                "sample": "2100-12-31",
                "values": [],
            },
        ],
    }


def test_list_intents(client):
    @client.app.intent_handler("Test_Intent")
    def handle(i: int, t: str, f: float, dt: date):
        ...

    r = client.get("/intents")
    assert r.status_code == 200
    assert r.json() == [
        {
            "name": "Test_Intent",
            "implementation": ["test_ui", "handle"],
            "parameters": [
                {
                    "name": "i",
                    "type": "int",
                    "required": True,
                    "sample": ui.samples("int"),
                    "values": [],
                },
                {
                    "name": "t",
                    "type": "str",
                    "required": True,
                    "sample": ui.samples("str"),
                    "values": [],
                },
                {
                    "name": "f",
                    "type": "float",
                    "required": True,
                    "sample": ui.samples("float"),
                    "values": [],
                },
                {
                    "name": "dt",
                    "type": "date",
                    "required": True,
                    "sample": str(ui.samples("date")),
                    "values": [],
                },
            ],
        }
    ]


def test_list_types(client):

    assert client.get("/types").json() == [
        "bool",
        "int",
        "float",
        "complex",
        "str",
        "timedelta",
        "datetime",
        "date",
        "time",
        "TimeRange",
        "TimeSet",
        "AttributeV2",
        "typing.List[str]",
    ]


def test_worker_attach(mocker, client):

    # Workaround for Python 3.7 that has no AsyncMock
    worker_mock = mocker.patch.object(
        ui.notifier, "worker", return_value=asyncio.Future()
    )
    with client:
        worker_mock.assert_called_once()

    with client:
        with client.websocket_connect("/logs") as websocket:
            # TODO:
            pass
