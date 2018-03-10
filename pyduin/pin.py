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

    def __init__(self, Pin):
        self.Pin = weakref.proxy(Pin)

    def on(self, value=0):
        print """ Enable pwm for pin """
        return True

    def off(self):
        print """ Disable pwm """
        return True

    def state(self):
        print """ Get PWM state """
        return True


class Mode(object):

    def __init__(self, Pin, pin_mode):
        self.Pin = weakref.proxy(Pin)
        self.wanted_mode = pin_mode
        self._setpinmodetext = """Set pin mode for  pin %d to """ % (self.Pin.pin_id)
        self.set_mode(pin_mode)


    def analogOrDigital(self):
        return self.Pin.pin_type


    def output(self):
        aod = self.analogOrDigital()
        self.wanted_mode = self.Pin.pin_mode = 'output'

        print """%s OUTPUT""" % self._setpinmodetext
        message = "<MO%02d001>" if self.analogOrDigital() == 'digital'  else "<MO%s030>"
        message = message % self.Pin.pin_id
        r = self.Pin.Arduino.send(message)
        self.Pin.pin_mode='output'
        return r


    def input(self):
        self.wanted_mode = self.Pin.pin_mode = 'input'
        self.wanted_mode = 'input'
        print """%s INPUT""" % self._setpinmodetext
        message = "<MI%02d000>" if self.analogOrDigital() == 'digital'  else "<MI%s000>"
        message = message % self.Pin.pin_id
        r = self.Pin.Arduino.send( message)
        self.Pin.pin_mode='input'
        return r


    def input_pullup(self):
        self.wanted_mode = self.Pin.pin_mode = 'input_pullup'
        print """%s INPUT_PULLUP""" % self._setpinmodetext
        message = "<MP%02d000>" if self.analogOrDigital() == 'digital'  else "<MP%s000>"
        message = message % self.Pin.pin_id
        r = self.Pin.Arduino.send( message)
        self.Pin.pin_mode='input_pullup'
        return r


    def get_mode(self):
        message = "<mm%02d000>" if self.analogOrDigital() == 'digital'  else "<mm%sd000>"
        message = message % self.Pin.pin_id
        r = self.Pin.Arduino.send(message)
        return r


    def set_mode(self, mode):
        """
            Sets the pin mode for this Pin
        """
        modesetter = getattr(self, mode, False)
        if modesetter:
            modesetter()
            return True
        print "Could not set mode %s for pin %s" % (mode, self.Pin.pin_id)
        return False


class ArduinoPin(object):
    """
           Base Arduino Pin
    """

    role = False

    def __init__(self,arduino, pin_id, **config):
        self.Arduino = weakref.proxy(arduino)
        self.pin_id = int(pin_id)
        self.pin_type = config.get('pin_type', 'digital')
        self.pwm_capable = config.get('pwm_capable', False)
        self.pwm_enabled = config.get('pwm_enabled', False)
        self.pin_mode = config.get('pin_mode', 'input_pullup')
        if self.pwm_capable:
            self.pwm = PWM(self)
        if self.pwm_capable and self.pwm_enabled:
            self.pwm.on('0')
        self.Mode = Mode(self, self.pin_mode)


    def set_mode(self, mode):
        """
            Sets the pin mode for this Pin
        """
        return self.Mode.set_mode(mode)


    def get_mode(self, as_int=False):
        """
            Get the pin mode for this pin
        """
        return self.Mode.get_mode()

    def high(self):
        message = "<AD%02d001>" %  self.pin_id
        self.Arduino.send(message)

    def low(self):
        message = "<AD%02d000>" % self.pin_id
        self.Arduino.send(message)

    def state(self):
        m = "<aD%02d000>" % self.pin_id
        self.Arduino.send(messafe)
