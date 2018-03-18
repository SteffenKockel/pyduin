# pyduin 0.2.1

## What?

A pyhton wrapper for arduino. It consists of two parts

* A python library for arduino, pin, pinmode
* An arduino firmware

## What for?

To interact seamless with an arduino from within python. Once an arduino has the correct firmware applied, one can set pin modes, pin states, pwm values and more. It can

* Download dependencies (IDE, libraries, Arduino.mk)
* Flash arduinos
* Control arduino pins (if flashed with `pyduin.ino`)

The code is als intended to be used and originates from a [crossbar.io](https://crossbar.io) prowered server that constantly holds the Serial connection to the arduino and converts the output to JSON. The CLI wrapper was written to ease the arduino handling in the context of python based projects.

## How to install?

Currently, only pip installs are available. At least Debian distributions are planned to get a package.
```bash
pip install pyduin
```
### As python module

After installation the `pyduin` module can be imported.
```python
from pyduin import arduino

Arduino = arduino.Arduino(model='nano', tty='/dev/ttyUSB0', pinfile='~/.pyduin/pinfiles/nano.yml', 'baudrate'=115200)
firmware_version = Arduino.get_firmware_version()
Arduino.Pins[13].set_mode('OUTPUT')
Arduino.Pins[13].high()
free_mem = Arduino.get_free_memory()
```
### Using the CLI

The first operation to use would be to install the needed dependencies in `~/.pyduin/`. The following command creates `~/.pyduin.yml` if it does not exist, downloads the arduino IDE defined in `~/pyduin.yml`, and also downloads the librariese defined in `~./pyduin.yml`.

```
arduino_cli.py --install-dependencies
```

To connect to an arduino, it is necessary to specify the `baudrate`, `tty`, `model` and `pinfile` arguments. Since there are some defaults set (see: `arduino_cli.py --help`), only differing arguments need to be specified. The following call shows the default values for `baudrate` and `tty` ommited, but `pinfile` and `model` present. This means that implicitly `/dev/ttyUSB0` will be used and the connection speed will be `115200` baud.

```
arduino_cli.py --model nano --pin 4 --action high
```

#### The buddy list

The buddy-list feature allows one to define buddies. Here the same defaults apply as when invoked from command line. Thus only differences need to be specified.

```yaml
buddies:
  uber:
    model: nano
    flavour: atmega328
    tty: /dev/uber
    pinfile: ~/.pyduin/uber_pins.yml
    ino: ~/arduino-sketchbook/uber/uber.ino
```

#### Flashing firmware to the arduino

Then the buddies can be addressed with the `-B` option. The following example would build the `.ino` file from the example above and flash it to the arduino. **Note: `model` and `flavour` are mandatory for --flash**
```
arduino_cli.py --buddy uber --flash
```
It can also be done without the buddy list.
```
arduino_cli.py --model nano --flavour atmega328 --flash --ino ~/inodev/devel.ino
```

If the `ino` option is ommitted, then the project firmware gets applied.

#### Control the arduinos pins

This feature is more to test pins than to be used in real applications. Opening a serial connection **resets most arduinos** unless there are hardware modifications applied. Currently not all operations are fully supported.
```
arduino_cli.py --buddy uber --pin 4 --action high
```
#### Get firmware version from the arduino

```
arduino_cli.py --buddy uber --action version
```
