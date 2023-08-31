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
import logging
import os
from shutil import copyfile, which
import subprocess
import sys
import time

from jinja2 import Template
from termcolor import colored
import yaml


from pyduin.arduino import Arduino, ArduinoConfigError
from pyduin import _utils as utils
from pyduin import AttrDict, VERSION

logger = utils.logger

def get_basic_config(args):
    """
        Get configuration,  needed for all operations
    """
    configfile = args.configfile or '~/.pyduin.yml'
    confpath = os.path.expanduser(configfile)
    utils.ensure_user_config_file(confpath)
    with open(confpath, 'r', encoding='utf-8') as _configfile:
        cfg = yaml.load(_configfile, Loader=yaml.Loader)
    logger.debug("Using configuration file: %s", confpath)

    workdir = args.workdir or cfg.get('workdir', '~/.pyduin')
    logger.debug("Using workdir %s", workdir)
    cfg['workdir'] = os.path.expanduser(workdir)

    platformio_ini = args.platformio_ini or utils.platformio_ini
    logger.debug("Using platformio.ini in: %s", platformio_ini)
    cfg['platformio_ini'] = platformio_ini

    cfg['firmware'] = getattr(args, "firmware_file", False) or utils.firmware
    logger.debug("Using firmware from: %s", cfg['firmware'])

    board = args.board or utils.get_buddy_cfg(cfg, args.buddy, 'board')

    if board:
        cfg['pinfile'] = args.pinfile or utils.board_pinfile(board)
        logger.debug("Using pinfile from: %s", cfg['pinfile'])
        cfg['board'] = board
    else:
        logger.error("Cannot determine pinfile: %s", board)
        cfg['pinfile'] = False
    return cfg

def _get_arduino_config(args, config):
    """
    Determine tty, baudrate, model and pinfile for the currently used arduino.
    """
    arduino_config = {}
    for opt in ('tty', 'baudrate', 'board', 'pinfile'):
        _opt = getattr(args, opt)
        arduino_config[opt] = _opt
        if not _opt:
            try:
                _opt = config['buddies'][args.buddy][opt]
                arduino_config[opt] = _opt
            except KeyError:
                logger.debug("%s not set in buddylist", opt)

    # Ensure defaults.
    if not arduino_config.get('tty'):
        arduino_config['tty'] = '/dev/ttyUSB0'
    if not arduino_config.get('baudrate'):
        arduino_config['baudrate'] = 115200
    if not arduino_config.get('pinfile'):
        pinfile = os.path.join(utils.pinfiledir, f'{arduino_config["board"]}.yml')
        arduino_config['pinfile'] = pinfile
    logger.debug("device_config: %s", arduino_config)
    config['_arduino_'] = arduino_config
    model = config['_arduino_']['board']
    check_board_support(model, config)
    logger.debug("Using pinfile: %s", arduino_config['pinfile'])

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
        errmsg = f'Buddy "{buddy}" not described in configfile\'s "buddies" section. Aborting.'
        raise ArduinoConfigError(errmsg)
    return True


def check_board_support(board, config):
    """
    Determine if the configured model is supported. Do so by checking the
    platformio config file for env definitions.
    """
    parser = configparser.ConfigParser(dict_type=AttrDict)
    parser.read(config['platformio_ini'])
    sections = parser.sections()
    boards = [x.split(':')[-1] for x in sections if x.startswith('env:')]
    if not board in boards:
        logger.error("Board (%s) not in supported boards list %s",
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
    logger.debug(config)
    proxy_tty = config['_arduino_']['tty']
    if not proxy_tty.endswith('.tty'):
        proxy_tty = os.path.join(os.sep, 'tmp', f'{os.path.basename(proxy_tty)}.tty')
    logger.debug("Socat proxy expected at: %s", proxy_tty)
    return proxy_tty


def get_arduino(args, config):
    """
        Get an arduino object, open the serial connection if it is the first connection
        or wait=True (socat off/unavailable) and return it. To circumvent restarts of
        the arduino on reconnect, one has two options

        * Start a socat proxy
        * Do not hang_up_on close
    """
    if config['serial']['hang_up_on_close'] and config['serial']['use_socat']:
        errmsg = "Will not handle 'use_socat:yes' in conjunction with 'hang_up_on_close:no'" \
                 "Either set 'use_socat' to 'no' or 'hang_up_on_close' to 'yes'."
        raise ArduinoConfigError(errmsg)

    aconfig = config['_arduino_']
    if config['serial']['use_socat'] and getattr(args, 'fwcmd', '') != 'flash':
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
            subprocess.Popen(socat_cmd) # pylint: disable=consider-using-with
            print(colored(f'Started socat proxy on {proxy_tty}', 'cyan'))
            time.sleep(1)

        aconfig['tty'] = proxy_tty

    arduino = Arduino(tty=aconfig['tty'], baudrate=aconfig['baudrate'],
                  pinfile=aconfig['pinfile'], board=aconfig['board'],
                  wait=True)
    return arduino

def check_dependencies():
    """
        Check, if platformio and socat are available.
    """
    ret = True
    pio = which('pio')
    if pio:
        logger.info("Platformio found in %s.", pio)
    else:
        logger.warning("Platformio not installed. Flashing does not work.")
        ret = False
    socat = which('socat')
    if socat:
        logger.info("Socat found in %s", socat)
    else:
        logger.warning("Socat not found. Some features may not work.")
        ret = False
    return ret


def prepare_buildenv(config):
    """ Idempotent function that ensures the platformio build env exists and contains
    the required files in the wanted state. """
    workdir = config['workdir']
    srcdir = os.path.join(workdir, 'src')
    os.makedirs(workdir, exist_ok=True)
    os.makedirs(srcdir, exist_ok=True)
    platformio_ini = os.path.join(workdir, 'platformio.ini')
    if not os.path.isfile(platformio_ini):
        copyfile(config['platformio_ini'], platformio_ini)
    firmware = os.path.join(workdir, 'src', 'pyduin.cpp')
    if not os.path.isfile(firmware):
        copyfile(config['firmware'], firmware)


def update_firmware(config):  # pylint: disable=too-many-locals,too-many-statements
    """
        Update firmware on arduino (cmmi!)
    """
    proxy_tty = _get_proxy_tty_name(config)
    if os.path.exists(proxy_tty):
        print(colored("Socat proxy running. Stopping.", 'red'))
        cmd = f'ps aux | grep socat | grep -v grep | grep {proxy_tty} | awk '+"'{ print $2 }'"
        pid = subprocess.check_output(cmd, shell=True).strip()
        subprocess.check_output(['kill', f'{pid.decode()}'])
        time.sleep(1)
    os.chdir(config['workdir'])
    out = subprocess.check_output(['pio', 'run', '-e', config['_arduino_']['board'], '-t',
                                   'upload', '--upload-port', config['_arduino_']['tty']])
    print(out)


def versions(arduino, workdir):
    """ Print both firmware and package version """
    res = {"pyduin": VERSION,
           "device": arduino.get_firmware_version(),
           "available": utils.available_firmware_version(workdir) }
    return res

def template_firmware(arduino, config):
    """ Render firmware from template """
    _tpl = '{%s}'
    fwenv = {
        "num_analog_pins": arduino.pinfile.num_analog_pins,
        "num_digital_pins": arduino.pinfile.num_digital_pins,
        "num_pwm_pins": arduino.pinfile.num_pwm_pins,
        "pwm_pins": _tpl % ", ".join(arduino.pinfile.pwm_pins),
        "analog_pins": _tpl % ", ".join(arduino.pinfile.analog_pins),
        "digital_pins": _tpl % ", ".join(arduino.pinfile.digital_pins)
    }

    firmware = f'{os.path.expanduser(config["workdir"])}/src/pyduin.cpp'
    logger.debug("Using firmware template: %s", firmware)
    with open(firmware, 'r', encoding='utf-8') as template:
        tpl = Template(template.read())
        tpl = tpl.render(fwenv)
        #logger.debug(tpl)

    with open(firmware, 'w', encoding='utf8') as template:
        template.write(tpl)

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
    paa('-p', '--pinfile', default=False,
        help="Pinfile to use (default: <package_install_dir>/pinfiles/<board>.yml")
    paa('-s', '--baudrate', type=int, default=False)
    paa('-t', '--tty', default=False, help="Arduino tty (default: '/dev/ttyUSB0')")
    paa('-w', '--workdir', type=str, default=False,
        help="Alternate workdir path (default: ~/.pyduin)")

    subparsers = parser.add_subparsers(help="Available sub-commands", dest="cmd")
    subparsers.add_parser("dependencies", help="Check dependencies")
    subparsers.add_parser("versions", help="List versions", aliases=['v'])
    subparsers.add_parser("free", help="Get free memory from device", aliases='f')
    firmware_parser = subparsers.add_parser("firmware", help="Firmware options", aliases=['fw'])
    fwsubparsers = firmware_parser.add_subparsers(help='Available sub-commands', dest="fwcmd")
    firmwareversion_parser = fwsubparsers.add_parser('version', aliases=['v'],
                                                     help="List firmware versions")
    fwsubparsers.add_parser('flash', aliases=['f'], help="Flash firmware to device")
    fwsubparsers.add_parser("lint", help="Lint Firmware in <workdir>", aliases=['l'])
    fwv_subparsers = firmwareversion_parser.add_subparsers(help="Available sub-commands",
                                                           dest='fwscmd')
    fwv_subparsers.add_parser('device', help="Device Firmware", aliases=['d'])
    fwv_subparsers.add_parser("available", help="Available Firmware", aliases=['a'])

    pin_parser = subparsers.add_parser("pin")
    pin_parser.add_argument('pin', default=False, type=int, help="The pin to do action x with.",
                            metavar="<pin_id>")
    pinsubparsers = pin_parser.add_subparsers(help="Available sub-commands", dest="pincmd")
    pinmode_parser = pinsubparsers.add_parser("mode", help="Set pin modes")
    pinmode_parser.add_argument('mode', default=False,
                                choices=["input", "output", "input_pullup","pwm"],
                                help="Pin mode. 'input','output','input_pullup', 'pwm'")
    pinsubparsers.add_parser("high", aliases=['h'])
    pinsubparsers.add_parser("low", aliases=['l'])
    pinsubparsers.add_parser("state")
    digitalpin_parser_pwm = pinsubparsers.add_parser("pwm")
    digitalpin_parser_pwm.add_argument('value', type=int, help='0-255')

    args = parser.parse_args()
    try:
        basic_config = get_basic_config(args)
        config = get_pyduin_userconfig(args, basic_config)
    except ArduinoConfigError as error:
        print(colored(error, 'red'))
        sys.exit(1)

    log_level = args.log_level or config.get('log_level', 'info')
    logger.setLevel(level=getattr(logging, log_level.upper()))
    #logger.basicConfig(level=getattr(logger, log_level.upper()))
    # re-read configs to be able to see the log messages.
    basic_config = get_basic_config(args)
    config = get_pyduin_userconfig(args, basic_config)

    #if getattr(args, 'fwcmd', False) not in ('flash', 'f'):
    arduino = get_arduino(args, config)
    prepare_buildenv(config)
    if args.cmd in ('versions', 'v'):
        print(versions(arduino, config['workdir']))
        sys.exit(0)
    elif args.cmd == "dependencies":
        check_dependencies()
        sys.exit(0)
    elif args.cmd in ('free', 'f'):
        print(arduino.get_free_memory())
        sys.exit(0)
    elif args.cmd in ('firmware', 'fw'):
        if args.fwcmd in ('version', 'v'):
            _ver = versions(arduino, config['workdir'])
            print(_ver)
            if args.fwscmd in ('device', 'd'):
                print(_ver['device'])
            elif args.fwscmd in ('a', 'available'):
                print(_ver['available'])
            else:
                del _ver['pyduin']
                print(_ver)
        elif args.fwcmd in ('lint', 'l'):
            template_firmware(arduino, config)
            lint_firmware()
        elif args.fwcmd in ('flash', 'f'):
            template_firmware(arduino, config)
            lint_firmware()
            update_firmware(config)
        sys.exit(0)
    elif args.cmd == 'pin':
        if args.pincmd in ('high', 'low', 'h', 'l'):
            act = args.pincmd
            act = 'high' if act == 'h' else act
            act = 'low' if act == 'l' else act
            pin = arduino.Pins[args.pin]
            res = getattr(pin, act)()
            logger.debug(res)
        elif args.pincmd == 'mode' and args.mode in ('input_pullup', 'input', 'output', 'pwm'):
            pin = arduino.Pins[args.pin]
            res = pin.set_mode(args.mode)
            logger.debug(res)
        sys.exit(0)
    else:
        print("Nothing to do")
    sys.exit(1)

if __name__ == '__main__':
    main()
