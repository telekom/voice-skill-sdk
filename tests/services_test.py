#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#
import unittest
import logging
import importlib
from unittest.mock import patch
import skill_sdk
from skill_sdk.services import setup_services
from skill_sdk.services.base import BaseService
from skill_sdk.config import Config
import requests_mock


class TestSetupServices(unittest.TestCase):

    @requests_mock.mock()
    @patch.object(logging.Logger, 'debug')
    @patch('skill_sdk.config.config', new_callable=Config)
    def test_setup_services(self, req_mock, config_mock, log_mock):
        config_mock['zipkin'] = {'sample_rate': '100'}
        config_mock['service-text'] = {'active': 'true'}
        config_mock['service-location'] = {'active': 'true'}
        with patch('skill_sdk.services.text.setup_service') as text_mock, \
                patch('skill_sdk.services.zipkin.setup_service') as zipkin_mock:

            importlib.reload(skill_sdk.entities)
            from skill_sdk.entities import Location
            loc = Location('Berlin')
            self.assertEqual(loc.coordinates, None)

            setup_services()

            text_mock.assert_called_once()
            zipkin_mock.assert_called_once()

            req_mock.get('http://service-location-service:1555/v1/location/geo', text='{"lat": 50.0, "lng": 8.0}')
            from skill_sdk.services import location
            importlib.reload(skill_sdk.services.location)
            from skill_sdk.entities import Location
            loc = Location('Berlin')
            self.assertEqual(loc.coordinates, (50, 8))

    @patch('skill_sdk.config.config', new_callable=Config)
    def test_setup_services_module_not_found(self, config_mock):
        config_mock['zipkin'] = {'sample_rate': '100'}
        config_mock['service-text'] = {'active': 'true'}
        config_mock['service-location'] = {'active': 'true'}
        config_mock['service-pronunciation'] = {'active': 'true'}
        with patch.dict('sys.modules', {'skill_sdk.services.text': None}), \
                patch.dict('sys.modules', {'skill_sdk.services.zipkin': None}), \
                patch.dict('sys.modules', {'skill_sdk.services.location': None}), \
                patch.dict('sys.modules', {'skill_sdk.services.pronunciation': None}):
            setup_services()


class TestBaseService(unittest.TestCase):

    def test_url(self):
        service = BaseService()
        service.BASE_URL = 'http://service-text-service:1555/v1/base'
        self.assertEqual(service.url, 'http://service-text-service:1555/v1/base')
        service.BASE_URL = 'http://service-text-service:1555/services/base/api/v1/'
        self.assertEqual(service.url, 'http://service-text-service:1555/services/base/api/v1')
        service.BASE_URL = 'http://service-text-service:1555/'
        self.assertEqual(service.url, 'http://service-text-service:1555/v0/base')

    def test_no_base_url(self):
        b = BaseService()
        with self.assertRaises(ValueError):
            self.assertEqual(b.url, None)
