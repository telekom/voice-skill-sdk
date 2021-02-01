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
# Skill service adapters
#

from typing import Any


def setup_services():
    """ Load optional cloud services

    :return:
    """
    import importlib
    from ..config import config
    from . import log   # noqa: F401

    def setup(service_name: str):
        """ Setup service: each submodule implements the function """

        try:
            module_name = '.' + service_name.split('-')[-1]
            # Type hint to prevent MyPy error: Module has no attribute "setup_service"
            service: Any = importlib.import_module(module_name, __name__)
            service.setup_service()
        except ModuleNotFoundError:
            pass

    [setup(service) for service in ('zipkin', 'jaeger', 'service-text', 'service-location')
     if config.active(service)]

    setup('prometheus')
