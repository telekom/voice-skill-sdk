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
    """ define "trace_id"/"span_id" attributes for logging
    """
    __slots__ = ['trace_id', 'span_id']

    def __init__(self, trace_id, span_id):
        self.trace_id = trace_id
        self.span_id = span_id


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
        self._noop_span = Span(tracer=None, context=SpanContext(None, None), operation_name=None)
        self._noop_scope = opentracing.Scope(self, self._noop_span)


class Tracer(opentracing.Tracer):
    """ define "service_name" attribute for logging
    """
    def __init__(self, service_name, scope_manager=None):
        """ Add "service_name" to tracer
        """
        self._scope_manager = scope_manager if scope_manager else ScopeManager()
        self._noop_span_context = SpanContext(None, None)
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
        """ Add "operation_name" to no-op span implementation
        """
        self._noop_span = Span(tracer=self, context=self._noop_span_context, operation_name=operation_name)
        return self._noop_span


class start_span:   # NOSONAR: backward compatibility
    """ Tracing helper/span wrapper. Can be used as both context manager and decorator:

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
        logger.debug(f"Starting span [{self.operation_name}] for service [{self._get_service_name()}]")
        return self.span

    def finish(self):
        logger.debug(f"Finishing span [{self.operation_name}] for service [{self._get_service_name()}]")
        return self.span


def get_service_name():
    """ Returns the service name, try to get from config or fallback to skill name.

    :return:
    """
    from .config import config
    return config.get('skill', 'name', fallback='unnamed_service')


def start_active_span(operation_name, request, **kwargs):
    """ Start a new span and return activated scope
    """
    tracer: Tracer = global_tracer()

    tags = kwargs.get('tags', {})
    if hasattr(request, 'url'):
        tags.update({'http.url': request.url})
    if hasattr(request, 'remote_addr'):
        tags.update({'peer.ipv4': request.remote_addr})
    if hasattr(request, 'caller_name'):
        tags.update({'peer.service': request.caller_name})

    logger.debug(f'Starting active span {operation_name} for service {getattr(tracer, "service_name", "unknown")}')
    headers = {key: value for key, value in request.headers.items()}
    logger.debug(f'HTTP-Header: {headers}')
    context = tracer.extract(format=Format.HTTP_HEADERS, carrier=headers)
    return tracer.start_active_span(operation_name, child_of=context, tags=tags, **kwargs)


def initialize_tracer(tracer=None):
    """ Initialize dummy tracer: to be replaced by actual implementation

    :return:
    """
    tracer = tracer or Tracer(get_service_name())
    set_global_tracer(tracer)
