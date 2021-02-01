#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

#
# Run/test/translate/display version
#

import sys
import logging
import pathlib
import argparse
import unittest
import importlib
from typing import Dict, List

from .config import config

ARG_RUN: str = 'run'
ARG_TEST: str = 'test'
ARG_VERSION: str = 'version'
ARG_TRANSLATE: str = 'translate'

logger = logging.getLogger(__name__)


def create_coverage():
    """
    Create Coverage instance

    :return:
    """
    from coverage import Coverage

    include = config.get('tests', 'include', fallback='./*, impl/*, src/*')
    include = [_.strip() for line in include.splitlines() for _ in line.split(',') if line and _]

    exclude = config.get('tests', 'exclude', fallback='tests/*, test/*, .venv/*, venv/*')
    exclude = [_.strip() for line in exclude.splitlines() for _ in line.split(',') if line and _]

    concurrency = config.get('tests', 'concurrency', fallback='gevent')
    concurrency = [_.strip() for line in concurrency.splitlines() for _ in line.split(',') if line and _]

    cov = Coverage(include=include, omit=exclude, concurrency=concurrency)
    cov.start()
    return cov


def run_tests(functional: bool = False, cover: bool = False):
    """
    Discover and run an included unittest suite

    :param functional:  start automatic functional test
    :param cover:       display coverage report
    :return: int:       0 for success, 1
    """

    cov = create_coverage() if cover else None

    if not run_unit_tests():
        return 'FAIL: unit tests'

    if functional and not run_func_tests():
        return 'FAIL: functional tests'

    # Report coverage if requested
    if cover:
        cov.stop()
        result = cov.report()
        if not isinstance(cover, bool) and isinstance(cover, int):
            return round(result) < cover and f'\nFAIL: expected {cover}% coverage' or 0

    return 0


def run_unit_tests() -> bool:
    """
    Discover and run integrates unit tests:
        unit tests are expected in `tests` directory, and following `*_test.py` file naming convention by default

    """

    # Discover all unit tests
    test_dir = config.get('tests', 'dir', fallback='tests')
    pattern = config.get('tests', 'patterns', fallback='*_test.py')
    test_suite = unittest.defaultTestLoader.discover(test_dir, pattern=pattern)

    # Create the basic runner and run the tests
    test_runner = unittest.TextTestRunner()
    result = test_runner.run(test_suite)
    return result.wasSuccessful()


def run_func_tests() -> bool:
    """
    Run functional tests:
        get the skill intents, start the skill in development mode
        and read the skill responses supplying different (both correct and incorrect) entity values

    :return:
    """
    from .test_helpers import FunctionalTest

    # Run the functional test if requested
    loader = unittest.TestLoader()
    loader.testMethodPrefix = 'default'
    func_suite = loader.loadTestsFromTestCase(FunctionalTest)

    # Create the basic runner and run the tests
    test_runner = unittest.TextTestRunner()
    result = test_runner.run(func_suite)
    return result.wasSuccessful()


def import_module(module: str) -> None:
    """
    Import from either python file or directory, silently ignoring import exceptions

    :param module:
    :return:
    """
    path = pathlib.Path(module)

    try:
        if module.endswith('.py'):
            importlib.import_module(module[:-3])
        elif path.is_dir():
            importlib.import_module(module)
            [importlib.import_module('.' + _.name[:-3], _.parent.name)
             for _ in path.iterdir() if _.is_file() and str(_).endswith('.py')]
        else:
            importlib.import_module(module)
    except ModuleNotFoundError as ex:
        logger.error(f"Cannot load {path.absolute()}: {repr(ex)}")


def _download_full_catalog(download_url: str, token: str = None, tenant: str = None) -> Dict:
    """
    Download a complete translation catalog from text service

    :param download_url:
    :param token:
    :param tenant:
    :return:
    """

    from .services.text import TextService
    logger.info(f'Downloading translations from {download_url}...')

    headers = {'X-Application-Authentication': f'Bearer {token}'} if token else {}
    headers.update({'X-Tenant': tenant}) if tenant else None

    service = TextService(headers=headers)
    service.BASE_URL = download_url
    return service.admin_get_full_catalog()


def translate_modules(modules: List[str],
                      force: bool = False,
                      download_url: str = None,
                      token: str = None,
                      tenant: str = None):
    """
    Create translation template and load translations from text service (if URL is given)

    :param modules: List of Python modules to scan
    :param force:   Overwrite existing translations if exist
    :param download_url:    Text services URL to download translations
    :param token:   Bearer authentication token (X-Application-Authentication)
    :param tenant:  Tenant for authentication   (X-Tenant)
    :return:
    """
    from . import l10n

    try:
        template = l10n.extract_translations(modules)
        if not template:
            return 'Failed to extract translations'
        if not download_url:
            return 'No "download_url" specified'

        logger.info(f'Translation template written to {template}')
        catalog = _download_full_catalog(download_url, token, tenant)

        if catalog:
            logger.info(f'Creating locales: {list(catalog)}')
            l10n.init_locales(template, list(catalog), force=force)

            for locale in catalog:
                path = l10n.update_translation(locale, catalog[locale])
                logger.info(f'"{locale}"" translation written to {path}')

            l10n.compile_locales()

    except (ModuleNotFoundError, BaseException) as ex:
        return f'Failed to update translations: {ex}'

    return 0


def manage():
    """
    Entry point
    """

    parser = argparse.ArgumentParser(prog='manage.py',
                                     description="helper for several Smart Voice Hub related skill tasks")
    subparsers = parser.add_subparsers(dest='subcmd')
    epilog = 'The following environmental variable will modify the behavior:\n\n' \
             'LOG_FORMAT    Switch the log format between GELF (JSON) or human readable. Values: "gelf", "human"\n' \
             'LOG_LEVEL     Set the logging level. Values: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL" \n' \
             'SKILL_CONF    Set configuration file. Default: "skill.conf" in project root \n' \
             'TOKENS_JSON   Set the auth tokens file. Default: "tokens.json" in project root \n' \
             '              '
    run = subparsers.add_parser(ARG_RUN, formatter_class=argparse.RawDescriptionHelpFormatter, epilog=epilog,
                                help='Run the HTTP server',
                                description='Run the HTTP server as configured to handle requests')

    run.add_argument('module', help='Run module, default "impl"', nargs='?', default='impl')

    #
    # These options should be arguments of the `run` sub-parser,
    #  but for historical reasons, "--dev" parameter was almost always used before "run"
    #
    parser.add_argument('-l', '--local', action='store_true', help='use local services')
    parser.add_argument('-t', '--dev', action='store_true', help='start in "development" mode')
    parser.add_argument('-nc', '--no-cache', action='store_true', help='disable local caches')

    test = subparsers.add_parser(ARG_TEST, help='Run tests', description='Run included unittest suite')
    test.add_argument('module', help='Run module, default "impl"', nargs='?', default='impl')
    test.add_argument('-f', '--functional', action='store_true', help='start automatic functional test')
    test.add_argument('-c', '--coverage', help='display coverage report', const=True, type=int,
                      default=0, action='store', nargs='?')

    subparsers.add_parser(ARG_VERSION, help='Print version', description='Print the skill version')

    translate = subparsers.add_parser(ARG_TRANSLATE, help='Extract translations',
                                      description='Extract translatable strings from Python files or modules.')
    translate.add_argument('modules', help='Modules to scan, default "impl"', nargs='*', default=['impl'])
    translate.add_argument('-f', '--force', action='store_true', help='overwrite existing translations')
    translate.add_argument('-d', '--download-url', action='store', type=str, nargs='?',
                           help='URL to download the translations from (text services URL)')
    translate.add_argument('-k', '--token', action='store', type=str, nargs='?',
                           help='Bearer authentication token (for the text services)')
    translate.add_argument('-n', '--tenant', action='store', type=str, nargs='?',
                           help='Tenant (for admin route authentication)')

    args = parser.parse_args()

    if len(sys.argv) <= 1:
        # Print usage
        parser.print_usage()
        sys.exit()

    if args.subcmd in (ARG_RUN, ARG_TEST):
        # Import module if supplied
        import_module(args.module)

    if args.subcmd == ARG_RUN:
        # Strip arguments to prevent them being passed over to Gunicorn
        if not args.dev:
            sys.argv = [arg for arg in sys.argv if arg not in ('-l', '--local', '-t', '--dev', '-nc', '--no-cache')]

        from . import skill
        skill.run(dev=args.dev, local=args.local, cache=not args.no_cache)

    if args.subcmd == ARG_TEST:
        # Run tests
        sys.exit(run_tests(args.functional, args.coverage))

    if args.subcmd == ARG_VERSION:
        # Print skill version
        print(f"{config.get('skill', ARG_VERSION)}")

    if args.subcmd == ARG_TRANSLATE:
        # Extract translation template from Python sources
        sys.exit(translate_modules(args.modules, args.force, args.download_url, args.token, args.tenant))


def patch():
    """
    We use gevent, so try to monkey-patch as early as possible (http://www.gevent.org/api/gevent.monkey.html).

        If your skill is using one of these modules or anything that depends on them,
            consider `monkey.patch_all()` at the very start of your app:
                **requests**, dns, os, queue, select, signal, socket, ssl, subprocess, sys, threading, time

        Note: Monkey-patched "threading" module interferes with source reloading feature

              To use "reloader" for development, monkey-patch everything but threading:
              `from gevent import monkey; monkey.patch_all(thread=False)`

    """
    worker_class = config.get('http', 'worker_class', fallback=None)

    if worker_class == 'gevent':
        from gevent import monkey
        monkey.patch_all()

    elif worker_class == 'eventlet':
        import eventlet
        eventlet.monkey_patch()


patch()
