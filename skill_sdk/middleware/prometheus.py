#
#
# voice-skill-sdk
#
# (C) 2021, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

"""Prometheus middleware"""

import time
import logging
from functools import partial, wraps
from typing import Any, Callable, Text
from contextlib import contextmanager, ContextDecorator
from fastapi import FastAPI
import httpx

from skill_sdk.config import settings

logger = logging.getLogger(__name__)

HTTP_REQUESTS_LATENCY_SECONDS = "http_requests_latency_seconds"
HTTP_PARTNER_REQUEST_COUNT = "http_partner_request_count"

try:
    from starlette_exporter import PrometheusMiddleware, handle_metrics
    from prometheus_client import Counter, Histogram
except ModuleNotFoundError:
    logger.error(
        '"PrometheusMiddleware" not found. Extra package is not installed. '
        'Make sure to install "skill-sdk[all]" to export Prometheus metrics.'
    )
    raise


class Prometheus(PrometheusMiddleware):
    """Middleware factory"""

    @staticmethod
    def requests_latency():
        """HTTP requests latency histogram"""

        metric_name = HTTP_REQUESTS_LATENCY_SECONDS
        if metric_name not in PrometheusMiddleware._metrics:
            PrometheusMiddleware._metrics[metric_name] = Histogram(
                metric_name,
                "HTTP Requests Latency in second",
                ("job", "version", "operation"),
            )
        return PrometheusMiddleware._metrics[metric_name]

    @staticmethod
    def partner_requests_count():
        """HTTP requests to partner services counter"""

        metric_name = HTTP_PARTNER_REQUEST_COUNT
        if metric_name not in PrometheusMiddleware._metrics:
            PrometheusMiddleware._metrics[metric_name] = Counter(
                metric_name,
                "HTTP Requests for services",
                ("job", "partner_name", "status"),
            )
        return PrometheusMiddleware._metrics[metric_name]


class prometheus_latency(ContextDecorator):  # noqa
    """
    Prometheus latency wrapper. Can be used as context manager and decorator:

        >>> # As context manager:
        >>> with prometheus_latency("operation_name"):
        >>>     ...

        >>> # As decorator:
        >>> @prometheus_latency("operation_name")
        >>> def decorated():
        >>>     ...

    """

    def __init__(self, operation_name: Text):
        self.operation_name = operation_name

    def __enter__(self):
        self.begin = time.perf_counter()

    def __exit__(self, exc_type, exc, exc_tb):
        end = time.perf_counter()

        labels = [settings.SKILL_NAME, settings.SKILL_VERSION, self.operation_name]
        Prometheus.requests_latency().labels(*labels).observe(end - self.begin)


def _inc_partner_call(partner_name: Text, response: httpx.Response) -> None:
    try:
        status_code = response.status_code
        labels = [settings.SKILL_NAME, partner_name, status_code]
        Prometheus.partner_requests_count().labels(*labels).inc()
    except AttributeError as ex:
        logger.error("Cannot log a partner call: %s", repr(ex))


@contextmanager
def partner_call(partner_name: Text, func: Callable[..., Any]):
    """
    Context manager to count HTTP requests to partner service

        >>> with partner_call('partner-service', client.get) as get:
        >>>     response = get(URL)

    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        """
        The actual logic: collect status code from wrapped function call and increase a metric counter

        :param args:
        :param kwargs:
        :return:
        """
        response = func(*args, **kwargs)
        _inc_partner_call(partner_name, response)

        return response

    yield wrapper


def count_partner_calls(partner_name: Text) -> Callable[[httpx.Response], None]:
    """
    Response hook to count HTTP requests to partner service,
    can be attached to `skill_sdk.requests.Client`/`AsyncClient`

        >>> from skill_sdk.requests import AsyncClient
        >>> from skill_sdk.middleware.prometheus import count_partner_calls
        >>>
        >>> async with AsyncClient(
        >>>     response_hook=count_partner_calls('partner-service')
        >>> ) as client:
        >>>     response = await client.get(URL)

    """

    return partial(_inc_partner_call, partner_name)


def setup(app: FastAPI) -> None:
    """
    Setup the Prometheus exporter middleware,
    and an app route to export the metrics

    :param app:
    :return:
    """

    app.add_middleware(
        Prometheus,
        app_name=settings.SKILL_NAME,
        prefix="http",
    )

    route = getattr(settings, "PROMETHEUS_ENDPOINT", "/prometheus")
    app.add_route(route, handle_metrics)
