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
import pathlib
import subprocess
from unittest.mock import patch, mock_open

from skill_sdk import l10n
from skill_sdk.l10n import load_translations, Message, Translations

# This is a content of an empty .mo file
EMPTY_MO_DATA = b'\xde\x12\x04\x95\x00\x00\x00\x00\x01\x00\x00\x00\x1c\x00\x00\x00$\x00\x00\x00\x03\x00\x00\x00,' \
                b'\x00\x00\x00\x00\x00\x00\x008\x00\x00\x00(\x00\x00\x009\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\
                x00\x00\x00\x00\x00Content-Type: text/plain; charset=UTF-8\n\x00'

test_old_data = '{"DEMO_MSG": ["impl/1.py"]}'


class TestL10n(unittest.TestCase):

    @patch('skill_sdk.l10n.pathlib.Path.open', mock_open(read_data=b""), create=True)
    @patch('skill_sdk.l10n.config.resolve_glob', return_value=[pathlib.Path('zh.mo')])
    @patch('skill_sdk.l10n.Translations', return_value=None)
    def test_load_translations(self, *args):
        self.assertEqual(load_translations('.')['zh'], None)
        with patch('skill_sdk.l10n.config.resolve_glob', return_value=[pathlib.Path('bad_lang_code.mo')]):
            self.assertEqual(load_translations('.'), {})

    @patch('builtins.open', mock_open(read_data=b'\xde\x12\x04\x95\x00\x00\x00\x00\x01\x00\x00\x00\x1c\x00\x00\x00$\x00\x00\x00\x03\x00\x00\x00,\x00\x00\x00\x00\x00\x00\x008\x00\x00\x00(\x00\x00\x009\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00Content-Type: text/plain; charset=UTF-8\n\x00'), create=True)
    def test_make_lazy_translation(self):
        from skill_sdk.l10n import _, _n, _a
        with open('de.mo') as f:
            tr = Translations(f)
            tr._catalog['KEY'] = 'VALUE'
            tr._catalog[('KEY', 1)] = 'VALUES'
            tr._catalog['KEY_PLURAL'] = 'VALUES'
            l10n.set_current_locale(None)
            self.assertEqual(_('KEY'), 'KEY')
            self.assertEqual(_n('KEY', 'KEY_PLURAL', 1), 'KEY')
            self.assertEqual(_n('KEY', 'KEY_PLURAL', 2), 'KEY_PLURAL')
            self.assertEqual(_a('KEY'), ['KEY'])
            l10n.set_current_locale(tr)
            self.assertEqual(_('KEY'), 'VALUE')
            self.assertEqual(_n('KEY', 'KEY_PLURAL', 2), 'VALUES')
            self.assertEqual(_a('KEY'), ['KEY'])

    @patch.object(pathlib.Path, 'exists', return_value=True)
    @patch('subprocess.run', return_value=0)
    def test_extract_translations(self, process, *a):
        with patch.object(pathlib.Path, 'is_file', return_value=True), \
                patch.object(pathlib.Path, 'is_dir', return_value=False):
            l10n.extract_translations(['a.py', 'b.my'])
            process.assert_called_once_with(['xgettext', '--language=python', '--output=locale/messages.pot',
                                             pathlib.Path('a.py')], check=True, stderr=-1, text=True)

        with patch.object(pathlib.Path, 'exists', return_value=False), patch.object(pathlib.Path, 'mkdir') as mkdir:
            l10n.extract_translations(['a.py', 'b.my'])
            mkdir.assert_called_once_with(parents=True)

        process.reset_mock()
        with patch.object(pathlib.Path, 'is_dir', return_value=True), \
                patch.object(pathlib.Path, 'is_file', return_value=True), \
                patch.object(pathlib.Path, 'iterdir', return_value=[pathlib.Path('impl/a.py'), pathlib.Path('impl/b.py')]):
            l10n.extract_translations(['impl'])
            process.assert_called_once_with(['xgettext', '--language=python', '--output=locale/messages.pot',
                                             pathlib.Path('impl/a.py'), pathlib.Path('impl/b.py')],
                                            check=True, stderr=-1, text=True)

        with patch.object(pathlib.Path, 'is_file', return_value=True), \
                patch.object(pathlib.Path, 'is_dir', return_value=False):
            l10n.extract_translations(['a.py', 'b.my'])
            process.side_effect = FileNotFoundError()
            self.assertIsNone(l10n.extract_translations(['a.py']))
            process.side_effect = subprocess.CalledProcessError(1, cmd='')
            self.assertIsNone(l10n.extract_translations(['a.py']))

    @patch('subprocess.run', return_value=0)
    def test_init_locales(self, process):
        with patch.object(pathlib.Path, 'is_file', return_value=True), \
                patch.object(pathlib.Path, 'is_dir', return_value=False), \
                patch.object(pathlib.Path, 'exists', return_value=True):
            l10n.init_locales(pathlib.Path('template'), ['en', 'de'])
            process.assert_any_call(['msginit', '--no-translator', '-i',
                                     pathlib.Path('template'), '-o', 'locale/en.po'], check=True, stderr=-1, text=True)
            process.assert_called_with(['msginit', '--no-translator', '-i',
                                        pathlib.Path('template'), '-o', 'locale/de.po'], check=True, stderr=-1, text=True)
            self.assertFalse(l10n.init_locales(pathlib.Path('template'), ['en', 'de'], force=True))
            process.side_effect = subprocess.CalledProcessError(1, cmd='')
            self.assertFalse(l10n.init_locales(pathlib.Path('template'), ['en', 'de']))

    def test_update_translations(self):
        with patch.object(pathlib.Path, 'open', mock_open(
                read_data='msgid "TEST" \n  msgstr "" \n\n msgid "TEST1" \n  msgstr "" \n')):
            result = l10n.translate_locale('en', {"TEST": "Test Translation"})
            self.assertEqual(result, ['msgid "TEST" \n', 'msgstr "Test Translation"', '\n',
                                      ' msgid "TEST1" \n', '  msgstr "" \n'])
            self.assertIsNone(l10n.translate_locale('en', []))
        with patch.object(pathlib.Path, 'open', mock_open(
                read_data='msgid "TEST" \n  msgstr "" \n\n msgid "TEST1" \n  msgstr "" \n')) as open_mock:
            l10n.update_translation('en', {"TEST": "Test Translation"})
            open_mock().writelines.assert_called_once_with(['msgid "TEST" \n', 'msgstr "Test Translation"', '\n',
                                                            ' msgid "TEST1" \n', '  msgstr "" \n'])

            logger = logging.getLogger('skill_sdk.l10n')
            with patch('skill_sdk.l10n.translate_locale', return_value=None), self.assertLogs(logger, level="INFO"):
                l10n.update_translation('en', {"TEST": "Test Translation"})

    def test_strings_escape(self):
        with patch.object(pathlib.Path, 'open', mock_open(
                read_data='msgid "TEST" \n  msgstr "" \n\n')):
            result = l10n.translate_locale('en', {"TEST": ['Test Translation with \'quotes\' and "doubles"',
                                                           'Second translation without both']})
            self.assertEqual(result, ['msgid "TEST" \n', 'msgstr "Test Translation with \'quotes\' and \\\"doubles\\\""', '\n'])
            result = l10n.translate_locale('en', {"TEST": ['\nMulti-line string\nWith loads of things here and there ']})
            self.assertEqual(result, ['msgid "TEST" \n', 'msgstr "Multi-line string"\n"With loads of things here and there"', '\n'])

    @patch('subprocess.run', side_effect=FileNotFoundError)
    @patch('skill_sdk.l10n.config.resolve_glob', return_value=[pathlib.Path('zh.mo')])
    def test_compile_locales(self, *args):
        self.assertIsNone(l10n.compile_locales())


class TestMessage(unittest.TestCase):

    def test_message_new(self):
        self.assertFalse(Message(''))
        self.assertEqual(' ', Message(' '))
        message = Message('{a}=={b}', a='1', b='1')
        self.assertEqual(message, '1==1')
        self.assertEqual(message.key, '{a}=={b}')
        self.assertEqual(message.kwargs, {'a': '1', 'b': '1'})
        message = Message('{0}!={1}', 'key', '0', '1')
        self.assertEqual(message, '0!=1')
        self.assertEqual(message.key, 'key')
        self.assertEqual(message.args, ('0', '1'))
        self.assertEqual(message.kwargs, {})

        message = 'Chuck Norris can instantiate interfaces'
        self.assertEqual(Message(message), message)
        self.assertEqual(Message(message).key, message)

    def test_message_simple_format(self):
        message = Message('{a}=={b}', 'key').format(a='1', b='1')
        self.assertEqual(message, '1==1')
        self.assertEqual(message.key, 'key')
        self.assertEqual(message.kwargs, {'a': '1', 'b': '1'})
        message = Message('{0}!={1}', 'key').format('0', '1')
        self.assertEqual(message, '0!=1')
        self.assertEqual(message.args, ('0', '1'))
        self.assertEqual(message.kwargs, {})

    def test_strip(self):
        self.assertEqual('Message', l10n.nl_strip(Message(' !Message?!,. ')))

    def test_message_extended_format(self):
        message1 = Message('{a}=={b}', a='1', b='1')
        message2 = Message('{c}=={d}', c='2', d='2')
        message3 = Message('{e}=={f}', e='3', f='3')

        with self.assertRaises(TypeError):
            Message('').join(None)
        self.assertEqual('', Message(' ').join(()))
        self.assertEqual('1==1', Message(' ').join((message1, )))
        self.assertEqual('1==1 2==2', Message(' ').join((message1, message2)))
        self.assertEqual('1==1 2==2 3==3', Message(' ').join((message1, message2, message3)))


class TestTranslations(unittest.TestCase):

    @patch('skill_sdk.l10n.pathlib.Path.open', mock_open(read_data=EMPTY_MO_DATA), create=True)
    @patch('skill_sdk.l10n.config.resolve_glob', return_value=[pathlib.Path('zh.mo')])
    def test_message_gettext(self, *args):
        tr = load_translations()['zh']
        message = tr.gettext('KEY', a='1', b='1')
        self.assertEqual(message, 'KEY')
        self.assertEqual(message.key, 'KEY')
        self.assertEqual(message.kwargs, {'a': '1', 'b': '1'})

    @patch('skill_sdk.l10n.pathlib.Path.open', mock_open(read_data=EMPTY_MO_DATA), create=True)
    @patch('skill_sdk.l10n.config.resolve_glob', return_value=[pathlib.Path('zh.mo')])
    def test_message_ngettext(self, *args):
        tr = load_translations()['zh']
        message = tr.ngettext('KEY1', 'KEY2', 1, a='1', b='1')
        self.assertEqual(message, 'KEY1')
        self.assertEqual(message.key, 'KEY1')
        self.assertEqual(message.kwargs, {'a': '1', 'b': '1'})


class TestNLFunctions(unittest.TestCase):

    def setUp(self) -> None:
        self.tr = Translations()

    def test_nl_cap_decap(self):
        self.assertEqual(l10n.nl_capitalize('cat dog AND fox'), 'Cat dog AND fox')
        self.assertEqual(l10n.nl_decapitalize('Cat dog AND fox'), 'cat dog AND fox')

    def test_nl_join(self):
        with self.assertRaises(TypeError):
            self.tr.nl_join(None)
        self.assertEqual(self.tr.nl_join([]), '')
        self.assertEqual(self.tr.nl_join([', dog.', ': fox ']), 'dog AND fox')
        self.assertEqual(self.tr.nl_join(['cat', ', dog.', ': fox ']), 'cat, dog AND fox')

    def test_nl_build(self):
        with self.assertRaises(TypeError):
            self.tr.nl_build()

        self.assertEqual(self.tr.nl_build('Header'), '')
        self.assertEqual(self.tr.nl_build(['Instantiate interfaces,']),
                         'Instantiate interfaces.')
        self.assertEqual(self.tr.nl_build('chuck Norris can', ['Instantiate interfaces,']),
                         'Chuck Norris can: instantiate interfaces.')
        self.assertEqual(self.tr.nl_build(' chuck Norris can:: ', ['Instantiate interfaces.', 'Jump over the lazy fox']),
                         'Chuck Norris can: instantiate interfaces AND jump over the lazy fox.')
