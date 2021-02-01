#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

#
# Describes Python Skill SDK in OpenAPI format
#

import yaml
import inspect
import logging
import pathlib
from typing import Dict, List
from apispec import APISpec

from . import routes
from .entities import AttributeV2, snake_to_camel
from .config import config
from .intents import Context, Intent
from .skill import get, app

logger = logging.getLogger()
HERE = pathlib.Path(__file__).parent


def attrs_examples(intent: Intent) -> Dict[str, List]:
    """ Create attribute samples for intent

    :param intent:
    :return:
    """

    # Extract parameter arguments from intent implementation
    parameters = {name: param for name, param in inspect.signature(intent.implementation).parameters.items()
                  if not (isinstance(param.annotation, type) and issubclass(param.annotation, Context))}

    # 'timezone' is always present
    if 'timezone' not in parameters:
        parameters['timezone'] = inspect.Parameter('timezone', inspect.Parameter.KEYWORD_ONLY, default='UTC')

    def value(param):
        """ Try to set value to an attribute """
        return param.default if param.default and param.default != inspect.Parameter.empty else 'value'

    attrs_v2 = {name: [AttributeV2({'value': value(param)}).dict()] for name, param in parameters.items()}

    return attrs_v2


def intent_examples(intents: Dict[str, Intent]) -> Dict[str, Dict]:
    """ Create example intent calls

    :param intents: List of intents
    :return:
    """
    examples = {f"{snake_to_camel(name)}Example": {
        'summary': name,
        'value': {
            'context': {
                'intent': name,
                'attributesV2': attrs_examples(intent),
                'configuration': {},
                'locale': 'de',
                'tokens': {}
            },
            'session': {
                'id': 123,
                'new': True,
                'attributes': {
                    'attr-1': 1,
                    'attr-2': '2'
                }
            }
        },
    } for name, intent in intents.items()}

    return examples


def render(iterable, **kwargs):
    """ Replace placeholders in a template """
    for value in iterable:
        for key, item in kwargs.items():
            value = value.replace(key, item)
        yield value


def create_spec(swagger_template=pathlib.Path(HERE / 'swagger.yml')):
    """ Load definitions from `swagger.yml`

    :param swagger_template:
    :return:
    """

    intents: Dict[str, Intent] = app().get_intents()

    auth_requested = bool(config.get('skill', 'auth', fallback=None) == 'basic'
                          and config.get('skill', 'api_key', fallback=None))

    security = [{'BasicAuth': ['read', 'write']}] if auth_requested else []

    try:

        with open(swagger_template, 'r') as stream:
            template = render(stream, API_BASE=routes.api_base(),
                              EXAMPLES=str(intent_examples(intents)),
                              INTENTS=str(intents.keys()),
                              SECURITY=str(security))

            # Create an APISpec
            spec = APISpec(
                title=config.get('skill', 'name'),
                version=config.get('skill', 'version'),
                openapi_version='3.0.1',
                info=dict(
                    description=config.get('skill', 'description', fallback=config.get('skill', 'name'))
                ),
                **yaml.safe_load(''.join(template))
            )

    except (yaml.YAMLError, OSError, FileNotFoundError) as e:
        logger.error("Can't load specification from %s: %s", swagger_template, repr(e))
        return None

    return spec


def swag(fmt: str = 'json'):
    """ Expose swagger.[json|yaml]

    :param fmt: output format [json|yaml]
    :return:
    """
    spec = create_spec()
    return spec.to_yaml() if fmt in ('yaml', 'yml') else spec.to_dict()


get('/v1/swagger.<fmt>', callback=swag)
