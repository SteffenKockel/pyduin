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
import lzma
import os
import requests
from shutil import copyfile, move
import subprocess
import tarfile
from termcolor import colored
import yaml
import sys
import zipfile

import pyduin.arduino

# Basic user config template

CONFIG_TEMPLATE = """
workdir: ~/.pyduin
arduino_makefile: ~/.pyduin/makefiles/Arduino-Makefile-%(version)s/Arduino.mk
arduino_makefile_version: 1.3.1
arduino_makefile_src: https://github.com/sudar/Arduino-Makefile/archive/%(version)s.tar.gz
arduino_architecture: linux64 # linux[32|64|arm]
arduino_src: https://downloads.arduino.cc/arduino-%(version)s-%(architecture)s.tar.xz
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

buddies:
  guinny-pig:
    model: nano
"""

# Makefile template

MAKEFILE_TEMPLATE = """
IDE_DIR = %(workdir)s/arduino-%(arduino_version)s
ARDUINO_SKETCHBOOK = %(workdir)s/arduino-sketches
USER_LIB_PATH = %(workdir)s/arduino-libraries
ARDUINO_HEADER = %(ide_dir)s/hardware/arduino/avr/cores/arduino/Arduino.h
ARDUINO_PORT = %(tty)s
ARDUINO_DIR  = %(ide_dir)s
BOARDS_TXT = %(ide_dir)s/hardware/arduino/avr/boards.txt
ARDUINO_CORE_PATH = %(ide_dir)s/hardware/arduino/avr/cores/arduino
ALTERNATE_CORE_PATH = %(ide_dir)s/hardware/arduino/avr/cores/arduino
ARDUINO_VAR_PATH = %(ide_dir)s/hardware/arduino/avr/variants
BOOTLOADER_PARENT = %(ide_dir)s/hardware/arduino/avr/bootloaders
#ARDUINO_LIBS = Ethernet Ethernet/utility SPI
BOARD_TAG  = nano
BOARD_SUB = atmega328
MCU = atmega328p
AVRDUDE = %(ide_dir)s/hardware/tools/avr/bin/avrdude
AVRDUDE_CONF = %(ide_dir)s/hardware/tools/avr/etc/avrdude.conf
AVRDUDE_ARD_BAUDRATE = 57600
AVRDUDE_ISP_BAUDRATE = 57600
include %(arduino_makefile)s
"""


def get_file(source, target):
    print "Getting %s from %s" % (source, target)
    source = os.expanduser(source) if source.startswith('~') else source
    if source.startswith('http'):
        res = requests.get(source)
        if res.status_code == 200:
            with open(target, 'wb') as target:
                for chunk in res:
                    target.write(chunk)
            return
        errmsg = "Cannot download %s from %s" % (os.path.basename(source), source)
        raise pyduin.arduino.ArduinoConfigError(errmsg)
    else:
        if not os.path.isfile(source):
            errmsg = "Source file %s does not exist"
            raise pyduin.arduino.ArduinoConfigError(errmsg)
        elif not os.path.isdir(os.path.dirname(target)):
            errmsg = "Target dir %s does not exist"
            raise pyduin.arduino.ArduinoConfigError(errmsg)
        copyfile(source, target)

def extract_file(src_file, targetdir, rebase=False):
    """
        Extract arduino source tarball. It's actually a .xz file
    """
    filetype = os.path.basename(src_file).split('.')[-1]
    if filetype == 'xz':
        # proudly copied from: https://stackoverflow.com/questions/17217073/how-to-decompress-a-xz-file-which-has-multiple-folders-files-inside-in-a-singl # pylint: disable=line-too-long
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
        move(path, rebase)


def get_arduino(args):
    """
        Get an arduino object, open the serial connection and return it
    """
    arduino = pyduin.arduino.Arduino(tty=args['tty'], baudrate=args['baudrate'],
                                 pinfile=args['pinfile'], model=args['model'])
    setattr(arduino, 'cli_mode', True)
    arduino.open_serial_connection()
    return arduino


def get_basic_config(args):
    """
        Get config needed for all operations
    """
    # Get basic config file
    configfile = args.configfile if args.configfile else '~/.pyduin.yml'
    if configfile.startswith('~'):
        configfile = os.path.expanduser(configfile)

    if not os.path.isfile(configfile):
        print("Writing default config file to %s " % configfile)
        with open(configfile, 'w') as _configfile:
            _configfile.write(CONFIG_TEMPLATE)

    with open(configfile, 'r') as _configfile:
        basic_config = yaml.load(_configfile)

    # Get workdir
    workdir = args.workdir if args.workdir else basic_config.get('workdir', '~/.pyduin')
    if workdir.startswith('~'):
        workdir = os.path.expanduser(workdir)
    basic_config['workdir'] = workdir

    if not os.path.isdir(workdir):
        print "Wordir does not exist '%s'. Creating" % workdir
        os.mkdir(workdir)

    # Get pinfile
    pinfiledir = '/'.join((workdir, 'pinfiles'))
    if not os.path.isdir(pinfiledir):
        print "Pinfile dir does not exist '%s'. Creating" % pinfiledir
        os.mkdir(pinfiledir)
    basic_config['pinfiledir'] = pinfiledir

    # Calculate IDE dir
    ide_dir = '/'.join((workdir, 'ide'))
    if not os.path.isdir(ide_dir):
        print "IDE dir does not exist: '%s'. Creating" % ide_dir
        os.mkdir(ide_dir)
    basic_config['ide_dir'] = ide_dir
    basic_config['full_ide_dir'] = '/'.join((ide_dir, basic_config['arduino_version']))

    return basic_config

def get_pyduin_userconfig(args, basic_config):
    """
        Get advanced config for arduino interaction
    """
    config = basic_config
    if args.buddy:
        if not config.get('buddies'):
            raise pyduin.arduino.ArduinoConfigError("Configfile is missing 'buddies' section")
        if not config['buddies'].get(args.buddy):
            errmsg = "Buddy '%s' not described in configfile's 'buddies' section" % args.buddy
            raise pyduin.arduino.ArduinoConfigError(errmsg)

    arduino_config = {}
    for opt in ('tty', 'baudrate', 'model', 'pinfile'):
        _opt = getattr(args, opt) if getattr(args, opt) else \
                config['buddies'][args.buddy][opt] if (args.buddy and \
                config.get('buddies') and config['buddies'].get(args.buddy) and \
                config['buddies'][args.buddy].get(opt, False)) else False
        arduino_config[opt] = _opt

    if not config.get('buddies'):
        config['buddies'] = {}
    config['_arduino_'] = arduino_config

    model = config['_arduino_']['model']
    if not model or model.lower() not in ('nano', 'mega', 'uno'):
        raise pyduin.arduino.ArduinoConfigError("Model is undefined or unknown: %s" % model)

    pinfile = os.path.expanduser(args.pinfile) if (args.pinfile and args.pinfile.startswith('~')) \
                else args.pinfile if args.pinfile \
                else config['buddies'][args.buddy].get('pinfile') if config['buddies'].get(args.buddy) \
                else False
    # no overrides for the pinfile
    default_pinfile = False if pinfile else True

    if not pinfile:
        pinfile = '/'.join((config['pinfiledir'], '%s.yml' % model))
    config['_arduino_']['pinfile'] = pinfile

    # If no pinfile present, attempt to download one from github.
    if not os.path.isfile(pinfile) and default_pinfile:
        print "No pinfile found, trying to download one..."
        get_file(config['pinfile_src'] % {'model': model}, pinfile)
        # errmsg = "Cannot find or download pinfile for model '%s'. Supported?" % model
        # raise pyduin.arduino.ArduinoConfigError(errmsg)

    return config


def update_firmware(args, config): # pylint: disable=too-many-locals
    """
        Update firmware on arduino (cmmi!)
    """
    aversion = config['arduino_version']
    full_ide_dir = config['full_ide_dir']
    print "Checking for arduino IDE %s in %s" % (aversion, full_ide_dir)
    if not os.path.isdir(full_ide_dir):
        print "Arduino ide version %s not present in %s. Downloading." %\
            (aversion, full_ide_dir)

    target = '/'.join((config['ide_dir'], '%s.tar.xz' % aversion))
    if not os.path.isfile(target) and not os.path.isdir(full_ide_dir):
        url = config['arduino_src'] % {'architecture': config['arduino_architecture'],
                                       'version': config['arduino_version']}
        print "Attempting to download arduin IDE from %s" % url
        get_file(url, target)
        # errmsg = "Cannot download arduino IDE version %s from %s." %\
        #         (aversion, url)
        #   raise pyduin.arduino.ArduinoConfigError(errmsg)

    elif os.path.isfile(target) and not os.path.isdir(full_ide_dir):
        print "Extracting archive.."
        print target, full_ide_dir
        extract_file(target, full_ide_dir)
    else:
        print "Found arduino IDE in %s" % full_ide_dir
    tmpdir = '/tmp/.pyduin'

    # Check, if Arduino.mk exists in the correct version. If not
    # download it and set a symlink
    mk_dir = '/'.join((config['workdir'], 'makefiles'))
    mk_version = config['arduino_makefile_version']
    mk_dir_full = '/'.join((mk_dir, 'Arduino-Makefile-%s' % mk_version))
    if not os.path.isdir(mk_dir):
        os.mkdir(mk_dir)

    if not os.path.isdir(mk_dir_full):
        mk_tar = '/'.join((mk_dir, 'Arduino-Makefile-%s.tar.gz' % mk_version ))
        url = config['arduino_makefile_src'] % {'version': mk_version}
        if not os.path.isfile(mk_tar):
            get_file(url, mk_tar)
        extract_file(mk_tar, mk_dir)

    # Generat a Makefile from template above.
    print "Compiling makefile."
    makefilevars = {'tty': config['_arduino_']['tty'],
                    'workdir': full_ide_dir,
                    'arduino_version': config['arduino_version'],
                    'ide_dir': '/'.join((full_ide_dir, 'arduino-%s' % config['arduino_version'])),
                    'arduino_makefile': config['arduino_makefile'] % {'version': mk_version},
                  }
    makefile = MAKEFILE_TEMPLATE % makefilevars
    # Create tmp dir if needed and place Makefile in tmp dir
    if not os.path.isdir(tmpdir):
        os.mkdir(tmpdir)
    makefilepath = '/'.join((tmpdir, 'Makefile'))
    if os.path.exists(makefilepath):
        os.remove(makefilepath)
    with open(makefilepath, 'w') as mkfile:
        mkfile.write(makefile)

    # Determine, which .ino file to use
    model = config['_arduino_']['model']
    ino = args.ino if args.ino else config.get('ino', '/usr/share/pyduin/ino/pyduin.ino')
    print "Getting .ino file from %s" % ino
    if not ino or not os.path.isfile(ino):
        errmsg = "Cannot find .ino in %s. Giving up." % ino
        raise pyduin.arduino.ArduinoConfigError(errmsg)

    # Get the actual .ino file aka 'sketch' to compile and upload
    print "Getting .ino file from %s" % ino
    inotmp = '/'.join((tmpdir, 'pyduin.ino'))
    if os.path.exists(inotmp):
        os.remove(inotmp)
    get_file(ino, inotmp)

    olddir = os.getcwd()

    # Get libs
    libdir = '/'.join((config['full_ide_dir'], 'arduino-libraries'))
    if not os.path.isdir(libdir):
        os.mkdir(libdir)
    os.chdir(libdir)
    for library, libconf in config['libraries'].iteritems():
        _libdir = '/'.join((libdir, library))
        if not os.path.isdir(_libdir):
            source = libconf.get('source', False)
            if not source:
                errmsg = "No source defined for lib %s and source not found in %s" %\
                        (library, libdir)
                raise pyduin.arduino.ArduinoConfigError(errmsg)
            target = '/'.join((libdir, os.path.basename(source)))
            if not os.path.isfile(target):
                print "Downloading library %s from %s" % (library, source)
                get_file(source, target)
            # finally, extract the file
            extract_file(target, libdir, rebase=library)

    os.chdir(tmpdir)
    print "Cleaning up"
    subprocess.check_output(['make', 'clean'])
    print "Compiling sketch"
    subprocess.check_output(['make', '-j4'])
    print "Flashing arduino"
    subprocess.check_output(['make', 'upload'])
    print colored("All Done!", "green")
    os.chdir(olddir)


def versions():
    """
        Print both firmware and package version
    """
    pass


def main():
    """
        Evaluate user arguments and determine task
    """
    parser = argparse.ArgumentParser(description='Manage arduino from command line.')
    paa = parser.add_argument
    paa('-a', '--action', default=False, type=str, help="Action, e.g 'on','off'")
    paa('-A', '--arduino-version', default='1.6.5-r5', help="IDE version to download and use")
    paa('-b', '--baudrate', default=115200, help="Connection speed (default: 115200)")
    paa('-B', '--buddy', type=str, default=False,
        help="Use identifier from configfile for detailed configuration")
    paa('-c', '--configfile', type=file, default=False,
        help="Alternate configfile (default: ~/.pyduin.yml)")
    paa('-f', '--flash', action='store_true', default=False,
        help="Flash firmware to the arduino (cmmi)")
    paa('-i', '--ino', default=False,
        help='.ino file to build and uplad.')
    paa('-m', '--model', default=False, help="Arduino model (e.g.: Nano, Uno)")
    paa('-p', '--pin', default=False, type=int, help="The pin to do action x with.")
    paa('-P', '--pinfile', default=False,
        help="Pinfile to use (default: ~/pyduin/pinfiles/<model>.yml")
    paa('-t', '--tty', default='/dev/ttyUSB0', help="Arduino tty (default: '/dev/ttyUSB0')")
    paa('-v', '--version', action='store_true', help='Show version info and exit')
    paa('-w', '--workdir', type=file, default=False,
        help="Alternate workdir path (default: ~/.pyduin)")


    args = parser.parse_args()

    # try to open ~/.pyduin

    if args.version:
        versions()

    try:
        basic_config = get_basic_config(args)
        config = get_pyduin_userconfig(args, basic_config)
    except pyduin.arduino.ArduinoConfigError, error:
        print colored(error, 'red')
        sys.exit(1)

    if args.flash:
        update_firmware(args, config)
        sys.exit(0)

    Arduino = get_arduino(config['_arduino_'])
    if args.action and args.action == 'free':
        print Arduino.get_free_memory()
        sys.exit(0)
    if args.action and args.action == 'version':
        print Arduino.get_firmware_version()
        sys.exit(0)
    if args.action and args.action in ('high','low','state'):
        if args.pin in Arduino.Pins.keys():
            pin = Arduino.Pins[args.pin]
            getattr(pin, args.action)()

    #print args

if __name__ == '__main__':
    main()
