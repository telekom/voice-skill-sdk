#
# voice-skill-sdk
#
# (C) 2021, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

"""Skill runner"""

import inspect
import logging
from functools import partial
from types import MappingProxyType, ModuleType
from typing import Any, Callable, Dict, Mapping, Text, Union
from fastapi import FastAPI

from skill_sdk import i18n, util
from skill_sdk.intents import handlers, invoke
from skill_sdk.responses import Response

logger = logging.getLogger(__name__)

#
# Fallback intent: called when no implementation found
#
#   Eq.: a skill handling 'Intent__One' and 'Intent__Two' receives 'Intent__Three' intent.
#
#       Normally this would trigger a "404: intent not found" response.
#
#       If skill implements a handler for 'FALLBACK_INTENT' intent,
#       this function is called instead.
#
FALLBACK_INTENT = "FALLBACK_INTENT"


class Skill(FastAPI):
    """Overloads FastAPI with intent handlers and translations"""

    locales: Mapping[Text, i18n.Translations]

    intents: Mapping[Text, Callable]

    #
    # Temporary dictionary with intent implementations
    #
    __intents: Dict[Text, Callable] = {}

    def __init__(
        self,
        *,
        translations: Dict[Text, i18n.Translations] = None,
        **kwargs,
    ) -> None:

        self.translations = translations or i18n.load_translations()
        self.intents = MappingProxyType(self.__intents)

        super().__init__(**kwargs)

        util.populate_intent_examples(self.intents)

    def get_intent(self, name: Text):
        """
        Return intent handler by name
            (or 'FALLBACK_INTENT' handler if not found)

        :param name:
        :return:
        """
        return self.intents.get(name, self.intents.get(FALLBACK_INTENT))

    def include(
        self,
        intent: Text = None,
        *,
        handler: Callable,
        error_handler: handlers.ErrorHandlerType = None,
    ) -> "Skill":
        """
        Add an intent handler to the skill

        :param intent:          intent name
        :param handler:         intent handler
        :param error_handler:   conversion error handler
        :return:
        """

        if (
            intent is not None
            and intent in self.intents
            and handler is not self.intents[intent]
        ):
            raise ValueError(
                f"Cannot redefine existing intent {repr(intent)} handler: {repr(self.intents[intent])}"
            )

        registered = ""
        try:
            registered = [
                intent
                for intent, implementation in self.intents.items()
                if handler is implementation
            ][0]
            logger.debug(
                "Intent %s handler %s already registered",
                repr(registered),
                repr(handler),
            )
        except IndexError:
            pass

        if intent and not registered:
            self.__intents[intent] = self.__register(intent, handler, error_handler)
            logger.debug("Intent %s handler: %s", repr(intent), repr(handler))

        return self

    @staticmethod
    def __register(
        intent: Text,
        handler: Callable[..., Any],
        error_handler: handlers.ErrorHandlerType = None,
    ):

        if not intent:
            raise ValueError("Intent name is required when adding intent handlers")

        if intent in Skill.__intents:
            raise ValueError(
                f"Duplicate intent {repr(intent)} with handler {repr(handler)}"
            )

        if not inspect.isfunction(handler):
            raise ValueError(
                f"Wrong handler type: {type(handler)}. Expecting coroutine or function."
            )

        decorated = handlers.intent_handler(handler, error_handler=error_handler)
        Skill.__intents[intent] = decorated
        logger.debug("Intent %s static handler: %s", repr(intent), repr(decorated))
        return decorated

    @staticmethod
    def intent_handler(
        intent: Text,
        handler: Callable = None,
        error_handler: handlers.ErrorHandlerType = None,
    ) -> Callable:
        """
        Decorator to wrap an intent implementation

        :param intent:          Intent name
        :param handler:         Handler function
        :param error_handler:   Optional handler to call if conversion error occurs
        :return:
        """

        if callable(intent) and handler is None:
            # If used as simple decorator, i.e.:
            #
            #   @intent_handler
            #   async def handler():
            #
            # In this case we simply return decorated function
            return handlers.intent_handler(intent, error_handler=error_handler)

        return partial(Skill.__register, intent, error_handler=error_handler)

    async def test_intent(
        self,
        intent: Text,
        translation: i18n.Translations = None,
        session: Union[util.CamelModel, Dict[Text, Text]] = None,
        **kwargs,
    ) -> Response:
        """
        Test an intent implementation

        :param intent:      Intent name
        :param translation: Translations to use (NullTranslations if not set)
        :param session:     Mocked session (can be a session result of previous test invoke)
        :param kwargs:      Intent's attributes
        :return:
        """
        try:
            handler = self.intents[intent]
        except KeyError:
            raise KeyError(f"Intent {intent} not found")

        r = util.create_request(intent, session=session, **kwargs).with_translation(
            translation if translation else i18n.Translations()
        )

        return await invoke(handler, r)

    @property
    def module(self) -> ModuleType:
        try:
            return getattr(self, "_module")
        except AttributeError:
            raise RuntimeError(
                '"module" property is only available in DEVELOPMENT mode.'
            ) from None

    def close(self):
        """
        Cleanup: Skill.__intents is static to enable backward-compatible "@intent_handler" decorators,
        that are not bound to a skill instance (yet).

        While it's not a big issue for a single-purpose skill, it is for SDK unit testing,
        when skill instances dynamically created and destroyed.

        To force cleanup:

            >>> from contextlib import closing
            >>> with closing(init_app()):
            >>>     ... # do your things

        """

        self.__intents.clear()


def init_app(config_path: Text = None, develop: bool = None) -> Skill:
    """
    Create FastAPI application from configuration file

    `skill` section of the config file is used to initialize FastAPI app,
    so any FastAPI initialization parameters, like `debug`, `title`, `description`, `version` can be used

    :param config_path:
    :param develop:         Flag to init an app in "development" mode:
                                overrides debug flag from configuration,
                                initializes Designer UI
    :return:
    """
    from skill_sdk import config, middleware, routes

    if config_path is not None:
        config.settings.Config.conf_file = config_path

    if develop is None:
        develop = config.settings.debug()

    app_config = {**config.settings.app_config(), **dict(debug=develop)}
    logger.debug("App config: %s", app_config)

    app = Skill(**app_config)

    middleware.setup_middleware(app)
    routes.setup_routes(app)

    # Since Prometheus metrics exporter is optional,
    # try to load prometheus middleware and simply eat an exception
    try:
        from middleware.prometheus import setup

        setup(app)
    except ModuleNotFoundError:
        pass

    if develop:
        from skill_sdk import ui

        ui.setup(app)

    return app


intent_handler = Skill.intent_handler


def test_intent(
    intent: Text,
    translation: i18n.Translations = None,
    session: Union[util.CamelModel, Dict[Text, Text]] = None,
    **kwargs,
) -> Response:
    """
    Backward compatible test helper

    :param intent:      Intent name
    :param translation: Translations to use (NullTranslations if not set)
    :param session:     Mocked session (can be a session result of previous test invoke)
    :param kwargs:      Intent's attributes
    :return:
    """

    app = Skill()

    return util.run_until_complete(
        app.test_intent(intent, translation, session=session, **kwargs)
    )
