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
import logging
import serial

from pyduin import _utils as utils
from pyduin import PinFile, DeviceConfigError, SocatProxy
from pyduin.pin import ArduinoPin

IMMEDIATE_RESPONSE = True


class Arduino:  # pylint: disable=too-many-instance-attributes
    """
        Arduino object that can send messages to any arduino
    """
    Connection = False
    analog_pins = False
    digital_pins = False
    pwm_cap_pins = False
    Busses = False

    # pylint: disable=too-many-arguments
    def __init__(self,  board=False, tty=False, baudrate=115200, pinfile=False,
                 serial_timeout=3, wait=False, socat=False, log_level=logging.INFO):
        self.board = board
        self.tty = tty
        self.baudrate = baudrate
        self._pinfile = pinfile or utils.board_pinfile(board)
        self.pinfile = False
        self.ready = False
        self.wait = wait
        self.serial_timeout = serial_timeout
        self.Pins = OrderedDict()
        self.socat = socat
        self.logger = utils.logger()
        self.logger.setLevel(utils.loglevel_int(log_level))
        self.pinfile = PinFile(self._pinfile)

        if not os.path.isfile(self._pinfile):
            raise DeviceConfigError(f'Cannot open pinfile: {self._pinfile}')

        if not self.baudrate:
            self.baudrate = self.pinfile.baudrate

        if self.socat:
            self.socat = SocatProxy(self.tty, self.baudrate, log_level=log_level)

        if self.wait and self.tty and self.baudrate:
            self.open_serial_connection()

    def open_serial_connection(self):
        """
            Open serial connection to the arduino and setup pins
            according to pinfile.
        """
        try:
            tty = self.socat.proxy_tty if self.socat else self.tty
            if self.socat:
                self.socat.start()
            self.Connection = serial.Serial(tty, self.baudrate, timeout=self.serial_timeout)  # pylint: disable=invalid-name
            self.setup_pins()
            self.ready = True
        except serial.SerialException as error:
            self.ready = False
            errmsg = f'Could not open Serial connection on {self.tty}'
            raise DeviceConfigError(errmsg) from error

    def setup_pins(self):
        """
            Setup pins according to pinfile.
        """
        for _pin in self.pinfile.pins:
            pin_id = _pin[1]['physical_id']
            self.Pins[pin_id] = ArduinoPin(self, pin_id, **_pin[1])

    def close_serial_connection(self):
        """
            Close the serial connection to the arduino.
        """
        self.Connection.close()

    def send(self, message):
        """
            Send a serial message to the arduino.
        """
        # print(message)
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

    @property
    def firmware_version(self):
        """ Get arduino firmware version """
        res = self.send("<zv00000>")
        if self.wait:
            return res.split("%")[-1]
        return True

    @property
    def free_memory(self):
        """ Return the free memory from the arduino """
        res = self.send("<zz00000>")
        if self.wait:
            return res.split("%")[-1]
        return res
