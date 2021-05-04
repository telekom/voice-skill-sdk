#
#
# voice-skill-sdk
#
# (C) 2021, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

"""Tracing middleware"""

import logging
from fastapi import FastAPI
from contextlib import ContextDecorator

logger = logging.getLogger(__name__)

try:
    from starlette_opentracing import StarletteTracingMiddleWare
    from opentracing import Tracer, global_tracer, set_global_tracer
except ModuleNotFoundError:
    logger.error(
        '"StarletteTracingMiddleWare" not found. Extra package is not installed. '
        'Make sure to install "skill-sdk[all]" to enable distributed tracing features.'
    )
    raise


class start_span(ContextDecorator):
    """
    Tracing helper/span wrapper.

    Can be used as both context manager and decorator:

        As context manager:
        >>> with start_span('span'):
        >>>    ...

        As decorator:
        >>> @start_span('span')
        >>> def decorated():
        >>>    ...

    """

    def __init__(self, operation_name, *args, **kwargs):
        self.operation_name = operation_name
        self.args = args
        self.kwargs = kwargs

    def __enter__(self):
        tracer = global_tracer()
        self._span = tracer.start_span(self.operation_name, *self.args, **self.kwargs)
        return self._span.__enter__()

    def __exit__(self, _exc_type, _exc_value, _exc_traceback):
        return self._span.__exit__(_exc_type, _exc_value, _exc_traceback)


def setup(app: FastAPI, tracer: Tracer) -> None:
    """
    Setup tracing: register a middleware and set global tracer instance

    :param app:
    :param tracer:
    :return:
    """
    set_global_tracer(tracer)
    app.add_middleware(StarletteTracingMiddleWare, tracer=tracer)
