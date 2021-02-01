#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

#
# Localization
#

import re
import pathlib
import logging
import subprocess
from threading import local
from typing import Dict, Iterator, List, Mapping, Optional, Tuple, Union
from gettext import NullTranslations, GNUTranslations

from .config import config

_thread_locals = local()

LOCALE_DIR = 'locale'
PROGRAM_NOT_FOUND = 'Failed to launch %s: not found. Make sure you have GNU gettext tools installed.'
RE_TRANSLATIONS = re.compile(r'^[a-z]{2}(-[A-Z]{2})?$')
logger = logging.getLogger(__name__)


translations: Mapping[str, Union['Translations', NullTranslations]] = {}


def get_locales() -> List[str]:
    """Get list of available locales, eg. ['de', 'fr']"""

    return list(translations.keys())


def get_translation(locale: str) -> Union['Translations', NullTranslations]:
    """Get translation for locale, or empty translation if does not exist"""

    global translations
    if locale not in translations:
        logger.error('A translation for locale %s is not available.', locale)
        return Translations()
    return translations[locale]


def set_current_locale(locale):
    """Set current locale"""
    return setattr(_thread_locals, 'locale', locale)


def make_lazy(locale, func, alt=None):
    """
    Make lazy translation function

    :param locale:  current locale
    :param func:    function to call
    :param alt:     alternative function if locale is not set
    :return:
    """
    def lazy_func(*args, **kwargs):
        """
        Lazy translations wrapper """
        try:
            return getattr(locale(), func)(*args, **kwargs)
        except AttributeError:
            logger.error('Calling translation functions outside of request context.')
            return alt(*args, **kwargs) if callable(alt) else None

    return lazy_func


_ = make_lazy(lambda: _thread_locals.locale, 'gettext', lambda m, *a, **kw: m)
_n = make_lazy(lambda: _thread_locals.locale, 'ngettext',
               lambda singular, plural, n, *a, **kw: singular if n == 1 else plural)
_a = make_lazy(lambda: _thread_locals.locale, 'getalltexts', lambda m, *a, **kw: [m])


def nl_capitalize(string: str):
    """
    Capitalize first character (the rest is untouched)

    :param string:
    :return:
    """
    return string[:1].upper() + string[1:]


def nl_decapitalize(string: str):
    """
    Decapitalize first character (the rest is untouched)

    :param string:
    :return:
    """
    return string[:1].lower() + string[1:]


def nl_strip(string: str) -> str:
    """
    Strip blanks and punctuation symbols

    :param string:
    :return:
    """
    return string.strip().strip('.,:!?').strip()


class TranslationError(Exception):
    """
    Exception raised when a translation could not be performed due to a missing ``.mo`` file, a missing translation
    key or if there are no suitable translations available in the text service.
    """


class Message(str):
    """
    String object that looks like a string and formats like a string,
    but encapsulates the original `key` and format arguments for use in `responses.Result`

    """

    # Message id
    key: str
    # Message string (un-formatted)
    value: str
    # Positional arguments
    args: Tuple
    # Keyword arguments
    kwargs: Dict

    def __new__(cls, value, key=None, *args, **kwargs):
        """
        Create a message with msgstr/msgid and format parameters

        :return:
        """
        message = value.format(*args, **kwargs) if isinstance(value, str) and (args or kwargs) else value
        string = super().__new__(cls, message)
        string.key = key or value
        string.args = args
        string.kwargs = kwargs
        string.value = value
        return string

    def format(self, *args, **kwargs) -> 'Message':
        """
        Create and return new Message object with given format parameters

        :return:
        """
        message = Message(self.value, self.key, *args, **kwargs)
        return message

    def strip(self, __chars: Optional[str] = None) -> 'Message':
        """
        Return new Message object with stripped value

        :return:
        """
        message = Message(self.value.strip(__chars), self.key, *self.args, **self.kwargs)
        return message


class Translations(GNUTranslations):
    """
    Lazy translations with an empty catalog
        dissembles gettext.NullTranslations if no translation available
    """

    def __init__(self, fp=None):
        self._catalog = {}
        self.plural = lambda n: int(n != 1)
        super().__init__(fp)

    def gettext(self, message, *args, **kwargs):
        return Message(super().gettext(message), message, *args, **kwargs)

    def ngettext(self, singular, plural, n, *args, **kwargs):
        message = plural if self.plural(n) else singular
        return Message(super().ngettext(singular, plural, n), message, *args, **kwargs)

    def nl_join(self, elements: List[str]) -> str:
        """
        Join a list in natural language:
            [items, item2, item3] -> 'item1, item2 and item3'

        :param elements:
        :return:
        """
        elements = [nl_strip(item) for item in elements]
        if len(elements) == 0:
            result = ''
        elif len(elements) == 1:
            result = elements[0]
        elif len(elements) == 2:
            result = Message(' ').join((elements[0], self.gettext('AND'), elements[1]))
        else:
            result = Message(' ').join((Message(', ').join(elements[:-1]), self.gettext('AND'), elements[-1]))
        return result

    def nl_build(self, header: str, elements: List[str] = None) -> str:
        """
        Build list in natural language:
            (header, [items, item2, item3]) -> 'Header: item1, item2 and item3.'

        :param header:      list header
        :param elements:    list elements
        :return:
        """
        if isinstance(header, (list, tuple)):
            header, elements = elements, header

        if elements is None:
            elements = []

        elements = [nl_decapitalize(nl_strip(item)) for item in elements]

        if header and elements:
            header = nl_strip(header)
            result = f"{nl_capitalize(header)}: {self.nl_join(elements)}."
        elif elements:
            result = f"{nl_capitalize(self.nl_join(elements))}."
        else:
            result = ''
        return result


#
#   Helper functions to work with local translations:
#       delegate the calls to GNU gettext utilities: `xgettext`, `msginit`, `msgfmt`
#

def get_locale_dir(locale_dir: str = None) -> pathlib.Path:
    """Returns locales folder location"""
    path = pathlib.Path(locale_dir or LOCALE_DIR)
    return path


def extract_translations(modules: List[str], locale_dir: str = None) -> Optional[pathlib.Path]:
    """
    Extract translatable strings from Python modules and write translations to `messages.pot`

    :param modules: List of Python modules to scan
    :param locale_dir:
    :return:
    """
    files = []
    program = 'xgettext'
    path = get_locale_dir(locale_dir)
    if not path.exists():
        path.mkdir(parents=True)

    output = path / 'messages.pot'
    for module in modules:
        path = pathlib.Path(module)
        if path.is_file() and path.suffix == '.py':
            files.append(path)
        elif path.is_dir():
            files.extend([_ for _ in path.iterdir() if _.is_file() and _.suffix == '.py'])

    logger.debug('Scanning %s', repr(files))
    try:
        subprocess.run([program, '--language=python', f'--output={str(output)}', *files],
                       check=True, stderr=subprocess.PIPE, text=True)
        logger.info('Translation template written to %s', repr(output))
        return output

    except FileNotFoundError:
        logger.error(PROGRAM_NOT_FOUND, program)

    except subprocess.CalledProcessError as ex:
        logger.error('Failed to extract translations: %s', repr(ex.stderr))
    return None


def init_locales(template: pathlib.Path, locales: List[str], locale_dir: str = None, force: bool = False) -> bool:
    """
    Create empty .po file in locale_dir

    :param template:    Template (.pot) file to create translation
    :param locales:     List of translations to initialize, eg. ['en', 'de', 'fr']
    :param locale_dir:  Locale folder
    :param force:       If `True`, try to unlink the [locale].po file first

    :return:            `True` if all locales have been initialized, `False` if error occurred
    """
    program = 'msginit'
    path = get_locale_dir(locale_dir)
    for locale in locales:
        output = path / f'{locale}.po'
        logger.info('Creating %s ...', repr(output))
        try:
            if force and output.exists():
                output.unlink()
            subprocess.run([program, '--no-translator', '-i', template, '-o', str(output)],
                           check=True, stderr=subprocess.PIPE, text=True)

        except FileNotFoundError:
            logger.error(PROGRAM_NOT_FOUND, program)
            return False

        except subprocess.CalledProcessError as ex:
            logger.error('Failed to create %s: %s', repr(output), repr(ex.stderr))
            return False

    return True


def _translate(lines: Iterator, messages: Dict) -> List:
    """
    Update lines from .po file with translated messages dict

    :param lines:
    :param messages:
    :return:
    """
    translated = []
    for line in lines:
        if line.strip().startswith('msgid'):
            translated.append(line)
            msgid = line.strip().split(' ')[-1].strip("'\"")
            msgstr = messages.get(msgid)
            if isinstance(msgstr, (list, tuple)):
                msgstr = next(iter(msgstr), None)
            if isinstance(msgstr, str):
                msgstr = msgstr.replace('"', '\\"')  # Escape double quotes
                msgstr = msgstr.strip()  # Strip blanks and new lines
                msgstr = msgstr.replace('\n', '"\n"')  # Add quotes to new lines
            try:
                line = f'msgstr "{msgstr}"' if msgstr else next(lines)
                next(lines)
            except StopIteration:
                pass
        translated.append(line)
    return translated


def translate_locale(locale: str, messages: Dict, locale_dir: str = None) -> Optional[List]:
    """
    Read data from .po file and update it with translated messages

    :param locale:
    :param messages:
    :param locale_dir:
    :return:
    """
    po_file = get_locale_dir(locale_dir) / f'{locale}.po'
    try:
        logger.info('Translating %s ...', po_file.name)
        with po_file.open() as f:
            lines = iter(f.readlines())
            return _translate(lines, messages)
    except (AttributeError, KeyError, FileNotFoundError) as ex:
        logger.error('Failed to translate %s: %s', po_file.name, repr(ex))
        return None


def update_translation(locale: str, messages: Dict, locale_dir: str = None):
    """
    Update .po file with translated messages

    :param locale:
    :param messages:
    :param locale_dir:
    :return:
    """
    po_file = get_locale_dir(locale_dir) / f'{locale}.po'
    translated = translate_locale(locale, messages, locale_dir)
    if translated:
        with po_file.open("w+") as f:
            logger.info('Updating %s ...', po_file.name)
            f.writelines(translated)
            return po_file
    else:
        logger.info('Nothing to translate in %s', po_file.name)


def compile_locales(locale_dir: str = None):
    """
    Compile all languages available in locale_dir:
        launches `msgfmt` utility to compile .po to .mo files

    :param locale_dir:
    :return:
    """
    program = 'msgfmt'
    search_glob = get_locale_dir(locale_dir) / '*.po'
    for po_file in config.resolve_glob(search_glob):
        logger.info('Compiling %s ...', po_file.name)
        try:
            subprocess.run([program, '-o', str(po_file.with_suffix('.mo')),
                            str(po_file)], check=True, stderr=subprocess.PIPE, text=True)

        except FileNotFoundError:
            logger.error(PROGRAM_NOT_FOUND, program)

        except subprocess.CalledProcessError as ex:
            logger.error('Failed to compile %s: %s', po_file.name, repr(ex.stderr))


def load_translations(locale_dir: str = None) -> Mapping[str, Translations]:
    """
    Load local languages available in locale_dir

    :param locale_dir:
    :return:
    """
    logger.info('Loading gettext translations...')

    compile_locales(locale_dir)

    _translations: Dict[str, Translations] = {}

    search_glob = get_locale_dir(locale_dir) / '*.mo'
    for mo_file in config.resolve_glob(search_glob):
        lang = mo_file.stem
        if RE_TRANSLATIONS.match(lang):
            with mo_file.open(mode="rb") as f:
                _translations[lang] = Translations(f)

    return _translations
