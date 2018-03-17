#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  arduino.py
#
"""
    Arduino module
"""
from collections import OrderedDict
import os
import serial
import time
import yaml

from pin import ArduinoPin # pylint: disable=relative-import

IMMEDIATE_RESPONSE = True

class ArduinoConfigError(BaseException):
    """
        Error Class to throw on config errors
    """
    pass


class Arduino(object): # pylint: disable=too-many-instance-attributes
    """
        Arduino object that can send messages to any arduino
    """
    Connection = False # pylint: disable=invalid-name
    analog_pins = False
    digital_pins = False
    pwm_cap_pins = False
    Pins = False # pylint: disable=invalid-name
    Busses = False # pylint: disable=invalid-name
    pinfile = False


    def __init__(self, tty=False, baudrate=False, model=False, pinfile=False, **config):
        _model = config['model'].lower() if config.get('model') else False
        self.model = model.lower() if model else _model # pylint: disable=maybe-no-member
        self.tty = tty if tty else config.get('tty', False)
        self.baudrate = baudrate if baudrate else config.get('baudrate', False)
        self._pinfile = pinfile if pinfile else config.get('pinfile', False)
        self.ready = False
        self.cli_mode = False

        if not self.model or not self.tty or not self.baudrate or not self._pinfile:
            mandatory = ('model', 'tty', 'baudrate', '_pinfile')
            missing = [x.lstrip('_') for x in mandatory if getattr(self, x) == False]
            raise ArduinoConfigError("The following mandatory options are missing: %s" % missing)

        if not os.path.isfile(self._pinfile):
            raise ArduinoConfigError("Cannot open pinfile: %s" % self._pinfile)


    def open_serial_connection(self):
        """
            Open serial connection to the arduino and setup pins
            according to pinfile.
        """
        try:
            self.Connection = serial.Serial(self.tty, self.baudrate, timeout=10) # pylint: disable=invalid-name
            time.sleep(1.5)
            self.setup_pins()
            self.ready = True
            return True
        except serial.SerialException:
            print "Could not open Serial connection on %s" % (self.tty)
            self.ready = False
            return False


    def setup_pins(self):
        """
            Setup pins according to pinfile.
        """
        self.analog_pins = []
        self.digital_pins = []
        self.pwm_cap_pins = []
        self.Pins = OrderedDict() # pylint: disable=invalid-name
        self.Busses = {} # pylint: disable=invalid-name

        with open(self._pinfile, 'r') as pinfile:
            self.pinfile = yaml.load(pinfile)

        _Pins = sorted(self.pinfile['Pins'].items(), # pylint: disable=invalid-name
                       key=lambda x: int(x[1]['physical_id']))

        for name, pinconfig in _Pins: # pylint: disable=unused-variable
            pin_id = pinconfig['physical_id']
            # Dont't register a pin twice
            if pin_id in self.Pins.keys():
                return False
            Pin = ArduinoPin(self, pin_id, **pinconfig) # pylint: disable=invalid-name,star-args
            # Determine capabilities
            if Pin.pin_type == 'analog':
                self.analog_pins.append(pin_id)
            elif Pin.pin_type == 'digital':
                self.digital_pins.append(pin_id)
            if Pin.pwm_capable == True:
                self.pwm_cap_pins.append(pin_id)
            # Update pin dict
            self.Pins[pin_id] = Pin


    def close_serial_connection(self):
        """
            Close the serial connection to the arduino.
        """
        self.Connection.close()


    def send(self, message):
        """
            Send a serial message to the arduino.
        """
        self.Connection.write(message)
        if self.cli_mode == True:
            msg = self.Connection.readline().strip()
            if msg == "Boot complete":
                msg = self.Connection.readline().strip()
            return msg
        return True


    def get_firmware_version(self):
        """
            Get arduino firmware version
        """
        res = self.send("<zv00000>")
        if self.cli_mode:
            return res.split("%")[-1]
        return True


    def get_free_memory(self):
        """
            Return the free memory from the arduino
        """
        res = self.send("<zz00000>")
        if self.cli_mode:
            return res.split("%")[-1]
        return res
