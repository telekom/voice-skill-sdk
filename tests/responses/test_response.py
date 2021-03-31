#
# voice-skill-sdk
#
# (C) 2021, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#

import unittest
from pydantic import ValidationError

from skill_sdk.responses import (
    ask,
    ask_freetext,
    tell,
    Card,
    CardAction,
    AudioPlayer,
    Response,
    ResponseType,
)
from skill_sdk.util import create_context
from skill_sdk.responses.task import ClientTask


class TestResponse(unittest.TestCase):
    def setUp(self):
        self.simple_response = Response("abc123", ResponseType.TELL)
        self.ask_response = Response("abc123", ResponseType.ASK)
        c = Card("SIMPLE", title_text="cardtitle", text="cardtext")
        self.card_response = Response(
            "abc123", ResponseType.TELL, card=c, result={"code": 22}
        )
        self.ctx = create_context("TELEKOM_Clock_GetTime")

    def test_init_text(self):
        self.assertEqual(self.simple_response.text, "abc123")
        self.assertEqual(self.simple_response.type, "TELL")

    def test_init_full(self):
        self.assertEqual(self.card_response.text, "abc123")
        self.assertEqual(self.card_response.type, "TELL")
        self.assertEqual(self.card_response.card.title_text, "cardtitle")
        self.assertEqual(self.card_response.result.data["code"], 22)
        self.assertEqual(self.card_response.push_notification, None)

    def test_init_bad_type(self):
        with self.assertRaises(ValueError):
            Response("abc123", "TEL")

    def test_dict_ask(self):
        response = self.ask_response.dict()
        self.assertEqual("abc123", response["text"])
        self.assertEqual("ASK", response["type"])

    def test_dict_simple(self):
        response = self.simple_response.dict()
        self.assertEqual("abc123", response["text"])
        self.assertEqual("TELL", response["type"])
        self.assertNotIn("pushNotification", response)

    def test_dict_card(self):
        response = self.card_response.dict()
        self.assertEqual(response["text"], "abc123")
        self.assertEqual(response["type"], "TELL")
        self.assertEqual(response["card"]["data"]["titleText"], "cardtitle")
        self.assertEqual(response["result"]["data"]["code"], 22)

    def test_response_with_card(self):
        response = (
            tell("Hola")
            .with_card(
                title_text="Title",
                text="Text",
                action=CardAction.INTERNAL_RESPONSE_TEXT,
            )
            .dict()
        )

        self.assertEqual(
            {
                "type": "TELL",
                "text": "Hola",
                "card": {
                    "type": "GENERIC_DEFAULT",
                    "version": 1,
                    "data": {
                        "titleText": "Title",
                        "text": "Text",
                        "action": "internal://showResponseText",
                    },
                },
            },
            response,
        )

    def test_response_with_command(self):
        response = tell("Hola").with_command(AudioPlayer.play_stream("URL")).dict()
        self.assertEqual(
            {
                "text": "Hola",
                "type": "TELL",
                "result": {
                    "data": {
                        "use_kit": {
                            "kit_name": "audio_player",
                            "action": "play_stream",
                            "parameters": {"url": "URL"},
                        }
                    },
                    "local": True,
                },
            },
            response,
        )

    def test_response_with_session(self):
        response = ask("Hola?").with_session(
            attr1="attr-1",
            attr2="attr-2",
        )
        self.assertEqual(
            {
                "text": "Hola?",
                "type": "ASK",
                "session": {"attributes": {"attr1": "attr-1", "attr2": "attr-2"}},
            },
            response.dict(),
        )
        with self.assertRaises(ValueError):
            tell("Hola").with_session(
                attr1="attr-1",
                attr2="attr-2",
            )

    def test_response_with_task(self):
        response = tell("Hola").with_task(ClientTask.invoke("WEATHER__INTENT"))
        self.assertEqual(
            {
                "type": "TELL",
                "text": "Hola",
                "result": {
                    "data": {},
                    "local": True,
                    "delayedClientTask": {
                        "invokeData": {"intent": "WEATHER__INTENT", "parameters": {}},
                        "executionTime": {
                            "executeAfter": {
                                "reference": "SPEECH_END",
                                "offset": "P0D",
                            }
                        },
                    },
                },
            },
            response.dict(),
        )

    def test_tell(self):
        r = tell("Hello")
        self.assertIsInstance(r, Response)
        self.assertEqual("TELL", r.type)

    def test_ask(self):
        r = ask("Question")
        self.assertIsInstance(r, Response)
        self.assertEqual("ASK", r.type)

    def test_ask_freetext(self):
        r = ask_freetext("Question")
        self.assertIsInstance(r, Response)
        self.assertEqual("ASK_FREETEXT", r.type)

    def test_init_push_notification(self):
        response = self.simple_response.with_notification(
            target_name="device", message_payload="payload"
        ).dict()
        self.assertEqual("abc123", response["text"])
        self.assertEqual("TELL", response["type"])
        self.assertEqual(
            {"messagePayload": "payload", "targetName": "device"},
            response["pushNotification"],
        )

    #
    # TODO: double check if this functionality requested by skills, remove if not needed
    #
    """
    def test_message(self):
        response = Response(Message('{abc}123', 'KEY', abc='abc')).dict()
        self.assertEqual('abc123', response['text'])
        self.assertEqual(ResponseType.TELL, response['type'])
        self.assertEqual({'key': 'KEY', 'value': '{abc}123', 'args': (), 'kwargs': {'abc': 'abc'}},
                         response['result']['data'])
    """
