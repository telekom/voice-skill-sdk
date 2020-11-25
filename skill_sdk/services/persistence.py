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
# Persistence service
#

import json
import logging
from functools import partial
from typing import Dict, Optional
import requests
from skill_sdk.config import config
from skill_sdk.requests import CircuitBreakerSession
from skill_sdk.services.prometheus import prometheus_latency, partner_call
from skill_sdk.services.base import BaseService

PARSE_EXCEPTION = "%s responded with error. Data not available: %s"
REQUEST_EXCEPTION = "%s did not respond: %s"

DEFAULT_SERVICE_TIMEOUT = 10
logger = logging.getLogger(__name__)
config.read_environment('SERVICE_PERSISTENCE_URL', 'service-persistence', 'url')


class Hasher(dict):
    """ A wrapper around `dict` to allow safely traversing a dictionary:
            so you can traverse it like `d['key1']['key2']` or `d.get('a').get('b')`
            without raising KeyError or AttributeError

            TODO: Clarify if still needed

    """
    def __missing__(self, key):
        """ Return empty Hasher if key missing """
        return Hasher()

    def get(self, key, default=None):
        """ Set default to return Hasher instance """
        default = default or Hasher()
        return super().get(key, default)


class PersistenceService(BaseService):
    """ Persistence service: a simple key-value store """

    VERSION = 1
    NAME = 'persistence'

    def __init__(self):
        super().__init__(add_auth_header=True)
        self.BASE_URL = config.get("service-persistence", "url", fallback="http://service-persistence-service:1555")
        self.id = config.get('skill', 'id', fallback=config.get('skill', 'name'))

    @property
    def session(self):
        """ Persistence service returns HTTP 404 if there is no skill data available
            To workaround this behaviour, make 404 a non-failure code

        """

        _session = CircuitBreakerSession(internal=True,
                                         circuit_breaker=self.CIRCUIT_BREAKER,
                                         good_codes=(range(200, 400), 404))

        _session.request = partial(_session.request, headers=self._headers(), timeout=self.timeout)
        return _session

    @property
    def timeout(self):
        return config.get("service-persistence", "timeout", fallback=DEFAULT_SERVICE_TIMEOUT)

    def _get(self, url: str) -> Hasher:
        """ Read the data

        @param url:
        :return:        Hasher instance
        """
        result = Hasher()
        _url = '/'.join((self.url, url.strip('/\\')))
        with self.session as session:
            try:
                with partner_call(session.get, PersistenceService.NAME) as get:
                    data = get(_url).json()
                    result = Hasher(data)

            except (KeyError, json.decoder.JSONDecodeError) as ex:
                logger.error(PARSE_EXCEPTION, _url, ex)
            except requests.exceptions.RequestException as ex:
                logger.error(REQUEST_EXCEPTION, _url, ex)
            return result

    @prometheus_latency('service-persistence.get')
    def get(self) -> Hasher:
        """ Read the skill data

        :return:        Hasher instance
        """
        return self._get("entry/data")

    @prometheus_latency('service-persistence.get_all')
    def get_all(self) -> Hasher:
        """ Read all the data

        :return:        Hasher instance
        """
        return self._get("entry")

    @prometheus_latency('service-persistence.set')
    def set(self, data: Dict) -> Optional[requests.Response]:
        """ Update/Insert the data

        :param data:    data
        :return:
        """
        response = None

        with self.session as session:
            try:
                with partner_call(session.post, PersistenceService.NAME) as post:
                    response = post(f"{self.url}/entry", json=dict(data=data))

            except requests.exceptions.RequestException as ex:
                logger.error(REQUEST_EXCEPTION, self.url, ex)
            return response

    @prometheus_latency('service-persistence.delete')
    def delete(self) -> Optional[requests.Response]:
        """ Delete all data

        :param context:
        :return:
        """
        response = None
        with self.session as session:
            try:
                with partner_call(session.delete, PersistenceService.NAME) as delete:
                    response = delete(f"{self.url}/entry")

            except requests.exceptions.RequestException as ex:
                logger.error(REQUEST_EXCEPTION, self.url, ex)
            return response

    read = get

    update = set
