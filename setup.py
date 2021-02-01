#!/usr/bin/env python

import os
import sys

try:
    from setuptools import setup, Command, find_packages
    from setuptools.command.develop import develop
    from setuptools.command.sdist import sdist
except ImportError:
    exit("This package requires Python version >= 3.7 and Python's setuptools")

HERE = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(HERE, 'requirements.txt')) as f:
    install_requires = f.read().splitlines()

about = {}
with open(os.path.join(HERE, 'skill_sdk', '__version__.py')) as f:
    exec(f.read(), about)


class NewSkillCommand(Command):

    description = 'create new skill and install SDK in development mode'
    user_options = [
        ('metadata=', 'm', "JSON file to read domain context metadata"),
    ]

    def initialize_options(self):
        self.metadata = None

    def finalize_options(self):
        pass

    def run(self):
        new_skill(self.verbose, self.metadata)


class DevelopCommand(develop):
    """Launch 'new-skill' wizard if --new-skill option is set"""

    user_options = develop.user_options + [("new-skill", None, "create new skill from template")]

    boolean_options = develop.boolean_options + ['new-skill']

    def initialize_options(self):
        self.new_skill = False
        super().initialize_options()

    def finalize_options(self):
        if not self.new_skill:
            super().finalize_options()

    def run(self):
        if generator_available():
            if self.new_skill:
                self.distribution.install_requires = [],
                return new_skill(self.verbose)

            self.distribution.entry_points = {'console_scripts': [
                'new-skill = skill_generator.__main__:venv_main [generator]',
            ]}

        self.distribution.packages += ['skill_generator', 'swagger_ui']
        super().run()


class SDistCommand(sdist):
    """ Add skill_generator and swagger_ui to source distribution """

    def run(self):
        self.distribution.packages += ['skill_generator', 'swagger_ui']
        super().run()


def new_skill(verbose: int, metadata: str = None):
    """
    Run new-skill wizard

    @param verbose:     verbose output
    @param metadata:    optional domain context metadata definition file
    @return:
    """
    import subprocess
    install = [sys.executable, '-m', 'pip', 'install', 'cookiecutter', '-q', '--disable-pip-version-check']
    generator = [sys.executable, os.path.join(HERE, 'skill_generator', '__main__.py')]
    generator += ['-m', metadata] if metadata else []
    generator += ['-' + 'v'*verbose] if verbose else []

    # This is how we try to identify if we're inside of virtual environment
    # Thanks to that unknown guy on stackoverflow
    if not (hasattr(sys, 'real_prefix') or hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        # inside virtual environment, '--user' flag won't work
        install += ['--user']

    subprocess.check_call(install)

    try:
        subprocess.check_call(generator)
    except subprocess.CalledProcessError:
        exit('There was an error creating new skill. Check log for details')


def generator_available():
    """
    Check if skill_generator is available

    :return:
    """
    try:
        with open(os.path.join(HERE, 'skill_generator', '__main__.py')):
            return True
    except FileNotFoundError:
        return False


options = dict(
    name=about['__name__'],
    version=about['__version__'],
    description=about['__description__'],
    long_description='Skill SDK for Python is a full-stack micro-service builder '
                     'for creating Magenta smart speaker skills.',

    url=about['__url__'],
    author=about['__author__'],
    author_email=about['__author_email__'],
    license=about['__license__'],

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        "License :: OSI Approved :: MIT License",
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: Implementation :: CPython',
    ],

    packages=find_packages(exclude=['tests', 'skill_generator', 'swagger_ui']),
    include_package_data=True,
    install_requires=install_requires,
    python_requires=">=3.7",
    setup_requires=['wheel'],
    extras_require={
        'generator': ['cookiecutter']
    },
    cmdclass=dict(
        [('new_skill', NewSkillCommand)] if generator_available() else [],
        develop=DevelopCommand,
        sdist=SDistCommand,
    ),
)

#
#   Remove internal services from core distribution
#
if '--core' in sys.argv[1:]:
    options['name'] = 'skill_sdk_core'
    options['description'] += ' (core)'
    options['packages'] = [package for package in options['packages']
                           if package not in ('skill_sdk.services', )]
    sys.argv.remove("--core")

setup(**options)
