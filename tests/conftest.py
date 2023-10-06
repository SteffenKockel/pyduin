# pylint: disable=W0621,C0116,C0114
# -*- coding: utf-8 -*-
#pytest_plugins = ['device']
import pytest
import serial

from pyduin.arduino import Arduino as Device

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

    # @property
    # def ret(self):
    #     return self._ret.encode('utf-8')

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

@pytest.fixture(scope="function")
def device_fixture(monkeypatch):
    monkeypatch.setattr('serial.Serial', SerialMock)
    #monkeypatch.setattr('Device.boardfile', boardfile)
    yield Device('uno', tty='/mock/tty', wait=True)


@pytest.fixture(scope="function")
def device_fixture_baudrate_override(monkeypatch):
    monkeypatch.setattr('serial.Serial', SerialMock)
    yield Device('uno', tty="/mock/tty", baudrate=1234567, wait=True)


@pytest.fixture(scope="function")
def device_fixture_serial_failing(monkeypatch):
    monkeypatch.setattr('serial.Serial', FailingSerialMock)
    yield Device('uno', tty='/mock/tty', baudrate=1234567, wait=False)
