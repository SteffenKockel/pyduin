 #!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  pin.py
#
"""
    Arduino pin module
"""
import weakref


class Mode:
    """
        A pin mode object
    """

    def __init__(self, pin, pin_mode):
        self.pin = weakref.proxy(pin)
        self.logger = self.pin.arduino.logger
        self.wanted_mode = pin_mode
        self._setpinmodetext = f'Set pin mode for pin {self.pin.pin_id} to'
        if not self.pin.arduino.wait:
            self.set_mode(pin_mode)

    # def analog_or_digital(self):
    #     """
    #         Get the pin type (analog or digital)
    #     """
    #     return self.pin.pin_type

    def output(self):
        """
            Set mode for this pin to output
        """
        self.wanted_mode = self.pin.pin_mode = 'output'
        self.logger.info('%s OUTPUT', self._setpinmodetext)
        self.pin.pin_mode = 'output'
        return self.pin.arduino.send(f'<MO{self.pin.pin_id:02d}001>')

    def input(self):
        """
            Set mode for this pin to INPUT
        """
        self.wanted_mode = self.pin.pin_mode = 'input'
        self.wanted_mode = 'input'
        self.logger.info("%s INPUT", self._setpinmodetext)
        self.pin.pin_mode = 'input'
        return self.pin.arduino.send(f'<MI{self.pin.pin_id:02d}000>')

    def input_pullup(self):
        """
            Set mode for this pin to INPUT_PULLUP
        """
        self.wanted_mode = self.pin.pin_mode = 'input_pullup'
        self.logger.info("%s INPUT_PULLUP", self._setpinmodetext)
        self.pin.pin_mode = 'input_pullup'
        return self.pin.arduino.send(f'<MP{self.pin.pin_id:02d}000>')

    @property
    def get_wanted_mode(self):
        """ Return the mode expected for this pin """
        return self.pin.pin_mode

    def get_mode(self):
        """
            Get the mode from this pin
        """
        message = f'<MR{self.pin.pin_id:02d}000>'
        return self.pin.arduino.send(message)

    def set_mode(self, mode):
        """
            Sets the pin mode for this Pin
        """
        if mode == 'pwm':
            mode = 'output'
        modesetter = getattr(self, mode.lower(), False)
        if modesetter:
            return modesetter()
        print("Could not set mode %s for pin %s", mode, self.pin.pin_id)
        return False


class ArduinoPin:  # pylint: disable=too-many-instance-attributes
    """
           Base Arduino Pin
    """

    role = False

    def __init__(self, arduino, **pin_config):
        self.arduino = weakref.proxy(arduino)  # pylint: disable=invalid-name
        self.pin_id = pin_config['physical_id']
        self.pin_type = 'analog' if 'analog' in pin_config.get('extra', [])  else 'digital'
        #self.pwm_capable = pin_config.get('pwm_capable', False)
        #self.pwm_enabled = pin_config.get('pwm_enabled', False)
        self.pin_mode = pin_config.get('pin_mode', 'input_pullup')
        self.Mode = Mode(self, self.pin_mode)  # pylint: disable=invalid-name
        self.message = ""

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
        self.message = f'<DW{self.pin_id:02d}001>'
        return self.arduino.send(self.message)

    def low(self):
        """
            Set this pin to LOW
        """
        self.message = f'<DW{self.pin_id:02d}000>'
        return self.arduino.send(self.message)

    def read(self):
        """
            Read-out a pin. 
        """
        self.message = f'<{self.pin_type[0].upper()}R{self.pin_id:02d}000>'
        return self.arduino.send(self.message)

    def pwm(self, value=0):
        """
            Set pin to a specific pwm value
        """
        # @TODO, check, if the pin is indeed a pwm capable pin
        self.message = f'<AW{self.pin_id:02d}{value:03d}>'
        return self.arduino.send(self.message)
