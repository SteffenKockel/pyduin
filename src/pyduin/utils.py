""" Useful functions to save redundant code """
import os
import logging
import re
import subprocess
import time
from shutil import copyfile, which
from collections import OrderedDict
from termcolor import colored
import yaml

#from .arduino import DeviceConfigError

# Basic user config template
CONFIG_TEMPLATE = """
log_level: info

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

    @staticmethod
    def loglevel_int(level):
        """ Return the integer corresponding to log level string """
        if isinstance(level, int):
            return level
        return getattr(logging, level.upper())

    @staticmethod
    def dependencies():
        """ Check, if platformio and socat are available. """
        ret = True
        pio = which('pio')
        if pio:
            print(colored(f'Platformio found in {pio}.', 'green'))
        else:
            print(colored('Platformio not installed. Flashing does not work.'))
            ret = False
        socat = which('socat')
        if socat:
            print(colored(f'Socat found in {socat}.', 'green'))
        else:
            print(colored('Socat not found. Some features may not work.', 'red'))
            ret = False
        return ret



class PinFile:
    """ Represents a pinfile and provides functions mostly required for templating
    the firmware for different boards """
    _analog_pins = []
    _digital_pins = []
    _pwm_pins = []
    pins = OrderedDict()
    _pinfile = False
    _baudrate = False

    def __init__(self, pinfile):
        if not os.path.isfile(pinfile):
            raise DeviceConfigError(f'Cannot open pinfile: {pinfile}')

        with open(pinfile, 'r', encoding='utf-8') as pfile:
            self._pinfile = yaml.load(pfile, Loader=yaml.Loader)

        self.pins = sorted(list(self._pinfile['Pins'].items()),
                       key=lambda x: int(x[1]['physical_id']))

        for name, pinconfig in self.pins:  # pylint: disable=unused-variable
            pin_id = str(pinconfig['physical_id'])
            if pinconfig.get('pin_type') == 'analog':
                self._analog_pins.append(pin_id)
            elif pinconfig.get('pin_type', 'digital') == 'digital':
                self._digital_pins.append(pin_id)
            if pinconfig.get('pwm_capable'):
                self._pwm_pins.append(pin_id)

        self._baudrate = self._pinfile['baudrate']

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

    @property
    def extra_libs(self):
        """ Return a list of extra libraries to include in the firmware """
        fwcfg = self._pinfile.get('firmware', False )
        if fwcfg:
            extra_libs = fwcfg.get('extra_libs', False)
            if extra_libs:
                return fwcfg['extra_libs']
        return []

    @property
    def baudrate(self):
        """ Return the baudrate used to connect to this board """
        return self._baudrate


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
                 log_level=logging.INFO):
        self.source_tty = source_tty
        self.baudrate = baudrate
        self.proxy_tty = proxy_tty
        self.config = config
        self.logger = PyduinUtils.logger()
        self.logger.setLevel(PyduinUtils.loglevel_int(log_level))

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
        #cmd = f'ps aux | grep socat | grep -v grep | grep {self.proxy_tty} | awk '+"'{ print $2 }'"
        cmd = f'pgrep -a socat | grep "{self.proxy_tty}" | grep -Eo "^[0-9]+?"'
        pid = subprocess.check_output(cmd, shell=True).strip()
        subprocess.check_output(['kill', f'{pid.decode()}'])
        time.sleep(1)


    # @classmethod
    # def get(cls, source_tty, baudrate, proxy_tty=None, config=None):
    #     return(cls, source_tty, baudrate, proxy_tty, config)

class BuildEnv:
    """ A class that represents a buildenv for device firmware """

    # pylint: disable=too-many-arguments
    def __init__(self, workdir, board, tty, platformio_ini=False, log_level=logging.INFO):
        self.utils = PyduinUtils()
        self.logger = self.utils.logger()
        self.workdir = os.path.expanduser(workdir)
        self.board = board
        self.tty = tty
        self.platformio_ini = platformio_ini if platformio_ini else self.utils.platformio_ini
        self.project_dir = os.path.join(workdir, board)
        self.logger.setLevel(self.utils.loglevel_int(log_level))

    def create(self):
        """ Create directories and copy over files """
        os.makedirs(self.project_dir, exist_ok=True)
        self.logger.debug("Creating workdir in %s if not exists", self.project_dir)
        platformio_ini_target = os.path.join(self.workdir, 'platformio.ini')
        if not os.path.isfile(platformio_ini_target):
            self.logger.debug("Copying: %s", platformio_ini_target)
            copyfile(self.platformio_ini, platformio_ini_target)
        board_dir = os.path.join(self.workdir, self.board, 'src')
        if not os.path.exists(board_dir):
            self.logger.debug("Creating project_dir %s", board_dir)
            os.makedirs(board_dir, exist_ok=True)
        firmware = os.path.join(board_dir, 'pyduin.cpp')
        if not os.path.isfile(firmware):
            self.logger.debug("Copying: %s", firmware)
            copyfile(self.utils.firmware, firmware)

    def build(self):
        """ Build the firmware and upload it to the device. """
        os.chdir(self.workdir)
        cmd = ['pio', 'run', '-e', self.board, '-t', 'upload', '--upload-port', self.tty,
               '-d', self.project_dir, '-c', self.platformio_ini]
        self.logger.debug(cmd)
        out = subprocess.check_output(cmd)
        print(out)
