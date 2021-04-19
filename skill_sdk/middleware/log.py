#
#
# voice-skill-sdk
#
# (C) 2021, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

"""Logging middleware: extract headers for logging"""

from enum import Enum
from starlette_context.plugins.base import Plugin


class HeaderKeys(str, Enum):
    """Internal testing headers"""

    trace_id = "X-B3-TraceId"
    span_id = "X-B3-SpanId"
    tenant_id = "X-TenantId"
    testing_flag = "X-Testing"
    user_debug_log = "X-User-Debug-Log"


class TraceIdPlugin(Plugin):
    """Extracts trace ID from request"""

    key = HeaderKeys.trace_id


class SpanIdIdPlugin(Plugin):
    """Extracts span ID from request"""

    key = HeaderKeys.span_id


class TenantIdIdPlugin(Plugin):
    """**IMPORTANT**: for logging purpose only, do not base tenant-specific logic on this header

    Extracts tenant ID from request
    """

    key = HeaderKeys.tenant_id


class TestingFlagPlugin(Plugin):
    """
    Extracts "testing" flag from request:
    testing flag distinguishes testing traffic from production
    """

    key = HeaderKeys.testing_flag


class UserDebugLogPlugin(Plugin):
    """
    Extracts "user debug log" flag from request:
    the flag is set to temporary activate debug logging for the user
    """

    key = HeaderKeys.user_debug_log
