#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  arduino_cli.py
#
"""
    Arduino CLI functions and templates
"""
import argparse
import logging
import subprocess
import sys

from pyduin.arduino import Arduino
from pyduin import _utils as utils
from pyduin import VERSION, BuildEnv
from pyduin.utils import CliConfig

logger = utils.logger()


def get_arduino(config):
    """
        Get an arduino object, open the serial connection if it is the first connection
        or wait=True (socat off/unavailable) and return it. To circumvent restarts of
        the arduino on reconnect, one has two options

        * Start a socat proxy
        * Do not hang_up_on close
    """
    # if config['serial']['hang_up_on_close'] and config['serial']['use_socat']:
    #     errmsg = "Will not handle 'use_socat:yes' in conjunction with 'hang_up_on_close:no'" \
    #              "Either set 'use_socat' to 'no' or 'hang_up_on_close' to 'yes'."
    #     raise DeviceConfigError(errmsg)

    # aconfig = config['_arduino_']
    # socat = False
    # if config['serial']['use_socat'] and getattr(args, 'fwcmd', '') not in ('flash', 'f'):
    #     socat = SocatProxy(aconfig['tty'], aconfig['baudrate'], log_level=args.log_level)
    #     socat.start()
    arduino = Arduino(**config)
    return arduino

def prepare_buildenv(arduino, config, args):
    """ Idempotent function that ensures the platformio build env exists and contains
    the required files in the wanted state. """

    buildenv = BuildEnv(config.workdir, config.board, config.tty, log_level=config.log_level,
                        platformio_ini=config.platformio_ini)
    buildenv.create(force_recreate=getattr(args, 'no_cache', False))
    setattr(arduino, 'buildenv', buildenv)


def update_firmware(arduino):  # pylint: disable=too-many-locals,too-many-statements
    """
        Update firmware on arduino (cmmi!)
    """
    if arduino.socat:
        arduino.socat.stop()
    arduino.buildenv.build()

def versions(arduino, workdir):
    """ Print both firmware and package version """
    res = {"pyduin": VERSION,
           "device": arduino.firmware_version,
           "available": utils.available_firmware_version(workdir) }
    return res

def template_firmware(arduino):
    """ Render firmware from template """
    arduino.buildenv.template_firmware(arduino)

def lint_firmware():
    """ Static code check firmware """
    try:
        print("Running cpplint...")
        res = subprocess.check_output(['cpplint', utils.firmware])
        print(res)
    except subprocess.CalledProcessError:
        logger.error("The firmware contains errors")

def main(): # pylint: disable=too-many-locals,too-many-statements,too-many-branches
    """
        Evaluate user arguments and determine task
    """
    parser = argparse.ArgumentParser(prog="pyduin")
    paa = parser.add_argument
    paa('-B', '--buddy', help="Use identifier from configfile for detailed configuration")
    paa('-b', '--board', default=False, help="Board name")
    paa('-c', '--configfile', type=argparse.FileType('r'), default=False,
        help="Alternate configfile (default: ~/.pyduin.yml)")
    paa('-I', '--platformio-ini', default=False, type=argparse.FileType('r'),
        help="Specify an alternate platformio.ini")
    paa('-l', '--log-level', default=False)
    paa('-p', '--boardfile', default=False,
        help="Pinfile to use (default: <package_install_dir>/boardfiles/<board>.yml")
    paa('-s', '--baudrate', type=int, default=False)
    paa('-t', '--tty', default=False, help="Device tty. Consult `platformio device list`")
    paa('-w', '--workdir', type=str, default=False,
        help="Alternate workdir path (default: ~/.pyduin)")

    subparsers = parser.add_subparsers(help="Available sub-commands", dest="cmd")
    subparsers.add_parser("dependencies", help="Check dependencies")
    subparsers.add_parser("versions", help="List versions", aliases=['v'])
    subparsers.add_parser("free", help="Get free memory from device", aliases='f')
    ledparser = subparsers.add_parser("led", help="Interact with builtin LEDs (if available).")
    ledparser.add_argument('led', help='The id of the LED to interact with.', type=int)
    ledparser.add_argument('action', choices=['on','off'])
    firmware_parser = subparsers.add_parser("firmware", help="Firmware options", aliases=['fw'])
    fwsubparsers = firmware_parser.add_subparsers(help='Available sub-commands', dest="fwcmd")
    firmwareversion_parser = fwsubparsers.add_parser('version', aliases=['v'],
                                                     help="List firmware versions")
    flash_subparser = fwsubparsers.add_parser('flash', aliases=['f'],
                                               help="Flash firmware to device")
    flash_subparser.add_argument('-n', '--no-cache', action="store_true", default=False)
    fwsubparsers.add_parser("lint", help="Lint Firmware in <workdir>", aliases=['l'])
    fwv_subparsers = firmwareversion_parser.add_subparsers(help="Available sub-commands",
                                                           dest='fwscmd')
    fwv_subparsers.add_parser('device', help="Device Firmware", aliases=['d'])
    fwv_subparsers.add_parser("available", help="Available Firmware", aliases=['a'])

    pin_parser = subparsers.add_parser("pin", help="Pin related actions (high,low,pwm)",
                                        aliases=['p'])
    pin_parser.add_argument('pin', default=False, type=str, help="The pin to do action x with.",
                            metavar="<pin_id>")
    pinsubparsers = pin_parser.add_subparsers(help="Available sub-commands", dest="pincmd")
    pinmode_parser = pinsubparsers.add_parser("mode", help="Set pin modes")
    pinmode_parser.add_argument('mode', default=False,
                                choices=["input", "output", "input_pullup","pwm"],
                                help="Pin mode. 'input','output','input_pullup', 'pwm'")
    pinsubparsers.add_parser("high", aliases=['h'])
    pinsubparsers.add_parser("low", aliases=['l'])
    pinsubparsers.add_parser("read")
    digitalpin_parser_pwm = pinsubparsers.add_parser("pwm")
    digitalpin_parser_pwm.add_argument('value', type=int, help='0-255')

    args = parser.parse_args()
    if args.cmd == "dependencies":
        utils.dependencies()
        sys.exit(0)
    if not args.cmd:
        print("Nothing to do")
        sys.exit(1)

    config = CliConfig(args)
    log_level = args.log_level or config.log_level
    logger.setLevel(level=getattr(logging, log_level.upper()))
    arduino = get_arduino(config.arduino_config)

    prepare_buildenv(arduino, config, args)

    if args.cmd in ('versions', 'v'):
        print(versions(arduino, config.workdir))
        sys.exit(0)
    elif args.cmd in ('free', 'f'):
        print(arduino.free_memory)
        sys.exit(0)
    elif args.cmd in ('firmware', 'fw'):
        if args.fwcmd in ('version', 'v'):
            _ver = versions(arduino, config.workdir)
            print(_ver)
            if args.fwscmd in ('device', 'd'):
                print(_ver['device'])
            elif args.fwscmd in ('a', 'available'):
                print(_ver['available'])
            else:
                del _ver['pyduin']
                print(_ver)
        elif args.fwcmd in ('lint', 'l'):
            template_firmware(arduino)
            lint_firmware()
        elif args.fwcmd in ('flash', 'f'):
            template_firmware(arduino)
            lint_firmware()
            update_firmware(arduino)
        sys.exit(0)
    elif args.cmd == 'led':
        pin = arduino.get_led(args.led)
        pin.set_mode('output')
        res = pin.high() if args.action == 'on' else pin.low()
    elif args.cmd in ('pin', 'p'):
        if args.pincmd in ('high', 'low', 'h', 'l', 'pwm', 'p'):
            act = args.pincmd
            act = 'high' if act == 'h' else act
            act = 'low' if act == 'l' else act
            act = 'pwm' if act == 'p' else act
            pin = arduino.get_pin(args.pin)
            func = getattr(pin, act)
            if act == 'pwm':
                res = func(args.value)
            else:
                res = func()
            logger.debug(res)
        elif args.pincmd == 'mode' and args.mode in ('input_pullup', 'input', 'output', 'pwm'):
            pin = arduino.get_pin(args.pin)
            res = pin.set_mode(args.mode)
            logger.debug(res)
        elif args.pincmd == 'read':
            pin = arduino.get_pin(args.pin)
            res = pin.read()
            print(res.split('%')[-1])
        sys.exit(0)
    sys.exit(0)
if __name__ == '__main__':
    main()
