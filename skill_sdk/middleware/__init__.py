#
#
# voice-skill-sdk
#
# (C) 2021, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

"""Middleware definitions"""

from starlette_context.middleware import RawContextMiddleware
from starlette_context import context  # noqa

from skill_sdk.middleware import (
    error,
    log,
)

from skill_sdk.middleware.log import HeaderKeys


def setup_middleware(app):
    """
    Setup default middlewares: error and context

    :param app:
    :return:
    """

    error.setup_middleware(app)

    app.add_middleware(
        RawContextMiddleware,
        plugins=(
            log.TraceIdPlugin(),
            log.SpanIdIdPlugin(),
            log.TenantIdIdPlugin(),
            log.TestingFlagPlugin(),
            log.UserDebugLogPlugin(),
        ),
    )
