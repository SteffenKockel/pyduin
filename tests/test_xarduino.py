# pylint: disable=W0621,C0116,C0114
# -*- coding: utf-8 -*-
"""
Note: For some esotheric reason these tests fail or make other tests
fail, when not run last. The filename test_xarduino.py ensures that
these tests are executed last.
"""
from collections import OrderedDict
import pytest
import pyduin

def test_mock_serial(device_fixture):
    device_fixture.Connection.response = "Hello from fixture."
    assert device_fixture.Connection.readline() == "Hello from fixture.".encode('utf-8')
    device_fixture.Connection.response = "0%13%0"
    assert device_fixture.send('<AD13000>') == '0%13%0'

def test_mock_reread_on_boot_complete(device_fixture):
    message = "Boot complete"
    device_fixture.Connection.response = 'Boot complete'
    ret = device_fixture.send(message)
    assert ret == message
    assert device_fixture.Connection.called == 2

def test_wait_false(device_fixture_nowait):
    # pylint: disable=unused-variable
    with pytest.raises(KeyError) as err:
        device_fixture_nowait.get_pin(13)
    assert device_fixture_nowait.Pins == OrderedDict()

def test_baudrate(device_fixture):
    assert device_fixture.baudrate == 115200

def test_tty(device_fixture):
    assert device_fixture.tty == "/mock/tty"

def test_baudrate_override(device_fixture_baudrate_override):
    assert device_fixture_baudrate_override.baudrate == 1234567

def test_get_pin(device_fixture):
    assert isinstance(device_fixture.get_pin("A0"), pyduin.pin.ArduinoPin)
    # pylint: disable=unused-variable
    with pytest.raises(pyduin.utils.PinNotFoundError) as error:
        assert device_fixture.get_pin(2000)

def test_get_led(device_fixture):
    # pylint: disable=unused-variable
    with pytest.raises(pyduin.utils.LEDNotFoundError) as error:
        assert device_fixture.get_led(13)
    assert isinstance(device_fixture.get_led(1), pyduin.pin.ArduinoPin)

# This also tests wait=False and does not work with wait=True
def test_connection_failure(device_fixture_serial_failing):
    # pylint: disable=W0612
    with pytest.raises(pyduin.utils.DeviceConfigError) as result:
        assert device_fixture_serial_failing.open_serial_connection()

def test_firmware_version(device_fixture):
    device_fixture.Connection.response = "0.0.0"
    assert device_fixture.firmware_version == "0.0.0"

def test_firmware_version_nowait(device_fixture):
    device_fixture.Connection.response = "0.0.0"
    setattr(device_fixture, "wait", False)
    assert device_fixture.firmware_version

def test_free_memory(device_fixture):
    device_fixture.Connection.response = "1234"
    assert device_fixture.free_memory == "1234"
    setattr(device_fixture, "wait", False)
    assert device_fixture.free_memory

def test_close_serial_connection(device_fixture):
    assert not device_fixture.close_serial_connection()

def test_socat_on(device_fixture_socat_on):
    assert isinstance(device_fixture_socat_on.socat, pyduin.utils.SocatProxy)
    assert device_fixture_socat_on.open_serial_connection()
