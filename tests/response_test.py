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
from types import SimpleNamespace
from unittest.mock import patch

import bottle
from bottle import HTTPResponse

from skill_sdk import l10n, tell, ask, ask_freetext
from skill_sdk.test_helpers import create_context
from skill_sdk.intents import Context
from skill_sdk.responses import (Card, GENERIC_DEFAULT, ErrorResponse, Response, Reprompt,
                                 RESPONSE_TYPE_ASK, RESPONSE_TYPE_TELL, RESPONSE_TYPE_ASK_FREETEXT)


class TestCard(unittest.TestCase):

    def test_init(self):
        sc = Card('DEMOTYPE', title="Title", text="Text")
        self.assertEqual(sc.data['title'], "Title")
        self.assertEqual(sc.data['text'], "Text")

    def test_init_no_type(self):
        with self.assertRaises(ValueError):
            Card(None)

    def test_dict(self):
        sc = Card('DEMOTYPE')
        self.assertDictEqual(sc.dict(), {
            'type': 'DEMOTYPE',
            'version': 1,
        })
        sc = Card('DEMOTYPE', title="Title", text="Text", key_a=1)
        self.assertDictEqual(sc.dict(), {
            'type': 'DEMOTYPE',
            'version': 1,
            'data': {'title': 'Title', 'text': 'Text', 'keyA': 1},
        })

    def test_init_default_type(self):
        self.assertEqual(GENERIC_DEFAULT, Card().type_)


class TestErrorResponse(unittest.TestCase):

    def test_init(self):
        er = ErrorResponse(500, 'internal error')
        self.assertEqual(er.code, 500)
        self.assertEqual(er.text, 'internal error')

    def test_as_response_400(self):
        response = ErrorResponse(2, 'invalid token').as_response()
        self.assertIsInstance(response, (bottle.HTTPResponse,))
        self.assertEqual(response.status_code, 400)

    def test_as_reponse_500(self):
        response = ErrorResponse(999, 'unhandled exception').as_response()
        self.assertIsInstance(response, (bottle.HTTPResponse,))
        self.assertEqual(response.status_code, 500)

    def test_as_reponse_unknown_code(self):
        response = ErrorResponse(123, 'weird error').as_response()
        self.assertIsInstance(response, (bottle.HTTPResponse,))
        self.assertEqual(response.status_code, 500)


class TestResponse(unittest.TestCase):

    def setUp(self):
        self.simple_response = Response('abc123')
        self.ask_response = Response('abc123', RESPONSE_TYPE_ASK, ask_for=('location', 'CITY'))
        card = Card('SIMPLE', title='cardtitle', text='cardtext', token_id={'secret': 'token'})
        self.card_response = Response('abc123', RESPONSE_TYPE_TELL, card=card, result={'code': 22})

        session = {'attributes': {"key-1": "value-1",
                                  "key-2": "value-2"}}
        self.ctx = create_context("TELEKOM_Clock_GetTime", session=session)

    def test_init_text(self):
        self.assertEqual(self.simple_response.text, 'abc123')
        self.assertEqual(self.simple_response.type_, RESPONSE_TYPE_TELL)

    def test_init_full(self):
        self.assertEqual(self.card_response.text, 'abc123')
        self.assertEqual(self.card_response.type_, RESPONSE_TYPE_TELL)
        self.assertEqual(self.card_response.card.data['title'], 'cardtitle')
        self.assertEqual(self.card_response.result['code'], 22)
        self.assertEqual(self.card_response.push_notification, None)

    def test_init_push_notification(self):
        self.simple_response.push_notification = {'device': [{'payload': 1}, {'payload': 2}]}
        response = self.simple_response.dict(self.ctx)
        self.assertEqual(response['text'], 'abc123')
        self.assertEqual(response['type'], 'TELL')
        self.assertEqual(response['pushNotification'], {'device': [{'payload': 1}, {'payload': 2}]})

    def test_init_bad_type(self):
        with self.assertRaises(ValueError):
            Response('abc123', 'TEL')

    def test_dict_ask(self):
        response = self.ask_response.dict(self.ctx)
        self.assertEqual(response['text'], 'abc123')
        self.assertEqual(response['type'], 'ASK')

    @patch('skill_sdk.responses.warn')
    def test_dict_ask_deprecated(self, warn_mock):
        response = Response('abc123', RESPONSE_TYPE_ASK, ask_for=('location', 'CITY')).dict(self.ctx)
        self.assertNotIn('askForAttribute', response)
        warn_mock.assert_called_with('"ask_for" parameter is deprecated.', DeprecationWarning, stacklevel=2)

    def test_dict_simple(self):
        response = self.simple_response.dict(self.ctx)
        self.assertEqual(response['text'], 'abc123')
        self.assertEqual(response['type'], 'TELL')
        self.assertNotIn('pushNotification', response)

    def test_dict_card(self):
        response = self.card_response.dict(self.ctx)
        self.assertEqual(response['text'], 'abc123')
        self.assertEqual(response['type'], 'TELL')
        self.assertEqual(response['card']['data']['title'], 'cardtitle')
        self.assertEqual(response['result']['data']['code'], 22)
        self.assertEqual(response['card']['tokenId'], {'secret': 'token'})

    @patch.object(Response, 'dict', return_value='{}')
    def test_response(self, dict_mock):
        response = self.simple_response.as_response(None)
        self.assertIsInstance(response, HTTPResponse)
        self.assertEqual(response.status_code, 200)

    def test_message(self):
        response = Response(l10n.Message('{abc}123', 'KEY', abc='abc')).dict(self.ctx)
        self.assertEqual(response['text'], 'abc123')
        self.assertEqual(response['type'], 'TELL')
        self.assertEqual(response['result']['data'],
                         {'key': 'KEY', 'value': '{abc}123', 'args': (), 'kwargs': {'abc': 'abc'}})

    def test_dict_simple_result_is_none(self):
        """ Make sure the optional fields are stripped off if empty
        """
        response = self.simple_response.dict(self.ctx)
        self.assertEqual(response['session'], {'attributes': {'key-1': 'value-1', 'key-2': 'value-2'}})
        self.assertNotIn('result', response)
        self.assertNotIn('card', response)
        self.assertNotIn('pushNotification', response)
        # For the coverage sake:
        request = SimpleNamespace()
        request.headers = {}
        request.json = {
            "context": {
                "attributes": {...},
                "intent": "TELEKOM_Clock_GetTime",
                "locale": "de",
                "tokens": {},
                "clientAttributes": {}
            },
            "version": 1
        }
        ctx = Context(request)
        self.assertNotIn('session', self.simple_response.dict(ctx))

    def test_tell(self):
        """ Check if responses.tell returns Response(type_=RESPONSE_TYPE_TELL)
        """
        r = tell('Hello')
        self.assertIsInstance(r, Response)
        self.assertEqual(r.type_, RESPONSE_TYPE_TELL)

    def test_ask(self):
        """ Check is responses.ask returns Response(type_=RESPONSE_TYPE_ASK)
        """
        r = ask('Question')
        self.assertIsInstance(r, Response)
        self.assertEqual(r.type_, RESPONSE_TYPE_ASK)

    def test_ask_freetext(self):
        """ Check is responses.ask returns Response(type_=RESPONSE_TYPE_ASK_FREETEXT)
        """
        r = ask_freetext('Question')
        self.assertIsInstance(r, Response)
        self.assertEqual(r.type_, RESPONSE_TYPE_ASK_FREETEXT)

    def test_reprompt_response(self):
        """ Test responses.Reprompt response
        """
        self.assertIsInstance(Reprompt('abc123'), Response)
        response = Reprompt('abc123').dict(self.ctx)
        self.assertEqual(response['session']['attributes']['TELEKOM_Clock_GetTime_reprompt_count'], '1')
        self.assertEqual(response['text'], 'abc123')
        self.assertEqual(response['type'], 'ASK')
        with patch.dict(self.ctx.session, {'TELEKOM_Clock_GetTime_reprompt_count': '1'}):
            response = Reprompt('abc123').dict(self.ctx)
            self.assertEqual(response['session']['attributes']['TELEKOM_Clock_GetTime_reprompt_count'], '2')
            self.assertEqual(response['text'], 'abc123')
            self.assertEqual(response['type'], 'ASK')
            response = Reprompt('abc123', '321cba', 2).dict(self.ctx)
            self.assertNotIn('TELEKOM_Clock_GetTime_reprompt_count', response['session']['attributes'])
            self.assertEqual(response['text'], '321cba')
            self.assertEqual(response['type'], 'TELL')
        with patch.dict(self.ctx.session, {'TELEKOM_Clock_GetTime_reprompt_count': 'not a number'}):
            response = Reprompt('abc123').dict(self.ctx)
            self.assertEqual(response['session']['attributes']['TELEKOM_Clock_GetTime_reprompt_count'], '1')
        response = Reprompt('abc123', entity='Time').dict(self.ctx)
        self.assertEqual(response['session']['attributes']['TELEKOM_Clock_GetTime_reprompt_count'], '1')
        self.assertEqual(response['session']['attributes']['TELEKOM_Clock_GetTime_Time_reprompt_count'], '1')

    def test_response_repr(self):
        """ Test Response representation
        """
        response = Response('Hola', RESPONSE_TYPE_ASK)
        self.assertEqual("{'text': 'Hola', 'type_': 'ASK', 'card': None, "
                         "'push_notification': None, 'result': {'data': {}, 'local': True}}", repr(response))
