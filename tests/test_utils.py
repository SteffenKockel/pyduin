# pylint: disable=W0621,C0116,C0114
# -*- coding: utf-8 -*-

import os
import pytest
import yaml
from pyduin.utils import PyduinUtils, CONFIG_TEMPLATE

@pytest.fixture(scope="function")
def utils_fixture(monkeypatch):
    monkeypatch.setattr('pyduin.utils.PyduinUtils._configfile', "foo")
    monkeypatch.setattr('pyduin.utils.PyduinUtils._workdir', 'bar')
    return PyduinUtils()

def test_package_root(utils_fixture):
    assert 'arduino.py' in os.listdir(utils_fixture.package_root)

def test_boardfiledir(utils_fixture):
    assert 'uno.yml' in os.listdir(utils_fixture.boardfiledir)

def test_supported_boards(utils_fixture):
    assert utils_fixture.supported_boards == \
        ['sparkfun_promicro16', 'nanoatmega328', 'uno']

def test_configfiledir(utils_fixture):
    assert utils_fixture.configfile == "foo"

def test_firmwaredir(utils_fixture):
    assert utils_fixture.firmwaredir == \
        os.path.join(utils_fixture.package_root, 'data', 'platformio')

def test_firmware(utils_fixture):
    assert os.path.isfile(utils_fixture.firmware)

def test_available_firmware_version(utils_fixture, tmp_path):
    assert utils_fixture.available_firmware_version() == "0.7.0"
    assert utils_fixture.available_firmware_version('/fake/dir') == "0.7.0"
    _dir = tmp_path / 'src'
    _dir.mkdir()
    _file = _dir / "pyduin.cpp"
    _file.write_text('String firmware_version = "0.0.0";\n')
    wdir = os.path.dirname(_dir)
    assert utils_fixture.available_firmware_version(workdir=wdir) == "0.0.0"
    _file = _dir / "pyduin.cpp"
    _file.write_text('No firmware version present";\n')
    assert utils_fixture.available_firmware_version(workdir=wdir) == "unknown"

def test_platformio_ini(utils_fixture):
    assert utils_fixture.platformio_ini == \
        os.path.join(utils_fixture.package_root, 'data', 'platformio','platformio.ini')

def test_ensure_user_config_file(utils_fixture, tmp_path):
    destination = os.path.join(tmp_path, 'pyduin.yml')
    utils_fixture.ensure_user_config_file(destination)
    assert os.path.isfile(destination)

def test_get_buddy_cfg(utils_fixture):
    assert not utils_fixture.get_buddy_cfg({}, "")
    config = yaml.safe_load(CONFIG_TEMPLATE)
    assert utils_fixture.get_buddy_cfg(config, "uno1") == \
        {"board": "uno", "tty": "/dev/ttyACM0"}
    assert utils_fixture.get_buddy_cfg(config, "uno1", "board") == "uno"

def test_loglevel_int(utils_fixture):
    assert utils_fixture.loglevel_int('debug') == 10
    assert utils_fixture.loglevel_int(10) == 10
