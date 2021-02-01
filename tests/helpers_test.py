#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

#
# Test helpers
#

import csv
import yaml
import json
import gettext
import logging
import unittest
import datetime
from os import PathLike
from unittest.mock import patch, mock_open
from skill_sdk.test_helpers import create_context, invoke_intent, mock_datetime_now, set_translations, test_context
from skill_sdk.skill import intent_handler
from skill_sdk import Response, l10n

logger = logging.getLogger()


def _sniff(file_name: str or PathLike, delimiters=None):
    with open(file_name) as f:
        sample = f.read(1024)
        dialect = csv.Sniffer().sniff(sample, delimiters=delimiters or ',:;|')
        return dialect


def load_csv(file_name: str or PathLike, delimiters=None):
    """ Helper: load CSV data

    :param file_name:
    :param delimiters:
    :return:
    """
    try:
        with open(file_name) as f:
            dialect = _sniff(file_name, delimiters)
            lines = [line for line in f.readlines() if line.strip()]
            reader = csv.DictReader(lines, dialect=dialect)
            data = [{key.strip(): value.strip() for key, value in row.items()} for row in reader]
            return data

    except (OSError, FileNotFoundError, csv.Error) as e:
        logger.error(f"Can't load {file_name}: {e}")


def load(file_name: str or PathLike):
    """ Helper: load data from YAML/JSON

    :param file_name:
    :return:
    """
    try:
        with open(file_name) as f:
            data = yaml.safe_load(f)
            return data

    except (OSError, FileNotFoundError, csv.Error, yaml.YAMLError) as e:
        logger.error(f"Can't load {file_name}: {e}")


json_data = """
{
    "responseList": [
        {
            "name": "PlayBillList",
            "msg": {
                "counttotal": "1",
                "playbilllist": [
                    {
                        "id": "-1"
                    }
                ],
                "playbillVersion": [
                    {
                        "channelId": "404",
                        "date": "20180721",
                        "version": "20180725020057"
                    }
                ]
            }
        }
    ]
}
"""

yaml_data = """
    SessionRequestDto:
      properties:
        id:
          type: string
          example: '1234'
        attributes:
          type: object
        new:
          type: boolean
          example: true
      required: ['attributes', 'id', 'new']
"""

csv_data = """
        Utterance                                                             | Intent         | Program          | Skill              | Response   | Action       | State
        "Was läuft gerade auf Prosieben?"                                     | "TV__PROGRAM"  | "prosieben"      | "skill-tv-manager" | "TELL"     | "läuft"      | true
        "Was ist denn im TV morgen früh auf Prosieben zu sehen?"              | "TV__PROGRAM"  | "prosieben"      | "skill-tv-manager" | "TELL"     | "läuft"      | true
        "Was wird gleich um 6 Uhr in Arte gezeigt?"                           | "TV__PROGRAM"  | "arte"           | "skill-tv-manager" | "TELL"     | "läuft"      | true
        "Was läuft um 23 Uhr auf ARD?"                                        | "TV__PROGRAM"  | "das erste"      | "skill-tv-manager" | "TELL"     | "läuft"      | true
"""


class TestSelf(unittest.TestCase):

    @patch('builtins.open', mock_open(read_data=json_data))
    def test_test_helper_load_binary(self):
        result = load('binary.bin')
        self.assertEqual(result, json.loads(json_data))

    @patch('builtins.open', mock_open(read_data=b'\xde\x12\x04\x95\x00'))
    def test_test_helper_load_json(self):
        result = load('json.json')
        self.assertIsNone(result)

    @patch('builtins.open', mock_open(read_data=yaml_data))
    def test_test_helper_load_yaml(self):
        result = load('yaml.yml')
        self.assertEqual(result, yaml.safe_load(yaml_data))

    def test_test_helper_load_csv(self):
        with patch('builtins.open', mock_open(read_data=csv_data)):
            dialect = _sniff('csv.csv', ',:;|')
        with patch('builtins.open', mock_open(read_data=csv_data)), \
             patch(__name__ + '._sniff', return_value=dialect):
            result = load_csv('csv.csv')
            self.assertEqual(len(result), 4)
        with patch('builtins.open', side_effect=OSError):
            result = load_csv('csv.csv')
            self.assertIsNone(result)


class TestHelpers(unittest.TestCase):

    def test_invoke_intent(self):

        @intent_handler('Test_Helper_Intent')
        def decorated_test(date_str: str = None, date_date: datetime.date = None):
            return Response(f"{date_str}", date_date=date_date)

        response = invoke_intent('Test_Helper_Intent', date_str=['2001-12-31', '2001-12-31', ],
                                 date_date=['2001-12-31', '1001-12-31', ])
        self.assertEqual(response.text, '2001-12-31')
        self.assertEqual(response.result['date_date'], datetime.date(2001, 12, 31))

        with self.assertRaises(KeyError):
            invoke_intent('Test_Blah_Intent')

    def test_create_context(self):
        """ Test `create_context` helper and `test_context` manager """
        from skill_sdk.intents import context

        attr_v2 = dict(id=1, value='value', extras={}, nestedIn=[], overlapsWith=[])
        result = create_context('Test_Helper_Intent', attr=attr_v2, session={'id': '12345', 'new': False})

        self.assertEqual('Test_Helper_Intent', context.intent_name)
        self.assertEqual({'attr': ['value'], 'timezone': ['Europe/Berlin']}, result.attributes)
        self.assertEqual(attr_v2, result.attributesV2['attr'][0])

        with test_context('Another_Test_Helper_Intent', attribute=['value']):
            self.assertEqual('Another_Test_Helper_Intent', context.intent_name)

            with test_context('Third_Test_Helper_Intent', attribute='value'):
                self.assertEqual('Third_Test_Helper_Intent', context.intent_name)

            self.assertEqual('Another_Test_Helper_Intent', context.intent_name)

        self.assertEqual('Test_Helper_Intent', context.intent_name)

    def test_create_context_remove_none_values(self):
        """ Do not add "None" values to test context """

        result = create_context('Test_Helper_Intent', none_value=None)
        self.assertEqual({'timezone': [
            {'id': 0, 'value': 'Europe/Berlin', 'extras': {}, 'nestedIn': [], 'overlapsWith': []}
        ]}, result.attributesV2)

    def test_mock_datetime_now(self):
        """ Test datetime.datetime.now patch """
        with mock_datetime_now(datetime.datetime(year=9999, month=12, day=31, hour=23, minute=59), datetime):
            self.assertEqual(datetime.datetime.now(),
                             datetime.datetime(year=9999, month=12, day=31, hour=23, minute=59))
            self.assertEqual(datetime.datetime.utcnow(),
                             datetime.datetime(year=9999, month=12, day=31, hour=23, minute=59))

    def test_set_translations(self):
        """ Test set_translations helper """
        with patch.object(l10n, 'translations', {'de': None}):
            self.assertEqual(l10n.translations['de'], None)
            set_translations()
            self.assertIsInstance(l10n.translations['de'], gettext.NullTranslations)
            set_translations(l10n.Translations())
            self.assertIsInstance(l10n.translations['de'], l10n.Translations)
            set_translations({'de': l10n.Translations(), 'en': l10n.Translations()})
            self.assertIsInstance(l10n.translations['en'], l10n.Translations)
            with self.assertRaises(TypeError):
                set_translations(1)
