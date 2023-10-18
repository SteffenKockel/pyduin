# pylint: disable=W0621,C0116,C0114
# -*- coding: utf-8 -*-
#pytest_plugins = ['device']
import argparse
import pytest
import serial
import yaml

from pyduin.arduino import Arduino as Device
from pyduin.utils import BuildEnv, CONFIG_TEMPLATE, PyduinUtils, BoardFile




class SerialMock():
    """ Intended to replace the serial module during tests """
    _ret =  "Hello from fixture."
    _called = 0
    response = ""
    def __init__(self, tty, baudrate, timeout=0):
        pass

    @property
    def called(self):
        return self._called

    def close(self):
        return None

    def write(self, message):
        pass

    def readline(self):
        self._called += 1
        return self.response.encode('utf-8')

# pylint: disable=R0903,W0613
class FailingSerialMock():
    """ Mocks a failing connection """
    def __init__(self, tty, baudrate, timeout=0):
        raise serial.SerialException

@pytest.fixture
def serialmock_fixture(monkeypatch):
    monkeypatch.setattr('serial.Serial', SerialMock)

@pytest.fixture
def subprocess_fixture(monkeypatch):
    def _return(*args, **kwargs):
        return b''
    monkeypatch.setattr('subprocess.check_output', _return)
    monkeypatch.setattr('subprocess.Popen', _return)

@pytest.fixture(scope="function")
def device_fixture(serialmock_fixture):
    yield Device('uno', tty='/mock/tty', wait=True)

@pytest.fixture(scope="function")
def device_fixture_baudrate_override(serialmock_fixture):
    yield Device('uno', tty="/mock/tty", baudrate=1234567, wait=True)

@pytest.fixture(scope="function")
def device_fixture_serial_failing(monkeypatch):
    monkeypatch.setattr('serial.Serial', FailingSerialMock)
    yield Device('uno', tty='/mock/tty', baudrate=1234567, wait=False)

@pytest.fixture(scope="function")
def device_fixture_nowait(serialmock_fixture):
    yield Device('uno', tty='/mock/tty', baudrate=9876543, wait=False)

@pytest.fixture(scope="function")
def device_fixture_socat_on(serialmock_fixture):
    yield Device('uno', tty='/mock/tty', baudrate=12343545, socat=True)

@pytest.fixture(scope="function")
def buildenv_fixture(subprocess_fixture, cli_testdir_fixture):
    buildenv = BuildEnv(cli_testdir_fixture, 'uno', '/mock/tty')
    rlist = ['-t', 'upload', '--upload-port', '/mock/tty']
    buildenv.cmd = list(filter(lambda x: x not in rlist, buildenv.cmd))
    yield buildenv

## Cli interface

@pytest.fixture
def which_success(serialmock_fixture, monkeypatch):
    def success(path):
        return f'/foo/bin/{path}'
    monkeypatch.setattr('shutil.which', success)

@pytest.fixture
def which_fail(serialmock_fixture, monkeypatch):
    # pylint: disable=unused-argument
    def fail(path):
        return None
    monkeypatch.setattr('shutil.which', fail)

## Cli Config

@pytest.fixture
def namespace_fixture():
    yield argparse.Namespace(
        tty=False,
        configfile=False,
        log_level=False,
        workdir=False,
        platformio_ini=False,
        buddy=False,
        board=False,
        baudrate=False)

@pytest.fixture
def cli_testdir_fixture(monkeypatch, tmp_path):
    """ This must be included whenever configurations are tested to avoid
    that local pathes and eventually existing configs will be used during
    tests """
    cpath = f'{tmp_path}/pyduin.yml'
    wdir =  tmp_path / '.pyduin'
    wdir.mkdir()
    monkeypatch.setattr('pyduin.utils.CliConfig.default_config_path', cpath)
    monkeypatch.setattr('pyduin.utils.CliConfig.default_workdir', wdir)
    return tmp_path

@pytest.fixture
def cfg_tpl_fixture():
    return yaml.safe_load(CONFIG_TEMPLATE)


## Utils

@pytest.fixture(scope="function")
def utils_fixture(monkeypatch, tmp_path):
    monkeypatch.setattr('pyduin.utils.PyduinUtils._configfile', "foo")
    monkeypatch.setattr('pyduin.utils.PyduinUtils._workdir', tmp_path)
    return PyduinUtils()


## BoardFile

@pytest.fixture(scope="module")
def boardfile_fixture():
    _boardfile = BoardFile('tests/data/boardfiles/nano2.yml')
    return _boardfile

@pytest.fixture(scope="module")
def boardfile_fixture_extra_libs():
    yield BoardFile('tests/data/boardfiles/nano3.yml')

@pytest.fixture(scope="module")
def boardfile_fixture_baudrate_missing():
    return BoardFile('tests/data/boardfiles/baudrate_not_set.yml')
    