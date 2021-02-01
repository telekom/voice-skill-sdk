#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# Deutsche Telekom AG and all other contributors /
# copyright owners license this file to you under the MIT
# License (the "License"); you may not use this file
# except in compliance with the License.
# You may obtain a copy of the License at
#
# https://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

import importlib
import contextlib
from typing import Callable, ContextManager

from . import manage

from .skill import (
    initialize,
    intent_handler,
    test_intent
)

from .intents import (
    Context,
    context
)

from .sessions import Session

from .responses import (
    Card,
    Response,
    Reprompt,
    ask,
    tell,
    ask_freetext
)


def lazy_load(
        module: str,
        attr: str
) -> Callable[..., ContextManager]:
    """ Lazy load a context manager from module, return `contextlib.suppress` (no-op) if loading failed

    :param module:  Module name
    :param attr:    Context manager name
    :return:
    """
    def wrapper(*args) -> ContextManager:
        """ Get a context manager
        """
        try:
            cls = getattr(importlib.import_module(module, __package__), attr)
        except (AttributeError, ModuleNotFoundError):
            cls = contextlib.suppress
        return cls(*args)
    return wrapper


K8sChecks = lazy_load('.services.k8s', 'K8sChecks')
RequiredForReadiness = lazy_load('.services.k8s', 'required_for_readiness')

# flake8: noqa
