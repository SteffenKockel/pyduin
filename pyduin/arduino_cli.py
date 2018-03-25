#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  arduino_cli.py
#
"""
    Arduino CLI functions and templates
"""
import argparse
import contextlib
from distutils.spawn import find_executable  # pylint: disable=no-name-in-module,import-error
import lzma
import os
import re
from shutil import copyfile, move
import subprocess
import sys
import tarfile
import time
import zipfile

import requests
import yaml
from termcolor import colored

from pyduin.arduino import Arduino, ArduinoConfigError

SUPPORTED_MODELS = ('nano', 'mega', 'uno')
ARDUINO_RELEASES = ('0013', '0014', '0015', '0016', '0017', '0018', '0019', '0020', '0021',
                    '0022', '0023', '1.0', '1.0.1', '1.0.2', '1.0.3', '1.0.4', '1.0.5',
                    '1.6.0', '1.6.1', '1.6.2', '1.6.3', '1.6.4', '1.6.5-r5', '1.6.6', '1.6.7',
                    '1.6.8', '1.6.9', '1.6.10', '1.6.11', '1.6.12', '1.6.13', '1.8.0',
                    '1.8.1', '1.8.2', '1.8.3', '1.8.4')

# Basic user config template

CONFIG_TEMPLATE = """
workdir: ~/.pyduin
#arduino_makefile: /usr/share/arduino/Arduino.mk
arduino_makefile: ~/.pyduin/makefiles/Arduino-Makefile-%(version)s/Arduino.mk
#arduino_makefile_version: 1.6.0
arduino_makefile_version: 1.3.1
arduino_makefile_src: https://github.com/sudar/Arduino-Makefile/archive/%(version)s.tar.gz
arduino_architecture: linux64 # linux[32|64|arm]
#arduino_src: https://downloads.arduino.cc/arduino-%(version)s-%(architecture)s.tar.xz
arduino_src: https://github.com/arduino/Arduino/releases/tag/%(version)s
pinfile_src: https://raw.githubusercontent.com/SteffenKockel/pyduin/master/pinfiles/%(model)s.yml
arduino_version: 1.6.5-r5

libraries:
  DHT:
    source: https://github.com/adafruit/DHT-sensor-library/archive/1.2.3.tar.gz
  OneWire:
    source: https://github.com/PaulStoffregen/OneWire/archive/v2.3.3.tar.gz
  DallasTemperature:
    source: https://github.com/milesburton/Arduino-Temperature-Control-Library/archive/3.8.0.tar.gz
  MemoryFree:
    source: https://github.com/mpflaga/Arduino-MemoryFree/archive/master.zip

serial:
  use_socat: yes

buddies:
  guinea-pig:
    model: nano
    flavour: atmega328
  guinea-pig2:
    model: nano
    flavour: atmega168
"""

# Makefile template

MAKEFILE_TEMPLATE = """
IDE_DIR = %(workdir)s/arduino-%(arduino_version)s
ARDUINO_SKETCHBOOK = %(workdir)s/examples
USER_LIB_PATH = %(workdir)s/user-libraries
ARDUINO_HEADER = %(ide_dir)s/hardware/arduino/avr/cores/arduino/Arduino.h
ARDUINO_PORT = %(tty)s
ARDUINO_DIR  = %(ide_dir)s
BOARDS_TXT = %(ide_dir)s/hardware/arduino/avr/boards.txt
ARDUINO_CORE_PATH = %(ide_dir)s/hardware/arduino/avr/cores/arduino
ALTERNATE_CORE_PATH = %(ide_dir)s/hardware/arduino/avr/cores/arduino
ARDUINO_VAR_PATH = %(ide_dir)s/hardware/arduino/avr/variants
BOOTLOADER_PARENT = %(ide_dir)s/hardware/arduino/avr/bootloaders
#ARDUINO_LIBS = Ethernet Ethernet/utility SPI
BOARD_TAG  = %(model)s
#BOARD_SUB = %(board_sub)s
MCU = %(mcu)s
AVRDUDE = %(ide_dir)s/hardware/tools/avr/bin/avrdude
AVRDUDE_CONF = %(ide_dir)s/hardware/tools/avr/etc/avrdude.conf
AVRDUDE_ARD_BAUDRATE = %(baudrate)s
AVRDUDE_ISP_BAUDRATE = %(baudrate)s
include %(arduino_makefile)s
"""

SOCAT_CMD_DEBUG = \
    ('/usr/bin/socat', '-x', '-s', '-ddd' '-ddd',
     '%(source_tty)s,b%(baudrate)s,cs8,parenb=0,cstopb=0,clocal=0,raw,echo=0,setlk,flock-ex-nb,nonblock=1',
     'PTY,link=%(proxy_tty)s,b%(baudrate)s,cs8,parenb=0,cstopb=0,clocal=0,raw,echo=0,setlk,flock-ex-nb,nonblock=1')

SOCAT_CMD = \
    ('/usr/bin/socat', '-s', '-d',
     '%(source_tty)s,b%(baudrate)s,cs8,parenb=0,cstopb=0,clocal=0,raw,echo=0,setlk,flock-ex-nb,nonblock=1',
     'PTY,link=%(proxy_tty)s,b%(baudrate)s,cs8,parenb=0,cstopb=0,clocal=0,raw,echo=0,setlk,flock-ex-nb,nonblock=1')


def get_file(source, target):
    """
    Download/copy a file from source to targer
    """
    print colored("Getting %s from %s" % (target, source), 'blue')
    source = os.path.expanduser(source) if source.startswith('~') else source
    if source.startswith('http'):
        res = requests.get(source)
        if res.status_code == 200:
            with open(target, 'wb') as _target:
                for chunk in res:
                    _target.write(chunk)
            return
        errmsg = "Cannot download %s from %s" % (os.path.basename(source), source)
        raise ArduinoConfigError(errmsg)
    else:
        if not os.path.isfile(source):
            errmsg = "Source file %s does not exist"
            raise ArduinoConfigError(errmsg)
        elif not os.path.isdir(os.path.dirname(target)):
            errmsg = "Target dir %s does not exist"
            raise ArduinoConfigError(errmsg)
        copyfile(source, target)


def extract_file(src_file, targetdir, rebase=False):
    """
        Extract arduino source tarball. It's actually a .xz file
    """
    filetype = os.path.basename(src_file).split('.')[-1]
    if filetype == 'xz':
        # proudly copied from:
        # https://stackoverflow.com/questions/17217073/how-to-decompress-a-xz-file-which-has-multiple-folders-files-inside-in-a-singl # pylint: disable=line-too-long
        with contextlib.closing(lzma.LZMAFile(src_file)) as xz_file:
            with tarfile.open(fileobj=xz_file) as source_file:
                path = source_file.members[0].path
                source_file.extractall(targetdir)
    elif filetype == 'zip':
        with zipfile.ZipFile(src_file, "r") as zip_file:
            path = zip_file.namelist()[0].rstrip('/')
            zip_file.extractall(targetdir)
    elif filetype == 'gz':
        with tarfile.open(src_file, "r") as gz_file:
            path = gz_file.members[0].path
            gz_file.extractall(path=targetdir)

    if rebase:
        move('/'.join((targetdir, path)), rebase)


def get_user_config_path(args):
    """
    Determine the user config path
    """
    configfile = args.configfile if args.configfile else '~/.pyduin.yml'
    return os.path.expanduser(configfile)


def check_user_config_file(location):
    """
    Check, if basic config file ~/.pyduin.yml exists
    """
    if not os.path.isfile(location):
        print colored("Writing default config file to %s " % location, 'blue')
        with open(location, 'w') as _configfile:
            _configfile.write(CONFIG_TEMPLATE)


def get_user_config(location):
    """
    Load the user config file and parse yaml
    """
    with open(location, 'r') as _configfile:
        basic_config = yaml.load(_configfile)
    return basic_config


def get_workdir(args, config):
    """
    Calculate wordkir path
    """
    workdir = args.workdir if args.workdir else config.get('workdir', '~/.pyduin')
    return os.path.expanduser(workdir)


def ensure_dir(identifier, directory):
    """ Create directory if it does not exist. Identifier is used for message. """
    if not os.path.isdir(directory):
        print colored("'%s' does not exist '%s'. Creating" % (identifier, directory), 'blue')
        return os.mkdir(directory)
    return True


def get_pinfile_dir(workdir):
    """ Calculate pinfile directory """
    pinfiledir = '/'.join((workdir, 'pinfiles'))
    return pinfiledir


def get_ide_dir(workdir):
    """ Calculate dir where all IDE's will be located """
    ide_dir = '/'.join((workdir, 'ide'))
    return ide_dir


def get_full_ide_dir(ide_dir, arduino_version):
    """ Calculate dir to IDE use for this run """
    return '/'.join((ide_dir, 'arduino-%s' % arduino_version))


def get_arduino_version(args, basic_config):
    """ Determine arduino version to use """
    version = args.arduino_version if args.arduino_version else \
              basic_config['arduino_version']
    if not version in ARDUINO_RELEASES:
        errmsg = "The given arduino IDE version does not exist: %s. Available versions: \n%s" % \
                 (version, '\n'.join(ARDUINO_RELEASES))
        raise ArduinoConfigError(errmsg)
    return version


def get_basic_config(args):
    """
        Get config needed for all operations
    """
    confpath = get_user_config_path(args)
    check_user_config_file(confpath)
    basic_config = get_user_config(confpath)

    # Get workdir
    basic_config['workdir'] = get_workdir(args, basic_config)
    ensure_dir('workdir', basic_config['workdir'])

    # Get pinfile_dir
    basic_config['pinfiledir'] = get_pinfile_dir(basic_config['workdir'])
    ensure_dir('pinfiledir', basic_config['pinfiledir'])

    # Calculate IDE dir, version, full_ide_dir
    basic_config['ide_dir'] = get_ide_dir(basic_config['workdir'])
    ensure_dir('ide_dir', basic_config['ide_dir'])
    basic_config['arduino_version'] = get_arduino_version(args, basic_config)
    basic_config['full_ide_dir'] = get_full_ide_dir(basic_config['ide_dir'],
                                                    basic_config['arduino_version'])
    return basic_config


def verify_buddy(buddy, config):
    """
    Determine if the given buddy is defined in config file and the configfile has
    a 'buddies' section at all.
    """
    if not config.get('buddies'):
        raise ArduinoConfigError("Configfile is missing 'buddies' section")
    if not config['buddies'].get(buddy):
        errmsg = "Buddy '%s' not described in configfile's 'buddies' section" % buddy
        raise ArduinoConfigError(errmsg)
    return True


def check_model_support(model):
    """ Determine if the configured model is supported """
    if not model or model.lower() not in SUPPORTED_MODELS:
        raise ArduinoConfigError("Model is undefined or unknown: %s" % model)
    return True


def _get_arduino_config(args, config):
    """
    Determine tty, baudrate, model and pinfile for the currently used arduino.
    """
    arduino_config = {}
    for opt in ('tty', 'baudrate', 'model', 'pinfile'):
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
        pinfile = '/'.join((config['pinfiledir'], '%s.yml' % arduino_config['model']))
        arduino_config['pinfile'] = pinfile

    # Ensure buddies section exists, even if empty
    config['buddies'] = config.get('buddies', {})
    config['_arduino_'] = arduino_config
    model = config['_arduino_']['model']
    check_model_support(model)

    # If no pinfile can be found, attempt to download one from github.
    if not os.path.isfile(arduino_config['pinfile']):
        try:
            get_file(config['pinfile_src'] % {'model': model}, pinfile)
        except ArduinoConfigError, error:
            errmsg = "Cannot find/download pinfile for model '%s'. Error: %s" % (model, error)
            raise ArduinoConfigError(errmsg)
    return config


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
    proxy_tty = os.path.sep.join((config['workdir'], '%s.tty' % tty))
    return proxy_tty


def get_arduino(args, config):
    """
        Get an arduino object, open the serial connection if it is the first connection
        or cli_mode=True (socat off/unavailable) and return it. To circumvent restarts of
        the arduino on reconnect, one has two options

        * Start a socat proxy
        * Do not hang_up_on_close
    """
    if not config['serial']['hang_up_on_close'] and config['serial']['use_socat']:
        errmsg = "Will not handle 'use_socat:yes' in conjunction with 'hang_up_on_close:no'" \
                 "Either set 'use_socat' to 'no' or 'hang_up_on_close' to 'yes'."
        raise ArduinoConfigError(errmsg)

    aconfig = config['_arduino_']
    if config['serial']['use_socat'] and not args.flash:
        socat = find_executable('socat')
        if not socat:
            errmsg = "Cannot find 'socat' in PATH, but use is configured in ~/.pyduin.yml"
            raise ArduinoConfigError(errmsg)
        proxy_tty = _get_proxy_tty_name(config)

        is_proxy_start = False if os.path.exists(proxy_tty) else True
        # start the socat proxy
        if not os.path.exists(proxy_tty):
            # Enforce hulpc:on
            subprocess.check_output(['stty', '-F', aconfig['tty'], 'hupcl'])
            time.sleep(1)
            socat_opts = {'baudrate': aconfig['baudrate'],
                          'source_tty': aconfig['tty'],
                          'proxy_tty': proxy_tty
                         }
            socat_cmd = tuple([x % socat_opts for x in SOCAT_CMD])
            subprocess.Popen(socat_cmd)
            print colored('Started socat proxy on %s' % proxy_tty, 'cyan')
            time.sleep(1)

        # Connect via socat proxy
        if os.path.exists(proxy_tty):
            arduino = Arduino(tty=proxy_tty, baudrate=aconfig['baudrate'],
                              pinfile=aconfig['pinfile'], model=aconfig['model'])
            if not is_proxy_start:
                setattr(arduino, 'cli_mode', True)
                arduino.open_serial_connection()
            elif is_proxy_start:
                arduino.open_serial_connection()
                setattr(arduino, 'cli_mode', True)

    elif not config['serial']['hang_up_on_close']:
        # Switch hupcl (hang up on close) off to preserve the connection
        subprocess.check_output(['stty', '-F', aconfig['tty'], '-hupcl'])
        # Check, if (presumably) this connection needs initialisation or not
    else:
        arduino = Arduino(tty=aconfig['tty'], baudrate=aconfig['baudrate'],
                          pinfile=aconfig['pinfile'], model=aconfig['model'])
        setattr(arduino, 'cli_mode', True)
        arduino.open_serial_connection()
    return arduino


def check_ide_and_libs(config):  # pylint: disable=too-many-locals,too-many-branches
    """
        Update firmware on arduino (cmmi!)
    """
    # Check arduino IDE presence. If the desired version does
    # not exist locally, it will get downloaded and ectracted
    aversion = config['arduino_version']
    ide_dir = config['ide_dir']
    full_ide_dir = config['full_ide_dir']
    # print colored("Checking for arduino IDE %s in %s" % (aversion, full_ide_dir), 'yellow')
    if not os.path.isdir(full_ide_dir):
        msg = "Arduino ide version %s not present in %s. Downloading." % (aversion, full_ide_dir)
        print colored(msg, 'yellow')

    target = '/'.join((config['ide_dir'], '%s.tar.xz' % aversion))
    if not os.path.isfile(target) and not os.path.isdir(full_ide_dir):
        url = config['arduino_src'] % {'architecture': config['arduino_architecture'],
                                       'version': config['arduino_version']}
        print colored("Attempting to download arduin IDE from %s" % url, 'green')
        get_file(url, target)

    if os.path.isfile(target) and not os.path.isdir(full_ide_dir):
        print colored("Extracting archive %s to %s" % (target, full_ide_dir), 'yellow')
        extract_file(target, ide_dir)
    else:
        print colored("Found arduino IDE in %s" % full_ide_dir, 'green')

    # Get libs as defined in .pyduin
    libdir = '/'.join((config['full_ide_dir'], 'user-libraries'))

    if not os.path.isdir(libdir):
        os.mkdir(libdir)

    for library, libconf in config['libraries'].iteritems():
        _libdir = '/'.join((libdir, library))
        # print colored("Checking for library %s" % _libdir, 'yellow')
        if not os.path.isdir(_libdir):
            source = libconf.get('source', False)
            if not source:
                errmsg = "No source defined for lib %s and source not found in %s" %\
                        (library, libdir)
                raise ArduinoConfigError(errmsg)

            target = '/'.join((libdir, os.path.basename(source)))
            if not os.path.isfile(target):
                get_file(source, target)
            # finally, extract the file
            extract_file(target, libdir, rebase='/'.join((libdir, library)))
        else:
            print colored("Found library %s" % _libdir, 'green')

    # Check, if Arduino.mk exists in the correct version. If not
    # download and extract it.

    mk_dir = '/'.join((config['workdir'], 'makefiles'))
    mk_version = config['arduino_makefile_version']
    mk_dir_full = '/'.join((mk_dir, 'Arduino-Makefile-%s' % mk_version))
    # print colored("Checking for %s" % mk_dir_full, 'yellow')
    ensure_dir('arduino_mk', mk_dir)

    if not os.path.isdir(mk_dir_full):
        mk_tar = '/'.join((mk_dir, 'Arduino-Makefile-%s.tar.gz' % mk_version))
        url = config['arduino_makefile_src'] % {'version': mk_version}
        if not os.path.isfile(mk_tar):
            get_file(url, mk_tar)
        extract_file(mk_tar, mk_dir)
    else:
        print colored("Found %s" % mk_dir_full, 'green')


def update_firmware(args, config):  # pylint: disable=too-many-locals,too-many-statements
    """
        Update firmware on arduino (cmmi!)
    """
    tmpdir = '/tmp/.pyduin'

    # Get the boards.txt. This file holds the mcu and board definition.
    flavour = args.flavour if args.flavour else config['buddies'][args.buddy]['flavour'] if \
        config.get('buddies') and args.buddy in config['buddies'].keys() and \
        config['buddies'][args.buddy].get('flavour') and args.buddy else False
    model = config['_arduino_']['model']
    # print config['_arduino_']
    full_ide_dir = config['full_ide_dir']
    mculib = "%s/hardware/arduino/avr/boards.txt" % full_ide_dir
    with open(mculib) as _mculib:
        mculib = _mculib.readlines()

    mcu = [x for x in mculib if re.search(r"^%s\..*mcu=" % model, x)] if not flavour else \
          [x for x in mculib if re.search(r"^%s\..*.%s.*mcu=" % (model, flavour), x)]
    if not mcu or len(mcu) != 1:
        errmsg = "Cannot find mcu correspondig to flavour %s and model %s in boards.txt" % (flavour, model)
        raise ArduinoConfigError(errmsg)
    mcu = mcu[0].split('=')[1].strip()

    isp_baudrate = [x for x in mculib if re.search(r"^%s\..*upload.speed=" % model, x)] if not flavour else \
                   [x for x in mculib if re.search(r"^%s\..*.%s.*upload.speed=" % (model, flavour), x)]
    if not isp_baudrate or len(isp_baudrate) != 1:
        errmsg = "Cannot determine upload baudrate for flavour %s and model %s from boards.txt" % (flavour, model)
        raise ArduinoConfigError(errmsg)
    baudrate = isp_baudrate[0].split('=')[1].strip()

    # Generat a Makefile from template above.
    makefilevars = {'tty': config['_arduino_']['tty'],
                    'workdir': full_ide_dir,
                    'arduino_version': config['arduino_version'],
                    'ide_dir': full_ide_dir,
                    'arduino_makefile': config['arduino_makefile'] % {'version': config['arduino_makefile_version']},
                    'mcu': mcu,
                    'board_sub': flavour,
                    'model': model,
                    'baudrate': baudrate
                   }
    makefile = MAKEFILE_TEMPLATE % makefilevars
    # Create tmp dir if needed and place Makefile in tmp dir
    ensure_dir('tmpdir', tmpdir)

    makefilepath = '/'.join((tmpdir, 'Makefile'))
    print colored("Writing makefile to %s" % makefilepath, 'blue')
    if os.path.exists(makefilepath):
        os.remove(makefilepath)
    with open(makefilepath, 'w') as mkfile:
        mkfile.write(makefile)

    # Determine, which .ino file to use
    # @FIXME: ino file location (download?)
    ino = args.ino if args.ino else config.get('ino', '/usr/share/pyduin/ino/pyduin.ino')
    ino = os.path.expanduser(ino) if ino.startswith('~') else \
        '/'.join((os.getcwd(), ino)) if not ino.startswith('/') else ino

    if not os.path.isfile(ino) or not ino:
        errmsg = "Cannot find .ino in %s. Giving up." % ino
        raise ArduinoConfigError(errmsg)

    # Get the actual .ino file aka 'sketch' to compile and upload
    inotmp = '/'.join((tmpdir, 'pyduin.ino'))
    if os.path.exists(inotmp):
        os.remove(inotmp)
    get_file(ino, inotmp)

    if not os.path.exists(config['_arduino_']['tty']):
        errmsg = "%s not found. Connected?" % config['_arduino_']['tty']
        raise ArduinoConfigError(errmsg)

    proxy_tty = _get_proxy_tty_name(config)
    if os.path.exists(proxy_tty):
        print colored("Socat proxy running. Stopping.", 'red')
        cmd = "ps aux | grep socat | grep -v grep | grep %s | awk '{ print $2 }'" % proxy_tty
        pid = subprocess.check_output(cmd, shell=True).strip()
        subprocess.check_output(['kill', '%s' % pid])
        time.sleep(1)

    olddir = os.getcwd()
    os.chdir(tmpdir)
    print colored("Running make clean", 'green')
    subprocess.check_output(['make', 'clean'])
    print colored("Running make", 'green')
    subprocess.check_output(['make', '-j4'])
    print colored("Running make upload", 'green')
    subprocess.check_output(['make', 'upload'])
    print colored("All Done!", "green")
    os.chdir(olddir)


def versions():
    """
        Print both firmware and package version
    """
    pass


def main():  # pylint: disable=too-many-statements,too-many-branches,too-many-locals
    """
        Evaluate user arguments and determine task
    """
    parser = argparse.ArgumentParser(description='Manage arduino from command line.')
    paa = parser.add_argument
    paa('-a', '--action', default=False, type=str, help="Action, e.g 'high', 'low'")
    paa('-A', '--arduino-version', default='1.6.5-r5', help="IDE version to download and use")
    paa('-b', '--baudrate', default=False, help="Connection speed (default: 115200)")
    paa('-B', '--buddy', type=str, default=False,
        help="Use identifier from configfile for detailed configuration")
    paa('-c', '--configfile', type=file, default=False,
        help="Alternate configfile (default: ~/.pyduin.yml)")
    paa('-f', '--flash', action='store_true', default=False,
        help="Flash firmware to the arduino (cmmi)")
    paa('-D', '--install-dependencies', action='store_true',
        help='Download and install dependencies according to ~/.pyduin.yml')
    paa('-F', '--flavour', default=False, type=str,
        help="Model Flavour. E.g atmega328, atmega168")
    paa('-i', '--ino', default=False,
        help='.ino file to build and uplad.')
    paa('-m', '--model', default=False, help="Arduino model (e.g.: Nano, Uno)")
    paa('-M', '--mode', default=False, choices=["input", "output", "input_pullup"],
        help="Pin mode. 'input','output','input_pullup'")
    paa('-p', '--pin', default=False, type=int, help="The pin to do action x with.")
    paa('-P', '--pinfile', default=False,
        help="Pinfile to use (default: ~/.pyduin/pinfiles/<model>.yml")
    paa('-t', '--tty', default=False, help="Arduino tty (default: '/dev/ttyUSB0')")
    paa('-v', '--version', action='store_true', help='Show version info and exit')
    paa('-w', '--workdir', type=str, default=False,
        help="Alternate workdir path (default: ~/.pyduin)")

    args = parser.parse_args()

    # try to open ~/.pyduin

    try:
        if args.version:
            versions()

        if args.install_dependencies:
            basic_config = get_basic_config(args)
            check_ide_and_libs(basic_config)
            sys.exit(0)

        elif args.flash:
            basic_config = get_basic_config(args)
            config = get_pyduin_userconfig(args, basic_config)
            check_ide_and_libs(config)
            update_firmware(args, config)
            sys.exit(0)

        basic_config = get_basic_config(args)
        config = get_pyduin_userconfig(args, basic_config)

        arduino = get_arduino(args, config)
    except ArduinoConfigError, error:
        print colored(error, 'red')
        sys.exit(1)

    actions = ('free', 'version', 'high', 'low', 'state', 'mode')

    if args.action and args.action == 'free':
        print arduino.get_free_memory()
        sys.exit(0)
    if args.action and args.action == 'version':
        print arduino.get_firmware_version()
        sys.exit(0)

    try:
        color = 'green'
        if args.action and args.action.lower() not in actions:
            raise ArduinoConfigError("Action '%s' is not available" % args.action)
        if args.action and args.action in ('high', 'low', 'state'):
            if not args.pin:
                raise ArduinoConfigError("The requested --action requires a --pin. Aborting")
            if not args.pin in arduino.Pins.keys():
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
            print colored(state, color)
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
                print colored(state, color)

    except ArduinoConfigError, error:
        print colored(error, 'red')
        sys.exit(1)


if __name__ == '__main__':
    main()
