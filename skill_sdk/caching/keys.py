#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

#
# Function call keys
#

import pickle
import logging
from hashlib import sha512
from skill_sdk.config import config

logger = logging.getLogger(__name__)


class FunctionCallKeyGenerator:
    """ Generate function call key (as bytes object)
            {prefix}{function name/arguments}

    """

    def __init__(self, prefix=None, hashing=True, type_safe=False, protocol: int = pickle.DEFAULT_PROTOCOL):
        """ Constructor

        :param prefix:      skill name
        :param hashing:     if True, the key will be hashed with sha512
        :param type_safe:   if True, more verbose key generated (including __qualname__ and type)
        """
        if not prefix:
            prefix = config.get('skill', 'name', fallback='unnamed_service')
        logger.debug('Initializing FunctionCallKeyGenerator with hashing=%s and type_safe=%s', hashing, type_safe)
        self.prefix = prefix
        self.hashing = hashing
        self.type_safe = type_safe
        self.protocol = protocol

    def __call__(self, callable_, args, kwargs):
        """ Generator

        :param callable_:
        :param args:
        :param kwargs:
        :return:
        """
        logger.debug('Generating key for %s; %s; %s', callable, args, kwargs)
        format_string = '{c.__qualname__}_{c.__class__.__qualname__}' if self.type_safe else '{c.__qualname__}'
        callable_string = format_string.format(c=callable_)

        args_bytes = pickle.dumps((callable_string, args, kwargs), protocol=self.protocol)

        logger.debug('intermediate key: %s', args_bytes)

        if self.hashing:
            args_bytes = sha512(args_bytes).digest()

        key = self.prefix.encode() + b'_' + args_bytes
        logger.debug('resulting key: %s', key)
        return key
