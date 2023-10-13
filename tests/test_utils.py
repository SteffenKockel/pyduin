# pylint: disable=W0621,C0116,C0114
# -*- coding: utf-8 -*-

import logging
import os
import time

import pytest
import yaml
from pyduin.utils import PyduinUtils, CONFIG_TEMPLATE, BuildEnvError, \
    SocatProxy

@pytest.fixture(scope="function")
def utils_fixture(monkeypatch, tmp_path):
    monkeypatch.setattr('pyduin.utils.PyduinUtils._configfile', "foo")
    monkeypatch.setattr('pyduin.utils.PyduinUtils._workdir', tmp_path)
    return PyduinUtils()


@pytest.fixture(scope="function")
def utils_fixture_deps_broken(utils_fixture, monkeypatch):
    # pylint: disable=unused-argument
    def return_nothing(path):
        return None
    monkeypatch.setattr('shutil.which', return_nothing)
    return utils_fixture

@pytest.fixture(scope="function")
def utils_fixture_deps_ok(utils_fixture, monkeypatch):
    # pylint: disable=unused-argument
    def return_nothing(path):
        return f'/foo/bin/{path}'
    monkeypatch.setattr('shutil.which', return_nothing)
    return utils_fixture

def test_boardfile_override(utils_fixture):
    board = 'nanoatmega328'
    _dir = utils_fixture.workdir / board
    _dir.mkdir()
    _file = os.path.join(_dir, f'{board}.yml')
    with open(_file, "w", encoding='utf-8') as boardfile:
        boardfile.write('foo:bar')
    assert utils_fixture.boardfile_for('nanoatmega328') == _file

def test_package_root(utils_fixture):
    assert 'arduino.py' in os.listdir(utils_fixture.package_root)

def test_boardfiledir(utils_fixture):
    assert 'uno.yml' in os.listdir(utils_fixture.boardfiledir)

def test_supported_boards(utils_fixture):
    assert utils_fixture.supported_boards == \
        ['sparkfun_promicro16', 'nanoatmega328', 'uno'].sort()

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
    _file.write_text('String firmware_version = "0.0.1";\n')
    wdir = os.path.dirname(_dir)
    assert utils_fixture.available_firmware_version(workdir=wdir) == "0.0.1"
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

#def test_boardfile_for_override(tmp_path)

def test_get_buddy_cfg(utils_fixture):
    config = yaml.safe_load(CONFIG_TEMPLATE)
    assert utils_fixture.get_buddy_cfg(config, "uno1") == \
        {"board": "uno", "tty": "/dev/ttyACM0"}
    assert utils_fixture.get_buddy_cfg(config, "uno1", "board") == "uno"

def test_get_buddy_cfg_failure(utils_fixture):
    assert not utils_fixture.get_buddy_cfg({}, "nobuddy")

def test_loglevel_int(utils_fixture):
    assert utils_fixture.loglevel_int('debug') == 10
    assert utils_fixture.loglevel_int(10) == 10

def test_dependencies(utils_fixture_deps_ok):
    assert utils_fixture_deps_ok.dependencies()

def test_dependencies_not_found(utils_fixture_deps_broken):
    assert not utils_fixture_deps_broken.dependencies()

# BuildEnv

def test_buildenv_init(buildenv_fixture):
    assert buildenv_fixture.board == 'uno'
    assert buildenv_fixture.tty == '/mock/tty'
    assert os.path.isdir(buildenv_fixture.workdir)
    assert isinstance(buildenv_fixture.logger, logging.Logger)
    assert os.path.isfile(buildenv_fixture.platformio_ini)
    assert buildenv_fixture.project_dir == os.path.join(
        buildenv_fixture.workdir,
        buildenv_fixture.board)
    assert buildenv_fixture.logger.level == logging.INFO

def test_buildenv_create_and_recreate(buildenv_fixture):
    buildenv_fixture.create()
    platformio_created = os.path.join(buildenv_fixture.workdir, 'platformio.ini')
    assert os.path.isfile(platformio_created)
    board_dir = os.path.join(
        buildenv_fixture.workdir,
        buildenv_fixture.board,
        'src')
    assert os.path.isdir(board_dir)
    fwfile = os.path.join(board_dir, 'pyduin.cpp')
    assert os.path.isfile(fwfile)

    mtime = os.stat(fwfile)
    time.sleep(1) # This seems to be required for mtime to make a difference :/
    buildenv_fixture.create(force_recreate=True)
    mtime2 = os.stat(fwfile)
    assert mtime != mtime2

    os.chmod(buildenv_fixture.workdir, 0o444)
    # pylint: disable=unused-variable
    with pytest.raises(BuildEnvError) as err:
        assert buildenv_fixture.create(force_recreate=True)

def test_buildenv_buildenv_build(buildenv_fixture, device_fixture):
    buildenv_fixture.create()
    buildenv_fixture.template_firmware(device_fixture)
    assert 'upload' not in buildenv_fixture.cmd
    assert buildenv_fixture.build()
    assert os.path.isfile(os.path.join(
        buildenv_fixture.project_dir,
        ".pio/build/uno/firmware.hex"))

def test_buildenv_build_failure(buildenv_fixture, device_fixture):
    buildenv_fixture.create()
    buildenv_fixture.template_firmware(device_fixture)
    fwfile = os.path.join(buildenv_fixture.project_dir, 'src', 'pyduin.cpp')
    with open(fwfile, 'a', encoding='utf-8') as _fwfile:
        _fwfile.write("\nI will <> destroy {} your build")
    # pylint: disable=unused-variable
    with pytest.raises(BuildEnvError) as err:
        assert buildenv_fixture.build()

# SocatProxy

def test_socat():
    socat = SocatProxy('/mock/ttyUSB0', 1234567)
    assert socat.baudrate == 1234567
    assert socat.source_tty == '/mock/ttyUSB0'
    assert not socat.debug
    assert isinstance(socat.logger, logging.Logger)
    assert socat.proxy_tty == os.path.join(os.sep, 'tmp', 'ttyUSB0.tty')
    # pylint: disable=line-too-long
    cmd = ('/usr/bin/socat', '-s', '-d',
        '/mock/ttyUSB0,b1234567,cs8,parenb=0,cstopb=0,clocal=0,raw,echo=0,setlk,flock-ex-nb,nonblock=1',
        'PTY,link=/tmp/ttyUSB0.tty,b1234567,cs8,parenb=0,cstopb=0,clocal=0,raw,echo=0,setlk,flock-ex-nb,nonblock=1')
    assert socat.socat_cmd == cmd

def test_socat_debug():
    socat = SocatProxy('/mock/ttyUSB0', 7654321, log_level=logging.DEBUG)
    assert socat.debug
    # pylint: disable=line-too-long
    cmd = ('/usr/bin/socat', '-s', '-x', '-ddd', '-ddd',
        '/mock/ttyUSB0,b7654321,cs8,parenb=0,cstopb=0,clocal=0,raw,echo=0,setlk,flock-ex-nb,nonblock=1',
        'PTY,link=/tmp/ttyUSB0.tty,b7654321,cs8,parenb=0,cstopb=0,clocal=0,raw,echo=0,setlk,flock-ex-nb,nonblock=1')
    assert socat.socat_cmd == cmd

def test_socat_proxy_tty():
    socat = SocatProxy('/dev/ttyUSB0', 1234567, proxy_tty='/foo/bar/dev')
    assert socat.proxy_tty == '/foo/bar/dev'

def test_socat_start_stop(monkeypatch):
    socat = SocatProxy('/dev/ttyACM0', 9876543)

    # pylint: disable=unused-argument
    def return_true(*args, **kwargs):
        if kwargs.get('shell'):
            return '986 '.encode('utf-8')
        return True

    monkeypatch.setattr('subprocess.check_output', return_true)
    monkeypatch.setattr('subprocess.Popen', return_true)
    assert socat.start()
    assert socat.stop()
