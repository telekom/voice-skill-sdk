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
# Geolocation service
#

import json
import logging
import requests

from timezonefinder.timezonefinder import TimezoneFinder
from skill_sdk.config import config
from skill_sdk import entities
from skill_sdk.caching.decorators import CallCache
from skill_sdk.caching.local import LocalFIFOCache
from skill_sdk.services.base import BaseService
from skill_sdk.services.prometheus import partner_call, prometheus_latency

logger = logging.getLogger(__name__)
config.read_environment('SERVICE_LOCATION_URL', 'service-location', 'url')


class GeoLookupError(Exception):
    """ Thrown if reverse geo-lookup is unsuccessful """
    pass


class Location(entities.Location):
    """ Location entity:  supports geo lookup with location service

    """

    def __init__(self, location_text=None, **kwargs):
        super().__init__(location_text, **kwargs)
        self._forward_lookup_failed = False
        self._reverse_lookup_failed = False

    def _forward_geo_lookup(self):
        self._coordinates = None
        self._timezone = None

        if self._forward_lookup_failed:
            return
        if not self._text and not self._city and not self._postalcode:
            raise ValueError('Reverse lookup requires text to be set.')
        try:
            service = LocationService()
            params = self._generate_params_for_lookup()
            result = service.forward_lookup(params)
            if result:
                lat = result['lat']
                lng = result['lng']
                self._coordinates = (lat, lng)
                self._timezone = result.get('timeZone')
                self._text = result.get('address', {}).get('addressComponents', {}).get('city')
                city = result.get('address', {}).get('addressComponents', {}).get('city')
                if city is not None:
                    self._text = city
        except BaseException:
            logger.exception('Forward lookup failed.')
            self._forward_lookup_failed = True
            raise

    def _reverse_geo_lookup(self):
        if self._reverse_lookup_failed:
            return
        if not self._coordinates:
            raise ValueError('Reverse lookup requires coordinates to be set.')
        lat, lng = [str(c) for c in self._coordinates]
        try:
            service = LocationService()
            result = service.reverse_lookup(lat, lng)
            if result:
                city = result.get('addressComponents', {}).get('city')
                if city is not None:
                    self._text = city
        except BaseException:
            logger.exception('Reverse lookup failed.')
            self._reverse_lookup_failed = True
            raise

    def _generate_params_for_lookup(self):
        _params = {}
        _params.update({'text': self._text}) if self._text else None
        _params.update({'lang': self._language}) if self._language else None
        _params.update({'city': self._city}) if self._city else None
        _params.update({'country': self._country}) if self._country else None
        _params.update({'postalcode': self._postalcode}) if self._postalcode else None
        return _params

    @property
    def timezone(self):
        if self._timezone:
            return self._timezone

        tf = TimezoneFinder()
        coords = self.coordinates
        return tf.timezone_at(lng=coords[1], lat=coords[0])

    @property
    def text(self):
        if self._text:
            return self._text
        self._reverse_geo_lookup()
        if self._text:
            return self._text
        raise GeoLookupError('Could not do geocoding.')

    @property
    def coordinates(self):
        if self._coordinates:
            return self._coordinates
        self._forward_geo_lookup()
        if self._coordinates:
            return self._coordinates
        else:
            return None


class LocationService(BaseService):
    """ Location service with geo-coding """

    VERSION = 1
    NAME = 'location'

    def __init__(self):
        super().__init__(add_auth_header=config.getboolean("service-location", "auth_header", fallback=False))
        self.BASE_URL = f'{config.get("service-location", "url", fallback="http://service-location-service:1555")}'

    @prometheus_latency('service-location.forward_lookup')
    @CallCache([LocalFIFOCache(max_size=100)])
    def forward_lookup(self, location_params):
        url = f'{self.url}/geo'
        with self.session as session:
            try:
                with partner_call(session.get, LocationService.NAME) as get:
                    result = get(url, params=location_params, headers=self._headers())
                return result.json()
            except (json.decoder.JSONDecodeError, requests.exceptions.RequestException) as ex:
                logger.error(f"{self.url}/geo?{location_params} responded with error: {ex}")
                if isinstance(ex, requests.exceptions.RequestException):
                    raise

    @prometheus_latency('service-location.reverse_lookup')
    @CallCache([LocalFIFOCache(max_size=100)])
    def reverse_lookup(self, latitude, longitude):
        url = f'{self.url}/reversegeo'
        params = {'lat': latitude, 'lng': longitude}
        with self.session as session:
            try:
                with partner_call(session.get, LocationService.NAME) as get:
                    result = get(url, params=params, headers=self._headers())
                return result.json()
            except (json.decoder.JSONDecodeError, requests.exceptions.RequestException) as ex:
                logger.error(f"{self.url}/reversegeo?{params} responded with error: {ex}")
                if isinstance(ex, requests.exceptions.RequestException):
                    raise


def setup_service():
    """ Replace skill_sdk.entities.Location with current implementation

    :return:
    """
    entities.Location = Location
