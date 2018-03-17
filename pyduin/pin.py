#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  pin.py
#
"""
    Arduino pin module
"""
import weakref


class PWM(object):
    """
        A pulse width modulation object
    """

    def __init__(self, Pin):
        self.Pin = weakref.proxy(Pin) # pylint: disable=invalid-name

    def enable(self, value=0): # pylint: disable=no-self-use
        """
            Enable PWM for this pin
        """
        print """ Enable pwm for pin with value %s""" % value
        return True

    def disable(self): # pylint: disable=no-self-use
        """
            Disable PWM for this pin
        """
        print """ Disable pwm """
        return True

    def state(self): # pylint: disable=no-self-use
        """
            Determine PWM state and level
        """
        print """ Get PWM state """
        return True

class Mode(object):
    """
        A pin mode object
    """

    def __init__(self, Pin, pin_mode):
        self.Pin = weakref.proxy(Pin) # pylint: disable=invalid-name
        self.wanted_mode = pin_mode
        self._setpinmodetext = """Set pin mode for pin %d to""" % (self.Pin.pin_id)
        self.set_mode(pin_mode)


    def analog_or_digital(self):
        """
            Get the pin type (analog or digital)
        """
        return self.Pin.pin_type


    def output(self):
        """
            Set mode for this pin to output
        """
        self.wanted_mode = self.Pin.pin_mode = 'output'
        print """%s OUTPUT""" % self._setpinmodetext
        message = "<MO%02d001>" if self.analog_or_digital() == 'digital'  else "<MO%s030>"
        message = message % self.Pin.pin_id
        self.Pin.pin_mode = 'output'
        return self.Pin.Arduino.send(message)


    def input(self):
        """
            Set mode for this pin to INPUT
        """
        self.wanted_mode = self.Pin.pin_mode = 'input'
        self.wanted_mode = 'input'
        print """%s INPUT""" % self._setpinmodetext
        message = "<MI%02d000>" if self.analog_or_digital() == 'digital'  else "<MI%s000>"
        message = message % self.Pin.pin_id
        self.Pin.pin_mode = 'input'
        return self.Pin.Arduino.send(message)


    def input_pullup(self):
        """
            Set mode for this pin to INPUT_PULLUP
        """
        self.wanted_mode = self.Pin.pin_mode = 'input_pullup'
        print """%s INPUT_PULLUP""" % self._setpinmodetext
        message = "<MP%02d000>" if self.analog_or_digital() == 'digital'  else "<MP%s000>"
        message = message % self.Pin.pin_id
        self.Pin.pin_mode = 'input_pullup'
        return self.Pin.Arduino.send(message)


    def get_mode(self):
        """
            Get the mode from this pin
        """
        message = "<mm%02d000>" if self.analog_or_digital() == 'digital'  else "<mm%sd000>"
        message = message % self.Pin.pin_id
        return self.Pin.Arduino.send(message)


    def set_mode(self, mode):
        """
            Sets the pin mode for this Pin
        """
        modesetter = getattr(self, mode.lower(), False)
        if modesetter:
            return modesetter()
        print "Could not set mode %s for pin %s" % (mode, self.Pin.pin_id)
        return False


class ArduinoPin(object): # pylint: disable=too-many-instance-attributes
    """
           Base Arduino Pin
    """

    role = False

    def __init__(self, arduino, pin_id, **config):
        self.Arduino = weakref.proxy(arduino) # pylint: disable=invalid-name
        self.pin_id = int(pin_id)
        self.pin_type = config.get('pin_type', 'digital')
        self.pwm_capable = config.get('pwm_capable', False)
        self.pwm_enabled = config.get('pwm_enabled', False)
        self.pin_mode = config.get('pin_mode', 'input_pullup')
        if self.pwm_capable:
            self.pwm = PWM(self)
        if self.pwm_capable and self.pwm_enabled:
            self.pwm.enable('0')
        self.Mode = Mode(self, self.pin_mode) # pylint: disable=invalid-name


    def set_mode(self, mode):
        """
            Sets the pin mode for this Pin
        """
        return self.Mode.set_mode(mode)


    def get_mode(self):
        """
            Get the pin mode for this pin
        """
        return self.Mode.get_mode()

    def high(self):
        """
            Set this pin to HIGH
        """
        message = "<AD%02d001>" %  self.pin_id
        return self.Arduino.send(message)


    def low(self):
        """
            Set this pin to LOW
        """
        message = "<AD%02d000>" % self.pin_id
        return self.Arduino.send(message)


    def state(self):
        """
            Determine, if the state is LOW or HIGH
        """
        message = "<aD%02d000>" % self.pin_id
        return self.Arduino.send(message)
