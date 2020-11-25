#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#
import logging
import unittest
from unittest.mock import patch

from configparser import ConfigParser
from skill_sdk import l10n
from skill_sdk.requests import BadHttpResponseCodeException
from skill_sdk.services.location import Location
import requests_mock

l10n.translations = {'de': l10n.Translations()}


class TestEntityLocation(unittest.TestCase):

    @requests_mock.mock()
    def test_coordinates_lookup_failed(self, req_mock):
        loc = Location('some place')
        loc._forward_lookup_failed = True
        self.assertIsNone(loc.coordinates)

    @requests_mock.mock()
    def test_forward_geo_lookup_ok(self, req_mock):
        req_mock.get('http://service-location-service:1555/v1/location/geo',
                     text='{"lat": 50.0, "lng": 8.0}')
        loc = Location('some place')
        result = loc._forward_geo_lookup()
        self.assertEqual(result, None)
        self.assertEqual(loc._coordinates, (50.0, 8.0))

    @requests_mock.mock()
    def test_forward_geo_lookup_bad_data(self, req_mock):
        req_mock.get('http://service-location-service:1555/v1/location/geo',
                     text='{}')
        loc = Location('some place')
        self.assertEqual(loc._text, 'some place')
        loc = Location(language='de')
        with self.assertRaises(ValueError):
            loc._forward_geo_lookup()

    @requests_mock.mock()
    def test_forward_geo_lookup_not_valid_json(self, req_mock):
        req_mock.get('http://service-location-service:1555/v1/location/geo',
                     text='not a json')
        loc = Location('some place')
        loc._forward_geo_lookup()
        self.assertEqual(loc._text, 'some place')

    @requests_mock.mock()
    def test_forward_geo_lookup_server_error(self, req_mock):
        req_mock.get('http://service-location-service:1555/v1/location/geo',
                     status_code=500)
        loc = Location('some place')
        with self.assertRaises(BadHttpResponseCodeException):
            loc._forward_geo_lookup()

    def test_reverse_geo_lookup_failed_before(self):
        loc = Location(coordinates=(50.0, 8.0))
        loc._reverse_lookup_failed = True
        result = loc._reverse_geo_lookup()
        self.assertEqual(result, None)
        self.assertEqual(loc._text, None)

    def test_reverse_geo_lookup_no_coordinates(self):
        loc = Location('some place')
        with self.assertRaises(ValueError):
            loc._reverse_geo_lookup()

    @requests_mock.mock()
    def test_reverse_geo_lookup_ok(self, req_mock):
        req_mock.get('http://service-location-service:1555/v1/location/reversegeo',
                     text='{"addressComponents": {"city": "some place"}}')
        loc = Location(coordinates=(50.0, 8.0))
        result = loc._reverse_geo_lookup()
        self.assertEqual(result, None)
        self.assertEqual(loc._text, 'some place')

    @requests_mock.mock()
    def test_reverse_geo_lookup_bad_data(self, req_mock):
        req_mock.get('http://service-location-service:1555/v1/location/reversegeo',
                     text='{"addressComponents": {}}')
        loc = Location(coordinates=(50.0, 8.0))
        result = loc._reverse_geo_lookup()
        self.assertIsNone(loc._text)

    @requests_mock.mock()
    @patch.object(logging.Logger, 'error')
    def test_reverse_geo_lookup_server_error(self, req_mock, log_mock):
        req_mock.get('http://service-location-service:1555/v1/location/reversegeo',
                     text='{}', status_code=500)
        loc = Location(coordinates=(50.0, 8.0))
        with self.assertRaises(BadHttpResponseCodeException):
            loc._reverse_geo_lookup()
        req_mock.get('http://service-location-service:1555/v1/location/reversegeo',
                     text='not a json')
        loc = Location('some place', coordinates=(50.0, 8.0))
        loc._reverse_geo_lookup()
        self.assertEqual(loc._text, 'some place')

    def test_text_present(self):
        self.assertEqual(Location('some place').text, 'some place')

    @requests_mock.mock()
    def test_text_coordinates(self, req_mock):
        req_mock.get('http://service-location-service:1555/v1/location/reversegeo',
                     text='{"addressComponents": {"city": "some place"}}')
        self.assertEqual(Location(coordinates=(50.0, 8.0)).text, 'some place')

    def test_text_lookup_failed(self):
        loc = Location(coordinates=(50.0, 8.0))
        loc._reverse_lookup_failed = True
        from skill_sdk.services.location import GeoLookupError
        with self.assertRaises(GeoLookupError):
            loc.text

    def test_coordinates_present(self):
        self.assertEqual(Location(coordinates=(50.0, 8.0)).coordinates, (50.0, 8.0))

    @requests_mock.mock()
    def test_coordinates_text(self, req_mock):
        req_mock.get('http://service-location-service:1555/v1/location/geo',
                     text='''{
                     "lat": 50.0,
                     "lng": 8.0,
                     "timeZone": "Europe/Berlin",
                     "location":{
                        "addressComponents": {"city": "some place"}
                     }}''')
        self.assertEqual(Location('some place').coordinates, (50.0, 8.0))

    @requests_mock.mock()
    def test_timezone_with_data_from_location_service(self, req_mock):
        req_mock.get('http://service-location-service:1555/v1/location/geo',
                     text='{"lat": 50.0, "lng": 8.0, "timeZone": "Europe/Berlin", "address":{"addressComponents": {"city": "some place"}}}')
        loc = Location('some place')
        loc._forward_geo_lookup()
        self.assertEqual(loc.timezone, 'Europe/Berlin')
        self.assertEqual(loc.text, 'some place')

    @requests_mock.mock()
    def test_timezone_with_no_data_from_location_service(self, req_mock):
        req_mock.get('http://service-location-service:1555/v1/location/geo',
                     text='{"lat": 50.0, "lng": 8.0}')
        loc = Location('some place')
        loc._forward_geo_lookup()
        self.assertEqual(loc.timezone, 'Europe/Berlin')

    @patch.object(logging.Logger, 'debug')
    @patch('skill_sdk.services.location.config', new_callable=ConfigParser)
    @patch('skill_sdk.services.location.LocationService.session')
    @patch('skill_sdk.services.base.request')
    def test_auth_header(self, req_mock, session_mock, config_mock, log_mock):
        config_mock['service-location'] = {'auth_header': 'true'}
        req_mock.json = {"context": {
            "attributes": {'location': 'Berlin'},
            "intent": "TELEKOM_Demo_Intent",
            "locale": "de",
            "tokens": {"cvi": "eyJ123"},
            "clientAttributes": {}
        }}
        loc = Location('some place')
        coordinates = loc.coordinates
        log_mock.assert_called_with('Adding CVI token to authorization header.')
        session_mock.__enter__().get.assert_called_once_with(
            'http://service-location-service:1555/v1/location/geo',
            headers={'Accept': 'application/json', 'Content-Type': 'application/json', 'Authorization': 'Bearer eyJ123'},
            params={'text': 'some place'})
