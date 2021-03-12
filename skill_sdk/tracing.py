#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

#
# Generic tracing adapter
#

import logging
from opentracing.mocktracer import MockTracer
from opentracing.mocktracer.context import SpanContext
from opentracing.mocktracer.span import MockSpan as Span    # noqa: F401
from opentracing import global_tracer, set_global_tracer
from opentracing import (
    InvalidCarrierException,
    UnsupportedFormatException,     # noqa: F401
    SpanContextCorruptedException,  # noqa: F401
)
from opentracing.propagation import Format
from functools import wraps

EVENT = "event"
logger = logging.getLogger(__name__)


class Codec:
    """
    Codec to pass-through internal headers without creating spans
    """

    trace_header = "X-B3-TraceId"
    span_header = "X-B3-SpanId"
    testing_header = "X-Testing"
    simple_testing = 'Testing'

    def inject(self, span_context, carrier):
        """
        Inject headers

        :param span_context:
        :param carrier:
        :return:
        """
        if not isinstance(carrier, dict):
            raise InvalidCarrierException("carrier not a dictionary")
        carrier[self.trace_header] = str(span_context.trace_id)
        carrier[self.span_header] = str(span_context.span_id)

        if span_context.baggage.get("testing"):
            carrier[self.testing_header] = "1"
            carrier[self.simple_testing] = 'true'

    def extract(self, carrier):
        """
        Extract headers

        :param carrier:
        :return:
        """
        if not isinstance(carrier, dict):
            raise InvalidCarrierException("carrier not a dictionary")
        lowercase_keys = dict([(k.lower(), k) for k in carrier])
        trace_id = carrier.get(lowercase_keys.get(self.trace_header.lower()))
        span_id = carrier.get(lowercase_keys.get(self.span_header.lower()))
        testing = carrier.get(lowercase_keys.get(self.testing_header.lower()))
        return SpanContext(trace_id=trace_id, span_id=span_id, baggage=dict(testing=bool(testing)))


class Tracer(MockTracer):

    def __init__(self, scope_manager=None):
        super(Tracer, self).__init__(scope_manager=scope_manager)
        self.register_propagator(Format.HTTP_HEADERS, Codec())


class start_span:
    """
    Tracing helper/span wrapper. Can be used as both context manager and decorator:

        # As context manager:
        with start_span('span'):
            ...

        # As decorator:
        @start_span('span')
        def decorated():
            ...

    """

    def __init__(self, operation_name, tracer: Tracer = None, *args, **kwargs):
        if "child_of" in kwargs:
            tracer = getattr(kwargs["child_of"], 'tracer', global_tracer())

        self.span = None
        self.tracer = tracer
        self.args = args or ()
        self.kwargs = kwargs or {}
        self.operation_name = operation_name

    def __enter__(self):
        return self.start().__enter__()

    def __exit__(self, _exc_type, _exc_value, _exc_traceback):
        self.span.__exit__(_exc_type, _exc_value, _exc_traceback)

    def __call__(self, func):
        @wraps(func)
        def decorated(*args, **kwargs):  # NOSONAR
            with self.start():
                result = func(*args, **kwargs)
                self.finish()
                return result

        return decorated

    def start(self):
        self.tracer = self.tracer or global_tracer()
        self.span = self.tracer.start_span(
            self.operation_name, *self.args, **self.kwargs
        )
        return self.span

    def finish(self):
        return self.span.finish()


def get_service_name():
    """
    Returns the service name, try to get from config or fallback to skill name.

    :return:
    """
    from .config import config

    return config.get("skill", "name", fallback="unnamed_service")


def start_active_span(operation_name, request, **kwargs):
    """Start a new span and return activated scope"""

    tracer: Tracer = global_tracer()

    tags = kwargs.get("tags", {})
    if hasattr(request, "url"):
        tags.update({"http.url": request.url})
    if hasattr(request, "remote_addr"):
        tags.update({"peer.ipv4": request.remote_addr})
    if hasattr(request, "caller_name"):
        tags.update({"peer.service": request.caller_name})

    headers = {key: value for key, value in request.headers.items()}
    logger.debug("HTTP-Header: %s", repr(headers))
    ctx = tracer.extract(format=Format.HTTP_HEADERS, carrier=headers)
    return tracer.start_active_span(operation_name, child_of=ctx, tags=tags, **kwargs)


def initialize_tracer(tracer=None):
    """
    Initialize a tracer: to be replaced by actual implementation

    :return:
    """
    tracer = tracer or Tracer()
    set_global_tracer(tracer)
