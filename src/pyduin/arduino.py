#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  arduino.py
#
"""
    Arduino module
"""

from collections import OrderedDict
import logging
import serial

from pyduin import _utils as utils
from pyduin import DeviceConfigError, SocatProxy
from pyduin.pin import ArduinoPin

IMMEDIATE_RESPONSE = True


class Arduino:  # pylint: disable=too-many-instance-attributes
    """
        Arduino object that can send messages to any arduino
    """
    def __init__(self,  board, tty, **kwargs):

        self.tty = tty
        self.board = board
        self.wait = kwargs.get('wait', False)
        self.serial_timeout = kwargs.get('serial_timeout', 3)
        self.Pins = OrderedDict()
        self.socat = kwargs.get('socat', False)
        self.logger = utils.logger()
        log_level = kwargs.get('log_level', logging.INFO)
        self.logger.setLevel(utils.loglevel_int(log_level))
        self.boardfile = utils.get_boardfile_obj(self.board)
        self.baudrate = kwargs.get('baudrate', False) or self.boardfile.baudrate

        if self.socat:
            self.socat = SocatProxy(self.tty, self.baudrate, log_level=log_level)

        if self.wait and self.tty and self.baudrate:
            self.open_serial_connection()

    def open_serial_connection(self):
        """
            Open serial connection to the arduino and setup pins
            according to boardfile.
        """
        try:
            tty = self.socat.proxy_tty if self.socat else self.tty
            if self.socat:
                self.socat.start()
            self.Connection = serial.Serial(tty, self.baudrate, timeout=self.serial_timeout)  # pylint: disable=invalid-name
            self.setup_pins()
            return True
        except serial.SerialException as error:
            errmsg = f'Could not open Serial connection on {self.tty}'
            raise DeviceConfigError(errmsg) from error

    def setup_pins(self):
        """
            Setup pins according to boardfile.
        """
        for pin in self.boardfile.pins:
            self.Pins[pin['physical_id']] = ArduinoPin(self, **pin)

    def get_pin(self, pin):
        """ Return the pin object of a given pin (or it's alias) """
        pin = self.boardfile.normalize_pin_id(pin)
        return self.Pins[pin]

    def get_led(self, led:int):
        """ Return the pin object correspinding to an id of an led """
        return self.Pins[self.boardfile.led_to_pin(led)]

    def close_serial_connection(self):
        """
            Close the serial connection to the arduino.
        """
        return self.Connection.close()

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

    @property
    def firmware_version(self):
        """ Get arduino firmware version """
        res = self.send("<zv00000>")
        if self.wait:
            return res.split("%")[-1]
        return res

    @property
    def free_memory(self):
        """ Return the free memory from the arduino """
        res = self.send("<zz00000>")
        if self.wait:
            return res.split("%")[-1]
        return res
