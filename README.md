# pyduin 0.5.1.dev

## What?

A pyhton wrapper for Arduino and other IOT devices such as ESP. It aims to support everything, that platformio supports. It consists of two parts

* A python library for arduino, pin, pinmode
* A firmware to be loaded onto the device

### What for?

To interact seamless with an Arduino from within python. Once an Arduino has the correct firmware applied, one can set pin modes, pin states, pwm values and more. It can

This makes it easy to wire a sensor to an IOT device, connect it to the computer and start working with the sensor values in Python. The library supports:

- Analog read and write
- Digital read and write
- OneWire
- 
### Installation

Only `pip` installs are available.

```bash
pip install pyduin
```

## Usage

## As python module

After installation the `pyduin` module can be imported.
```python
from pyduin import arduino

Arduino = arduino.Arduino(model='nano', tty='/dev/ttyUSB0', pinfile='~/.pyduin/pinfiles/nano.yml', 'baudrate'=115200)
firmware_version = Arduino.get_firmware_version()
Arduino.Pins[13].set_mode('OUTPUT')
Arduino.Pins[13].high()
free_mem = Arduino.get_free_memory()
```
## CLI

The first operation to use would be to install the needed dependencies in `~/.pyduin/`. The following command creates `~/.pyduin.yml` if it does not exist, downloads the arduino IDE defined in `~/pyduin.yml`, and also downloads the libraries defined in `~./pyduin.yml`.

```
arduino_cli.py --install-dependencies
```
This works also in combination with the `version` switch.
```
arduino_cli.py --install-dependencies --version=1.6.5-r5
```
This currently does not install `socat`. To make meaningful use of the CLI features, the installation and usage of `soact` is recommendet. To activate usage, edit `~/.pyduin.yml` and set `use_socat` to `yes` (default).
```yaml
serial:
  use_socat: yes
```
If `socat` is installed, a proxy will be started for every device that connections are made to. The pins get set up accordint to the pinfile and the inital modes get set on first conect. The following connections **will not reset the arduino**. The proxy will stop safely on device disconnect. The proxy will also be stopped for flashing.

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

Opening a serial connection **resets most arduinos**. `pyduin` circumvents this drawback with a `socat` proxy. Also another variant (`hupcl:off`) is in the pipeline. The difference is, that `socat` will set all pin modes on startup while the `hupcl` approach will require the user to set the pin mode manually. The big plus of the `hupcl` approach independence of third party applications.
```
arduino_cli.py --buddy uber --pin 4 --action high
```
Also the pin mode can be set
```
arduino_cli.py --buddy uber --pin 4 --action mode --mode input
```
#### Get firmware version from the arduino

```
arduino_cli.py --buddy uber --action version
```
#### Get free memory from the arduino

```
arduino_cli.py --buddy uber --action free
```
