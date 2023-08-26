""" Useful functions to save redundant code """
import os
import logging
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
        return os.path.dirname(os.path.dirname(__file__))

    @property
    def pinfiledir(self):
        """ Return the directory within the package, where the pinfiles resied """
        return os.path.join(self.package_root, 'pinfiles')

    @property
    def firmwaredir(self):
        """ Return the directory within the package, where the firmware resides """
        return os.path.join(self.package_root, 'src')

    @property
    def firmware(self):
        """ Return full path to default firmware file """
        return os.path.join(self.firmwaredir, 'pyduin.ino')

    @property
    def platformio_ini(self):
        """ Return the pull path to default platformio.ini """
        return os.path.join(self.package_root, 'platformio.ini')

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
