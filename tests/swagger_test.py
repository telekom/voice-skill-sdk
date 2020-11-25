#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#
import yaml
import unittest

import logging
from unittest.mock import patch
from datetime import timezone as tz
from skill_sdk import swagger, skill


@skill.intent_handler('HELLO_INTENT')
def hello(timezone: tz):
    pass


class TestSwagger(unittest.TestCase):

    def test_swag(self):
        swagger_json = swagger.swag('json')
        self.assertIsInstance(swagger_json, dict)
        schemas = swagger_json['components']['schemas']
        self.assertIn('SkillInfoResponseDto', schemas)
        self.assertIn('CardDto', schemas)
        self.assertIn('SessionRequestDto', schemas)
        self.assertIn('SessionResponseDto', schemas)
        self.assertIn('SkillContextDto', schemas)
        self.assertIn('InvokeSkillRequestDto', schemas)
        self.assertIn('InvokeSkillResponseDto', schemas)
        self.assertIn('PushNotificationDto', schemas)
        self.assertIn('ResultDto', schemas)

    @patch('yaml.safe_load', side_effect=yaml.YAMLError())
    @patch('builtins.open', side_effect=OSError())
    @patch.object(logging.Logger, 'error')
    def test_create_spec_os_error(self, logger, *args):
        swagger.create_spec()
        logger.assert_called_once()
