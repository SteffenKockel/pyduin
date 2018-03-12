import argparse
import contextlib
import lzma
import os
import requests
from shutil import copyfile
import subprocess
import tarfile
import yaml

CONFIG_TEMPLATE = """
workdir: ~/.pyduin
arduino_makefile: /usr/share/arduino/Arduino.mk
#arduino_makefile_version: 1.6.0
#arduino_makefile: https://raw.githubusercontent.com/sudar/Arduino-Makefile/%(version)s/Arduino.mk
arduino_architecture: linux64 # linux[32|64|arm]
#arduino_src: https://www.arduino.cc/download_handler.php?f=/arduino-%(version)s-%(architecture)s.tar.xz
arduino_src: https://downloads.arduino.cc/arduino-%(version)s-%(architecture)s.tar.xz
pinfile_src: https://raw.githubusercontent.com/SteffenKockel/pyduin/master/pinfiles/%(model)s.yml
arduino_version: 1.6.5-r5
libraries:
  - https://github.com/adafruit/DHT-sensor-library.git
buddies:
  guinny-pig:
    model: nano
"""

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

import pyduin.arduino

def extract_arduino(srcdir, targetdir):
    # proudly copied from: https://stackoverflow.com/questions/17217073/how-to-decompress-a-xz-file-which-has-multiple-folders-files-inside-in-a-singl
    with contextlib.closing(lzma.LZMAFile(srcdir)) as xz:
        with tarfile.open(fileobj=xz) as f:
            f.extractall(targetdir)

def get_arduino(args):
    arduino = pyduin.arduino.Arduino(tty=args['tty'], baudrate=args['baudrate'],
                                     pinfile=args['pinfile'], model=args['model'])
    arduino.open_serial_connection()


def get_basic_config(args):
    """
        Get config needed for all operations
    """
    configfile = args.configfile if args.configfile else '~/.pyduin.yml'
    if configfile.startswith('~'):
        configfile = os.path.expanduser(configfile)

    if not os.path.isfile(configfile):
        raise pyduin.arduino.ArduinoConfigError("Cannot open config file '%s'" % configfile)

    with open(configfile, 'r') as _configfile:
        basic_config = yaml.load(_configfile)

    workdir = args.workdir if args.workdir else basic_config.get('workdir', '~/.pyduin')
    if workdir.startswith('~'):
        workdir = os.path.expanduser(workdir)
    basic_config['workdir'] = workdir

    if not os.path.isdir(workdir):
        print "Wordir does not exist '%s'. Creating" % workdir
        os.mkdir(workdir)

    pinfiledir = '/'.join((workdir, 'pinfiles'))
    if not os.path.isdir(pinfiledir):
        print "Pinfile dir does not exist '%s'. Creating" % pinfiledir
        os.mkdir(pinfiledir)
    basic_config['pinfiledir'] = pinfiledir

    ide_dir = '/'.join((workdir, 'ide'))
    if not os.path.isdir(ide_dir):
        print "IDE dir does not exist: '%s'. Creating" % ide_dir
        os.mkdir(ide_dir)
    basic_config['ide_dir'] = ide_dir

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
            raise pyduin.arduino.ArduinoConfigError("Buddy '%s' not described in configfile's 'buddies' section" % args.buddy)

    arduino_config = {}
    for opt in ('tty', 'baudrate', 'model', 'pinfile'):
        _opt = getattr(args, opt) if getattr(args, opt) else \
                config['buddies'][args.buddy][opt] if (args.buddy and \
                config.get('buddies') and config['buddies'].get(args.buddy) and \
                config['buddies'][args.buddy].get(opt, False)) else False
        arduino_config[opt] = _opt

    buddy = args.buddy if args.buddy else 'arduino'
    if not config.get('buddies'):
        config['buddies'] = {}
    config['_arduino_'] = arduino_config

    model = config['_arduino_']['model']
    if not model or model.lower() not in ('nano','mega','uno'):
        raise pyduin.arduino.ArduinoConfigError("Model is undefined or unknown: %s" % model)

    pinfile = os.path.expand(args.pinfile) if (args.pinfile and args.pinfile.startswith('~')) else \
                args.pinfile if args.pinfile else config['buddies'][args.buddy].get('pinfile')
    # no overrides for the pinfile
    default_pinfile = False if pinfile else True

    if not pinfile:
        pinfile = '/'.join((config['pinfiledir'], '%s.yml' % model))
    config['_arduino_']['pinfile'] = pinfile

    # If no pinfile present, attempt to download one from github.
    if not os.path.isfile(pinfile) and default_pinfile:
        print "No pinfile found, trying to download one..."
        res = requests.get(config['pinfile_src'] % {'model':model})
        if res.status_code == 200:
            with open(pinfile, 'wb') as _pinfile:
                for chunk in res:
                    _pinfile.write(chunk)
        else:
            errmsg = "Cannot find or download pinfile for model '%s'. Supported?" % model
            raise pyduin.arduino.ArduinoConfigError(errmsg)

    return config


def update_firmware(config):
    """
        Update firmware on arduino (cmmi!)
    """
    aversion = config['arduino_version']

    ide_path = '/'.join((config['ide_dir'], config['arduino_version']))
    print "Checking for arduino IDE %s in %s" % (aversion, ide_path)
    if not os.path.isdir(ide_path):
        print "Arduino ide version %s not present in %s. Downloading." %\
            (aversion, ide_path)
        os.mkdir(ide_path)

    target = '/'.join((ide_path, '%s.tar.xz' % aversion))
    full_ide_dir = '/'.join((ide_path,'arduino-%s' % aversion))
    if not os.path.isfile(target) and not os.path.isdir(full_ide_dir):
        url = config['arduino_src'] % {'architecture': config['arduino_architecture'],
                                       'version': config['arduino_version']}
        print "Attempting to download arduin IDE from %s" % url
        res = requests.get(url)
        if res.status_code == 200:
            with open(target, 'wb') as ide_tarball:
                for chunk in res:
                    ide_tarball.write(chunk)
        else:
            errmsg = "Cannot download arduino IDE version %s from %s." %\
                    (aversion, url)
            raise pyduin.arduino.ArduinoConfigError(errmsg)

    elif os.path.isfile(target) and not os.path.isdir(full_ide_dir):
        print "Extracting archive.."
        print target, ide_path
        extract_arduino(target, ide_path)
    else:
        print "Found arduino IDE in %s" % ide_path
    tmpdir = '/tmp/.pyduin'
    print "Compiling makefile..."
    makefilevars = {'tty': config['_arduino_']['tty'],
                    'workdir': ide_path,
                    'arduino_version': config['arduino_version'],
                    'ide_dir': full_ide_dir,
                    'arduino_makefile': config['arduino_makefile'],
                  }
    makefile = MAKEFILE_TEMPLATE % makefilevars
    if not os.path.isdir(tmpdir):
        os.mkdir(tmpdir)
    makefilepath = '/'.join((tmpdir,'Makefile'))
    if os.path.exists(makefilepath):
        os.remove(makefilepath)
    with open(makefilepath, 'w') as mkfile:
        mkfile.write(makefile)
    ino = config['ino']
    print "Getting .ino file from %s" % ino
    inopath = '/'.join((tmpdir,'pyduin.ino'))
    if os.path.exists(inopath):
        os.remove(inopath)
    if ino.startswith("~"):
        ino = os.path.expanduser(ino)
    copyfile(ino, inopath)
    olddir = os.getcwd()
    os.chdir(tmpdir)
    print subprocess.check_output(['make', 'clean'])
    print subprocess.check_output(['make','-j4'])
    print subprocess.check_output(['make', 'upload'])
    os.chdir(olddir)





def versions():
    pass


def main():
    parser = argparse.ArgumentParser(description='Manage arduino from command line.')
    paa = parser.add_argument
    paa('-a', '--arduino-version', default='1.6.5-r5', help="IDE version to download and use")
    paa('-v', '--version', action='store_true', help='Show version info and exit')
    paa('-I', '--install-dependencies', action='store_true', help='Download and extract arduino IDE')
    paa('-t', '--tty', default='/dev/ttyUSB0', help="Arduino tty (default: '/dev/ttyUSB0')")
    paa('-m', '--model', default=False, help="Arduino model (e.g.: Nano, Uno)")
    paa('-b', '--baudrate', default=115200, help="Connection speed (default: 115200)")
    paa('-p', '--pinfile', default=False, help="Pinfile to use (default: ~/pyduin/pinfiles/<model>.yml")
    paa('-c', '--configfile', type=file, default=False, help="Alternate configfile (default: ~/.pyduin.yml)")
    paa('-w', '--workdir', type=file, default=False, help="Alternate workdir path (default: ~/.pyduin)")
    paa('-B', '--buddy', type=str, default=False, help="Use identifier from configfile for detailed configuration")
    paa('-f', '--flash', action='store_true', default=False, help="Flash firmware to the arduino (cmmi)")

    args = parser.parse_args()

    # try to open ~/.pyduin

    if args.version:
        version()

    basic_config = get_basic_config(args)
    config = get_pyduin_userconfig(args, basic_config)
    if args.flash:
        update_firmware(config)
        return


    print config

    get_arduino(config['_arduino_'])
    print args

if __name__ == '__main__':
    main()
