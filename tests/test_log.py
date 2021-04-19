#
# voice-skill-sdk
#
# (C) 2021, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#

import json
import logging
from logging import makeLogRecord, INFO
from unittest.mock import patch
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from skill_sdk import log, init_app

app = init_app()


@app.route("/test")
async def index(request: Request):
    record = makeLogRecord(
        {
            "levelno": INFO,
            "levelname": "INFO",
        }
    )
    return JSONResponse(json.loads(log.CloudGELFFormatter().format(record)))


@app.route("/log")
async def index(request: Request):
    logger = logging.getLogger(__name__)
    logger.debug("Debug message")
    return JSONResponse("ok")


client = TestClient(app)


def test_log_record():
    resp = client.get(
        "/test",
        headers={
            "x-b3-traceid": "trace-id",
            "X-B3-SpanId": "span-id",
            "X-TenantId": "tenant-id",
        },
    )

    expected = ["trace-id", "span-id", "tenant-id"]
    assert [
        v for k, v in resp.json().items() if k in ("traceId", "spanId", "tenant")
    ] == expected


def test_user_log():

    with patch.object(logging.Logger, "_log") as mock_debug:
        client.get(
            "/log",
        )
        mock_debug.assert_not_called()

        client.get(
            "/log",
            headers={
                "x-user-debug-log": "1",
            },
        )
        mock_debug.assert_called_once_with(10, "Debug message", ())
