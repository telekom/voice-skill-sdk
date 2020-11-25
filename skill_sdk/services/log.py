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
# Cloud logging
#

import os
import logging

logger = logging.getLogger(__name__)

# Default log levels per environment
ENVIRONMENT_LOG_LEVELS = {
    "skill-edge": "DEBUG",
    "platform-edge": "DEBUG",
    "integration": "DEBUG",
    "staging": "DEBUG"
}

# Deployment environment
SPAN_TAG_ENVIRONMENT = os.getenv("SPAN_TAG_ENVIRONMENT", 'None')

# Default log level for current environment
DEFAULT_LOG_LEVEL = ENVIRONMENT_LOG_LEVELS.get(SPAN_TAG_ENVIRONMENT, "ERROR")

# Log level set in current environment
LOG_LEVEL = os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL)
logging.basicConfig(level=LOG_LEVEL)

logger.debug(f'Environment: "{SPAN_TAG_ENVIRONMENT}", logging level: "{LOG_LEVEL}"')
