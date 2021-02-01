#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# Deutsche Telekom AG and all other contributors /
# copyright owners license this file to you under the MIT
# License (the "License"); you may not use this file
# except in compliance with the License.
# You may obtain a copy of the License at
#
# https://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

import io
import os
import sys
import json
import time
import click
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Optional
from cookiecutter.main import cookiecutter
from cookiecutter.log import configure_logger
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

VENV_DIR: str = '.venv'
HERE: Path = Path(__file__).absolute().parent


def read_config(from_file: Path) -> Dict:
    try:
        with from_file.open() as data:
            return json.load(data)
    except (ValueError, json.JSONDecodeError):
        # Could not decode JSON
        click.secho(f'There seems to be an error in {from_file}', fg='red')
        sys.exit(1)


def prompt_overwrite(skill_dir: Path) -> bool:
    confirm = True
    if skill_dir.exists():
        confirm = click.confirm(f'Project directory {skill_dir} exists. Overwrite?', default=True)
        if not confirm:
            click.secho('Exiting...')
            sys.exit()
    return confirm


def validate(context: dict) -> dict:
    """ Validate domain context metadata

    :param context:
    :return:
    """
    assert isinstance(context['intents'], (list, tuple))
    for intent in context['intents']:
        assert isinstance(intent['name'], str)
        assert isinstance(intent['entities'], (list, tuple))
        required_entities = [item for sublist in intent['requiredEntities'] for item in sublist]
        for entity in intent['entities']:
            assert isinstance(entity['name'], str)
            assert entity['type'] in ('FREETEXT', 'ZIP_CODE', 'ROOM', 'TIMEZONE', 'DEVICE_NAME',
                                      'OTHER_DEVICE_NAMES', 'DYNAMIC_DEVICE_DATA', 'STT_TEXT')

            # Create an intent handler call parameter with type hint
            _entity = entity['name']
            _type = 'str'
            _required = '' if (_entity in required_entities) else ' = None'
            entity.update(as_parameter=f"{_entity}: {_type}{_required}")

        # Create `handler_name` and `arguments` parameter for @intent_handler decorator
        handler_name = f"{intent['name'].lower()}_handler"
        arguments = {entity['name']: dict({'type': entity['type']},
                                          **{'missing': 'error'} if (entity['name'] in required_entities) else {})
                     for entity in intent['entities']} or {}
        intent.update(arguments=arguments, handler_name=handler_name)

    return context


def create_implementation(metadata: io.BufferedReader, skill_dir: Path, extra_context: dict = None) -> None:
    """ Validate the metadata, cleanup the introduction implementation and create new skeleton from templates

    :param metadata:
    :param skill_dir:
    :param extra_context:
    :return:
    """
    try:
        context = validate(json.load(metadata))

        # Cleanup introduction implementations and tests
        for folder in (skill_dir / 'impl', skill_dir / 'tests', skill_dir / 'locale'):
            if folder.is_dir():
                for file_path in folder.glob('[!_]*.py'):
                    if file_path.is_file():
                        file_path.unlink()
            else:
                folder.mkdir()

        env = Environment(loader=FileSystemLoader(str(HERE / 'templates')))

        extra_context = extra_context or {}
        # Create implementations
        with (skill_dir / 'impl/main.py').open('w+') as impl_main:
            template = env.get_template('main.j2')
            impl_main.write(template.render(context=context, **extra_context))

        # Create tests skeleton
        with (skill_dir / 'tests/main_test.py').open('w+') as test_main:
            template = env.get_template('main_test.j2')
            test_main.write(template.render(context=context, **extra_context))

        # Copy translations
        [shutil.copy(locale, skill_dir / 'locale' / locale.name)
         for locale in (HERE / 'templates').glob('*.po')]

        # Add README.md
        with (skill_dir / 'README.md').open('w+') as readme:
            template = env.get_template('README.j2')
            readme.write(template.render(context=context, **extra_context))

    except TemplateNotFound as ex:
        click.secho(f'Missing template: {ex}', fg='red')
        sys.exit(1)
    except (AssertionError, KeyError, ValueError, json.JSONDecodeError, Exception) as ex:
        click.secho(f'There seems to be an error in {getattr(metadata, "name", repr(metadata))}',
                    fg='red')
        sys.exit(1)


@click.command()
@click.option('-n', '--name', default='my-skill', prompt='Name of the skill', help='Name of the skill')
@click.option('-l', '--language', default='python', prompt='Programming language', help='Programming language')
@click.option('-o', '--out', default='~/skills', prompt='Directory to create the project',
              type=click.Path(file_okay=False), help='Directory to create the project')
@click.option('-m', '--metadata', type=click.File('rb'), help='JSON file to read domain context metadata')
@click.option('-v', '--verbose', help='Verbose output', count=True)
def venv_main(name: str, language: str, out: str, metadata: Optional[io.BufferedReader] = None, verbose: int = 1):

    #
    # We'll create:
    #
    #   1. A new project from template
    #   2. Virtual environment for the project
    #   3. Install required dependencies
    #

    template_dir = HERE / 'skill_template'
    output_dir = Path(os.path.expanduser(out) if out.startswith('~/') else out)

    # Check if project already exists and ask to overwrite it
    skill_dir = output_dir / '-'.join(['skill', name, language])
    overwrite_if_exists = prompt_overwrite(skill_dir)

    # Read json configuration and replace the variables
    extra_context = read_config(template_dir / 'cookiecutter.json')
    extra_context.update({
        'skill_name': name,
        'programming_language': language
    })

    stdout = sys.stdout if verbose else open(os.devnull, 'w')
    configure_logger(stream_level='DEBUG' if verbose > 1 else 'INFO')

    # Run cookiecutter with all parameters set without prompting
    start = time.time()
    skill_dir = cookiecutter(str(template_dir),
                             extra_context=extra_context,
                             output_dir=str(output_dir),
                             overwrite_if_exists=overwrite_if_exists,
                             no_input=True)
    cookies_time = time.time() - start

    # Create implementation from domain context metadata
    if metadata:
        create_implementation(metadata, Path(skill_dir), extra_context=extra_context)

    # Create virtual environment
    venv = Path(skill_dir) / VENV_DIR
    click.secho(f'Creating virtual environment in {venv}', fg='green')
    start = time.time()

    try:
        subprocess.check_call((sys.executable, '-m', 'venv', str(venv), '--clear'), stderr=stdout, stdout=stdout)
    except subprocess.CalledProcessError:
        click.secho('ERROR: creating virtual environment failed!', fg='red')
        click.secho('Some distros might require `python3-venv` package installed.', fg='yellow')
        raise

    # Install SDK in "editable" mode
    click.secho(f'Installing skill SDK for Python', fg='green')

    python = venv / ('Scripts' if os.name == 'nt' else 'bin') / 'python'
    subprocess.check_call((str(python), '-m', 'pip', 'install', '-e', str(HERE.parent)), stderr=stdout, stdout=stdout)

    venv_time = time.time() - start

    if verbose:
        click.secho(f'Timing: cookiecutter took {round(cookies_time, 2)} sec, '
                    f'venv took {round(venv_time, 2)}', fg='green')

    return 0


def main():
    if __name__ == '__main__':
        sys.exit(venv_main())


main()
