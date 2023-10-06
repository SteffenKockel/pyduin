# pylint: disable=W0621,C0116,C0114
# -*- coding: utf-8 -*-
"""
Note: For some esotheric reason these tests fail or make other tests
fail, when not run last. The filename test_xarduino.py ensures that
these tests are executed last.
"""
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

#def test_wait_false(device_fixture_nowait):
#    assert hasattr(device_fixture_nowait, 'Connection')

def test_baudrate(device_fixture):
    assert device_fixture.baudrate == 115200

def test_tty(device_fixture):
    assert device_fixture.tty == "/mock/tty"

def test_baudrate_override(device_fixture_baudrate_override):
    assert device_fixture_baudrate_override.baudrate == 1234567

# This also tests wait=False and does not work with wait=True
def test_connection_failure(device_fixture_serial_failing):
    # pylint: disable=W0612
    with pytest.raises(pyduin.utils.DeviceConfigError) as result:
        assert device_fixture_serial_failing.open_serial_connection()
