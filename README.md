# pyduin 0.2

## What?

A pyhton wrapper for arduino. It consists of two parts

* A python library for arduino, pin, pinmode
* An arduino firmware

## What for?

To interact seamless with an arduino from within python. Once an arduino has the correct firmware applied, one can set pin modes, pin states, pwm values and more.

## Is it usable?

Yes it is. But it is ~~neither packaged~~ nor well documented. Working on a usable release.

## How

At the moment, only pip installs are available. At least Debian distributions are planned to get a package.

```
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
free_mem = Arduino.get_free_mempry()
```

### Using the CLI

Whenever the CLI is invoked, it checks for a user config dir `~/.pyduin` and a user config file in `~/.pyduin.yml`. If the directory is not present, it will get created. If the configfile does not exist, it will be created. The configuration file then can be used as a starting point. Especially the buddy-list may be an interesting feature. It is intended to arduino(s) or classes of devices to make interaction with the target device even more seamless.

To connect to an arduino, it is necessary to specify the `baudrate`, `tty`, `model` and `pinfile` arguments. Since there are some defaults set (`--help`), only differing arguments need to be specified. The following call shows the default values for `baudrate` and `tty` ommited, but `pinfile` and `model` present. This means that implicitly `/dev/ttyUSB0` will be used and the connection speed will be `115200` baud.

```
arduino_cli.py --model nano --pinfile ~/test-pinfile.yml
```

The buddy-list allows to define some buddies. Here the same defaults apply and only differences need to be specified.

```yaml
buddies:
  uber:
    tty: /dev/uber
    pinfile: ~/.pyduin/uber_pins.yml
    ino: ~/arduino-sketchbook/uber/uber.ino
```
Then the buddies can be addressed with the `-B` option. The following example would build the `.ino` file from the example above and flash it to the arduino.
```
arduino_cli.py --buddy uber --flash
```
If the `ino` option is ommitted, then the project firmware gets applied. The script downloads an arduino IDE, extracts it to `~/.pyduin/ide/VERSION/arduino-VERSION/` and uses this ide to compile and upload the file to the arduino. A `Makefile` and the `ino` file get copied to `/tmp/.pyduin` and then `make` is run via subrocess.

#### Control the arduinos pins

This feature is more to test pins than to be used in real applications. Opening a serial connection **resets most arduinos** unless there are hardware modifications applied. Currently not all operations are fully supported.
```
arduino_cli.py --buddy uber --pin 4 --action high
```

#### Get firmware version from the arduino
```
arduino_cli.py --buddy uber --action version
```
