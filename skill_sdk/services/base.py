#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#

#
# Base service
#

import logging
import pathlib
from urllib import parse
from typing import Optional
from functools import partial

from skill_sdk.circuit_breaker import SkillCircuitBreaker
from skill_sdk.requests import CircuitBreakerSession
from skill_sdk.skill import request

logger = logging.getLogger(__name__)

# Default timeout when accessing the service
DEFAULT_SERVICE_TIMEOUT = 10


class BaseService:
    """
    The base for internal services

    """

    # Service URL
    BASE_URL: Optional[str] = None

    # Service version
    VERSION: int = 0

    # Service name
    NAME: str = 'base'

    # Circuit breaker
    CIRCUIT_BREAKER = SkillCircuitBreaker()

    # Timeout value
    timeout = DEFAULT_SERVICE_TIMEOUT

    def __init__(self, add_auth_header=False, headers=None):
        self.add_auth_header = add_auth_header
        self.headers = headers or {}

    def _headers(self):
        """ Returns request headers

        :return:
        """
        if self.headers:
            # Hide tokens when logging
            stripped = {k: '*****' if isinstance(v, str) and v.lower().startswith('bearer') else v
                        for k, v in self.headers.items()}
            logger.debug(f'Additional headers: {stripped}')

        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            **self.headers
        }

        if self.add_auth_header:
            # Get CVI token from current request
            context = request.json and 'context' in request.json and request.json['context'] or {}
            tokens = context.get('tokens', {})
            cvi_token = tokens.get('cvi')
            if cvi_token:
                logger.debug('Adding CVI token to authorization header.')
                headers.update({'Authorization': f'Bearer {cvi_token}'})
            else:
                logger.error('Authorization header is requested, but no CVI token found in the current request.')

        return headers

    @property
    def url(self):
        """ Service endpoint URL """

        if not self.BASE_URL:
            raise ValueError(f'BASE_URL for Service {self.__class__.__name__} not set.')
        #
        #   Construct the service endpoint URL:
        #       - for internal service {self.BASE_URL}/v[1|2]/{self.NAME}
        #           e.g: http://http://service-text-service:8080/v1/text
        #       - via device gateway {self.BASE_URL}/v[1|2]
        #
        url = parse.urlparse(self.BASE_URL)
        path = pathlib.PurePosixPath(url.path)
        if not ('/v1' in str(path) or '/v2' in str(path)):
            path = path / f'v{self.VERSION}'
        if not (self.NAME.lower() in str(path).lower()):
            path = path / f'{self.NAME}'
        path = str(path).rstrip('/')
        return parse.urlunparse(url._replace(path=path))

    @property
    def session(self):
        """ Creates and returns new circuit breaker session """

        _session = CircuitBreakerSession(internal=True, circuit_breaker=self.CIRCUIT_BREAKER)
        _session.request = partial(_session.request, headers=self._headers(), timeout=self.timeout)
        return _session
