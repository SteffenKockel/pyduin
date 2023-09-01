""" Useful functions to save redundant code """
import os
import logging
import re
import subprocess
import time
from collections import OrderedDict
from termcolor import colored
import yaml

#from .arduino import DeviceConfigError

# Basic user config template
CONFIG_TEMPLATE = """

serial:
  use_socat: no
  hang_up_on_close: no

buddies:
  nano1:
    board: nanoatmega238
    use_socat: yes
    tty: /dev/ttyUSB1
  uno1:
    board: uno
"""


class DeviceConfigError(BaseException):
    """
        Error Class to throw on config errors
    """

class PyduinUtils:
    """ Wrapper for some useful functions. Exists, to be able to make
    use of @propget decorator and ease handling on the usage side """

    @staticmethod
    def logger():
        """ Return the pyduin log facility
        @TODO: add option to log to file """
        logging.basicConfig()
        logger = logging.getLogger('pyduin')
        return logger

    @property
    def package_root(self):
        """ Return the packages root dir. Needed for assets pinfiles and firmware """
        return os.path.dirname(__file__)

    @property
    def pinfiledir(self):
        """ Return the directory within the package, where the pinfiles resied """
        return os.path.join(self.package_root, 'data', 'pinfiles')

    @property
    def firmwaredir(self):
        """ Return the directory within the package, where the firmware resides """
        return os.path.join(self.package_root, 'data', 'platformio')

    @property
    def firmware(self):
        """ Return full path to default firmware file """
        return os.path.join(self.firmwaredir, 'pyduin.cpp')

    def available_firmware_version(self, workdir):
        """ Return the version of the firmware that resides in <workdir> over the
        the shipped one in data. If no custom firmware is available in <workdir>/src,
        then the version of the shipped firmware file in data is replied. """
        if os.path.isfile(os.path.join(workdir, 'src', 'pyduin.cpp')):
            firmware = os.path.join(workdir, 'src', 'pyduin.cpp')
        else:
            firmware = self.firmware
        with open(firmware, 'r', encoding='utf8') as fwfile:
            for line in fwfile.readlines():
                res = re.search(r'firmware_version = "([0-9].+?)"', line)
                if res:
                    return res.group(1)
        return "unknown"


    @property
    def platformio_ini(self):
        """ Return the pull path to default platformio.ini """
        return os.path.join(self.firmwaredir, 'platformio.ini')

    def board_pinfile(self, board):
        """ Return the full path to a specific pinfile in the package """
        return os.path.join(self.pinfiledir, f'{board}.yml')

    @staticmethod
    def ensure_user_config_file(location):
        """ Check, if basic config file ~/.pyduin.yml exists, else create
        basic config from template.
        """
        if not os.path.isfile(location):
            logging.info('Writing default config file to %s', location)
            with open(location, 'w', encoding='utf-8') as _configfile:
                _configfile.write(CONFIG_TEMPLATE)

    @staticmethod
    def get_buddy_cfg(config, buddy, key=False):
        """ Return the board used for a specific command. """
        if buddy:
            try:
                if not key:
                    return config['buddies'][buddy]
                return config['buddies'][buddy][key]
            except KeyError:
                return False
        return False


class PinFile:
    """ Represents a pinfile and provides functions mostly required for templating
    the firmware for different boards """
    _analog_pins = []
    _digital_pins = []
    _pwm_pins = []
    pins = OrderedDict()
    pinfile = False

    def __init__(self, pinfile):
        if not os.path.isfile(pinfile):
            raise DeviceConfigError(f'Cannot open pinfile: {pinfile}')

        with open(pinfile, 'r', encoding='utf-8') as pfile:
            self.pinfile = yaml.load(pfile, Loader=yaml.Loader)

        self.pins = sorted(list(self.pinfile['Pins'].items()),
                       key=lambda x: int(x[1]['physical_id']))

        for name, pinconfig in self.pins:  # pylint: disable=unused-variable
            pin_id = str(pinconfig['physical_id'])
            if pinconfig.get('pin_type') == 'analog':
                self._analog_pins.append(pin_id)
            elif pinconfig.get('pin_type', 'digital') == 'digital':
                self._digital_pins.append(pin_id)
            if pinconfig.get('pwm_capable'):
                self._pwm_pins.append(pin_id)

    @property
    def analog_pins(self):
        """ Return a list of analog pin id's """
        return self._analog_pins

    @property
    def digital_pins(self):
        """ Return a list of digital pin id's """
        return self._digital_pins

    @property
    def pwm_pins(self):
        """ return a list of pwm-capable pin id'w """
        return self._pwm_pins

    @property
    def num_analog_pins(self):
        """ Return the number of analog pins for the given board """
        return len(self._analog_pins)

    @property
    def num_digital_pins(self):
        """ Return the number of digital pins for the given board """
        return len(self._digital_pins)

    @property
    def num_pwm_pins(self):
        """ Return the number of pwm-capable pins """
        return len(self._pwm_pins)


class AttrDict(dict):
    """ Helper class to ease the handling of ini files with configparser. """
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

class SocatProxy:
    """ A class that represents a serial proxy based on socat """
    debug = False

    # pylint: disable=too-many-arguments
    def __init__(self, source_tty, baudrate, proxy_tty=None, config=None,
                 log_level=logging.DEBUG):
        self.source_tty = source_tty
        self.baudrate = baudrate
        self.proxy_tty = proxy_tty
        self.config = config
        self.logger = PyduinUtils.logger()
        if not isinstance(log_level, int):
            log_level = getattr(logging, log_level.upper())
        self.logger.setLevel(log_level)

        if not self.proxy_tty:
            proxy_tty = os.path.basename(source_tty)
            self.proxy_tty = os.path.join(os.sep, 'tmp', f'{proxy_tty}.tty')
            self.logger.debug("Socat proxy expected at: %s", self.proxy_tty)

    @property
    def socat_cmd(self):
        """ Return assembled socat comd string """
        common_opts = "cs8,parenb=0,cstopb=0,clocal=0,raw,echo=0,setlk,flock-ex-nb,nonblock=1"
        cmd = ['/usr/bin/socat', '-s']
        extra_opts = ['-x', '-ddd', '-ddd'] if self.debug else ['-d']
        cmd.extend(extra_opts)
        cmd.extend([f'{self.source_tty},b{self.baudrate},{common_opts}',
                    f'PTY,link={self.proxy_tty},b{self.baudrate},{common_opts}'])
        return (*cmd,)

    def start(self):
        """ Start the socat proxy """
        if not os.path.exists(self.proxy_tty):
            subprocess.check_output(['stty', '-F', self.source_tty, 'hupcl'])
            subprocess.Popen(self.socat_cmd) # pylint: disable=consider-using-with
            print(colored(f'Started socat proxy on {self.proxy_tty}', 'cyan'))
            time.sleep(1)

    def stop(self):
        """ Stop the socat proxy """
        cmd = f'ps aux | grep socat | grep -v grep | grep {self.proxy_tty} | awk '+"'{ print $2 }'"
        # cmd = f'pgrep -a socat | grep "{self.proxy_tty}" | grep -Eo "^[0-9]+?"'
        pid = subprocess.check_output(cmd, shell=True).strip()
        subprocess.check_output(['kill', f'{pid.decode()}'])
        time.sleep(1)


    # @classmethod
    # def get(cls, source_tty, baudrate, proxy_tty=None, config=None):
    #     return(cls, source_tty, baudrate, proxy_tty, config)