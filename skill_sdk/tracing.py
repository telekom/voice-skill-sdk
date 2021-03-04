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
import opentracing
from opentracing import global_tracer, set_global_tracer
from opentracing import InvalidCarrierException, UnsupportedFormatException, SpanContextCorruptedException  # noqa: F401
from opentracing.propagation import Format
from functools import wraps

EVENT = 'event'
logger = logging.getLogger(__name__)


class SpanContext(opentracing.SpanContext):
    """
    define "trace_id"/"span_id" attributes for logging
    """
    __slots__ = ['trace_id', 'span_id', 'testing']

    def __init__(self, trace_id, span_id, testing):
        self.trace_id = trace_id
        self.span_id = span_id
        self.testing = testing


class Span(opentracing.Span):
    """ define "operation_name" attribute for logging
    """

    __slots__ = ['_context', '_tracer', 'operation_name']

    def __init__(self, tracer, context, operation_name):
        """ Add "operation_name"
        """
        super().__init__(tracer=tracer, context=context)
        self.operation_name = operation_name

    def set_operation_name(self, operation_name):
        """ Set the operation name.

        :param operation_name: the new operation name
        :return: Returns the Span for chaining
        """
        self.operation_name = operation_name
        return self

    @property
    def context(self):
        return self._context

    @property
    def span_name(self):    # backward compat
        return self.operation_name

    @property
    def trace_id(self):
        return self.context.trace_id

    @property
    def span_id(self):
        return self.context.span_id

    @property
    def parent_id(self):
        return self.context.parent_id


class ScopeManager(opentracing.ScopeManager):
    """ Scope manager """
    def __init__(self):
        self._noop_span = Span(tracer=None, context=SpanContext(None, None, None), operation_name=None)
        self._noop_scope = opentracing.Scope(self, self._noop_span)


class Codec:
    """
    Codec to pass-through internal headers without creating spans
    """
    trace_header = 'X-B3-TraceId'
    span_header = 'X-B3-SpanId'
    testing_header = 'X-Testing'

    def inject(self, span_context, carrier):
        """
        Inject headers

        :param span_context:
        :param carrier:
        :return:
        """
        if not isinstance(carrier, dict):
            raise InvalidCarrierException('carrier not a dictionary')
        carrier[self.trace_header] = span_context.trace_id
        carrier[self.span_header] = span_context.span_id
        carrier[self.testing_header] = span_context.testing

    def extract(self, carrier):
        """
        Extract headers

        :param carrier:
        :return:
        """
        if not isinstance(carrier, dict):
            raise InvalidCarrierException('carrier not a dictionary')
        lowercase_keys = dict([(k.lower(), k) for k in carrier])
        trace_id = carrier.get(lowercase_keys.get(self.trace_header.lower()))
        span_id = carrier.get(lowercase_keys.get(self.span_header.lower()))
        testing = carrier.get(lowercase_keys.get(self.testing_header.lower()))
        return SpanContext(trace_id=trace_id, span_id=span_id, testing=testing)


class Tracer(opentracing.Tracer):
    """
    Add "service_name" attribute for logging
    """
    _supported_formats = [Format.HTTP_HEADERS]

    def __init__(self, service_name, scope_manager=None):
        """Add "service_name" to tracer"""
        self._scope_manager = scope_manager if scope_manager else ScopeManager()
        self._noop_span_context = SpanContext(None, None, None)
        self._noop_span = Span(tracer=self, context=self._noop_span_context, operation_name=None)
        self._noop_scope = opentracing.Scope(self._scope_manager, self._noop_span)
        self.service_name = service_name

    def start_span(self,
                   operation_name=None,
                   child_of=None,
                   references=None,
                   tags=None,
                   start_time=None,
                   ignore_active_span=False):
        """Add "operation_name" to no-op span implementation"""
        self._noop_span = Span(tracer=self, context=self._noop_span_context, operation_name=operation_name)
        return self._noop_span

    def extract(self, format, carrier):
        """
        Extract headers:

            X-B3-SpanId
            X-B3-TraceId
            X-Testing

        :param format:
        :param carrier:
        :return:
        """
        if format == Format.HTTP_HEADERS:
            return Codec().extract(carrier)
        else:
            raise UnsupportedFormatException(format)

    def inject(self, span_context: SpanContext, format, carrier):
        """
        Inject headers

        :param span_context:
        :param format:
        :param carrier:
        :return:
        """
        if format == Format.HTTP_HEADERS:
            return Codec().inject(span_context, carrier)
        else:
            raise UnsupportedFormatException(format)


class StartSpan:
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
        if 'child_of' in kwargs:
            tracer = kwargs['child_of'].tracer

        self.span = None
        self.tracer = tracer
        self.args = args or ()
        self.kwargs = kwargs or {}
        self.operation_name = operation_name

    def __enter__(self):
        return self.start().__enter__()

    def __exit__(self, _exc_type, _exc_value, _exc_traceback):
        self.finish().__exit__(_exc_type, _exc_value, _exc_traceback)

    def __call__(self, func):
        @wraps(func)
        def decorated(*args, **kwargs):     # NOSONAR
            with self.start():
                result = func(*args, **kwargs)
                self.finish()
                return result
        return decorated

    def _get_service_name(self):
        return self.tracer.service_name if hasattr(self.tracer, 'service_name') else 'unknown'

    def start(self):
        self.tracer = self.tracer or global_tracer()
        self.span = self.tracer.start_span(self.operation_name, *self.args, **self.kwargs)
        logger.debug("Starting span [%s] for service [%s]", self.operation_name, self._get_service_name())
        return self.span

    def finish(self):
        logger.debug("Finishing span [%s] for service [%s]", self.operation_name, self._get_service_name())
        return self.span


start_span = StartSpan   # backward compatibility


def get_service_name():
    """
    Returns the service name, try to get from config or fallback to skill name.

    :return:
    """
    from .config import config
    return config.get('skill', 'name', fallback='unnamed_service')


def start_active_span(operation_name, request, **kwargs):
    """Start a new span and return activated scope"""
    tracer: Tracer = global_tracer()

    tags = kwargs.get('tags', {})
    if hasattr(request, 'url'):
        tags.update({'http.url': request.url})
    if hasattr(request, 'remote_addr'):
        tags.update({'peer.ipv4': request.remote_addr})
    if hasattr(request, 'caller_name'):
        tags.update({'peer.service': request.caller_name})

    logger.debug('Starting active span [%s] for service [%s]', operation_name, getattr(tracer, "service_name", "unknown"))
    headers = {key: value for key, value in request.headers.items()}
    logger.debug('HTTP-Header: %s', repr(headers))
    context = tracer.extract(format=Format.HTTP_HEADERS, carrier=headers)
    return tracer.start_active_span(operation_name, child_of=context, tags=tags, **kwargs)


def initialize_tracer(tracer=None):
    """ Initialize dummy tracer: to be replaced by actual implementation

    :return:
    """
    tracer = tracer or Tracer(get_service_name())
    set_global_tracer(tracer)
