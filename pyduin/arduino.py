#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  arduino.py
#
"""
    Arduino module
"""
from collections import OrderedDict
import serial
import time
import weakref
import yaml
import os

from pin import ArduinoPin

IMMEDIATE_RESPONSE = True

class ArduinoConfigError(BaseException):
    pass


class Arduino(object):
    """
        Arduino object that can send messages to any arduino
    """
    Connection = False

    def __init__(self, tty=False, baudrate=False, model=False, pinfile=False, **config):

        self.model = model.lower() if model else \
            (config['model'].lower() if config.get('model', False) else False)
        self.tty = tty if tty else config.get('tty', False)
        self.baudrate = baudrate if baudrate else config.get('baudrate', False)
        self._pinfile = pinfile if pinfile else config.get('pinfile', False)
        self.ready = False
        self.return_arduino_answers = False

        if not self.model or not self.tty or not self.baudrate or not self._pinfile:
            mandatory = ('model', 'tty', 'baudrate', '_pinfile')
            missing = [x.lstrip('_') for x in mandatory if getattr(self,x) == False]
            raise ArduinoConfigError("The following mandatory options are missing: %s" % missing)

        if not os.path.isfile(self._pinfile):
            raise ArduinoConfigError("Cannot open pinfile: %s" % self._pinfile)


    def open_serial_connection(self):
        # Connect to ardino. Has to happen before configuring any pins
        try:
            self.Connection = serial.Serial( self.tty, self.baudrate, timeout=3)
            time.sleep(2)
            self.setup_pins()
            #self.ready = True
            return True
        except serial.SerialException:
            print "Could not open Serial connection on %s" % (self.tty)
            self.ready = False
            return False


    def setup_pins(self):

        self.analog_pins = []
        self.digital_pins = []
        self.pwm_cap_pins = []
        self.Pins = OrderedDict()
        self.Busses = {}
        Pins = {}

        with open(self._pinfile, 'r') as pinfile:
            self.pinfile = yaml.load(pinfile)

        _Pins = sorted(self.pinfile['Pins'].items(),
                       key=lambda x:int(x[1]['physical_id']))

        for name, pinconfig in _Pins:
            pin_id = pinconfig['physical_id']
            # Dont't register a pin twice
            if pin_id in self.Pins.keys():
                return False
            Pin = ArduinoPin(self, pin_id, **pinconfig)
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
        self.Connection.close()


    def send(self, message):
        self.Connection.write(message)
        if self.return_arduino_answers:
            return self.Connection.readline().strip()
        return True

