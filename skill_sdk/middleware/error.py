#
#
# voice-skill-sdk
#
# (C) 2021, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

"""Error middleware"""

import logging
import traceback
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder

from skill_sdk.responses import ErrorCode

logger = logging.getLogger(__name__)

INTERNAL_ERROR = "Internal error"
BAD_REQUEST = "Bad request"
NOT_FOUND = "Not found"


def setup_middleware(app: FastAPI):
    """
    Setup error handlers (only those that have a corresponding error code in skill SPI):

        - 400: BAD_REQUEST
        - 404: NOT_FOUND
        - 422 is reraised as 400
        - 500: INTERNAL_ERROR

    :param app:
    :return:
    """

    @app.exception_handler(400)
    async def handle_400(request, exc):
        """Log the exception and return BAD_REQUEST"""

        logger.exception("%s %s: %s", request.method, request.url, repr(exc))
        return JSONResponse(
            status_code=400,
            content=dict(code=ErrorCode.BAD_REQUEST, text=BAD_REQUEST),
        )

    @app.exception_handler(404)
    async def handle_404(request, exc):
        """Log the exception and return NOT_FOUND"""

        logger.exception("%s %s: %s", request.method, request.url, repr(exc))
        return JSONResponse(
            status_code=404,
            content=dict(code=ErrorCode.NOT_FOUND, text=NOT_FOUND),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_422(request, exc):
        """Unprocessable entity: raised by Pydantic validators"""

        logger.exception("%s %s: %s", request.method, request.url, repr(exc))
        return JSONResponse(
            status_code=422,
            content=dict(
                code=ErrorCode.BAD_REQUEST,
                text=BAD_REQUEST,
                detail=jsonable_encoder(exc.errors()),
            ),
        )

    @app.exception_handler(500)
    async def handle_500(request, exc):
        """Log the exception and return INTERNAL_ERROR"""

        logger.exception("500 error raised, returning internal error: %s", repr(exc))
        content = dict(
            code=ErrorCode.INTERNAL_ERROR,
            text=INTERNAL_ERROR,
        )

        # Output the exception in "debug" mode
        if request.app.debug():
            content.update(detail=jsonable_encoder(traceback.format_exc()))

        return JSONResponse(
            status_code=500,
            content=content,
        )
