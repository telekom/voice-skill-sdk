#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

#
# Requests adapters with circuit breakers
#

from typing import Tuple, Union
from urllib.parse import urlparse
import logging
import time

from requests.exceptions import RequestException
from requests.sessions import Session

from .caching.local import CacheControlLocalLRUCache
from .circuit_breaker import DEFAULT_CIRCUIT_BREAKER
from .tracing import global_tracer, Format
from .log import _trim
from .config import config
from cachecontrol.adapter import CacheControlAdapter

logger = logging.getLogger(__name__)

USE_LOCAL_SERVICES = False
DEFAULT_REQUEST_TIMEOUT = 5
DEFAULT_HTTP_CACHE = CacheControlLocalLRUCache(1000)


class BadHttpResponseCodeException(RequestException):
    """ Raised if http return status code is not in expected range """

    def __init__(self, status_code, *args, **kwargs):
        self.status_code = status_code
        super().__init__(*args, **kwargs)

    def __repr__(self):
        text = f'BadHttpResponseCodeException {self.status_code}' + (': ' + _trim(repr(self.response))
                                                                     if self.response else '')
        return text

    __str__ = __repr__


class CircuitBreakerSession(Session):
    """ Requests session with a circuit breaker """

    DEFAULT_TIMEOUT = config.get('requests', 'timeout', fallback=DEFAULT_REQUEST_TIMEOUT)

    def __init__(self, internal=False,
                 circuit_breaker=None,
                 good_codes=(),
                 bad_codes=range(400, 600),
                 cache=None,
                 timeout=None):
        Session.__init__(self)
        self.internal = internal
        self.circuit_breaker = circuit_breaker or DEFAULT_CIRCUIT_BREAKER
        self.good_codes = good_codes
        self.bad_codes = bad_codes
        if cache is None:
            cache = DEFAULT_HTTP_CACHE
        self.mount('http://', CacheControlAdapter(cache=cache))
        self.mount('https://', CacheControlAdapter(cache=cache))
        self.timeout = timeout or self.DEFAULT_TIMEOUT

    def _check_status_code(self, response):
        def _code_in(code: int, item: Union[int, range, Tuple]) -> bool:
            """ Check if code is in allowed range

            @param code:
            @param item:
            @return:
            """
            _eval = {
                'tuple': lambda i: any(_code_in(code, _) for _ in i),
                'range': lambda i: code in i,
                'int': lambda i: code == i,
            }
            return _eval.get(type(item).__name__, lambda i: False)(item)

        if self.good_codes and _code_in(response.status_code, self.good_codes):
            return

        if _code_in(response.status_code, self.bad_codes):
            raise BadHttpResponseCodeException(response.status_code, response=response)

    def request(self, method, url, **kwargs):

        kwargs.setdefault('timeout', self.timeout)

        if USE_LOCAL_SERVICES:
            host = urlparse(url).hostname
            if host.startswith('service-') and host.endswith('-service'):
                logger.debug('Settings local proxy for host %s', host)
                kwargs.update(proxies={'http': 'http://localhost:8888'})

        @self.circuit_breaker
        def _inner_call(*args, **kwargs):
            """ Wraps Session.request """
            response = Session.request(*args, **kwargs)
            logger.debug('Request headers: %s', response.request.headers)
            logger.debug('Response headers: %s', response.headers)
            self._check_status_code(response)
            return response

        operation_name = f"HTTP request ({'internal' if self.internal else 'external'})"
        with global_tracer().start_span(operation_name, tags={'http_method': method.upper(), 'http_url': url}) as span:
            if self.internal:
                logger.debug('Internal service, adding tracing headers.')
                headers = kwargs.setdefault('headers', {})
                span.tracer.inject(span.context, Format.HTTP_HEADERS, headers)

            try:
                span.set_tag('request_start', time.time())
                result = _inner_call(self, method, url, **kwargs)
                span.set_tag('request_end', time.time())
                logger.debug('HTTP completed with status code: %d', result.status_code)
                span.set_tag('http_status_code', result.status_code)
            except Exception as e:
                logger.warning('HTTP request failed with error: %s', e)
                span.log_kv({'error': str(e)})
                raise
            return result
