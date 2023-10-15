""" Useful functions to save redundant code """
import configparser
import os
import logging
import re
import subprocess
import time
from shutil import copyfile, rmtree
import shutil
from collections import OrderedDict
from jinja2 import Template
from termcolor import colored
import yaml

# Basic user config template
CONFIG_TEMPLATE = """
log_level: info
# default_buddy: nano1

serial:
  use_socat: no
  hang_up_on_close: no

buddies:
  nano1:
    board: nanoatmega328
    use_socat: yes
    tty: /dev/ttyUSB1
  uno1:
    board: uno
    tty: /dev/ttyACM0
"""


class DeviceConfigError(BaseException):
    """
        Error Class to throw on config errors
    """

class BuildEnvError(BaseException):
    """ Error class to be thrown on errors in the build environment """
    def __init__(self, *args, msg=False, **kwargs):
        _msg = msg or 'An error occurred in the build env.'
        super().__init__(msg, *args, **kwargs)

class PinNotFoundError(BaseException):
    """ Error class to throw, when a pin cannot be found """
    def __init__(self, pin, *args, **kwargs):
        msg = f'Pin {pin} cannot be resolved to a pin on the device.'
        super().__init__(msg, *args, **kwargs)

class LEDNotFoundError(BaseException):
    """ Error class to be thrown when an led cannot be resolved to a pin """
    def __init__(self, led, *args, **kwargs):
        msg = f'LED {led} cannot be resolved to a pin on the device.'
        super().__init__(msg, *args, **kwargs)

class PyduinUtils:
    """ Wrapper for some useful functions. Exists, to be able to make
    use of @propget decorator and ease handling on the usage side """

    _configfile = os.path.expanduser('~/.pyduin.yml')
    _workdir = os.path.expanduser('~/.pyduin')
    @staticmethod
    def logger():
        """ Return the pyduin log facility
        @TODO: add option to log to file """
        logging.basicConfig()
        logger = logging.getLogger('pyduin')
        return logger

    @property
    def package_root(self):
        """ Return the packages root dir. Needed for assets boardfiles and firmware """
        return os.path.dirname(__file__)

    @property
    def boardfiledir(self):
        """ Return the directory within the package, where the boardfiles resied """
        return os.path.join(self.package_root, 'data', 'boardfiles')

    @property
    def configfile(self):
        """ Return the default path to the users config file """
        return self._configfile

    @property
    def workdir(self):
        """ Return the directory where the build environments live """
        return self._workdir

    @property
    def firmwaredir(self):
        """ Return the directory within the package, where the firmware resides """
        return os.path.join(self.package_root, 'data', 'platformio')

    @property
    def firmware(self):
        """ Return full path to default firmware file """
        return os.path.join(self.firmwaredir, 'pyduin.cpp')

    def available_firmware_version(self, workdir=None):
        """ Return the version of the firmware that resides in <workdir> over the
        the shipped one in data. If no custom firmware is available in <workdir>/src,
        then the version of the shipped firmware file in data is replied. """
        if not workdir:
            workdir = self._workdir
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

    def boardfile_for(self, board):
        """ Return the full path to a specific boardfile in the package """
        # check for overrides in workdir
        if os.path.isfile(os.path.join(self.workdir, board, f'{board}.yml')):
            return os.path.join(self.workdir, board, f'{board}.yml')
        return os.path.join(self.boardfiledir, f'{board}.yml')

    def get_boardfile_obj(self, board):
        """ Get the boardfile object for a given board """
        return BoardFile(self.boardfile_for(board))

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
        """ Return the requested buddy from the config . """
        try:
            if not key:
                return config['buddies'][buddy]
            return config['buddies'][buddy][key]
        except KeyError:
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
        pio = shutil.which('pio')
        if pio:
            print(colored(f'Platformio found in {pio}.', 'green'))
        else:
            print(colored('Platformio not installed. Flashing does not work.', 'red'))
            ret = False
        socat = shutil.which('socat')
        if socat:
            print(colored(f'Socat found in {socat}.', 'green'))
        else:
            print(colored('Socat not found. Some features may not work.', 'red'))
            ret = False
        return ret



class BoardFile:
    """ Represents a boardfile and provides functions mostly required for templating
    the firmware for different boards """
    _analog_pins = []
    _digital_pins = []
    _pwm_pins = []
    _physical_pin_ids = []
    _leds = []
    _spi_interfaces = {}
    _i2c_interfaces = {}
    pins = OrderedDict()
    _boardfile = False
    _baudrate = False
    boardfile_dir = False

    def __init__(self, boardfile):
        if not os.path.isfile(boardfile):
            raise DeviceConfigError(f'Cannot open boardfile: {boardfile}')

        with open(boardfile, 'r', encoding='utf-8') as pfile:
            self._boardfile = yaml.load(pfile, Loader=yaml.Loader)
        self.boardfile_dir = boardfile
        self.pins = sorted(list(self._boardfile['pins']),
                       key=lambda x: int(x['physical_id']))

        for pinconfig in self.pins:

            pin_id = pinconfig['physical_id']
            self._physical_pin_ids.append(pin_id)
            extra = pinconfig.get('extra', [])

            if 'analog' in extra and not pin_id in self._analog_pins:
                self._analog_pins.append(pin_id)
            else:
                self._digital_pins.append(pin_id)

            if extra:
                if 'pwm' in extra:
                    self._pwm_pins.append(pin_id)

                for match in list(filter(re.compile("led[0-9]+").match, extra)):
                    self._leds.append({match: pin_id})
                # spi
                for match in list(filter(re.compile("sda|scl").match, extra)):
                    num = re.findall(re.compile(r'\d+'), match) or ['0']
                    # pylint: disable=expression-not-assigned
                    self._i2c_interfaces.get(num[0]) or \
                        self._i2c_interfaces.setdefault(num[0], {})
                    self._i2c_interfaces[num[0]][match] = pin_id
                # i2c
                for match in list(filter(re.compile("ss|mosi|miso|sck").match, extra)):
                    num = re.findall(re.compile(r'\d+'), match) or ['0']
                    # pylint: disable=expression-not-assigned
                    self._spi_interfaces.get(num[0]) or \
                        self._spi_interfaces.setdefault(num[0], {})
                    self._spi_interfaces[num[0]][match] = pin_id


        self._baudrate = self._boardfile.get('baudrate', False)

    @property
    def analog_pins(self) -> list:
        """ Return a list of analog pin id's """
        return self._analog_pins

    @property
    def digital_pins(self):
        """ Return a list of digital pin id's """
        return self._digital_pins

    @property
    def pwm_pins(self) -> list:
        """ return a list of pwm-capable pin id'w """
        return self._pwm_pins

    @property
    def leds(self) -> list:
        """ Return a List of pins that have an LED connected """
        return self._leds

    @property
    def i2c_interfaces(self) -> list:
        """ Return a list of i2c interfaces """
        return self._i2c_interfaces

    @property
    def spi_interfaces(self) -> list:
        """ Return a list of spi interfaces """
        return self._spi_interfaces

    @property
    def num_analog_pins(self) -> int:
        """ Return the number of analog pins for the given board """
        return len(self._analog_pins)

    @property
    def num_digital_pins(self):
        """ Return the number of digital pins for the given board """
        return len(self._digital_pins)

    @property
    def num_pwm_pins(self) -> int:
        """ Return the number of pwm-capable pins """
        return len(self._pwm_pins)

    @property
    def num_physical_pins(self) -> int:
        """ Return the number of all physical pins """
        return len(self._physical_pin_ids)

    @property
    def physical_pin_ids(self):
        """ Return a list of all pins """
        return self._physical_pin_ids

    @property
    def extra_libs(self):
        """ Return a list of extra libraries to include in the firmware """
        fwcfg = self._boardfile.get('firmware', False )
        if fwcfg:
            extra_libs = fwcfg.get('extra_libs', False)
            if extra_libs:
                return fwcfg['extra_libs']
        return []

    @property
    def baudrate(self):
        """ Return the baudrate used to connect to this board """
        return self._baudrate

    def led_to_pin(self, led_id):
        """ Resolve led[0-9] back to an actual pin id """
        led = f'led{led_id}'
        pin = list(filter(lambda x: led in x ,self._leds))
        if pin:
            return pin[0][led]
        raise LEDNotFoundError(led)

    def normalize_pin_id(self, pin_id):
        """ Return the physical_id of a pin. This function is used to
        translate back pin alias names such as A[09]+ to a pin number
        """
        if isinstance(pin_id, str):
            try:
                pin_id = [{'physical_id': int(pin_id)}]
            except ValueError:
                pin_id = list(filter(lambda x:  x.get('alias') == pin_id, self.pins))

            try:
                pin_id = pin_id[0]['physical_id']
            except IndexError as exc:
                raise PinNotFoundError(pin_id) from exc

        if not pin_id in self.physical_pin_ids:
            raise PinNotFoundError(pin_id)
        return pin_id
        #return int(self.get_pin_config(pin_id)['physical_id'])

    def get_pin_config(self, pin_id:int):
        """ Return the configuration dict of a pin """
        try:
            return list(filter(lambda x: x['physical_id'] == pin_id, self.pins))[0]
        except IndexError:
            return {}

class AttrDict(dict):
    """ Helper class to ease the handling of ini files with configparser. """
    def __init__(self, *args, **kwargs):
        # pylint: disable=super-with-arguments
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

class SocatProxy:
    """ A class that represents a serial proxy based on socat """

    # pylint: disable=too-many-arguments
    def __init__(self, source_tty, baudrate, proxy_tty=None, log_level=logging.INFO):
        self.source_tty = source_tty
        self.baudrate = baudrate
        self.proxy_tty = proxy_tty
        self.logger = PyduinUtils.logger()
        self.logger.setLevel(PyduinUtils.loglevel_int(log_level))
        self.debug = log_level==logging.DEBUG

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
        return True

    def stop(self):
        """ Stop the socat proxy """
        cmd = f'pgrep -a socat | grep "{self.proxy_tty}" | grep -Eo "^[0-9]+?"'
        pid = subprocess.check_output(cmd, shell=True).strip()
        subprocess.check_output(['kill', f'{pid.decode()}'])
        time.sleep(1)
        return True


class BuildEnv:
    """ A class that represents a buildenv for device firmware """

    # pylint: disable=too-many-arguments, too-many-instance-attributes
    def __init__(self, workdir, board, tty, platformio_ini=False, log_level=logging.INFO):
        self.utils = PyduinUtils()
        self.logger = self.utils.logger()
        self.workdir = os.path.expanduser(workdir)
        self.board = board
        self.tty = tty
        self.platformio_ini = platformio_ini or self.utils.platformio_ini
        self.project_dir = os.path.join(workdir, board)
        self.logger.setLevel(self.utils.loglevel_int(log_level))
        self.cmd = ['pio', 'run', '-e', self.board,
                    '-t', 'upload', '--upload-port', self.tty,
                    '-d', self.project_dir, '-c', self.platformio_ini]

    def create(self, force_recreate=False):
        """ Create directories and copy over files """
        self.logger.debug("Creating workdir in %s if not exists", self.project_dir)
        try:
            if force_recreate:
                rmtree(self.project_dir)
            os.makedirs(self.project_dir, exist_ok=True)
        except PermissionError as err:
            raise BuildEnvError(f'Cannot recreate buildenv in {self.project_dir}') from err
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

    def template_firmware(self, arduino):
        """ Render firmware from template """
        _tpl = '{%s}'
        fwenv = {
            "num_analog_pins": arduino.boardfile.num_analog_pins,
            "num_digital_pins": arduino.boardfile.num_digital_pins,
            "num_pwm_pins": arduino.boardfile.num_pwm_pins,
            "pwm_pins": _tpl % ", ".join(map(str, arduino.boardfile.pwm_pins)),
            "analog_pins": _tpl % ", ".join(map(str, arduino.boardfile.analog_pins)),
            "digital_pins": _tpl % ", ".join(map(str, arduino.boardfile.digital_pins)),
            "physical_pins": _tpl % ", ".join(map(str, arduino.boardfile.physical_pin_ids)),
            "num_physical_pins":  arduino.boardfile.num_physical_pins,
            "extra_libs": '\n'.join(arduino.boardfile.extra_libs),
            "baudrate": arduino.baudrate
        }

        firmware = os.path.join(self.workdir, self.board, 'src', 'pyduin.cpp')
        self.logger.debug("Using firmware template: %s", firmware)

        with open(firmware, 'r', encoding='utf-8') as template:
            tpl = Template(template.read())
            tpl = tpl.render(fwenv)
            #logger.debug(tpl)

        with open(firmware, 'w', encoding='utf8') as template:
            template.write(tpl)

    def build(self):
        """ Build the firmware and upload it to the device. """
        os.chdir(self.workdir)
        self.logger.debug(self.cmd)
        try:
            out = subprocess.check_output(self.cmd)
            self.logger.debug(out)
            return True
        except subprocess.CalledProcessError as err:
            raise BuildEnvError(f'Build in {self.workdir} failed') from err

# pylint: disable=too-many-instance-attributes
class CliConfig:
    """ This class represents a configuration object needed for
    the commandline interface to work """
    default_config_path = '~/.pyduin.yml'
    default_workdir = '~/.pyduin'
    workdir = False
    platformio_ini = False
    firmware_file = False
    buddy = False
    utils = PyduinUtils()
    logger = utils.logger()
    config_template = CONFIG_TEMPLATE
    board = False
    boardfile = False
    baudrate = False
    socat = False
    userconfig = False

    def __init__(self, args):
        """ Determine which userconfig and log_level to use.  """
        self.args = args
        self.set_userconfig()
        self.set_loglevel()
        self.logger.debug("Using configuration file: %s", self.userconfig_file)
        self.set_workdir()
        self.set_platformio_ini()
        self.set_firmware_file()
        self.set_buddy()
        self.set_board()
        self.set_tty()
        self.set_baudrate()
        self.set_use_socat()

    def set_userconfig(self):
        """ Determine which userconfig to use and how to access it """
        configfile = self.args.configfile or os.path.expanduser(self.default_config_path)
        if isinstance(configfile, str):
            if not os.path.isfile(configfile):
                self.create_default_userconfig(configfile)
            with open(configfile, 'r', encoding='utf-8') as _configfile:
                self.userconfig = yaml.load(_configfile, Loader=yaml.Loader)
            self.userconfig_file = configfile
        else:
            self.userconfig = yaml.safe_load(configfile)
            self.userconfig_file = os.path.abspath(configfile.name)


    def create_default_userconfig(self, location, rewrite=False):
        """ Check, if basic config file ~/.pyduin.yml exists, else create
        basic config from template.
        """
        if not os.path.isfile(location) or rewrite:
            self.logger.info('Writing default config file to %s', location)
            with open(location, 'w', encoding='utf-8') as _configfile:
                _configfile.write(self.config_template)

    def set_loglevel(self):
        """ Determine, which log level to use """
        self.log_level = self.args.log_level or self.userconfig.get('log_level', 'info')
        self.logger.setLevel(getattr(logging, self.log_level.upper()))

    def set_workdir(self):
        """ Determine, which workdir to use """
        self.workdir = self.args.workdir or \
            self.userconfig.get('workdir', self.default_workdir)
        self.logger.debug("Using workdir %s", self.workdir)

    def set_platformio_ini(self):
        """ Determine, which platformio.ini to use """
        self.platformio_ini = self.args.platformio_ini or self.utils.platformio_ini
        self.logger.debug("Using platformio.ini in: %s", self.platformio_ini)

    def set_firmware_file(self):
        """ Determine, which firmware file to use """
        self.firmware_file = self.utils.firmware
        self.logger.debug("Using firmware from %s", self.firmware_file)

    def set_buddy(self):
        """ Determine if the given buddy is defined in config file and the configfile has
        a 'buddies' section at all. """
        self.buddy = self.args.buddy or self.userconfig.get('default_buddy', False)
        self.logger.debug("Using buddy '%s'", self.buddy)
        if not self.userconfig.get('buddies'):
            self.logger.info("Configfile is missing 'buddies' section")
            self.userconfig['buddies'] = {}
        if self.buddy and not self.userconfig['buddies'].get(self.buddy):
            errmsg = f'Buddy "{self.buddy}" not described in configfile\'s "buddies" section.'
            raise DeviceConfigError(errmsg)
        return True

    def check_board_support(self, board):
        """
        Determine if the configured model is supported. Do so by checking the
        platformio config file for env definitions.
        """
        parser = configparser.ConfigParser(dict_type=AttrDict)
        parser.read(self.platformio_ini)
        sections = parser.sections()
        boards = [x.split(':')[-1] for x in sections if x.startswith('env:')]
        for boardfile in os.listdir(self.utils.boardfiledir):
            boards.append(boardfile.split('.')[0])
        boards = list(dict.fromkeys(list(filter(lambda x: boards.count(x)==2, boards))))
        if not board in boards:
            msg = f'Board ({board}) not in supported boards list {boards}'
            self.logger.error(msg)
            raise DeviceConfigError(msg)
        return True

    def set_board(self):
        """ Determine, which board to use """
        self.board = self.args.board
        if self.buddy and not self.board:
            self.board = self.userconfig['buddies'][self.buddy].get('board', False)
        if not self.board:
            raise DeviceConfigError("Cannot determine board for desired action.")
        self.logger.debug('Using board %s', self.board)
        self.check_board_support(self.board)
        self.boardfile = self.utils.get_boardfile_obj(self.board)

    def set_tty(self):
        """ Determine, which tty to use """
        self.tty = self.args.tty
        if self.buddy and not self.tty:
            self.tty = self.userconfig['buddies'][self.buddy].get('tty', False)
        if not self.tty:
            raise DeviceConfigError("Cannot determine tty to use for desired action.")

    def set_baudrate(self):
        """ Determine, which baudrate to use """
        self.baudrate = self.args.baudrate
        if self.buddy and not self.baudrate:
            self.baudrate = self.userconfig['buddies'][self.buddy].get('baudrate', False)
        if not self.baudrate:
            self.baudrate =  self.boardfile.baudrate
        self.logger.debug('Using baudrate %s', self.baudrate)
        if not self.baudrate:
            raise DeviceConfigError("Cannot determine baudrate to use for feature.")

    def set_use_socat(self):
        """ Determine whether to use socat proxy or not """
        if self.buddy:
            self.socat = self.userconfig['buddies'][self.buddy].get('use_socat', None)
        if self.socat is None:
            self.socat = self.userconfig['serial'].get('use_socat', False)

    @property
    def arduino_config(self):
        """ Return a usable configuration dict for the Arduino class """
        return {
            'wait': True,
            'tty': self.tty,
            'baudrate': self.baudrate,
            'boardfile': self.boardfile,
            'socat': self.socat,
            'board': self.board }
