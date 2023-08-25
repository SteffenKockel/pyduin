#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  arduino_cli.py
#
"""
    Arduino CLI functions and templates
"""
import argparse
import configparser
import os
from shutil import which
import subprocess
import sys
import time
import logging
import yaml
from termcolor import colored

from pyduin.arduino import Arduino, ArduinoConfigError
from pyduin import _utils as utils

# Basic user config template

CONFIG_TEMPLATE = """

serial:
  use_socat: no
  hang_up_on_close: no

buddies:
  nano1:
    board: nanoatmega238
  uno1:
    board: uno
"""

class AttrDict(dict):
    """ Helper class to ease the handling of ini files with configparser. """
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


def ensure_user_config_file(location):
    """
    Check, if basic config file ~/.pyduin.yml exists, else create basic config
    from template.
    """
    if not os.path.isfile(location):
        logging.info('Writing default config file to %s', location)
        with open(location, 'w', encoding='utf-8') as _configfile:
            _configfile.write(CONFIG_TEMPLATE)

def get_basic_config(args):
    """
        Get configuration,  needed for all operations
    """
    configfile = args.configfile or '~/.pyduin.yml'
    confpath = os.path.expanduser(configfile)
    ensure_user_config_file(confpath)
    with open(confpath, 'r', encoding='utf-8') as _configfile:
        cfg = yaml.load(_configfile, Loader=yaml.Loader)
    logging.debug("Using configuration file: %s", confpath)

    platformio_ini = args.platformio_ini or utils.platformio_ini
    logging.debug("Using platformio.ini in: %s", platformio_ini)
    parser = configparser.ConfigParser(dict_type=AttrDict)
    parser.read(platformio_ini)
    cfg['platformio_ini'] = parser

    cfg['firmware'] = args.firmware or utils.firmware
    logging.debug("Using firmware from: %s", cfg['firmware'])

    cfg['pinfiledir'] = args.pinfile_dir or utils.pinfiledir
    logging.debug("Using pinfiles from: %s", cfg['pinfiledir'])
    return cfg

def _get_arduino_config(args, config):
    """
    Determine tty, baudrate, model and pinfile for the currently used arduino.
    """
    arduino_config = {}
    for opt in ('tty', 'baudrate', 'board', 'pinfile'):
        _opt = getattr(args, opt) if getattr(args, opt) else \
               config['buddies'][args.buddy][opt] if \
               args.buddy and config.get('buddies') and \
               config['buddies'].get(args.buddy) and \
               config['buddies'][args.buddy].get(opt) else False
        arduino_config[opt] = _opt

    # Ensure defaults.
    if not arduino_config.get('tty'):
        arduino_config['tty'] = '/dev/ttyUSB0'
    if not arduino_config.get('baudrate'):
        arduino_config['baudrate'] = 115200
    if not arduino_config.get('pinfile'):
        pinfile = '/'.join((config['pinfiledir'], f'{arduino_config["board"]}.yml'))
        arduino_config['pinfile'] = pinfile

    # Ensure buddies section exists, even if empty
    config['buddies'] = config.get('buddies', {})
    config['_arduino_'] = arduino_config
    model = config['_arduino_']['board']
    check_board_support(model, config)
    logging.debug("Using pinfile: %s", arduino_config['pinfile'])

    if not os.path.isfile(arduino_config['pinfile']):
        errmsg = f'Cannot find pinfile {arduino_config["pinfile"]}'
        raise ArduinoConfigError(errmsg)
    return config

def verify_buddy(buddy, config):
    """
    Determine if the given buddy is defined in config file and the configfile has
    a 'buddies' section at all.
    """
    if not config.get('buddies'):
        raise ArduinoConfigError("Configfile is missing 'buddies' section")
    if not config['buddies'].get(buddy):
        errmsg = f'Buddy "{buddy}" not described in configfile''s "buddies" section'
        raise ArduinoConfigError(errmsg)
    return True


def check_board_support(board, config):
    """
    Determine if the configured model is supported. Do so by checking the
    platformio config file for env definitions.
    """
    sections = config['platformio_ini'].sections()
    boards = [x.split(':')[-1] for x in sections if x.startswith('env:')]
    if not board in boards:
        logging.error("Board (%s) not in supported boards list %s",
            board, boards)
        return False
    return True



def get_pyduin_userconfig(args, config):
    """
        Get advanced config for arduino interaction
    """
    if args.buddy:
        verify_buddy(args.buddy, config)
    config = _get_arduino_config(args, config)
    return config


def _get_proxy_tty_name(config):
    tty = os.path.basename(config['_arduino_']['tty'])
    proxy_tty = os.path.sep.join(('/tmp', f'{tty}.tty'))
    return proxy_tty


def get_arduino(args, config):
    """
        Get an arduino object, open the serial connection if it is the first connection
        or cli_mode=True (socat off/unavailable) and return it. To circumvent restarts of
        the arduino on reconnect, one has two options

        * Start a socat proxy
        * Do not hang_up_on_close
    """
    if config['serial']['hang_up_on_close'] and config['serial']['use_socat']:
        errmsg = "Will not handle 'use_socat:yes' in conjunction with 'hang_up_on_close:no'" \
                 "Either set 'use_socat' to 'no' or 'hang_up_on_close' to 'yes'."
        raise ArduinoConfigError(errmsg)

    aconfig = config['_arduino_']
    if config['serial']['use_socat'] and not args.flash:
        proxy_tty = _get_proxy_tty_name(config)

        #is_proxy_start = not os.path.exists(proxy_tty)
        # start the socat proxy
        if not os.path.exists(proxy_tty):
            # Enforce hulpc:on
            subprocess.check_output(['stty', '-F', aconfig['tty'], 'hupcl'])
            #time.sleep(1)
            socat_opts = {'baudrate': aconfig['baudrate'],
                          'source_tty': aconfig['tty'],
                          'proxy_tty': proxy_tty,
                          'debug': False
                         }
            socat_cmd = utils.socat_cmd(**socat_opts)
            print(socat_cmd)
            subprocess.Popen(socat_cmd) # pylint: disable=consider-using-with
            print(colored(f'Started socat proxy on {proxy_tty}', 'cyan'))
            time.sleep(1)

        aconfig['tty'] = proxy_tty

    arduino = Arduino(tty=aconfig['tty'], baudrate=aconfig['baudrate'],
                  pinfile=aconfig['pinfile'], board=aconfig['board'],
                  cli=True)
    return arduino

@staticmethod
def check_dependencies():
    """
        Check, if platformio and socat are available.
    """
    ret = True
    pio = which('pio')
    if pio:
        logging.debug("Platformio found in %s.", pio)
    else:
        logging.warning("Platformio not installed. Flashing does not work.")
        ret = False
    socat = which('socat')
    if socat:
        logging.debug("Socat found in %s", socat)
    else:
        logging.warning("Socat not found. Some features may not work.")
        ret = False
    return ret



def update_firmware(args, config):  # pylint: disable=too-many-locals,too-many-statements
    """
        Update firmware on arduino (cmmi!)
    """

    if not os.path.exists(config['_arduino_']['tty']):
        errmsg = f'{config["_arduino_"]["tty"]} not found. Connected?'
        raise ArduinoConfigError(errmsg)

    proxy_tty = _get_proxy_tty_name(config)
    if os.path.exists(proxy_tty):
        print(colored("Socat proxy running. Stopping.", 'red'))
        cmd = f'ps aux | grep socat | grep -v grep | grep {proxy_tty} | awk ''{ print $2 }'''
        pid = subprocess.check_output(cmd, shell=True).strip()
        subprocess.check_output(['kill', f'{pid}'])
        time.sleep(1)

    out = subprocess.check_output(['pio', '-e', args.model, 'upload'])
    logging.info(out)


def versions():
    """
        Print both firmware and package version
    """

def main():
    """
        Evaluate user arguments and determine task
    """
    parser = argparse.ArgumentParser(description='Manage arduino from command line.')
    paa = parser.add_argument
    paa('-a', '--action', default=False, type=str, help="Action, e.g 'high', 'low'")
    paa('-b', '--baudrate', default=False, help="Connection speed (default: 115200)")
    paa('-B', '--buddy', type=str, default=False,
        help="Use identifier from configfile for detailed configuration")
    paa('-c', '--configfile', type=argparse.FileType('r'), default=False,
        help="Alternate configfile (default: ~/.pyduin.yml)")
    paa('-f', '--flash', action='store_true', default=False,
        help="Flash firmware to the arduino (cmmi)")
    paa('-d', '--pinfile-dir')
    paa('-D', '--install-dependencies', action='store_true',
        help='Download and install dependencies according to ~/.pyduin.yml')
    paa('-F', '--firmware', default=False, type=argparse.FileType('r'),
        help="Alternate Firmware file.")
    paa('-i', '--ino', default=False,
        help='.ino file to build and uplad.')
    paa('-I', '--platformio-ini', default=False, type=argparse.FileType('r'),
        help="Specify an alternate platformio.ini")
    paa('-l', '--log-level', default="DEBUG")
    paa('-m', '--board', default=False, help="Board name")
    paa('-M', '--mode', default=False, choices=["input", "output", "input_pullup"],
        help="Pin mode. 'input','output','input_pullup'")
    paa('-p', '--pin', default=False, type=int, help="The pin to do action x with.")
    paa('-P', '--pinfile', default=False,
        help="Pinfile to use (default: <package_install_dir>/pinfiles/*.yml")
    paa('-t', '--tty', default=False, help="Arduino tty (default: '/dev/ttyUSB0')")
    paa('-v', '--version', action='store_true', help='Show version info and exit')
    paa('-w', '--workdir', type=str, default=False,
        help="Alternate workdir path (default: ~/.pyduin)")

    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper()))

    try:
        if args.version:
            versions()
            sys.exit(0)

        basic_config = get_basic_config(args)

        if args.install_dependencies:
            check_dependencies()
            sys.exit(0)

        elif args.flash:
            config = get_pyduin_userconfig(args, basic_config)
            check_dependencies()
            update_firmware(args, config)
            sys.exit(0)

        config = get_pyduin_userconfig(args, basic_config)

        arduino = get_arduino(args, config)
    except ArduinoConfigError as error:
        print(colored(error, 'red'))
        sys.exit(1)

    actions = ('free', 'version', 'high', 'low', 'state', 'mode')

    if args.action and args.action == 'free':
        print(arduino.get_free_memory())
        sys.exit(0)
    if args.action and args.action == 'version':
        print(arduino.get_firmware_version())
        sys.exit(0)

    try:
        color = 'green'
        if args.action and args.action.lower() not in actions:
            raise ArduinoConfigError(f'Action {args.action} is not available')
        if args.action and args.action in ('high', 'low', 'state'):
            if not args.pin:
                raise ArduinoConfigError("The requested --action requires a --pin. Aborting")
            if not args.pin in list(arduino.Pins.keys()):
                message = "Defined pin (%s) is not available. Check pinfile."
                raise ArduinoConfigError(message % args.pin)

            pin = arduino.Pins[args.pin]
            action = getattr(pin, args.action)
            result = action().split('%')
            state = 'low' if int(result[-1]) == 0 else 'high'
            err = False if args.action == 'high' and state == 'high' or \
                  args.action == 'low' and state == 'low' else True
            if err:
                color = 'red'
            print(colored(state, color))
            sys.exit(0 if not err else 1)

        elif args.action and args.action == 'mode':
            pinmodes = ('output', 'input', 'input_pullup', 'pwm')
            if not args.mode:
                raise ArduinoConfigError("'--action mode' needs '--mode <MODE>' to be specified")
            if args.mode.lower() not in pinmodes:
                raise ArduinoConfigError("Mode '%s' is not available." % args.mode)

            Pin = arduino.Pins[int(args.pin)]
            if args.mode == 'pwm':
                pass
            else:
                result = Pin.set_mode(args.mode).split('%')
                err = False if args.mode == 'input' and int(result[-1]) == 0 or \
                      args.mode == 'output' and int(result[-1]) == 1 or \
                      args.mode == 'input_pullup' and int(result[-1]) == 2 else True

                state = 'ERROR' if err else 'OK'
                if err:
                    color = 'red'
                print(colored(state, color))

    except ArduinoConfigError as error:
        print(colored(error, 'red'))
        sys.exit(1)


if __name__ == '__main__':
    main()
