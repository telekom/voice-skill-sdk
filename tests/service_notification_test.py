#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#
import json
import uuid
import datetime
import logging
import unittest
from typing import Dict
from skill_sdk.test_helpers import create_context
from skill_sdk.services.notification import Notification, NotificationService, MalformedResponseException
import requests_mock
import requests

notification = """
{
    "id": "45e37e4b-4b2c-42a6-9e3c-21c973f40e0d",
    "provider": "telephony",
    "addUpText": "CALLHISTORY_NOTIFICATION_TEXT",
    "mode": "push_soft",
    "read": false,
    "providerEnablerSetting": null
}
"""

all_notifications = """
[
    {
        "id": "45e37e4b-4b2c-42a6-9e3c-21c973f40e0d",
        "provider": "telephony",
        "addUpText": "CALLHISTORY_NOTIFICATION_TEXT",
        "mode": "push_soft",
        "read": false,
        "providerEnablerSetting": null
    },
    {
        "id": "ca1d8fbc-9ce9-4146-9234-fc6a57422319",
        "provider": "telephony",
        "addUpText": "CALLHISTORY_NOTIFICATION_TEXT",
        "mode": "push_soft",
        "read": true,
        "providerEnablerSetting": null
    }
]
"""

logger = logging.getLogger()

UUID_ZERO = uuid.UUID(int=0)
SERVICE_URL = 'http://service-notification-service:1555/v1/notification'
SERVICE_URL_ITEM = f'http://service-notification-service:1555/v1/notification/{UUID_ZERO}'
SERVICE_URL_PROVIDER = 'http://service-notification-service:1555/v1/notification?provider=unnamed-skill'


class TestNotification(unittest.TestCase):

    def test_notification(self):
        n = Notification.construct(**{'addUpText': 'CALLHISTORY_NOTIFICATION_TEXT', 'provider': 'callhistory'})
        self.assertEqual(n.add_up_text, 'CALLHISTORY_NOTIFICATION_TEXT')
        self.assertEqual(n.provider, 'callhistory')
        self.assertEqual(n.mode, 'push_soft')
        self.assertEqual(n.read, False)
        self.assertIsNone(n.id)
        self.assertEqual(repr(n),
                         'Notification(add_up_text=\'CALLHISTORY_NOTIFICATION_TEXT\', '
                         'provider=\'callhistory\', mode=<NotificationMode.push_soft: \'push_soft\'>, '
                         'valid_by=datetime.datetime(9999, 12, 31, 23, 59, 59, 999999), '
                         'provider_enabler_setting=None, read=False, id=None)')
        self.assertEqual(n.dict(), {
            'addUpText': 'CALLHISTORY_NOTIFICATION_TEXT',
            'provider': 'callhistory',
            'mode': 'push_soft',
            'validBy': '9999-12-31 23:59:59.999999',
            'read': 'False'})


class TestNotificationService(unittest.TestCase):

    ctx = create_context('INTENT')

    @requests_mock.mock()
    def test_persistence_get(self, mocker):
        mocker.get(SERVICE_URL_PROVIDER, text=all_notifications)

        service = NotificationService()
        result = service.get()
        self.assertIsInstance(result, Dict)
        self.assertEqual(result, {
            '45e37e4b-4b2c-42a6-9e3c-21c973f40e0d': Notification(
                add_up_text='CALLHISTORY_NOTIFICATION_TEXT',
                provider='telephony', mode='push_soft',
                valid_by=datetime.datetime(9999, 12, 31, 23, 59, 59, 999999),
                provider_enabler_setting=None, read=False,
                id='45e37e4b-4b2c-42a6-9e3c-21c973f40e0d'),
            'ca1d8fbc-9ce9-4146-9234-fc6a57422319': Notification(
                add_up_text='CALLHISTORY_NOTIFICATION_TEXT',
                provider='telephony', mode='push_soft',
                valid_by=datetime.datetime(9999, 12, 31, 23, 59, 59, 999999),
                provider_enabler_setting=None, read=True,
                id='ca1d8fbc-9ce9-4146-9234-fc6a57422319')
        })

    @requests_mock.mock()
    def test_persistence_get_invalid_data(self, mocker):
        mocker.get(SERVICE_URL_PROVIDER, text=all_notifications[:50])
        with self.assertLogs(logger, level="ERROR"):
            with self.assertRaises(MalformedResponseException):
                result = NotificationService().get()

    @requests_mock.mock()
    def test_persistence_get_not_authorized(self, mocker):
        mocker.get(SERVICE_URL_PROVIDER, text='Not Authorized', status_code=401)

        with self.assertLogs(logger, level="ERROR"):
            with self.assertRaises(requests.exceptions.RequestException):
                NotificationService().get()

    @requests_mock.mock()
    def test_persistence_get_response_timeout(self, mocker):
        mocker.get(SERVICE_URL_PROVIDER, exc=requests.exceptions.ConnectTimeout)

        with self.assertLogs(logger, level="ERROR"):
            with self.assertRaises(requests.exceptions.RequestException):
                NotificationService().get()

    @requests_mock.mock()
    def test_persistence_add(self, mocker):
        mocker.post(SERVICE_URL, text=notification)
        result = Notification(add_up_text='HELLO').add()
        self.assertEqual(result, {'45e37e4b-4b2c-42a6-9e3c-21c973f40e0d': json.loads(notification)})

    @requests_mock.mock()
    def test_persistence_add_fail(self, mocker):
        mocker.post(SERVICE_URL, exc=requests.exceptions.ConnectTimeout)
        with self.assertLogs(logger, level="ERROR"):
            with self.assertRaises(requests.exceptions.ConnectTimeout):
                NotificationService().add(Notification(add_up_text='HELLO'))

        mocker.post(SERVICE_URL, text=notification[10:])
        with self.assertLogs(logger, level="ERROR"):
            with self.assertRaises(MalformedResponseException):
                NotificationService().add(Notification(add_up_text='HELLO'))

    @requests_mock.mock()
    def test_persistence_mark_read(self, mocker):
        mocker.patch(SERVICE_URL_ITEM, text="[]")
        n = Notification(add_up_text='HELLO', id=str(UUID_ZERO))
        result = n.mark_as_read()
        self.assertIsInstance(result, requests.Response)

    @requests_mock.mock()
    def test_persistence_mark_read_fail(self, mocker):
        mocker.patch(SERVICE_URL_ITEM, exc=requests.exceptions.ConnectTimeout)
        service = NotificationService()
        with self.assertLogs(logger, level="ERROR"):
            with self.assertRaises(requests.exceptions.ConnectTimeout):
                result = service.mark_as_read(UUID_ZERO)
                self.assertEqual(result, {})

    @requests_mock.mock()
    def test_persistence_delete(self, mocker):
        mocker.delete(SERVICE_URL_ITEM, text="[]")
        n = Notification(add_up_text='HELLO', id=str(UUID_ZERO))
        result = n.delete()
        self.assertIsInstance(result, requests.Response)

    @requests_mock.mock()
    def test_persistence_delete_all(self, mocker):
        mocker.delete(SERVICE_URL_PROVIDER, text="[]")
        result = NotificationService().delete()
        self.assertIsInstance(result, requests.Response)
        self.assertEqual(result.status_code, 200)

    @requests_mock.mock()
    def test_persistence_delete_fail(self, mocker):
        mocker.delete(SERVICE_URL_ITEM, exc=requests.exceptions.ConnectTimeout)
        service = NotificationService()
        with self.assertLogs(logger, level="ERROR"):
            with self.assertRaises(requests.exceptions.ConnectTimeout):
                result = service.delete(UUID_ZERO)
                self.assertEqual(result, {})
