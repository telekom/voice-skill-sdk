#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#
import io
import os
import sys
import json
import shutil
import pathlib
import tempfile
import unittest
import subprocess
from unittest.mock import patch, mock_open, ANY

try:
    import cookiecutter
    import jinja2
    cookiecutter_available = True
except ModuleNotFoundError:
    cookiecutter_available = False
    install = [sys.executable, "-m", 'pip', 'install', 'cookiecutter', '-q']
    if not (hasattr(sys, 'real_prefix') or hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        install += ['--user']

    subprocess.run(install)
    import cookiecutter
    import jinja2


def tearDownModule():
    """ Uninstall cookiecutter if was not installed

    :return:
    """
    if not cookiecutter_available:
        subprocess.run([sys.executable, "-m", 'pip', 'uninstall', 'cookiecutter', '-y'])


test_metadata = {
    "intents": [
        {
            "name": "TEST_INTENT",
            "requiredEntities": [
                ["required_entity"],
            ],
            "entities": [
                {
                    "name": "entity",
                    "type": "FREETEXT",
                },
                {
                    "name": "required_entity",
                    "type": "FREETEXT",
                },
            ],
        }
    ]
}


class TestSkillGenerator(unittest.TestCase):

    def test_main(self):
        import skill_generator.__main__
        from skill_generator.__main__ import main
        with patch('sys.exit') as exit_mock, \
                patch.object(skill_generator.__main__, "__name__", "__main__"), \
                patch.object(skill_generator.__main__, "venv_main", return_value=1):
            main()
            exit_mock.assert_called_once_with(1)

    def test_read_config(self):
        from skill_generator.__main__ import read_config
        with patch.object(pathlib.Path, 'open', new_callable=mock_open, read_data=b''), \
             patch('sys.exit') as exit_mock, \
             patch('sys.stdout', new=io.StringIO()) as stdout:
            read_config(pathlib.Path('file'))
            self.assertTrue(stdout.getvalue().startswith('There seems to be an error in file'))
            exit_mock.assert_called_once_with(1)

        with patch.object(pathlib.Path, 'open', new_callable=mock_open, read_data='{"hello": "Hello"}'):
            data = read_config(pathlib.Path('file'))
            self.assertEqual(data, dict(hello='Hello'))

    def test_prompt_overwrite(self):
        from skill_generator.__main__ import prompt_overwrite
        with patch.object(pathlib.Path, 'exists', return_value=False):
            self.assertTrue(prompt_overwrite(pathlib.Path('file')))

        with patch.object(pathlib.Path, 'exists', return_value=True):
            with patch('sys.stdin', new=io.StringIO('y')) as stdin:
                self.assertTrue(prompt_overwrite(pathlib.Path('file')))
            with patch('sys.stdin', new=io.StringIO('n')) as stdin, \
                    patch('sys.stdout', new=io.StringIO()) as stdout, \
                    patch('sys.exit') as exit_mock:
                prompt_overwrite(pathlib.Path('file'))
                self.assertIn('Exiting...', stdout.getvalue())
                exit_mock.assert_called_once_with()

    @patch('subprocess.check_call', return_value=0)
    @patch('skill_generator.__main__.create_implementation')
    def test_venv_main(self, create_mock, call_mock):
        from click.testing import CliRunner
        from skill_generator.__main__ import venv_main, HERE, VENV_DIR

        runner = CliRunner()
        test_dir = tempfile.mkdtemp()
        venv = pathlib.Path(test_dir) / VENV_DIR
        python = venv / ('Scripts' if os.name == 'nt' else 'bin') / 'python'
        with patch('io.open', new_callable=mock_open, read_data='{"name": "test"}'), \
             patch('skill_generator.__main__.cookiecutter', return_value=test_dir):
            runner.invoke(venv_main, ['-n', 'test', '-l', 'python', '-o', test_dir, '-m', 'data', '-v'])
            create_mock.assert_called_once()
            call_mock.assert_any_call((sys.executable, '-m', 'venv', str(venv), '--clear'), stderr=ANY, stdout=ANY)
            call_mock.assert_any_call((str(python), "-m", "pip", "install", "-e", str(HERE.parent)), stderr=ANY, stdout=ANY)

        runner.invoke(venv_main, ['-n', 'test', '-l', 'python', '-o', test_dir])
        call_mock.assert_any_call((sys.executable, '-m', 'venv', str(venv), '--clear'), stdout=ANY, stderr=ANY)
        call_mock.assert_any_call((str(python), "-m", "pip", "install", "-e", str(HERE.parent)), stdout=ANY, stderr=ANY)

        with patch('subprocess.check_call', side_effect=subprocess.CalledProcessError(-1, 'cmd')):
            runner.invoke(venv_main, ['-n', 'test', '-l', 'python', '-o', test_dir])

        shutil.rmtree(test_dir)

    def test_validate(self):
        from skill_generator.__main__ import validate
        result = validate(test_metadata)
        self.assertIsInstance(result, dict)
        self.assertIsInstance(result['intents'], list)
        self.assertEqual(result['intents'][0]['handler_name'], 'test_intent_handler')
        self.assertEqual(result['intents'][0]['entities'],
                         [{'name': 'entity', 'type': 'FREETEXT', 'as_parameter': 'entity: str = None'},
                          {'name': 'required_entity', 'type': 'FREETEXT', 'as_parameter': 'required_entity: str'}])
        self.assertEqual(result['intents'][0]['arguments'],
                         {"entity": {"type": "FREETEXT"}, "required_entity": {"type": "FREETEXT", "missing": "error"}})

    @patch('sys.exit')
    def test_create_implementation(self, exit_mock):
        from skill_generator.__main__ import create_implementation
        test_dir = pathlib.Path(tempfile.mkdtemp())
        create_implementation(io.StringIO(''), test_dir)
        exit_mock.assert_called_once_with(1)
        create_implementation(io.StringIO(json.dumps(test_metadata)), test_dir)
        self.assertTrue((test_dir / 'impl' / 'main.py').exists())
        self.assertTrue((test_dir / 'tests' / 'main_test.py').exists())
        self.assertTrue((test_dir / 'locale' / 'de.po').exists())
        self.assertTrue((test_dir / 'locale' / 'en.po').exists())
        self.assertTrue((test_dir / 'locale' / 'fr.po').exists())
        # For the coverage sake:
        pathlib.Path(test_dir / 'tests' / 'test.py').mkdir()
        create_implementation(io.StringIO(json.dumps(test_metadata)), test_dir)
        shutil.rmtree(test_dir)
        with patch('skill_generator.__main__.json.load', side_effect=jinja2.TemplateNotFound('test')):
            exit_mock.reset_mock()
            create_implementation(io.StringIO(''), test_dir)
            exit_mock.assert_called_once_with(1)
