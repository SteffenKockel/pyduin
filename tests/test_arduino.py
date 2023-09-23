# -*- coding: utf-8 -*-
""" Test Arduino firmware """

import unittest
from io import StringIO

from mock import patch

from pyduin import arduino
from pyduin import _utils as utils

CONFIG = {
    'tty': '/dev/ttyUSB0',
    'baudrate': '115200',
    'pinfile': 'tests/data/pinfiles/nano.yml',
    'board': 'nanoatmega328' 
}

# pylint: disable=missing-docstring
class TestArduinoFirmwareMethods(unittest.TestCase):

    def setUp(self):
        CONFIG['pinfile'] = utils.board_pinfile(CONFIG['board'])
        self.arduino = arduino.Arduino(wait=True, **CONFIG)

    # def tearDown(self):
    #     self.arduino.Connection.close()

    @patch('sys.stdout', new_callable=StringIO)
    def test_connection(self, mock_stdout): # pylint: disable=unused-argument
        self.arduino.open_serial_connection()
        # Test for "Boot complete" after pin setup
        def read():
            return self.arduino.Connection.readline().strip().decode('utf-8')

        msg = read()
        self.assertEqual(msg, "Boot complete")

        # # Test for pin setup response
        # expected = ["0%2%2\r\n0%3%1\r\n0%4%1\r\n0%5%2\r\n"+
        #             "0%6%2\r\n0%7%2\r\n0%8%2\r\n0%9%2\r\n"+
        #             "0%10%2\r\n0%11%2\r\n0%12%2\r\n0%13%1\r\n"+
        #             "0%14%0\r\n0%15%2\r\n0%16%0\r\n0%17%0\r\n"+
        #             "0%18%2\r\n0%19%2\r\n0%20%-1\r\n0%21%-1\r\n"]
        # msg = ""
        # for i in range(2,22):
        #     msg += self.arduino.Connection.readline().strip().decode('utf-8')
        # self.assertEqual(msg, expected[0])


        # # Test for stdout
        # expected = ["Set pin mode for pin 2 to INPUT_PULLUP\n"+
        #             "Set pin mode for pin 3 to OUTPUT\n"+
        #             "Set pin mode for pin 4 to OUTPUT\n"+
        #             "Set pin mode for pin 5 to INPUT_PULLUP\n"+
        #             "Set pin mode for pin 6 to INPUT_PULLUP\n"+
        #             "Set pin mode for pin 7 to INPUT_PULLUP\n"+
        #             "Set pin mode for pin 8 to INPUT_PULLUP\n"+
        #             "Set pin mode for pin 9 to INPUT_PULLUP\n"+
        #             "Set pin mode for pin 10 to INPUT_PULLUP\n"+
        #             "Set pin mode for pin 11 to INPUT_PULLUP\n"+
        #             "Set pin mode for pin 12 to INPUT_PULLUP\n"+
        #             "Set pin mode for pin 13 to OUTPUT\n"+
        #             "Set pin mode for pin 14 to INPUT\n"+
        #             "Set pin mode for pin 15 to INPUT_PULLUP\n"+
        #             "Set pin mode for pin 16 to INPUT\n"+
        #             "Set pin mode for pin 17 to INPUT\n"+
        #             "Set pin mode for pin 18 to INPUT_PULLUP\n"+
        #             "Set pin mode for pin 19 to INPUT_PULLUP\n"+
        #             "Set pin mode for pin 20 to INPUT_PULLUP\n"+
        #             "Set pin mode for pin 21 to INPUT_PULLUP\n"
        #             ]

        # res = mock_stdout.getvalue()
        # self.assertEqual(res, expected[0])

        # # Test for pin mode OUTPUT
        # self.arduino.Pins[13].Mode.output()
        # msg = read()
        # self.assertEqual(msg, '0%13%1')

        # # Test for pin mode INPUT
        # self.arduino.Pins[13].Mode.input()
        # msg = read()
        # self.assertEqual(msg, '0%13%0')

        # # Test for pin mode INPUT_PULLUP}
        # self.arduino.Pins[13].Mode.input_pullup()
        # msg = read()
        # self.assertEqual(msg, '0%13%2')

        # # Test for pin on
        # for pin in (4,7,8,12):
        #     self.arduino.Pins[pin].Mode.output()
        #     msg = read()
        #     self.assertEqual(msg, '%'.join(('0', f'{pin}', '1')))

        #     self.arduino.Connection.write(f'<AD{pin:02d}001>')
        #     msg = read()
        #     self.assertEqual(msg, '%'.join(('0','{pin}', '1')))
        #     sleep(0.5)

        #     # Test for pin off
        #     self.arduino.Connection.write(f'<AD{pin:02d}000>')
        #     msg = read()
        #     self.assertEqual(msg, '%'.join(('0', '{pin}', '0')))

        # # Test for invalid command
        # self.arduino.Connection.write('<óskdjsj>')
        # msg = read()
        # self.assertEqual(msg, 'Invalid command:\xc3\xb3skdjsj')

        # # Test for memory consumption
        # self.arduino.free_memory()
        # msg = read()
        # aid,action,free = msg.split("%")
        # self.assertEqual('%'.join((aid, action)), '0%free_mem')

        # # Test for memory consumption
        # self.arduino.firmware_version()
        # msg = read()
        # self.assertEqual(msg, "0%version%0.5.0")

        # self.arduino.Connection.close()

        # Test for bus....

if __name__ == '__main__':
    unittest.main()
