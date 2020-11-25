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
# Distributed tracing (Jaeger)
#

import logging
from jaeger_client import Config

from skill_sdk.config import config

logger = logging.getLogger(__name__)


def setup_service():
    """ Initialize global Jaeger tracer

    :param config:          Optional tracer configuration
    :return:
    """
    service_config = config.get("jaeger", "config", fallback={'propagation': 'b3'})     # Backward compat Zipkin's B3
    logger.debug("Initializing tracer with %s", service_config)
    tracer_config = Config(config=service_config, service_name=get_service_name(), validate=True)
    tracer_config.initialize_tracer()


def get_service_name():
    """ Returns the service name, try to get from config or fallback to skill name.

    :return:
    """
    from skill_sdk.config import config
    return config.get('jaeger', 'service_name', fallback=config.get('skill', 'name', fallback='unnamed_service'))
