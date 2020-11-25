#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

#
# Local (L1) cache
#

from collections import OrderedDict
from itertools import count
import logging
import time

from skill_sdk.tracing import start_span

from skill_sdk.caching.exceptions import KeyNotFoundException

logger = logging.getLogger(__name__)

# after how man sets a validate is called.
CLEAN_UP_INTERVAL = 1000


class LocalCacheItem:
    """
    An item in the local cache.

    Carries the payload (data) and some metadata.
    """

    def __init__(self, payload):
        self.created = time.time()
        self.last_read = time.time()
        self._payload = payload

    @property
    def age(self):
        """ Get total item age """
        return time.time() - self.created

    @property
    def not_read_for(self):
        """ Get total unread time """
        return time.time() - self.last_read

    def touch(self):
        """ Set last_read to current time. """
        self.last_read = time.time()

    @property
    def payload(self):
        """ Return payload and mark item as read.  """
        self.touch()
        return self._payload


class BaseLocalCache:
    """
    Base class for all local caches.
    """

    def __init__(self):
        self.clean_up_counter = count(1)
        self.data = {}

    def __len__(self):
        return len(self.data)

    @property
    def name(self):
        return '{}'.format(self.__class__.__name__)

    def get(self, key):
        try:
            return self.data.__getitem__(key).payload
        except KeyError as e:
            raise KeyNotFoundException(*e.args) from e

    def get_no_conditions(self, key):
        try:
            return self.data.__getitem__(key).payload
        except KeyError as e:
            raise KeyNotFoundException(*e.args) from e

    def get_and_should_be_updated(self, key):
        return self.get(key), False

    def set(self, key, value):
        if not isinstance(value, LocalCacheItem):
            value = LocalCacheItem(value)
        self.data[key] = value
        self._validate_hook()

    def delete(self, key):
        if key in self.data:
            del self.data[key]

    def touch(self, key):
        try:
            self.data.__getitem__(key).touch()
        except KeyError as e:
            raise KeyNotFoundException(*e.args) from e

    def purge(self):
        logger.debug('Purging cache.')
        self.data.clear()

    def _validate_hook(self):
        if not (next(self.clean_up_counter) % CLEAN_UP_INTERVAL):
            logger.debug('Cache validate hook triggered.')
            self.validate()

    def validate(self):
        pass


class LocalFIFOCache(BaseLocalCache):
    """
    A cache with a maximum number of entries. If full the oldest item will be removed.
    """

    def __init__(self, max_size=100):
        logger.debug('Initializing %s with max_size %d', self.__class__.__name__, max_size)
        self.clean_up_counter = count(1)
        self.data = OrderedDict()
        self.max_size = max_size

    @property
    def name(self):
        return '{} size {}'.format(self.__class__.__name__, self.max_size)

    def set(self, key, value):
        BaseLocalCache.set(self, key, value)
        self.validate()

    @start_span('validate cache')
    def validate(self):
        while len(self) > self.max_size:
            self.data.popitem(last=False)


class LocalLRUCache(LocalFIFOCache):
    """
    A cache with a maximum number of entries.

    If full the item that was not read the longest will be removed.
    """

    def get(self, key):
        try:
            value = self.data.__getitem__(key).payload
            self.data.move_to_end(key)
            return value
        except KeyError as e:
            raise KeyNotFoundException(*e.args) from e


class CacheControlLocalLRUCache(LocalLRUCache):
    """
    Special cache for CacheControl with ugly workaround for ugly code.

    CacheControl uses `self.cache = cache or DictCache()`.
    Empty caches are considered False and can't be applied.

    """

    def __bool__(self):
        return True

    def close(self):
        pass

    def get(self, key):
        try:
            return super().get(key)
        except KeyError:
            return None


class LocalTimeoutCache(BaseLocalCache):
    """
    A cache where the item have a maximum lifetime.
    Item expired will be removed on validate().
    """

    def __init__(self, timeout=60):
        logger.debug('Initializing %s with timeout %d', self.__class__.__name__, timeout)
        self.clean_up_counter = count(1)
        self.data = OrderedDict()
        self.timeout = timeout

    @property
    def name(self):
        return '{} timeout {}'.format(self.__class__.__name__, self.timeout)

    def get(self, key):
        try:
            item = self.data.__getitem__(key)
            if item.age > self.timeout:
                self.delete(key)
                raise KeyNotFoundException(key)
            return item.payload
        except KeyError as e:
            raise KeyNotFoundException(*e.args) from e

    @start_span('validate cache')
    def validate(self):
        for key in list(self.data.keys()):
            try:
                if self.data[key].age > self.timeout:
                    self.delete(key)
                else:
                    break
            except (KeyNotFoundException, KeyError):
                pass


class LocalSoftTimeoutCache(LocalTimeoutCache):
    """
    A cache where the item have a maximum lifetime and a threshold as a decimal fraction between 0 and 1.

    Item expired will be removed on validate().

    Items with an age greater than threshold * time will report to be updated on get_and_should_be_updated().

    """

    def __init__(self, timeout=60, threshold=0.75):
        logger.debug('Initializing %s with timeout %d and threshold %f', self.__class__.__name__, timeout, threshold)
        self.clean_up_counter = count(1)
        self.data = OrderedDict()
        self.timeout = timeout
        if not 0.0 < threshold < 1.0:
            raise ValueError('threshold must be larger than 0 and smaller than 1.')
        self.threshold = threshold

    @property
    def name(self):
        return '{} timeout {} threshold {:.2f}'.format(self.__class__.__name__, self.timeout, self.threshold)

    def get_and_should_be_updated(self, key):
        try:
            item = self.data.__getitem__(key)
            if item.age > self.timeout:
                self.delete(key)
                raise KeyNotFoundException(key)
            update = item.age >= self.timeout * self.threshold
            return item.payload, update
        except KeyError as e:
            raise KeyNotFoundException(*e.args) from e
