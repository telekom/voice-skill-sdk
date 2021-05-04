#
# voice-skill-sdk
#
# (C) 2021, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#

"""Base for internal services"""

import logging
from typing import Dict, Text

from aiobreaker import CircuitBreaker

from skill_sdk.intents import r
from skill_sdk.requests import AsyncClient, Client

logger = logging.getLogger(__name__)

DEFAULT_AUTH_TOKEN = "cvi"

# Default timeout when accessing the service
DEFAULT_SERVICE_TIMEOUT = 10


class BaseService:
    """
    The base for cloud services

    """

    # Service version
    VERSION: int = 0

    # Service name
    NAME: Text = "base"

    # Circuit breaker: shared between client instances
    circuit_breaker: CircuitBreaker

    # Base service URL
    url: Text = ""

    # Timeout value
    timeout: float = DEFAULT_SERVICE_TIMEOUT

    #
    # Specifies if authorization header should be added to the request
    #
    add_auth_header: bool = True

    def __init__(
        self,
        url: Text,
        *,
        internal: bool = True,
        timeout: float = DEFAULT_SERVICE_TIMEOUT,
        headers: Dict[Text, Text] = None,
        add_auth_header: bool = None,
        auth_token: Text = DEFAULT_AUTH_TOKEN,
    ) -> None:
        self.url = url
        self.internal = internal
        self.timeout = timeout
        self.auth_token = auth_token
        self._headers = headers or {}

        # `True` for internal services, `False` for external, unless specified explicitly
        self.add_auth_header = (
            add_auth_header if add_auth_header is not None else internal
        )

        # circuit breaker with defaults: (fail_max=5, timeout_duration=60 sec)
        self.circuit_breaker = CircuitBreaker()

    def auth_header(self):
        """Add "Authorization" header for bearer auth

        :return:
        """

        # Get CVI token from current request
        try:
            token = r.context.tokens[self.auth_token]
            logger.debug("Adding auth token to authorization header.")
            return {"Authorization": f"Bearer {token}"}
        except (AttributeError, KeyError):
            logger.error(
                "No auth token %s found in the current request.", repr(self.auth_token)
            )
            return {}

    @property
    def headers(self) -> Dict:

        # Default request headers
        _headers: Dict[Text, Text] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        # If inside a request, add "Content-Language"
        if r and r.context:
            _headers.update({"Content-Language": r.context.locale})

        # Add "Authorization" header if requested
        if self.add_auth_header:
            _headers.update(self.auth_header())

        _headers.update(self._headers)

        logger.debug("Client headers: %s", repr(_headers))
        return _headers

    @property
    def client(self) -> Client:
        """Creates new client with circuit breaker"""

        return Client(
            internal=self.internal,
            base_url=self.url,
            headers=self.headers,
            timeout=self.timeout,
            circuit_breaker=self.circuit_breaker,
        )

    @property
    def async_client(self) -> AsyncClient:
        """Creates new async client with circuit breaker"""

        return AsyncClient(
            internal=self.internal,
            base_url=self.url,
            headers=self.headers,
            timeout=self.timeout,
            circuit_breaker=self.circuit_breaker,
        )
