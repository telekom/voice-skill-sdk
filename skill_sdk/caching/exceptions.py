#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

#
# Caching exceptions
#


class KeyNotFoundException(KeyError):
    """ The given key could not be found in the cache """
