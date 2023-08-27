""" Useful functions to save redundant code """
import os
import logging
import re
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


class PyduinUtils:
    """ Wrapper for some useful functions. Exists, to be able to make
    use of @propget decorator and ease handling on the usage side """

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
        return os.path.join(self.firmwaredir, 'pyduin.ino')

    def available_firmware_version(self, workdir):
        """ Return the version of the firmware that resides in <workdir> over the
        the shipped one in data. If no custom firmware is available in <workdir>/src,
        then the version of the shipped firmware file in data is replied. """
        if os.path.isfile(os.path.join(workdir, 'src', 'pyduin.ino')):
            firmware = os.path.join(workdir, 'src', 'pyduin.ino')
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
    def socat_cmd(source_tty, proxy_tty, baudrate, debug=False):
        """ Return assembled socat comd string """
        common_opts = "cs8,parenb=0,cstopb=0,clocal=0,raw,echo=0,setlk,flock-ex-nb,nonblock=1"
        cmd = ['/usr/bin/socat', '-s']
        extra_opts = ['-x', '-ddd', '-ddd'] if debug else ['-d']
        cmd.extend(extra_opts)
        cmd.extend([f'{source_tty},b{baudrate},{common_opts}',
                    f'PTY,link={proxy_tty},b{baudrate},{common_opts}'])
        return (*cmd,)

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

class AttrDict(dict):
    """ Helper class to ease the handling of ini files with configparser. """
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self
