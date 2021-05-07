#
# voice-skill-sdk
#
# (C) 2021, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

"""CLI: utility functions"""

import sys
import argparse
import logging
import importlib
import pathlib
from typing import Text, Tuple
from types import ModuleType

from skill_sdk import Skill


def add_logging_options(parser: argparse.ArgumentParser) -> None:
    """
    Add common logging argument parameters

    :param parser:
    :return:
    """
    logging_arguments = parser.add_argument_group("Logging options")

    logging_arguments.add_argument(
        "-v",
        "--verbose",
        help="Set logging to INFO.",
        action="store_const",
        dest="loglevel",
        const=logging.INFO,
    )
    logging_arguments.add_argument(
        "-vv",
        "--debug",
        help="Set logging to DEBUG.",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
    )
    logging_arguments.add_argument(
        "-q",
        "--quiet",
        help="Set logging to ERROR.",
        action="store_const",
        dest="loglevel",
        const=logging.ERROR,
    )


def import_module_app(import_from: Text) -> Tuple[ModuleType, Skill]:
    """
    Import application from python module or package

    :param import_from: module or package name, can be in following formats:
                        "app.py", "app:app" or "app_dir"

    :return:
    """
    module_str, _, app_str = import_from.partition(":")

    path = pathlib.Path(module_str)

    # Insert current directory to sys.path
    cwd = pathlib.Path("").absolute().__str__()
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    if path.suffix == ".py":
        module = importlib.import_module(path.stem)
    elif path.is_dir():
        module = importlib.import_module(module_str)
        [
            importlib.import_module("." + _.stem, _.parent.name)
            for _ in path.iterdir()
            if _.is_file() and _.suffix == ".py" and _.stem != "__init__"
        ]
    else:
        module = importlib.import_module(module_str)

    # Return imported module (and possibly, the name of application variable, eg `main:app`)
    app = getattr(module, app_str, None)

    # Add link to the originating module
    # for source reloading and intent handler updates from UI
    if isinstance(app, Skill):
        setattr(app, "_module", module)

    return module, app
