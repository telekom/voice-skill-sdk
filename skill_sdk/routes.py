#
#
# voice-skill-sdk
#
# (C) 2021, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

"""Route definitions"""

import logging
import secrets
from typing import Text

from fastapi import Depends, FastAPI, Request, Security
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from fastapi.security.http import (
    HTTPBasic,
    HTTPBasicCredentials,
    HTTP_401_UNAUTHORIZED,
)

import skill_sdk.i18n
from skill_sdk.config import settings
from skill_sdk.__version__ import __version__
from skill_sdk.intents import invoke

from skill_sdk.responses import SkillInfoResponse, SkillInvokeResponse

logger = logging.getLogger(__name__)
security = HTTPBasic()


def check_credentials(username: Text, password: Text):
    """
    Check request credentials:

        currently basic credential validation is used
        skill is invoked with user name "cvi" and a password specified as api_key in skill configuration

    :param username:
    :param password:
    :return:
    """

    def wrapper(credentials: HTTPBasicCredentials = Security(security)):
        """Check credentials and throw HTTP_401_UNAUTHORIZED if incorrect"""
        if not (
            secrets.compare_digest(credentials.username, username)
            and secrets.compare_digest(credentials.password, password)
        ):
            logger.warning("401 raised, returning: access denied.")
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Incorrect user name or password",
            )

    return wrapper


async def handle_info_request(request: Request):
    """
    Get skill info endpoint

        Returns the skill info to CVI:

            - skill id
            - supported SPI version
            - skill and SDK versions
            - supported locales

    :param request: Request
    :return:        JSONResponse
    """

    logger.debug("Handling info request.")

    return SkillInfoResponse(
        skill_id=settings.SKILL_NAME,
        skill_version=f"{settings.SKILL_VERSION} {__version__}",
        supported_locales=tuple(request.app.translations.keys()),
    )


async def invoke_intent(
    rq: Request,
    request: skill_sdk.intents.Request,
):
    """
    Invoke intent endpoint

        Sets the translation to requested locale and invokes an intent handler.

    :param rq:          original starlette's request
    :param request:     skill invoke request

    :return:
    """

    def _get_translation(
        app: skill_sdk.Skill, locale: Text
    ) -> skill_sdk.i18n.Translations:
        """Get translation for locale, or empty translation if does not exist"""

        if locale not in app.translations:
            logger.error("Translation for locale %s is not available.", repr(locale))
            return skill_sdk.i18n.Translations()
        return app.translations[locale]

    if request.context.intent not in rq.app.intents:
        logger.error("Intent not found: %s", repr(request.context.intent))
        return JSONResponse({"code": 1, "text": "Intent not found!"}, status_code=404)

    handler = rq.app.intents[request.context.intent]

    return await invoke(
        handler,
        request.with_translation(_get_translation(rq.app, request.context.locale)),
    )


def api_base():
    """
    API base is either set directly in `skill.conf` (required for deployment as Azure function), like

        skill:
            api_base: /api

        OR constructed from skill version and name: `/v{version:1}/{name:my-skill}` => `/v1/my-skill`

        skill:
            version: 1
            name: my-skill

    """

    return getattr(
        settings, "API_BASE", f"/v{settings.SKILL_VERSION}/{settings.SKILL_NAME}"
    )


async def health(r: Request) -> JSONResponse:
    """
    Health check endpoint

    :param r:   starlette's request

    :return:
    """
    if len(r.app.intents) < 1:
        return JSONResponse(dict(text="No intent handlers loaded!"), status_code=418)

    return JSONResponse(dict(text="Ok"), status_code=200)


def setup_routes(app: FastAPI):
    """
    Setup default skill routes:

        - GET   /info
        - POST  /
        - GET   /k8s/readiness
        - GET   /k8s/liveness

    :param app:
    :return:
    """

    authentication = (
        [Depends(check_credentials(settings.SKILL_API_USER, settings.SKILL_API_KEY))]
        if not app.debug
        else []
    )

    app.add_api_route(
        f"{api_base()}",
        invoke_intent,
        dependencies=authentication,
        methods=["POST"],
        response_model=SkillInvokeResponse,
        response_model_exclude_none=True,
        name="Invoke Intent",
        tags=["Skill endpoints"],
    )

    app.add_api_route(
        f"{api_base()}/info",
        handle_info_request,
        dependencies=authentication,
        response_model=SkillInfoResponse,
        name="Get Skill Info",
        tags=["Skill endpoints"],
    )

    app.add_api_route(
        settings.K8S_READINESS,
        health,
        name="Readiness Probe",
        tags=["Health endpoints"],
    )
    app.add_api_route(
        settings.K8S_LIVENESS, health, name="Liveness Probe", tags=["Health endpoints"]
    )
