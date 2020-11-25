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
# Kubernetes ready/alive endpoints
#

import logging
from typing import Set
from uuid import uuid1
from functools import wraps

from skill_sdk.skill import get, HTTPResponse

logger = logging.getLogger(__name__)


class K8sChecks:
    """ Readiness checks """

    ready_checks: Set[str] = set()

    def __init__(self, name):
        self.name = name

    @classmethod
    def register_ready_check(cls, name):
        cls.ready_checks.add(name)
        logger.debug(f'k8s check {name}')

    @classmethod
    def report_ready(cls, name):
        cls.ready_checks.discard(name)
        logger.debug(f'k8s {name} ready')

    @classmethod
    def ready(cls):
        return not cls.ready_checks

    def __enter__(self):
        self.register_ready_check(self.name)

    def __exit__(self, _exc_type, _exc_value, _exc_traceback):
        if not _exc_type:
            self.report_ready(self.name)


def required_for_readiness(name: str = None):
    """ Decorator to activate "Not Ready" lock on entry,
        will be released, when a decorated function completed

    :param name:
    :return:
    """
    name = name or str(uuid1())

    def wrapper(func):      # NOSONAR
        @wraps(func)
        def inner(*args, **kwargs):     # NOSONAR
            with K8sChecks(name):
                return func(*args, **kwargs)
        return inner
    return wrapper


@get('/k8s/liveness')
def liveness():
    """ K8s liveness endpoint.
    ---
    get:
        description: Tell kubernetes if we are alive
        responses:
            200:
                description: Success
        tags:
            - health
    """
    logger.debug('Liveness probe.')
    return 'alive'


@get('/k8s/readiness')
def readiness():
    """ K8s readiness endpoint.
    ---
    get:
        description: Tell kubernetes if we are ready
        responses:
            200:
                description: Ready
            503:
                description: Not ready
        tags:
            - health
    """
    logger.debug('Readiness probe...')
    if K8sChecks.ready():
        logger.debug('...ready')
        return 'ready'

    logger.error('...NOT ready')
    return HTTPResponse(status=503, body=str(K8sChecks.ready_checks))
