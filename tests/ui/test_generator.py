#
# voice-skill-sdk
#
# (C) 2021, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

import sys
import datetime
import pathlib
from distutils.dir_util import copy_tree

import pytest
from fastapi.testclient import TestClient

from skill_sdk import cli, util, ui

OK = "Ok"
APP = "app:app"
HERE = pathlib.Path(__file__).parent
LOCALHOST = "http://localhost"
MOCK_DATE = datetime.date(2100, 12, 31)
INTENTS = [
    {
        "name": "Test_Intent",
        "implementation": ["impl", "handle_test_intent"],
        "parameters": [
            {
                "name": "name",
                "type": "str",
                "required": False,
                "sample": "string value",
                "values": ["World"],
            }
        ],
    },
    {
        "name": "Another_Test_Intent",
        "implementation": ["impl", "handle_another_test_intent"],
        "parameters": [
            {
                "name": "date",
                "type": "date",
                "required": True,
                "sample": MOCK_DATE.isoformat(),
                "values": [],
            },
            {
                "name": "name",
                "type": "str",
                "required": False,
                "sample": "string value",
                "values": ["World"],
            },
        ],
    },
]


@pytest.fixture
def app(tmp_path, monkeypatch):
    skill_path = HERE / "skill"
    copy_tree(str(skill_path), str(tmp_path))
    monkeypatch.chdir(tmp_path)
    module, app = cli.import_module_app(APP)
    yield app
    app.close()

    # Cleanup: remove imported modules
    del sys.modules["app"]
    del sys.modules["impl"]


def test_parameters():
    assert ui.Parameter(name="date", type="date", required=True).as_code == "date: date"
    assert (
        ui.Parameter(name="string", type="str", required=False).as_code
        == "string: str = None"
    )
    assert (
        ui.Parameter(name="attr", type="AttributeV2", required=True).as_code
        == "attr: AttributeV2"
    )

    first, second = ui.Intent.parse_obj(INTENTS[0]), ui.Intent.parse_obj(INTENTS[1])
    assert first.parameters[0].as_code == 'name: str = "World"'
    assert second.parameters[0].as_code == "date: date"


def test_render():
    intents = [ui.Intent.parse_obj(_) for _ in INTENTS]

    impl = HERE / "skill" / "impl"
    assert ui.render_impl(intents) == (impl / "__init__.py").read_text()
    assert ui.render_tests(intents) == (impl / "test.py").read_text()
    assert ui.render_runner(intents) == (HERE / "skill" / "app.py").read_text()


def test_render_handlers(app):
    client = TestClient(app)
    with util.mock_date_today(MOCK_DATE):
        r = client.get(f"{LOCALHOST}/intents")
        assert r.json() == INTENTS

    response = client.post(f"{LOCALHOST}/intents", json=INTENTS).json()
    assert all(("impl" in response, "tests" in response, "runner" in response))
