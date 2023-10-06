# pylint: disable=W0621,C0116,C0114
# -*- coding: utf-8 -*-


# pin modes
# 0 = input
# 1 = output
# 2 = input_pullup


def test_digital_pin(device_fixture):
    pin = device_fixture.Pins[2]
    assert pin.pin_type == 'digital'
    device_fixture.Connection.response = '0%02%0'
    assert pin.get_mode() == "0%02%0"
    device_fixture.Connection.response = '0%02%1'
    assert pin.high() == '0%02%1'
    device_fixture.Connection.response = '0%02%0'
    assert pin.low() == "0%02%0"

def test_set_pin_mode_output(device_fixture):
    pin = device_fixture.Pins[13]
    device_fixture.Connection.response = '0%13%1'
    assert pin.set_mode('output') == '0%13%1'
    assert pin.get_mode() == '0%13%1'

def test_set_pin_mode_pwm(device_fixture):
    pin = device_fixture.Pins[5]
    device_fixture.Connection.response = '0%3%0'
    assert pin.set_mode('pwm') == '0%3%0'
    assert pin.get_mode() == '0%3%0'

def test_set_pin_mode_input(device_fixture):
    pin = device_fixture.Pins[12]
    device_fixture.Connection.response = '0%12%0'
    assert pin.set_mode('input') == '0%12%0'
    assert pin.get_mode() == '0%12%0'

def test_set_pin_mode_input_pullup(device_fixture):
    pin = device_fixture.Pins[8]
    device_fixture.Connection.response = '0%8%2'
    assert pin.set_mode('input_pullup') == '0%8%2'
    assert pin.get_mode() == '0%8%2'

def test_set_pin_mode_invalid_pin_mode(device_fixture):
    pin = device_fixture.Pins[9]
    assert not pin.set_mode('foo')

# def test_pin_digital_write(device_fixture):
#     pin = device_fixture.Pins[6]
#     device_fixture.Connection.response = '0%6%1'
#     assert pin.read() == '0%6%1'
#     assert pin.message == '<DW06001>'

def test_pin_analog_write(device_fixture):
    pin = device_fixture.get_pin('A3')
    assert pin.pin_type == 'analog'
    device_fixture.Connection.response = '0%17%222'
    assert pin.pwm(222) == '0%17%222'
    assert pin.message == '<AW17222>'

def test_digital_read(device_fixture):
    pin = device_fixture.Pins[2]
    device_fixture.Connection.response = '0%2%1'
    assert pin.read() == '0%2%1'
    assert pin.message == '<DR02000>'

def test_analog_read(device_fixture):
    pin = device_fixture.get_pin('A0')
    device_fixture.Connection.response = '0%14%348'
    assert pin.pin_type == 'analog'
    assert pin.read() == '0%14%348'
    assert pin.message == '<AR14000>'

def test_pin_high(device_fixture):
    pin = device_fixture.get_pin(4)
    device_fixture.Connection.response = '0%4%1'
    assert pin.high() == '0%4%1'
    assert pin.message == '<DW04001>'

def test_pin_low(device_fixture):
    pin = device_fixture.get_pin(7)
    device_fixture.Connection.response = '0%7%0'
    pin.low()
    assert pin.low() == '0%7%0'
    assert pin.message == '<DW07000>'
