# -*- coding: utf-8 -*-

import unittest
from mock import patch
import mock
import sys
from time import sleep
from pyduin.arduino import Arduino
from io import StringIO


CONFIG = {
    'tty': '/dev/ttyUSB0',
    'baudrate': '115200',
    'pinfile': 'tests/data/pinfiles/nano.yml',
    'model': 'NanO' # On purpose. To test lowercase conversion
}

class TestArduinoFirmwareMethods(unittest.TestCase):

    def setUp(self):
        self.Arduino = Arduino(**CONFIG)

    # def tearDown(self):
    #     self.Arduino.Connection.close()

    @patch('sys.stdout', new_callable=StringIO)
    def test_connection(self, mock_stdout):
        self.Arduino.open_serial_connection()
        # Test for "Boot complete" after pin setup
        msg = self.Arduino.Connection.readline().strip()
        self.assertEqual(msg, "Boot complete")

        # Test for pin setup response
        expected = ["0%2%2\r\n0%3%1\r\n0%4%1\r\n0%5%2\r\n"+
                    "0%6%2\r\n0%7%2\r\n0%8%2\r\n0%9%2\r\n"+
                    "0%10%2\r\n0%11%2\r\n0%12%2\r\n0%13%1\r\n"+
                    "0%14%0\r\n0%15%2\r\n0%16%0\r\n0%17%0\r\n"+
                    "0%18%2\r\n0%19%2\r\n0%20%-1\r\n0%21%-1\r\n"]
        msg = ""
        for i in range(2,22):
                msg += self.Arduino.Connection.readline()
        self.assertEqual(msg, expected[0])

        # Test for stdout
        expected = ["Set pin mode for pin 2 to INPUT_PULLUP\n"+
                    "Set pin mode for pin 3 to OUTPUT\n"+
                    "Set pin mode for pin 4 to OUTPUT\n"+
                    "Set pin mode for pin 5 to INPUT_PULLUP\n"+
                    "Set pin mode for pin 6 to INPUT_PULLUP\n"+
                    "Set pin mode for pin 7 to INPUT_PULLUP\n"+
                    "Set pin mode for pin 8 to INPUT_PULLUP\n"+
                    "Set pin mode for pin 9 to INPUT_PULLUP\n"+
                    "Set pin mode for pin 10 to INPUT_PULLUP\n"+
                    "Set pin mode for pin 11 to INPUT_PULLUP\n"+
                    "Set pin mode for pin 12 to INPUT_PULLUP\n"+
                    "Set pin mode for pin 13 to OUTPUT\n"+
                    "Set pin mode for pin 14 to INPUT\n"+
                    "Set pin mode for pin 15 to INPUT_PULLUP\n"+
                    "Set pin mode for pin 16 to INPUT\n"+
                    "Set pin mode for pin 17 to INPUT\n"+
                    "Set pin mode for pin 18 to INPUT_PULLUP\n"+
                    "Set pin mode for pin 19 to INPUT_PULLUP\n"+
                    "Set pin mode for pin 20 to INPUT_PULLUP\n"+
                    "Set pin mode for pin 21 to INPUT_PULLUP\n"
                    ]

        res = mock_stdout.getvalue()
        self.assertEqual(res, expected[0])

        # Test for pin mode OUTPUT
        self.Arduino.Pins[13].Mode.output()
        msg = self.Arduino.Connection.readline().strip()
        self.assertEqual(msg, '0%13%1')

        # Test for pin mode INPUT
        self.Arduino.Pins[13].Mode.input()
        msg = self.Arduino.Connection.readline().strip()
        self.assertEqual(msg, '0%13%0')

        # Test for pin mode INPUT_PULLUP}
        self.Arduino.Pins[13].Mode.input_pullup()
        msg = self.Arduino.Connection.readline().strip()
        self.assertEqual(msg, '0%13%2')

        # Test for pin on
        for pin in (4,7,8,12):
            self.Arduino.Pins[pin].Mode.output()
            msg = self.Arduino.Connection.readline().strip()
            self.assertEqual(msg, '%'.join(('0', '%d' % pin, '1')))

            self.Arduino.Connection.write('<AD%02d001>' % pin)
            msg = self.Arduino.Connection.readline().strip()
            self.assertEqual(msg, '%'.join(('0','%d' % pin, '1')))
            sleep(0.5)

            # Test for pin off
            self.Arduino.Connection.write('<AD%02d000>' % pin)
            msg = self.Arduino.Connection.readline().strip()
            self.assertEqual(msg, '%'.join(('0', '%d' % pin, '0')))

        # Test for invalid command
        self.Arduino.Connection.write('<óskdjsj>')
        msg = self.Arduino.Connection.readline().strip()
        self.assertEqual(msg, 'Invalid command:\xc3\xb3skdjsj')

        # Test for memory consumption
        self.Arduino.get_free_memory()
        msg = self.Arduino.Connection.readline().strip()
        aid,action,free = msg.split("%")
        self.assertEqual('%'.join((aid, action)), '0%free_mem')

        # Test for memory consumption
        self.Arduino.get_firmware_version()
        msg = self.Arduino.Connection.readline().strip()
        self.assertEqual(msg, "0%version%0.5.0")

        self.Arduino.Connection.close()

        # Test for bus....

if __name__ == '__main__':
    unittest.main()
