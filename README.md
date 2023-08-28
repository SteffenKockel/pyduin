# pyduin

A Python wrapper for Arduino and other IOT devices such as ESP. It aims to support everything, that platformio supports. It consists of two parts

* A python library
* A commandline interface
* A firmware to be loaded onto the device

### What for?

To interact seamless with an Arduino or other IOT device from within Python. Once a device has the correct firmware applied, one can set pin modes, pin states, pwm values and more.

This makes it easy to wire a sensor to an IOT device, connect it to a computer and start working with the sensor values in Python. The library supports:

- Analog read and write (wip)
- Digital read and write
- OneWire
- DHT Sensors
- SPI
- ...

### Device support

In theory, any device supported by [platformio](https://platformio.org/) can work. Currently, the following devices are supported

* Arduino Uno
* Arduino Nano

## Installation

### pyduin module

Only `pip` installs are available.

```bash
pip install pyduin
```

### Dependency socat

To make meaningful use of the CLI features, the installation and usage of `soact` is recommendet. To activate usage, edit `~/.pyduin.yml` and set `use_socat` to `yes` (default).
```yaml
serial:
  use_socat: yes
```
If `socat` is installed, a proxy will be started for every device that connections are made to. The pins get set up accordint to the pinfile and the inital modes get set on first conect. The following connections **will not reset the arduino**. The proxy will stop safely on device disconnect. The proxy will also be stopped for flashing.

## Usage

## As python module

After installation the `pyduin` module can be imported.
```python
from pyduin import arduino

Arduino = arduino.Arduino(model='nano', tty='/dev/ttyUSB0', pinfile='~/.pyduin/pinfiles/nano.yml', baudrate=115200)
firmware_version = Arduino.get_firmware_version()
Arduino.Pins[13].set_mode('OUTPUT')
Arduino.Pins[13].high()
free_mem = Arduino.get_free_memory()
```
## CLI

The following command turns on the onboard LED on an Arduino Nano
```
pyduin -t /dev/ttyUSB0 --board nanoatmega328 pin 13 high 
```

To connect to a device, it is necessary to specify the `baudrate`, `tty` and `model`(board) arguments. Since there are some defaults set (see: `pyduin --help`), only differing arguments need to be specified. The following call shows the default values for `baudrate` and `tty` ommited, but `pinfile` and `model` present. This means that implicitly `/dev/ttyUSB0` will be used and the connection speed will be `115200` baud.

#### The buddy list

The buddy-list feature allows one to define buddies. Here the same defaults apply as when invoked from command line. Thus only differences need to be specified.

```yaml
buddies:
  uber:
    board: nanoatmega328 # as in platformio
    tty: /dev/uber
    pinfile: ~/nanoatmega328_pins_dev.yml # optional 
    ino: ~/arduino-sketchbook/uber/uber.ino # optional
```

```
pyduin -B uber pin 13 high
```
## 

#### Flashing firmware to the Arduino

Then the buddies can be addressed with the `-B` option. The following example would build the `.ino` file from the example above and flash it to the Arduino. 
```
pyduin -B uber flash
```
It can also be done without the buddy list.
```
pyduin --board nanoatmega328 --tty=/dev/mytty flash
```

If the `--firmware` option is omitted, then the project firmware gets applied.

#### Control the arduinos pins

Opening a serial connection **resets most Arduinos**. `pyduin` circumvents this drawback with a `socat` proxy. Also another variant (`hupcl:off`) is in the pipeline. The difference is, that `socat` will set all pin modes on startup while the `hupcl` approach will require the user to set the pin mode manually. The big plus of the `hupcl` approach independence of third party applications.
```
pyduin --buddy uber pin 4 {high|low}
```
Also the pin mode can be set
```
pyduin -B uber pin 4 mode {input|ouput|input_pullup,pwm}
```
#### Get firmware version from the Arduino

```
pyduin --buddy uber firmware
```
#### Get free memory from the Arduino

```
pyduin --buddy uber free
```

## Contribute

```
mkdir pyduindev && cd !$
git git@github.com:SteffenKockel/pyduin.git
virtualenv .
. bin/activate
pip install -e .
```

### Add device

Adding a device works, by editing the `~/.pyduin/platformio.ini` and and provide a `pinfile`. These files and folders gets created, when attempting to flash firmware. Changes made here are preserved. A device must also provide a [pinfile]('/src/pyduin/data/pinfiles'). The name of the pinfile should have the name of the corresponding board name (as in platformio).
When developing, the pinfile can just be added in the repo structure. To test a pinfile while not in development mode, the `-p` option can be used.
