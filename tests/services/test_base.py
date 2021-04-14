#
# voice-skill-sdk
#
# (C) 2021, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

import respx
import pytest
from httpx import Response

from skill_sdk.services.base import BaseService, DEFAULT_AUTH_TOKEN

SERVICE_URL = "http://base-service:1555/v1/base/"
SERVICE_RESPONSE = {"hello": "Hello, World!"}


@respx.mock
@pytest.mark.asyncio
async def test_base_response():
    route = respx.get(SERVICE_URL).mock(
        return_value=Response(200, json=SERVICE_RESPONSE)
    )

    async with BaseService(SERVICE_URL).async_client as client:
        response = await client.get("")
        assert route.called
        assert response.json() == SERVICE_RESPONSE
        assert response.request.headers["Accept"] == "application/json"
        assert response.request.headers["Content-Type"] == "application/json"


@respx.mock
@pytest.mark.asyncio
async def test_auth_headers():
    from skill_sdk.util import test_request

    route = respx.get(SERVICE_URL).mock(
        return_value=Response(200, json=SERVICE_RESPONSE)
    )

    with test_request("", tokens={DEFAULT_AUTH_TOKEN: "eyJ"}):
        async with BaseService(SERVICE_URL).async_client as client:
            response = await client.get("")
            assert route.called
            assert response.json() == SERVICE_RESPONSE
            assert response.request.headers["Authorization"] == "Bearer eyJ"


@respx.mock
@pytest.mark.asyncio
async def test_circuit_breaker():
    from aiobreaker import CircuitBreakerState

    route = respx.get(SERVICE_URL).mock(return_value=Response(500))
    service = BaseService(SERVICE_URL)
    with service.client as c:
        fail_max = c.circuit_breaker.fail_max
        for _ in range(fail_max * 10):
            with pytest.raises(Exception):
                c.get(SERVICE_URL)
        assert c.circuit_breaker.state.state == CircuitBreakerState.OPEN
        assert route.call_count == fail_max

    route.reset()
    with service.client as c:
        with pytest.raises(Exception):
            c.get(SERVICE_URL)
        assert not route.called
