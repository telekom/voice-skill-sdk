#
# voice-skill-sdk
#
# (C) 2021, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

"""HTTP sync/async clients with circuit breaker"""

from typing import Callable, Iterable, List, Union
import logging
from warnings import warn

import httpx
from httpx import codes, HTTPError, Response  # noqa

from aiobreaker import (
    CircuitBreaker,
    CircuitBreakerState,  # noqa
)

from skill_sdk.config import settings
from skill_sdk.log import tracing_headers

logger = logging.getLogger(__name__)

DEFAULT_REQUESTS_TIMEOUT = settings.REQUESTS_TIMEOUT


class Client(httpx.Client):
    """
    Sync HTTP client with a circuit breaker
    """

    def __init__(
        self,
        *,
        internal: bool = False,
        circuit_breaker: CircuitBreaker = None,
        timeout: Union[int, float] = None,
        exclude: Iterable[codes] = None,
        response_hook: Callable[[httpx.Response], None] = None,
        **kwargs,
    ) -> None:
        """
        Construct sync client

        :param internal:        identifies a request to an internal service
                                propagate the tracing headers, if the request is internal

        :param circuit_breaker: optional circuit breaker, DEFAULT_CIRCUIT_BREAKER if not set
        :param timeout:         optional timeout for a request
        :param exclude:         list of HTTP status codes that are treated as "normal" (no exception is raised)
        :param response_hook:   function to be executed after a response is received (with response as argument)
        :param kwargs:          keyword arguments passed over to request
        """
        self.internal = internal

        # If no custom circuit breaker supplied, we'll create a new instance
        self.circuit_breaker = circuit_breaker or CircuitBreaker()

        self.exclude = tuple(exclude) if exclude else ()
        super().__init__(timeout=timeout or DEFAULT_REQUESTS_TIMEOUT, **kwargs)
        if response_hook:
            self.event_hooks = dict(response=[response_hook])

    def request(
        self,
        *args,
        exclude: Iterable[codes] = None,
        **kwargs,
    ):
        exclude = exclude or self.exclude

        # Propagate tracing headers if request is created as "internal"
        if self.internal:
            logger.debug("Internal service, adding tracing headers.")
            kwargs["headers"] = {
                **(kwargs.get("headers", None) or {}),
                **tracing_headers(),
            }

        @self.circuit_breaker
        def _inner_call(*a, **kw):
            """Wraps Client.request"""
            _r = super(Client, self).request(*a, **kw)

            if _r.status_code in exclude:
                logger.debug("Status code %s is excluded", _r.status_code)
            else:
                _r.raise_for_status()

            return _r

        try:
            result = _inner_call(*args, **kwargs)
            logger.debug("HTTP completed with status code: %d", result.status_code)

        except HTTPError as e:
            logger.error(
                "HTTP request [%s, %s] failed with error: %s",
                repr(args),
                repr(kwargs),
                repr(e),
            )
            raise
        return result


class AsyncClient(httpx.AsyncClient):
    """
    Async client with a circuit breaker
    """

    def __init__(
        self,
        *,
        internal: bool = False,
        circuit_breaker: CircuitBreaker = None,
        timeout: Union[int, float] = None,
        exclude: List[codes] = None,
        response_hook: Callable[[httpx.Response], None] = None,
        **kwargs,
    ) -> None:
        """
        Construct sync client

        :param internal:        identifies a request to an internal service
                                propagate the tracing headers, if the request is internal

        :param circuit_breaker: optional circuit breaker, DEFAULT_CIRCUIT_BREAKER if not set
        :param timeout:         optional timeout for a request
        :param exclude:         list of HTTP status codes that are treated as "normal" (no exception is raised)
        :param response_hook:   function to be executed after a response is received (with response as argument)
        :param kwargs:          keyword arguments passed over to request
        """
        self.internal = internal

        # If no custom circuit breaker supplied, we'll create a new instance
        self.circuit_breaker = circuit_breaker or CircuitBreaker()

        self.exclude = tuple(exclude) if exclude else ()
        super().__init__(timeout=timeout or DEFAULT_REQUESTS_TIMEOUT, **kwargs)
        if response_hook:
            self.event_hooks = dict(response=[response_hook])

    async def request(
        self,
        *args,
        exclude: Iterable[codes] = None,
        **kwargs,
    ):
        exclude = exclude or self.exclude

        # Propagate tracing headers if request is created as "internal"
        if self.internal:
            logger.debug("Internal service, adding tracing headers.")
            kwargs["headers"] = {
                **(kwargs.get("headers", None) or {}),
                **tracing_headers(),
            }

        @self.circuit_breaker
        async def _inner_call(*a, **kw):
            """Wraps Client.request"""
            _r = await super(AsyncClient, self).request(*a, **kw)

            if _r.status_code in exclude:
                logger.debug("Status code %s is excluded", _r.status_code)
            else:
                _r.raise_for_status()

            return _r

        try:
            result = await _inner_call(*args, **kwargs)
            logger.debug("HTTP completed with status code: %d", result.status_code)

        except HTTPError as e:
            logger.error(
                "HTTP request [%s, %s] failed with error: %s",
                repr(args),
                repr(kwargs),
                repr(e),
            )
            raise
        return result


class CircuitBreakerSession(Client):
    """**DEPRECATED**: HTTP(s) session with a circuit breaker.

    Renamed to `skill_sdk.requests.Client`
    The name is left for backward compatibility

    """

    def __init__(self, *args, **kwargs) -> None:
        warn(
            '"requests.CircuitBreakerSession" is deprecated.\n'
            'Please use "requests.Client" if you need a circuit breaker or "httpx.Client" if not.',
            DeprecationWarning,
            stacklevel=2,
        )

        super().__init__(*args, **kwargs)
