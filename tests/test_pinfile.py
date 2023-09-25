# -*- coding: utf-8 -*-
""" Test Arduino pinfile """

import pytest
from pyduin.utils import PinNotFoundError
from pyduin import PinFile

PINFILE = 'tests/data/pinfiles/nano.yml'

# pylint: disable=missing-docstring
class TestArduinoPinFile:
    pinfile = PinFile(PINFILE)

    def test_digital_pins(self):
        expected = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
        assert self.pinfile.digital_pins == expected

    def test_analog_pins(self):
        expected =  [14, 15, 16, 17, 18, 19, 20, 21]
        assert self.pinfile.analog_pins == expected

    def test_pwm_pins(self):
        expected = [3, 5, 6, 9, 10, 11]
        assert self.pinfile.pwm_pins == expected

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
