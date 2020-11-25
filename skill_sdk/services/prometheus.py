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
# Prometheus metrics
#

import os
import logging
from contextlib import contextmanager
from tempfile import mkdtemp
from threading import active_count
from prometheus_client.exposition import generate_latest
from functools import wraps

from circuitbreaker import CircuitBreakerMonitor
from prometheus_client import core
from prometheus_client import multiprocess, Gauge, Counter, Histogram

from skill_sdk.routes import api_base
from skill_sdk.config import config
from skill_sdk.skill import app, get, install, request

logger = logging.getLogger(__name__)

in_progress_requests = Gauge("inprogress_requests", "help", multiprocess_mode='livesum')
thread_count = Gauge('thread_count', 'Current active threads')
open_circuit_breakers = Gauge('open_circuit_breakers', 'Currently open circuit breakers')
intent_gauge = Gauge('active_intents', 'Currently active intents')
http_requests_total = Counter('http_server_requests_seconds_count', 'HTTP Requests',
                              ['job', 'version', 'status', 'method', 'uri'])
http_requests_latency_seconds = Histogram("http_requests_latency_seconds", "HTTP Requests Latency in second",
                                          ['job', 'version', 'operation'])
http_partner_request_count_total = Counter('http_partner_request_count', 'HTTP Requests for services',
                                           ['job', 'partner_name', 'status'])


def update_stats():
    """ Update current mertics """
    intent_gauge.set(len(app().get_intents()))
    thread_count.set(active_count())
    open_circuit_breakers.set(sum(1 for _ in CircuitBreakerMonitor.get_open()))


@contextmanager
def partner_call(callback, partner_name: str):
    """ Context manager to count HTTP requests to partner services
            ...
            with partner_call(session.get, 'partner-service-name') as get:
                response = get(URL)

    """
    def wrapper(*args, **kwargs):   # NOSONAR
        response = callback(*args, **kwargs)
        http_partner_request_count_total.labels(job=config.get('skill', 'name'),
                                                partner_name=partner_name,
                                                status=response.status_code).inc()
        return response
    yield wrapper


def prometheus(callback):
    """ In-progress requests counter """

    @in_progress_requests.track_inprogress()
    def wrapper(*args, **kwargs):   # NOSONAR
        response = callback(*args, **kwargs)

        http_requests_total.labels(job=config.get('skill', 'name'),
                                   version=config.get('skill', 'version'),
                                   method=request.method,
                                   uri=request.fullpath,
                                   status=response.status_code).inc()

        return response

    return wrapper if request.path == api_base() else callback


class PrometheusLatency:
    """ Prometheus latency  wrapper. Can be used as decorator:
            ...

        # As decorator:
        @prometheus_latency('operation_name')
        def decorated():
            ...

    """

    def __init__(self, operation_name: str, *args, **kwargs):
        self.args = args or ()
        self.kwargs = kwargs or {}
        self.operation_name = operation_name

    def __call__(self, func):
        @wraps(func)
        def decorated(*args, **kwargs):     # NOSONAR
            with http_requests_latency_seconds.labels(job=config.get('skill', 'name'),
                                                      version=config.get('skill', 'version'),
                                                      operation=self.operation_name).time():
                return func(*args, **kwargs)
        return decorated


prometheus_latency = PrometheusLatency


@get('/prometheus')
def metrics():
    """ Prometheus metrics endpoint.
    ---
    get:
        description: Get Prometheus metrics
        responses:
            200:
                description: Prometheus metrics
        tags:
            - health
    """
    logger.debug('Metrics requests.')
    if os.getenv('prometheus_multiproc_dir'):
        logger.debug('Collecting from %s', repr(os.getenv('prometheus_multiproc_dir')))
    update_stats()
    return generate_latest()


def setup_service():
    """ Setup prometheus client """

    # Initialize multiprocessing mode
    workers = config.getint('http', 'workers', fallback=1)
    if workers > 1:
        if not os.getenv('prometheus_multiproc_dir'):
            tmp = mkdtemp()
            os.environ['prometheus_multiproc_dir'] = tmp
            logger.debug('Multiprocess collector is set to %s', repr(tmp))
        multiprocess.MultiProcessCollector(core.REGISTRY)

    # Install middleware
    install(prometheus)
