# pylint: disable=W0621,C0116,C0114
# -*- coding: utf-8 -*-

# script_runner fixture documentation:
# https://github.com/kvas-it/pytest-console-scripts

import re
import pytest
from pyduin.utils import DeviceConfigError

# pylint: disable=unused-argument
def test_cli_help(cli_runner, script_runner):
    result = script_runner.run('pyduin --help', shell=True, check=True)
    assert result.returncode == 0
    assert not result.stdout == ''
    assert result.stderr == ''

def test_cli_dependencies_success(cli_runner_which_success, script_runner):
    result = script_runner.run('pyduin dependencies', shell=True, check=True)
    assert result.returncode == 0
    res = 'Platformio found in /foo/bin/pio.\nSocat found in /foo/bin/socat.\n'
    assert result.stdout == res

def test_cli_dependencies_failure(cli_runner_which_fail, script_runner):
    result = script_runner.run('pyduin dependencies', shell=True, check=True)
    res = "Platformio not installed. Flashing does not work.\n"
    res += "Socat not found. Some features may not work.\n"
    assert result.returncode == 0
    assert result.stdout == res

def test_cli_nothing_to_do(cli_runner, script_runner):
    result = script_runner.run('pyduin', shell=True)
    assert result.returncode == 1
    assert result.stdout == "Nothing to do\n"

def test_cli_invalid_choice(cli_runner, script_runner):
    result = script_runner.run('pyduin .', shell=True)
    assert result.returncode == 2
    assert result.stdout == ''
    assert re.findall('invalid choice', result.stderr)

def test_no_board(cli_runner, script_runner, tmp_path):
    path = f'{tmp_path}/pyduin.yml'
    with open(f'{path}', 'w', encoding='utf-8') as cfile:
        cfile.write("invalid: template")
    with pytest.raises(DeviceConfigError) as err:
        script_runner.run(f'pyduin --tty /foo/bar -c {path}', shell=True)
    assert str(err.value) == "Cannot determine board for desired action."

def test_invalid_board(cli_runner, script_runner):
    with pytest.raises(DeviceConfigError) as err:
        script_runner.run('pyduin --board=nixexista', shell=True)
    assert str(err.value).startswith('Board (nixexista) not in supported boards list')
