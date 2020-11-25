#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#

#
# Distributed tracing (Zipkin)
#

import os
import time
import json
import queue
import logging
import threading

from py_zipkin import zipkin
from opentracing.scope_managers import ThreadLocalScopeManager
from skill_sdk.config import config
from skill_sdk import tracing
import requests


logger = logging.getLogger(__name__)

# Read the reporting server URL from environment
config.read_environment('ZIPKIN_API_URL', 'zipkin', 'url')

# Deployment environment
SPAN_TAG_ENVIRONMENT = os.environ.get('SPAN_TAG_ENVIRONMENT', None)

# Default Zipkin collector URL
DEFAULT_ZIPKIN_API_URL = 'http://zipkin.opentracing.svc.cluster.local:9411/api/v1/spans'

# If service deployed to the cluster, use config value or default
ZIPKIN_API_URL = (SPAN_TAG_ENVIRONMENT and config.get("zipkin", "url", fallback=DEFAULT_ZIPKIN_API_URL))

QUEUE: queue.Queue = queue.Queue()


def setup_service():
    """ Setup Zipkin tracing service

    :return:
    """
    tracer = ZipkinTracer(service_name=get_service_name(),
                          port=config.getint('http', 'port', fallback=4242),
                          sample_rate=config.getfloat('zipkin', 'sample_rate', fallback=100.00),
                          transport_handler=queued_transport if ZIPKIN_API_URL else None)

    tracing.set_global_tracer(tracer)
    threading.Thread(target=zipkin_report_worker, daemon=True).start()


def get_service_name():
    """ Returns the service name, try to get from config or fallback to skill name.

    :return:
    """
    return config.get('zipkin', 'service_name', fallback=config.get('skill', 'name', fallback='unnamed_service'))


SAMPLED_FLAG = 0x01
DEBUG_FLAG = 0x02


def queued_transport(encoded_span):
    """  Put the span into the queue that is monitored by zipkin_report_worker

    @param encoded_span:
    @return:
    """
    if ZIPKIN_API_URL:
        QUEUE.put(encoded_span)


class B3Codec:
    """ https://github.com/openzipkin/b3-propagation

    """
    trace_header = 'X-B3-TraceId'
    span_header = 'X-B3-SpanId'
    parent_span_header = 'X-B3-ParentSpanId'
    sampled_header = 'X-B3-Sampled'
    flags_header = 'X-B3-Flags'

    def inject(self, span_context, carrier):
        """ Inject B3 headers

        :param span_context:
        :param carrier:
        :return:
        """
        if not isinstance(carrier, dict):
            raise tracing.InvalidCarrierException('carrier not a dictionary')
        carrier[self.trace_header] = span_context.trace_id
        carrier[self.span_header] = span_context.span_id
        if span_context.parent_id is not None:
            carrier[self.parent_span_header] = span_context.parent_id
        if int(span_context.flags) & DEBUG_FLAG == DEBUG_FLAG:
            carrier[self.flags_header] = '1'
        elif int(span_context.flags) & SAMPLED_FLAG == SAMPLED_FLAG:
            carrier[self.sampled_header] = '1'

    def extract(self, carrier):
        """ Extract B3 headers from a carrier

        :param carrier:
        :return:
        """
        if not isinstance(carrier, dict):
            raise tracing.InvalidCarrierException('carrier not a dictionary')
        lowercase_keys = dict([(k.lower(), k) for k in carrier])
        trace_id = carrier.get(lowercase_keys.get(self.trace_header.lower()))
        span_id = carrier.get(lowercase_keys.get(self.span_header.lower()))
        parent_id = carrier.get(lowercase_keys.get(self.parent_span_header.lower()))
        flags = 0x00
        sampled = carrier.get(lowercase_keys.get(self.sampled_header.lower()))
        if sampled == '1':
            flags |= SAMPLED_FLAG
        debug = carrier.get(lowercase_keys.get(self.flags_header.lower()))
        if debug == '1':
            flags |= DEBUG_FLAG
        return SpanContext(trace_id=trace_id, span_id=span_id,
                           parent_id=parent_id, flags=flags,
                           baggage=None)


class SpanContext(tracing.SpanContext):
    """ Current tracing context """

    __slots__ = ['trace_id', 'span_id', 'parent_id', 'flags', '_baggage']

    def __init__(self, trace_id, span_id, parent_id, flags, baggage=None):
        self.trace_id = trace_id
        self.span_id = span_id
        self.parent_id = parent_id or None
        self.flags = flags
        self._baggage = baggage or tracing.SpanContext.EMPTY_BAGGAGE


class Span(tracing.Span):
    """ Tracing span """

    def __init__(self, tracer, context, operation_name, span: zipkin.zipkin_span):
        """ Wrap Zipkin span
        """
        super(Span, self).__init__(tracer, context, operation_name)
        self._span = span

    def set_operation_name(self, operation_name):
        """ Set the operation name.

        :param operation_name: the new operation name
        :return: Returns the Span for chaining
        """
        super().set_operation_name(operation_name)
        self._span.override_span_name(operation_name)
        return self

    def log_kv(self, key_values, timestamp=None):
        """ Adds log record to the span

        :param key_values:
        :param timestamp:
        :return: itself, for call chaining.
        """
        key = json.dumps(key_values)
        self._span.annotations.update({key: timestamp or time.time()})
        return self

    def set_tag(self, key, value):
        """ Attach key/value pair to span

        :param key:     key or name of the tag. Must be a string.
        :param value:   value of the tag.
        :return:        itself, for call chaining.
        """
        self._span.update_binary_annotations({key: value})
        return self

    @property
    def flags(self):
        return self.context.flags

    def is_sampled(self):
        """ If this span is sampled """
        return self.context.flags & SAMPLED_FLAG == SAMPLED_FLAG

    def __enter__(self):
        """ Enable as context manager

        :return:
        """
        self._span.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """ Enable as context manager

        :param exc_type:
        :param exc_val:
        :param exc_tb:
        :return:
        """
        self._span.stop(exc_type, exc_val, exc_tb)

    def start(self):
        self._span.start()
        return self

    def finish(self, finish_time=None):
        self._span.stop()


class ZipkinTracer(tracing.Tracer):
    """ Minimal implementation of opentracing-compatible zipkin tracer
    """

    def __init__(self, service_name, port, sample_rate, transport_handler=None, scope_manager=None):
        super().__init__(service_name, scope_manager=scope_manager or ThreadLocalScopeManager())
        self._port = port
        self._sample_rate = sample_rate
        self._transport_handler = transport_handler or queued_transport

    def start_active_span(self, operation_name=None,
                          child_of=None,
                          references=None,
                          tags=None,
                          start_time=None,
                          ignore_active_span=False,
                          finish_on_close=True):

        """ Create a parent Zipkin span and activate the scope
            This should be the outer-most span inside the skill

        """
        span = self.start_span(
            operation_name,
            child_of,
            references,
            tags,
            start_time,
            ignore_active_span,
        )
        return self.scope_manager.activate(span.start(), finish_on_close)

    def start_span(self,
                   operation_name=None,
                   child_of=None,
                   references=None,
                   tags=None,
                   start_time=None,
                   ignore_active_span=False):

        logger.debug("Starting Zipkin span [%s] for service [%s]", operation_name, self.service_name)

        parent: Span = self.active_span if self.active_span and not ignore_active_span else child_of

        if parent is None:
            zipkin_attrs = zipkin.create_attrs_for_span(self._sample_rate)
        else:
            zipkin_attrs = zipkin.ZipkinAttrs(
                trace_id=parent.trace_id or zipkin.generate_random_64bit_string(),
                span_id=zipkin.generate_random_64bit_string(),
                parent_span_id=parent.span_id,
                flags=parent.flags,
                is_sampled=int(parent.flags) & SAMPLED_FLAG == SAMPLED_FLAG,
            )
        logger.debug('ZipkinAttrs: %s', repr(zipkin_attrs))

        zipkin_span = zipkin.zipkin_span(
            service_name=self.service_name,
            zipkin_attrs=zipkin_attrs,
            span_name=operation_name,
            transport_handler=self._transport_handler,
            port=self._port,
            sample_rate=self._sample_rate,
            binary_annotations=dict({
                'span.tag.environment': SPAN_TAG_ENVIRONMENT,
                'span.tag.service': self.service_name,
            }, **(tags or {}))
        )

        context = SpanContext(*zipkin_attrs)
        return Span(self, context, operation_name, zipkin_span)

    def extract(self, format, carrier):
        """ Extract B3 headers

        :param format:
        :param carrier:
        :return:
        """
        if format == tracing.Format.HTTP_HEADERS:
            return B3Codec().extract(carrier)
        else:
            raise tracing.UnsupportedFormatException(format)

    def inject(self, span_context: SpanContext, format, carrier):
        """ Inject B3 headers

        :param span_context:
        :param format:
        :param carrier:
        :return:
        """
        if format == tracing.Format.HTTP_HEADERS:
            return B3Codec().inject(span_context, carrier)
        else:
            raise tracing.UnsupportedFormatException(format)


def zipkin_report_worker():
    """ Zipkin report worker: listens to QUEUE and asynchronously reports spans to the server

    :return:
    """
    logger.info('Starting Zipkin reporter for service: [%s]', get_service_name())

    while True:
        try:
            span = QUEUE.get()
            logger.debug('Sending %s bytes to server...', len(span))

            # Post encoded data to Zipkin collector
            result = requests.post(
                url=ZIPKIN_API_URL,
                data=span,
                headers={'Content-Type': 'application/x-thrift'},
            )
            logger.debug('Zipkin server result: %s', repr(result))
        except Exception as ex:
            logger.error('Zipkin reporter failed for service [%s]: %s', get_service_name(), repr(ex))

        QUEUE.task_done()
