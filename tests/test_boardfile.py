# -*- coding: utf-8 -*-
""" Test Arduino pinfile """

import pytest
from pyduin.utils import PinNotFoundError
from pyduin import BoardFile

PINFILE = 'tests/data/boardfiles/nano.yml'

# pylint: disable=missing-docstring
class TestArduinoBoardFile:
    pinfile = BoardFile(PINFILE)

    def test_digital_pins(self):
        expected = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
        assert self.pinfile.digital_pins == expected

    def test_analog_pins(self):
        expected =  [14, 15, 16, 17, 18, 19, 20, 21]
        assert self.pinfile.analog_pins == expected

    def test_pwm_pins(self):
        expected = [3, 5, 6, 9, 10, 11]
        assert self.pinfile.pwm_pins == expected

    def test_led_pins(self):
        expected = [{'led1': 3},{'led10': 5},{'led': 13}]
        assert self.pinfile.leds == expected

    def test_i2c_interfaces(self):
        expected = {'1': {'sda1': 7, 'scl1': 8},
                    '20': {'sda20': 10, 'scl20': 11},
                    '0': {'sda': 18, 'scl': 19}}
        assert self.pinfile.i2c_interfaces == expected

    def test_spi_interfaces(self):
        expected = {'0': {'ss': 10, 'mosi': 11, 'miso': 12, 'sck': 13}}
        assert self.pinfile.spi_interfaces == expected

    def test_all_physical_pins(self):
        expected = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21]
        assert self.pinfile.physical_pin_ids == expected

    def test_normalize_pin_id_success(self):
        dataset = ((13, 13), ('13', 13), ('D13', 13), ('A0', 14))
        for data in dataset:
            assert self.pinfile.normalize_pin_id(data[0]) == data[1]

    def test_normalize_pin_failure(self):
        dataset = (1000, -99, 0, None, False, "D23", "AF")
        for data in dataset:
            with pytest.raises(PinNotFoundError) as result:
                assert self.pinfile.normalize_pin_id(data) == result
