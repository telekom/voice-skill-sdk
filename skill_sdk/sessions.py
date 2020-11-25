#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

#
# Invoke request session
#

import logging


MAX_SESSION_STORAGE_SIZE = 4096

logger = logging.getLogger(__name__)


class SessionOversizeError(Exception):
    '''
    an exception raised when the current action would increase the size of the session over
    :py:const:`MAX_SESSION_STORAGE_SIZE` bytes.
    '''


class SessionInvalidKeyError(Exception):
    '''
    This exception will be raised if a session key is an empty string.
    '''


class Session(dict):
    '''
    A session object that will persist between different of the intent that belong to one session.

    The session acts like a dictionary with a few limitation:

    * keys and values must by string, if they are not they are casted
    * keys must not be an empty string
    * the sum of all lengths of all keys and values must not exceed :py:const:`MAX_SESSION_STORAGE_SIZE`.

    The session is accessible as ``context.session`` in the intent handler.
    '''

    def __init__(self, session_id, new_session, *args, **kwargs):
        self.session_id = session_id
        self.new_session = new_session
        super().__init__(*args, **kwargs)

    def get_storage_size(self):
        '''
        Calculates the storage size of the session.
        '''
        size = sum(len(k) + len(v) for (k, v) in self.items())
        logger.debug('Size of session %s is now %s', self.session_id, size)
        return size

    def update(self, e=None, **kwargs):
        '''
        Replacement of the original update method to enforce the size limit by calling the overwritten
        :py:method:`__setitem__`.

        :param e: a dictionary with key/value pair to update with
        :param **kwargs: new key/value pairs can also be
        '''
        if e:
            for key, value in e.items():
                self[key] = value
        for key, value in kwargs.items():
            self[key] = value

    def __setitem__(self, key, value):
        '''
        Overwrites the original ``__setattr__` to enforce the limitations.
        '''
        key = key if isinstance(key, str) else str(key)
        value = value if isinstance(value, str) else str(value)
        if not key:
            raise SessionInvalidKeyError('Session key can not be empty strings')
        old_value = self.get(key)
        dict.__setitem__(self, key, value)
        if self.get_storage_size() > MAX_SESSION_STORAGE_SIZE:
            if old_value is not None:
                self.__setitem__(key, old_value)
            raise SessionOversizeError('Storing the value "{}" into "{}" will exceed the max. session size of {}.'
                                       .format(value, key, MAX_SESSION_STORAGE_SIZE))
