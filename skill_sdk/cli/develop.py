#
# voice-skill-sdk
#
# (C) 2021, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

"""CLI: "develop" command"""

#
#   - starts skill-designer
#   - starts skill in development mode
#   - displays skill logs in "Test -> log output"
#   - modifies Python sources in "Design"
#

import argparse
import logging
from contextlib import closing

import uvicorn

from skill_sdk.cli import import_module_app

logger = logging.getLogger(__name__)


def execute(arguments):
    """
    Run the app in "development" mode:

        set logging level to DEBUG
        logging format to human-readable
        override debug flag from configuration
        initialize Designer UI

    :param arguments:
    :return:
    """
    from skill_sdk import config, log, skill

    log.setup_logging(logging.DEBUG, config.FormatType.HUMAN)

    module_str, _, app_str = arguments.module.partition(":")
    config.settings.SKILL_DEBUG = True

    module, app = import_module_app(arguments.module)
    if app is None:
        app = skill.init_app()

    logger.info("Loaded app: %s", repr(app))
    logger.info("Loaded handlers: %s", list(app.intents))

    run_config = config.settings.http_config()

    logger.info("Starting app with config: %s", repr(run_config))

    with closing(app):
        uvicorn.run(app, **run_config)


def add_subparser(subparsers):
    """
    Command arguments parser

    :param subparsers:
    :return:
    """

    run_parser = subparsers.add_parser(
        "develop",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help="Starts the skill in development mode.",
    )
    run_parser.add_argument("module", help="Run module", nargs="?", default="impl")
    run_parser.set_defaults(command=execute)
