# pylint: disable=W0621,C0116,C0114
# -*- coding: utf-8 -*-

import pytest
from pyduin.utils import PinNotFoundError, BoardFile, DeviceConfigError

@pytest.fixture(scope="module")
def boardfile_fixture():
    _boardfile = BoardFile('tests/data/boardfiles/nano2.yml')
    return _boardfile

@pytest.fixture(scope="module")
def boardfile_fixture_extra_libs():
    yield BoardFile('tests/data/boardfiles/nano3.yml')

def test_digital_pins(boardfile_fixture):
    expected = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
    assert boardfile_fixture.digital_pins == expected

def test_analog_pins(boardfile_fixture):
    expected =  [14, 15, 16, 17, 18, 19, 20, 21]
    assert boardfile_fixture.analog_pins == expected

def test_pwm_pins(boardfile_fixture):
    expected = [3, 5, 6, 9, 10, 11]
    assert boardfile_fixture.pwm_pins == expected

def test_led_pins(boardfile_fixture):
    expected = [{'led1': 3}, {'led10': 5}]
    assert boardfile_fixture.leds == expected

def test_led_to_pin(boardfile_fixture):
    assert boardfile_fixture.led_to_pin('1') == 3
    assert boardfile_fixture.led_to_pin('10') == 5

def test_i2c_interfaces(boardfile_fixture):
    expected = {'1': {'sda1': 7, 'scl1': 8},
                '20': {'sda20': 10, 'scl20': 11},
                '0': {'sda': 18, 'scl': 19}}
    assert boardfile_fixture.i2c_interfaces == expected

def test_spi_interfaces(boardfile_fixture):
    expected = {'0': {'ss': 10, 'mosi': 11, 'miso': 12, 'sck': 13}}
    assert boardfile_fixture.spi_interfaces == expected

def test_all_physical_pins(boardfile_fixture):
    expected = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21]
    assert boardfile_fixture.physical_pin_ids == expected

def test_num_physical_pins(boardfile_fixture):
    assert boardfile_fixture.num_physical_pins == 20

def test_normalize_pin_id_success(boardfile_fixture):
    dataset = ((13, 13), ('13', 13), ('D13', 13), ('A0', 14))
    for data in dataset:
        assert boardfile_fixture.normalize_pin_id(data[0]) == data[1]

def test_normalize_pin_failure(boardfile_fixture):
    dataset = (1000, -99, 0, None, False, "D23", "AF")
    for data in dataset:
        with pytest.raises(PinNotFoundError) as result:
            assert boardfile_fixture.normalize_pin_id(data) == result

def test_get_pin_config(boardfile_fixture):
    data = {'alias': 'D13', 'extra': ['led', 'sck'], 'physical_id': 13}
    assert boardfile_fixture.get_pin_config(13) == data
    assert boardfile_fixture.get_pin_config(1) == {}


def test_extra_libs(boardfile_fixture_extra_libs):
    assert boardfile_fixture_extra_libs.extra_libs == ['foo', 'bar']

def test_boardfile_unreadable():
    # pylint: disable=unused-variable
    with pytest.raises(DeviceConfigError) as err:
        BoardFile('test/data/boardfiles/nonexistsnt.yml')
