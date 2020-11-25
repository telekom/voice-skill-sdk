#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

#
# Caching decorators
#

import logging
from typing import List
from functools import wraps

from skill_sdk.tracing import start_span

from skill_sdk.caching.exceptions import KeyNotFoundException
from skill_sdk.caching.keys import FunctionCallKeyGenerator
from skill_sdk.caching.local import BaseLocalCache


logger = logging.getLogger(__name__)

CACHES_ACTIVE = False


def lazy_call(func, alt):
    """ Call `func` if caches active, otherwise call `alt` """
    return lambda *a, **kw: func(*a, **kw) if CACHES_ACTIVE else alt(*a, **kw)


class CallCache:
    """ Memoize decorator, caches function return value

        sample usage:

        @CallCache([LocalFIFOCache(100), LocalTimeoutCache(3600)])
        def function_to_cache(n):
            return n * 2
    """

    def __init__(self, cache_chain=None, ignore_first_argument=False):
        if (not isinstance(cache_chain, list)  # is list
                or not cache_chain  # not empty
                or not all(isinstance(c, BaseLocalCache) for c in cache_chain)):  # all cache instances
            raise ValueError('You need to specify a chain of cache instances as list of BaseLocalCache '
                             'subclass instances.')
        logger.debug('Initializing CallCache with Cache: %s', '; '.join(c.name for c in cache_chain))
        self.cache_chain = cache_chain
        self.ignore_first_argument = ignore_first_argument
        self.key_generator = FunctionCallKeyGenerator(hashing=True, type_safe=True)

    def __call__(self, func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            """ Wrap call in a tracing span with a cache request """
            with start_span(f'cached call: {func.__qualname__}') as span:
                key_args = args[1:] if self.ignore_first_argument else args

                key = self.key_generator(func, key_args, kwargs)
                value = self.get_value_from_cache(key, span)

                # The value was not found in any cache, execute function and update upstream.
                if value is None:
                    logger.debug('Cache miss.')
                    span.set_operation_name(f'{func.__qualname__} (miss)')
                    span.log_kv({'cache.miss': 'true'})
                    with start_span('original call'):
                        value = func(*args, **kwargs)
                    with start_span('update upstream caches'):
                        [cache.set(key, value) for cache in self.cache_chain]

                return value

        return lazy_call(wrapper, func)

    @staticmethod
    def update_down_stream(down_stream: List, key, value) -> None:
        with start_span('update downstream caches'):
            for down_stream_cache in down_stream:
                down_stream_cache.set(key, value)

    def get_value_from_cache(self, key, span):
        """ Get the value from cache

        :param key:
        :param span:
        :return:
        """
        value = None
        down_stream = []
        for cache in self.cache_chain:
            try:
                value = cache.get(key)
                logger.debug('Cache hit L%d.', len(down_stream) + 1)
                span.set_operation_name(f"{span.operation_name} (hit L{len(down_stream) + 1})")
                span.log_kv({'cache.hit': cache.name})
                if down_stream:
                    self.update_down_stream(down_stream, key, value)
            except KeyNotFoundException:
                down_stream.append(cache)
        return value
