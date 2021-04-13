#
# voice-skill-sdk
#
# (C) 2021, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

"""Internationalization"""

import re
import random
import logging
import subprocess
from pathlib import Path
from functools import reduce
from types import MappingProxyType
from typing import Dict, Iterable, List, Optional, Mapping, Text, Tuple, Union

import yaml
from yaml.reader import ReaderError
from yaml.scanner import ScannerError
from babel import dates, lists, support

# Place your `[lang].po` files to `locale` directory
LOCALE_DIR = "locale"

PROGRAM = "pybabel"
PROGRAM_NOT_FOUND = f'Failed to launch "{PROGRAM} %s": not found. Make sure "{PROGRAM}" is in your PATH.'

RE_TRANSLATIONS = re.compile(r"^[a-z]{2}(-[A-Z]{2})?$")

logger = logging.getLogger(__name__)


def get_locale_dir(locale_dir: Text = None) -> Path:
    """Returns locales folder location"""
    return Path(locale_dir or LOCALE_DIR)


def make_lazy(func, alt=None):
    """
    Make lazy translation function

    :param func:    function to call
    :param alt:     alternative function if translation is not set
    :return:
    """

    def lazy_func(*args, **kwargs):
        """Lazy translations wrapper"""

        from skill_sdk.intents import r

        try:
            return getattr(r.get_translation(), func)(*args, **kwargs)
        except TypeError:
            logger.error("Calling translation functions outside of request context.")
        except AttributeError as e:
            logger.exception("%s", repr(e))
        return alt(*args, **kwargs) if callable(alt) else None

    return lazy_func


_ = make_lazy("gettext", lambda m, *a, **kw: m)
_n = make_lazy(
    "ngettext", lambda singular, plural, n, *a, **kw: singular if n == 1 else plural
)
_a = make_lazy("getalltexts", lambda m, *a, **kw: [m])


class TranslationError(Exception):
    """
    Exception raised when a translation could not be performed due to a missing ``.mo`` file, a missing translation
    key or if there are no suitable translations available in the text service.
    """


class Message(str):
    """String object that encapsulates formatting parameters"""

    # Message id
    key: Text

    # Message string (un-formatted)
    value: Text

    # Positional arguments
    args: Tuple

    # Keyword arguments
    kwargs: Dict

    def __new__(cls, value, key=None, *args, **kwargs):
        """
        Create a message with msgstr/msgid and format parameters

        :return:
        """
        message = (
            value.format(*args, **kwargs)
            if isinstance(value, str) and (args or kwargs)
            else value
        )
        string = super().__new__(cls, message)
        string.key = key or value
        string.args = args
        string.kwargs = kwargs
        string.value = value
        return string

    def format(self, *args, **kwargs) -> "Message":
        """
        Create and return new Message object with given format parameters

        :return:
        """
        message = Message(self.value, self.key, *args, **kwargs)
        return message

    def __add__(self, other: Union["Message", Text]) -> "Message":
        """
        Concatenate messages (or Message and str)

        :param other:
        :return:
        """
        if isinstance(other, Message):
            value = self.value + other.value
            args = self.args + other.args
            kwargs = {**self.kwargs, **other.kwargs}
        else:
            value = self.value + other
            args, kwargs = self.args, self.kwargs

        return Message(value, self.key, *args, **kwargs)

    def join(self, iterable: Iterable[Union["Message", Text]]):
        """
        Join messages in iterable and return a concatenated Message.

        :param iterable:
        :return:
        """
        return reduce(lambda x, y: x + self + y, iterable)

    def strip(self, __chars: Optional[Text] = None) -> "Message":
        """
        Return new Message object with stripped value

        :return:
        """
        message = Message(
            self.value.strip(__chars), self.key, *self.args, **self.kwargs
        )
        return message


class Translations(support.Translations):
    """Lazy translations, return Message object instead of formatted string"""

    def __init__(self, lang: Text = None, f=None):
        self.lang = lang
        try:
            with f.open(mode="rb") as fp:
                super().__init__(fp)
        except AttributeError:
            super().__init__()

    def gettext(self, message, *args, **kwargs) -> Message:
        return Message(super().gettext(message), message, *args, **kwargs)

    def ngettext(self, singular, plural, n, *args, **kwargs) -> Message:
        return Message(super().ngettext(singular, plural, n), singular, *args, **kwargs)

    def format_list(self, elements: List[Text], style="standard"):
        """
        Join list elements
            [items, item2, item3] -> 'item1, item2 and item3'

        :param elements:
        :param style:
        :return:
        """
        return lists.format_list(elements, style=style, locale=self.lang)

    # Backward compatibility
    nl_join = format_list

    def nl_build(self, header: Text, elements: List[Text]) -> Text:
        """
        Build list in natural language:
            (header, [items, item2, item3]) -> 'Header: item1, item2 and item3.'

        :param header:      list header
        :param elements:    list elements
        :return:
        """
        return Message(": ").join((header, self.format_list(elements)))

    def format_datetime(self, datetime=None, format="medium", tzinfo=None) -> Text:
        """Format datetime according to the locale"""
        return dates.format_datetime(datetime, format, tzinfo, self.lang)

    def format_date(self, date=None, format="medium") -> Text:
        """Format date according to the locale"""
        return dates.format_date(date, format, self.lang)

    def format_time(self, time=None, format="medium", tzinfo=None) -> Text:
        """Format time according to the locale"""
        return dates.format_time(time, format, tzinfo, self.lang)

    def format_timedelta(
        self,
        delta,
        granularity="second",
        threshold=0.85,
        add_direction=False,
        format="long",
    ) -> Text:
        """Format a time delta according to the rules of the given locale"""
        return dates.format_timedelta(
            delta, granularity, threshold, add_direction, format, self.lang
        )


class MultiStringTranslation(Translations):
    """Translations that allows single key to have multiple values"""

    def _parse(self, fp):
        """
        Load catalogue from YAML file

        :param fp:
        :return:
        """

        try:
            catalog = yaml.safe_load(fp)
            self._catalog = {
                k: v if isinstance(v, list) else [v] for k, v in catalog.items()
            }
        except (ReaderError, ScannerError) as ex:
            logger.exception(
                "Could not load translations from %s: %s", repr(fp), repr(ex)
            )
            raise RuntimeError from ex

    def __repr__(self):
        return f"<{type(self).__name__}: {repr(self.files)}>"

    def gettext(self, message, *args, **kwargs):
        logger.debug("Translating message %s to %s", repr(message), repr(self.lang))
        try:
            candidates = self._catalog[message]
            logger.debug("%s candidates: %s", len(candidates), repr(candidates))
            return Message(random.choice(candidates), message, *args, **kwargs)
        except LookupError:
            logger.warning("No translation for key: %s", repr(message))
            return super().gettext(message, *args, **kwargs)

    def ngettext(self, singular, plural, n, *args, **kwargs):
        logger.debug("Translating %s/%s/%s to %s", singular, plural, n, self.lang)
        return self.gettext(singular if n == 1 else plural, *args, **kwargs)

    def getalltexts(self, key, *args, **kwargs):
        logger.debug("Retrieving all translation messages for %s in %s", key, self.lang)
        try:
            candidates = self._catalog[key]
            logger.debug("%s candidates: %s", len(candidates), repr(candidates))
            return [Message(value, key, *args, **kwargs) for value in candidates]
        except LookupError:
            logger.warning("No translation for key: %s", key)
            return [super().gettext(key, *args, **kwargs)]


def compile_locales(locale_dir: Text = None, force: bool = False):
    """
    Compile all languages available in locale_dir:
    launches `pybabel compile` to compile .po to .mo files

    :param locale_dir:
    :param force:       force compilation even if *.mo files exist
    :return:
    """
    command = "compile"

    for po_file in get_locale_dir(locale_dir).glob("*.po"):

        mo_file = po_file.with_suffix(".mo")
        if mo_file.exists() and not force:
            logger.info("Skipping %s: %s exists", po_file.name, mo_file)
            continue

        logger.info("Compiling %s ...", po_file.name)
        try:

            result = subprocess.check_output(
                [
                    PROGRAM,
                    command,
                    "-i",
                    str(po_file),
                    "-o",
                    str(mo_file),
                ],
                text=True,
                stderr=subprocess.STDOUT,
            )
            logger.info(result)

        except FileNotFoundError:
            logger.error(PROGRAM_NOT_FOUND, command)

        except subprocess.CalledProcessError as ex:
            logger.error("Failed to compile %s: %s", po_file.name, ex.stdout)
            raise


def _load_yaml(locale_dir: Text = None) -> Dict[Text, MultiStringTranslation]:
    """
    Load multi-string translations from YAML files

    :param locale_dir:
    :return:
    """

    logger.info("Loading YAML translations...")

    return {
        yaml_file.stem: MultiStringTranslation(yaml_file.stem, yaml_file)
        for yaml_file in get_locale_dir(locale_dir).glob("*.yaml")
        if RE_TRANSLATIONS.match(yaml_file.stem)
    }


def _load_gettext(locale_dir: Text = None) -> Dict[Text, Translations]:
    """
    Load `gettext` translations from *.po/*.mo files

    :param locale_dir:
    :return:
    """

    logger.info("Loading gettext translations...")

    compile_locales(locale_dir)
    return {
        mo_file.stem: Translations(mo_file.stem, mo_file)
        for mo_file in get_locale_dir(locale_dir).glob("*.mo")
        if RE_TRANSLATIONS.match(mo_file.stem)
    }


def load_translations(locale_dir: Text = None) -> Mapping[Text, Translations]:
    """
    Load local languages available in locale_dir

    :param locale_dir:
    :return:
    """

    translations = _load_yaml(locale_dir) or _load_gettext(locale_dir)

    return MappingProxyType(translations)
