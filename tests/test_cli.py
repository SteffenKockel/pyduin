# pylint: disable=W0621,C0116,C0114
# -*- coding: utf-8 -*-

# script_runner fixture documentation:
# https://github.com/kvas-it/pytest-console-scripts

import re
import pytest
from pyduin.utils import DeviceConfigError

# pylint: disable=unused-argument
def test_cli_help(serialmock_fixture, script_runner):
    result = script_runner.run('pyduin --help', shell=True, check=True)
    assert result.returncode == 0
    assert not result.stdout == ''
    assert result.stderr == ''

def test_cli_dependencies_success(which_success, script_runner):
    result = script_runner.run('pyduin dependencies', shell=True, check=True)
    assert result.returncode == 0
    res = 'Platformio found in /foo/bin/pio.\nSocat found in /foo/bin/socat.\n'
    assert result.stdout == res

def test_cli_dependencies_failure(which_fail, script_runner):
    result = script_runner.run('pyduin dependencies', shell=True, check=True)
    res = "Platformio not installed. Flashing does not work.\n"
    res += "Socat not found. Some features may not work.\n"
    assert result.returncode == 0
    assert result.stdout == res

def test_cli_nothing_to_do(serialmock_fixture, script_runner):
    result = script_runner.run('pyduin', shell=True)
    assert result.returncode == 1
    assert result.stdout == "Nothing to do\n"

def test_cli_invalid_choice(serialmock_fixture, script_runner):
    result = script_runner.run('pyduin .', shell=True)
    assert result.returncode == 2
    assert result.stdout == ''
    assert re.findall('invalid choice', result.stderr)

def test_no_board(serialmock_fixture, script_runner, tmp_path):
    path = f'{tmp_path}/pyduin.yml'
    cfg = """
    buddies:
      foo:
        tty: /foo/bar
    """
    with open(f'{path}', 'w', encoding='utf-8') as cfile:
        cfile.write(cfg)
    #with pytest.raises(DeviceConfigError) as err:
    result = script_runner.run(f'pyduin -c {path}', shell=True)
    assert result.stdout == "Nothing to do\n"

def test_invalid_board(serialmock_fixture, script_runner):
    with pytest.raises(DeviceConfigError) as err:
        script_runner.run('pyduin -b nixexista versions', shell=True)
    assert str(err.value).startswith('Board (nixexista) not in supported boards list')


def test_default_buddy(serialmock_fixture, script_runner, tmp_path):
    path = f'{tmp_path}/pyduin.yml'
    cfg = """
    default_buddy: foo
    serial:
      use_socat: False
    buddies:
      foo:
        tty: /foo/bar
        board: uno
    """
    with open(f'{path}', 'w', encoding='utf-8') as cfile:
        cfile.write(cfg)
    result = script_runner.run(f'pyduin -c {path} versions', shell=True)
    assert result.stdout == "{'pyduin': '0.6.4', 'device': '', 'available': '0.7.0'}\n"

def test_pin_high(serialmock_fixture, script_runner, cli_testdir_fixture, subprocess_fixture):
    result = script_runner.run('pyduin -B nano1 pin 13 high', shell=True)
    assert result.stderr == ""

def test_firmware_update(serialmock_fixture, script_runner, cli_testdir_fixture,
    subprocess_fixture):
    result = script_runner.run('pyduin -B nano1 firmware flash', shell=True)
    assert result.returncode == 0
