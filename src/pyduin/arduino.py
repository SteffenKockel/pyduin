#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  arduino.py
#
"""
    Arduino module
"""
import os
from collections import OrderedDict

import serial

from pyduin import _utils as utils
from pyduin import PinFile
from pyduin.pin import ArduinoPin

IMMEDIATE_RESPONSE = True


class ArduinoConfigError(BaseException):
    """
        Error Class to throw on config errors
    """

class Arduino:  # pylint: disable=too-many-instance-attributes
    """
        Arduino object that can send messages to any arduino
    """
    Connection = False
    analog_pins = False
    digital_pins = False
    pwm_cap_pins = False
    Pins = False
    Busses = False
    pinfile = False

    # pylint: disable=too-many-arguments
    def __init__(self,  board=False, tty='/dev/ttyUSB0', baudrate=115200, pinfile=False,
                 serial_timeout=3, wait=False):
        self.board = board
        self.tty = tty
        self.baudrate = baudrate
        self._pinfile = pinfile or utils.board_pinfile(board)
        self.pinfile = False
        self.ready = False
        self.wait = wait
        self.serial_timeout = serial_timeout
        self.Pins = OrderedDict()

        # if not self.board or not self.tty or not self.baudrate or not self._pinfile:
        #     mandatory = ('board', 'tty', 'baudrate', '_pinfile')
        #     missing = [x.lstrip('_') for x in mandatory if not getattr(self, x)]
        #     raise ArduinoConfigError(f'The following mandatory options are missing: {missing}')

        if not os.path.isfile(self._pinfile):
            raise ArduinoConfigError(f'Cannot open pinfile: {self._pinfile}')

        if self.wait:
            self.open_serial_connection()

    def open_serial_connection(self):
        """
            Open serial connection to the arduino and setup pins
            according to pinfile.
        """
        try:
            self.Connection = serial.Serial(self.tty, self.baudrate, timeout=self.serial_timeout)  # pylint: disable=invalid-name
            #if self.cli==False and self.use_socat==False:
            #time.sleep(1)
            self.setup_pins()
            self.ready = True
        except serial.SerialException as error:
            self.ready = False
            errmsg = f'Could not open Serial connection on {self.tty}'
            raise ArduinoConfigError(errmsg) from error

    def setup_pins(self):
        """
            Setup pins according to pinfile.
        """
        self.pinfile = PinFile(self._pinfile)

        for name, pinconfig in self.pinfile.pins:
            pin_id = pinconfig['physical_id']
            Pin = ArduinoPin(self, pin_id, **pinconfig)
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
        self.Connection.write(message.encode('utf-8'))
        if self.wait:
            msg = self.Connection.readline().decode('utf-8').strip()
            if msg == "Boot complete":
                # It seems, we need to re-send, if the first thing we see
                # is the boot-complete. Before, the Serial does not seem
                # to be up reliably.
                self.Connection.write(message.encode('utf-8'))
                msg = self.Connection.readline().decode('utf-8').strip()
            return msg
        return True

    def get_firmware_version(self):
        """
            Get arduino firmware version
        """
        res = self.send("<zv00000>")
        if self.wait:
            return res.split("%")[-1]
        return True

    def get_free_memory(self):
        """
            Return the free memory from the arduino
        """
        res = self.send("<zz00000>")
        if self.wait:
            return res.split("%")[-1]
        return res
