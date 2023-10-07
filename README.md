# pyduin

[![Pylint](https://github.com/SteffenKockel/pyduin/actions/workflows/pylint.yml/badge.svg)](https://github.com/SteffenKockel/pyduin/actions/workflows/pylint.yml)
[![Yamllint](https://github.com/SteffenKockel/pyduin/actions/workflows/yamllint.yml/badge.svg)](https://github.com/SteffenKockel/pyduin/actions/workflows/yamllint.yml)
[![Pytest and Coverage](https://github.com/SteffenKockel/pyduin/actions/workflows/pytest.yml/badge.svg)](https://github.com/SteffenKockel/pyduin/actions/workflows/pytest.yml)
[![PyPI license](https://img.shields.io/pypi/l/pyduin.svg)](https://pypi.python.org/pypi/pyduin/)
[![PyPI download month](https://img.shields.io/pypi/dm/pyduin.svg)](https://pypi.python.org/pypi/pyduin/)
[![PyPI version fury.io](https://badge.fury.io/py/pyduin.svg)](https://pypi.python.org/pypi/pyduin/)
[![GitHub latest commit](https://badgen.net/github/last-commit/steffenkockel/pyduin)](https://GitHub.com/steffenkockel/pyduin/commit/)
[![PyPI status](https://img.shields.io/pypi/status/pyduin.svg)](https://pypi.python.org/pypi/pyduin/)

Pyduin is a Python wrapper for Arduino and other IOT devices such as ESP. It aims to support everything, that platformio supports. The following components are part of the package.

* A python library
* A firmware to be loaded onto the device
* A command-line interface (to flash the firmware)

## What for?

Pyduin makes it easy to interact with an Arduino or other IOT device from within Python. Once a device has the correct firmware applied, one can set pin modes, pin states, pwm values and more.

This makes it easy to wire a sensor, switch to an IOT device, connect it to a computer and start working with the sensor values in Python. The library supports:

- Analog read and write
- Digital read and write
- PWM
- Pin modes
- OneWire (firmware works, not yet implemented in lib)
- DHT Sensors (firmware works, not yet implemented in lib)
- SPI (firmware works, not yet implemented in lib)
- ...

## Device support

In theory, any device supported by [platformio](https://platformio.org/) can work. Currently, the following devices are supported

* Arduino Uno
* Arduino Nano
* Sparkfun Pro Micro (ATMEGA32U4)

## Installation

### pyduin module

Only `pip` installs are available.

```bash
pip install pyduin
```
## Dependency socat

Opening a serial connection **resets most Arduinos**. `pyduin` circumvents this drawback with a `socat` proxy.

To make meaningful use of the command-line features, the installation and usage of `soact` is recommended. To activate usage, edit `~/.pyduin.yml` and set `use_socat` to `yes` (default).
```yaml
serial:
  use_socat: yes
```
If `socat` is installed, a proxy will be started for every device that connections are made to. The pins get set up according to the board file and the initial modes get set on first connect. The following connections **will not reset the Arduino**. The proxy will stop safely on device disconnect. The proxy will also be stopped for flashing.

## Usage

## As python module

After installation the `pyduin` module can be imported.
```python
from pyduin import arduino

board = 'nanoatmega328'

Arduino = arduino.Arduino(board=board,
                          tty='/dev/ttyUSB0',
                          wait=True)
print(Arduino.firmware_version)
pin = Arduino.get_pin(13)
pin.set_mode('OUTPUT')
pin.high()
print(Arduino.free_memory)

```

## Command-line

The command-line interface provides a help page for all options and commands.

```
pyduin --help
```

Every positional argument that serves as a subcommand, has it's own help page.

```
pyduin firmware|pin|dependencies|versions --help
```

Most of the commands have shorter aliases. The following command sets the pwm value for pin 5 to 125.

```
pyduin --tty /dev/USB0 --baudrate 115200 --board nanoatmega328 pin 5 pwm 125
```
To connect to a device `--tty` and `--board` arguments are required.

## Configuration file

Pyduin creates a configuration file in `~/.pyduin.yml` from a template. This file contains some generic settings and the buddy list.

### The buddy list

The buddy-list feature allows one to define known devices aka buddies. In `~/.pyduin.yml` a dictionary of buddies can be declared. 
```yaml
buddies:
  uber:
    board: nanoatmega328 # as in platformio. required.
    tty: /dev/uber # required
    baudrate: 115200 # default derived from boardfile, optional
  under:
    board: uno
    tty: /dev/ttyUSB0
```
The buddies can be used in the command line interface.

```
pyduin -B uber pin 13 high
```

#### Default buddy

A `default_buddy` can be defined in the configuration file. This allows to target a device that is known and appropriately configured, without specifying the buddy option.

```
pyduin pin 13 high
```

### Flashing firmware to the Arduino

```
pyduin --buddy uber firmware flash
```
It can also be done without the buddy list.
```
pyduin --board nanoatmega328 --tty=/dev/mytty fw f
```

#### Control the Arduinos pins

 Using the command-line, the pins can be controlled as follows. The following command can be used to switch on and off digital pins.

```
pyduin --buddy uber pin 4 {high|low}
```
The pin mode can be set as follows
```
pyduin -B uber pin 4 mode {input|ouput|input_pullup,pwm}
```
A pin can also be read from. Resulting in `0` or `1` for digital pins and a value between `0` and `1024` (10bit) for analog pins. The analog pins also have aliases configured according to the Arduino conventions.

```
pyduin p A0 read
```

#### Control the builtin LED's

The builtin LED's defined in the board file can be addressed by their corresponding names

```bash
pyduin -B foo led1 {on|off}
```
Pyduin determines the correct read command in the background depending on the pins nature.

#### Get firmware version from the Device

```bash
pyduin --buddy uber firmware version [device|available]
```
#### Get free memory from the Device

```bash
pyduin --buddy uber free
```

## Contribute

To install the package in development mode, use `pip install -e`. This works pretty straight forward.

```
git clone git@github.com:SteffenKockel/pyduin.git
cd pyduin
virtualenv .
. bin/activate
pip install -e .
```

Pull requests welcome.

### Add a currently unsupported device

Adding a device works, by editing the `~/.pyduin/platformio.ini` and and providing a board file. Pyduin creates a build environment for every supported board in `~/.pyduin/`. These files and folders get created, when attempting to flash firmware to a device. Changes made here are preserved.

A device must also provide a [board file](https://github.com/SteffenKockel/pyduin/tree/master/src/pyduin/data/boardfiles). The name of the board file must use the name of the corresponding board name (as in platformio).

When developing in edit mode `(pip install -e .)`, the board file can  be added to the libraries data folder. Also changes to the `platformio.ini` can be made persistent this way. Feel free to share added devices with a pull request.
