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
from skill_sdk.test_helpers import create_context
from skill_sdk.services.persistence import Hasher, PersistenceService
import requests_mock
import requests

PERSISTENCE_URL = 'http://service-persistence-service:1555/v1/persistence/entry'

allSkillData = """
{
    "data": {
        "attrs": {
            "attr1": "value1",
            "attr2": "value2"
        }
    }
}
"""

skillData = """
{
    "attrs": {
        "attr1": "value1",
        "attr2": "value2"
    }
}
"""

setResponse = """
{
    "id": "5c49c430bd35a20001438a7c",
    "data": {
        "attrs": {
            "attr1": "value1",
            "attr2": "value2"
        }
    }
}
"""

logger = logging.getLogger()


class TestPersistenceService(unittest.TestCase):

    ctx = create_context('INTENT')

    @requests_mock.mock()
    def test_persistence_get(self, mocker):
        mocker.get(PERSISTENCE_URL + '/data', text=skillData)

        service = PersistenceService()
        result = service.get()
        self.assertIsInstance(result, Hasher)
        self.assertEqual(result, {'attrs': {'attr1': 'value1', 'attr2': 'value2'}})

    @requests_mock.mock()
    def test_persistence_get_invalid_data(self, mocker):
        mocker.get(PERSISTENCE_URL + '/data', text=skillData[:50])

        service = PersistenceService()
        with self.assertLogs(logger, level="ERROR"):
            result = service.get()
            self.assertFalse(result)

    @requests_mock.mock()
    def test_persistence_get_not_authorized(self, mocker):
        mocker.get(PERSISTENCE_URL + '/data', text='Not Authorized', status_code=401)

        service = PersistenceService()
        with self.assertLogs(logger, level="ERROR"):
            result = service.get()
            self.assertFalse(result)

    @requests_mock.mock()
    def test_persistence_get_response_timeout(self, mocker):
        mocker.get(PERSISTENCE_URL + '/data', exc=requests.exceptions.ConnectTimeout)

        service = PersistenceService()
        with self.assertLogs(logger, level="ERROR"):
            result = service.get()
            self.assertFalse(result)

    @requests_mock.mock()
    def test_persistence_get_all(self, mocker):
        mocker.get(PERSISTENCE_URL, text=allSkillData)

        service = PersistenceService()
        result = service.get_all()
        self.assertIsInstance(result, Hasher)
        self.assertEqual(result, {'data': {'attrs': {'attr1': 'value1', 'attr2': 'value2'}}})

    @requests_mock.mock()
    def test_persistence_get_all_invalid_data(self, mocker):
        mocker.get(PERSISTENCE_URL, text=skillData[:50])

        service = PersistenceService()
        with self.assertLogs(logger, level="ERROR"):
            result = service.get_all()
            self.assertFalse(result)

    @requests_mock.mock()
    def test_persistence_get_all_request_exception(self, mocker):
        mocker.get(PERSISTENCE_URL, exc=requests.exceptions.RequestException)

        service = PersistenceService()
        with self.assertLogs(logger, level="ERROR"):
            result = service.get_all()
            self.assertFalse(result)

    @requests_mock.mock()
    def test_persistence_set(self, mocker):
        import json
        mocker.post(PERSISTENCE_URL, text=setResponse)

        service = PersistenceService()
        result = service.set(json.loads(skillData))
        self.assertIsInstance(result, requests.Response)
        self.assertEqual(result.json()['data'], json.loads(skillData))

    @requests_mock.mock()
    def test_persistence_set_wrong_order(self, mocker):
        import json
        mocker.post(PERSISTENCE_URL, text=setResponse)

        service = PersistenceService()
        result = service.set({"attr1": "value1", "attr2": "value2"})
        self.assertIsInstance(result, requests.Response)
        self.assertEqual(result.json()['data'], json.loads(skillData))

    @requests_mock.mock()
    def test_persistence_set_fail(self, mocker):
        mocker.post(PERSISTENCE_URL, exc=requests.exceptions.ConnectTimeout)

        service = PersistenceService()
        with self.assertLogs(logger, level="ERROR"):
            result = service.set(skillData)
            self.assertEqual(result, None)

    @requests_mock.mock()
    def test_persistence_delete(self, mocker):
        mocker.delete(PERSISTENCE_URL, text="[]")
        service = PersistenceService()
        result = service.delete()
        self.assertIsInstance(result, requests.Response)

    @requests_mock.mock()
    def test_persistence_delete_fail(self, mocker):
        mocker.delete(PERSISTENCE_URL, exc=requests.exceptions.ConnectTimeout)

        service = PersistenceService()
        with self.assertLogs(logger, level="ERROR"):
            result = service.delete()
            self.assertEqual(result, None)


class TestHasher(unittest.TestCase):

    def test_hasher(self):
        h = Hasher({'a': 1})
        self.assertEqual(h['a'], 1)
        self.assertFalse(h['b']['c'])
        self.assertFalse(h.get('b').get('c').get('d'))
