#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

#
# Logging
#

import os
import time
import json
import inspect
import logging
from traceback import format_exc
from . import tracing

# Default log level: DEBUG
LOG_LEVEL = os.environ.get("LOG_LEVEL", "DEBUG")

# Default log format: GELF
LOG_FORMAT = os.environ.get('LOG_FORMAT', 'gelf')

# Maximal length of a string to log
LOG_ENTRY_MAX_STRING = 253


logging.basicConfig(level=LOG_LEVEL)


class SmartHubGELFFormatter(logging.Formatter):
    """ Graylog Extended Format (GELF) formatter
    """

    def format(self, record):
        """ Formats a record """

        tracer: tracing.Tracer = tracing.global_tracer()
        span: tracing.Span = tracer.active_span

        line = {
            # Timestamp in milliseconds
            "@timestamp": int(round(time.time() * 1000)),
            # Log message level
            "level": record.levelname,
            # Process id
            "process": os.getpid(),
            # Thread id
            "thread": str(record.thread),
            # Logger name
            "logger": record.name,
            # Log message
            "message": record.getMessage(),
            # Trace id
            "traceId": getattr(span, 'trace_id') if span else None,
            # Span id
            "spanId": getattr(span, 'span_id') if span else None,
            # Tenant: a skill is not aware of tenant, so we report a service name instead
            "tenant": getattr(tracer, 'service_name', tracing.get_service_name())
        }
        if record.exc_info:
            line['_traceback'] = format_exc()

        return json.dumps(line)


conf = {
    'gelf': {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {'class': 'skill_sdk.log.SmartHubGELFFormatter'},
        },
        'handlers': {
            'default': {
                'level': LOG_LEVEL,
                'formatter': 'standard',
                'class': 'logging.StreamHandler',
            },
        },
        'loggers': {
            '': {
                'handlers': ['default'],
                'level': LOG_LEVEL,
                'propagate': True
            },
        }
    },
    'human': {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'default': {
                'level': LOG_LEVEL,
                'class': 'logging.StreamHandler',
            },
        },
        'loggers': {
            '': {
                'handlers': ['default'],
                'level': LOG_LEVEL,
                'propagate': True
            },
            'pip': {
                'handlers': ['default'],
                'level': 'WARN',
                'propagate': True
            },

        }
    }
}

#
#   Under Windows we're going to run without Gunicorn anyway
#
try:
    from gunicorn.glogging import Logger

    class GunicornLogger(Logger):
        """ A logger to force gunicorn to log in the format defined by us.
        """

        def setup(self, cfg):
            self.loglevel = getattr(logging, LOG_LEVEL)
            self.error_log.setLevel(self.loglevel)
            self.access_log.setLevel(logging.INFO)

            self.error_log.name = 'gunicorn'
            self._set_handler(self.error_log, cfg.errorlog, SmartHubGELFFormatter())
            self._set_handler(self.access_log, cfg.errorlog, SmartHubGELFFormatter())

# Handle `no module named 'fcntl'`
except ModuleNotFoundError:         # pragma: no cover
    pass


###############################################################################
#                                                                             #
#  Helper functions: hide tokens, limit log message size                      #
#                                                                             #
###############################################################################
def get_logger(name: str = None):
    """ Logging wrapper: return logger by name if supplied or construct one with caller's name

    :param name:
    """
    if name:
        return logging.getLogger(name)
    frame = inspect.stack()[1]
    caller = inspect.getmodule(frame[0])
    return logging.getLogger(caller.__name__ if caller else 'Unknown')


def _trim(s):
    """ Trim long string to LOG_ENTRY_MAX_STRING(+3) length """
    return s if not isinstance(s, str) or len(s) < LOG_ENTRY_MAX_STRING else s[:LOG_ENTRY_MAX_STRING] + '...'


def _copy(d):
    """ Recursively copy the dictionary values, trimming long strings """
    if isinstance(d, dict):
        return {k: _copy(v) for k, v in d.items()}
    elif isinstance(d, (list, tuple)):
        return [_copy(v) for v in d]
    else:
        return _trim(d)


def hide_tokens(request):
    """ Hide tokens in a request """
    if 'context' in request:
        [request['context']['tokens'].update({key: '*****'})
         for key in (request['context']['tokens'] if 'tokens' in request['context'] else [])]
    return request


def prepare_for_logging(request):
    """ Replace tokens and trim long strings before logging a request

    :param request:
    :return:
    """
    if not isinstance(request, dict):
        return request

    return hide_tokens(_copy(request))
