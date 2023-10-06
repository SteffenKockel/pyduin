// Copyright 2023 Steffen Kockel info@steffen-kockel.de
// License MIT
{{ extra_libs }}
#include <DHT.h>
#include <string.h>
#include <OneWire.h>
#include <Wire.h>
#include <DallasTemperature.h>
#include <MemoryFree.h>


// command
// String s;


// command (byte 1)
// A | D - native pins
// M - set pin mode
// z - system commands
//
// Type (byte 2)
// R - Read
// W - Write
//
// z - memory usage
// v - version
// Pin (byte 3,4)
// 01-13 - digital pins
// A0-A7 (14-21) - analog pins
//
// Value (byte 5,6,7)
// 0-255 - for pwm enabled pins
// 000-001 for digital pins in INPUT/INPUT_PULLUP/OUTPUT


DHT *myDHT = NULL;
OneWire *myOneWire = NULL;
DallasTemperature *myDallasTemperature = NULL;
DeviceAddress OneWireAddr;

// firmware version
String firmware_version = "0.7.0";
// arduino id
int arduino_id = 0;
// command
char c;
// pin type
char t;
// pin
int p;
// value
int v;
// input
int i;
// temp
int pwmPins[{{ num_pwm_pins }}] = {{ pwm_pins }};
int num_pwm_Pins = {{ num_pwm_pins }};
// int analogPins[{{ num_analog_pins }}] = {{ analog_pins }};
// int num_analog_pins = {{ num_analog_pins }};
// int digitalPins[{{ num_digital_pins }}] = {{ digital_pins }};
// int num_digital_pins = {{ num_digital_pins }};
// int physical_pin_ids[{{ num_physical_pins }}] = {{ physical_pins }};
// int min_pin = {{ min_pin }}
// int max_pin = {{ max_pin }}
String tmp;
String pin;
String val;
//              1 2     3     4 5        6 7 8       9
// input format < A|a|s A|D   0-21|A0-A6 001|000|255 >
//                0     1     2 3        4 5 6       7


int getPinMode(uint8_t pin) {
  // if (pin >= physical_pin_ids) return (-1);
  // if (std::find(std::begin()))

  uint8_t bit = digitalPinToBitMask(pin);
  uint8_t port = digitalPinToPort(pin);
  volatile uint8_t *reg = portModeRegister(port);
  if (*reg & bit) return (OUTPUT);

  volatile uint8_t *out = portOutputRegister(port);
  return ((*out & bit) ? INPUT_PULLUP : INPUT);
}


void setup() {
  Serial.begin({{ baudrate }});
  Serial.println("Boot complete");
}


void invalid_command(String S) {
  Serial.print("Invalid command:");
  Serial.println(S);
}


void pwm(int p, int v) {
  // analog sensor/actor (PWM) WRITE
  // Check, if we really have a PWM capable
  // pin here.
  for (int j = 0; j < num_pwm_Pins; j++) {
    if (pwmPins[j] == p) {
      analogWrite(p, v);
      Serial.println(v);
    }
  }
}

void analog_actor_sensor(char c, char t, String tmp, int p, int v) {
  switch (c) {
    // analog actor/sensor
    case 'A':
      switch (t) {
        case 'R':
          // analog sensor/actor READ
          Serial.println(analogRead(p));
          break;
        case 'W':
          pwm(p, v);
          Serial.println(v);
          break;
      }
        break;
      // digital actor/sensor
    case 'D':
    // digital actor/sensor READ
      switch (c) {
        case 'R':
          Serial.println(digitalRead(p));
          break;
        case 'W':
          digitalWrite(p, v);
          // Serial.print(p);
          // Serial.println(v);
          Serial.println(digitalRead(p));
          break;
      }
      break;
  }
}


void onewire(int p, int v) {
  myOneWire = new OneWire(p);
  delay(200);
  // @FIXME: Make this dynamic - we are doing OneWire here!
  myDallasTemperature = new DallasTemperature(myOneWire);
  myDallasTemperature->getAddress(OneWireAddr, v);
  // @FIXME: Make this dynamic (resolution)
  myDallasTemperature->setResolution(OneWireAddr, 9);
  // myDallasTemperature->setResolution(OneWireAddr, 12);
  myDallasTemperature->requestTemperatures();
  Serial.print(v);
  Serial.print("%");
  Serial.println(myDallasTemperature->getTempCByIndex(v));
  delete myOneWire;
  delete myDallasTemperature;
}


void dhtsensor(int p, int v) {
  myDHT = new DHT(p, v);
  // delay(2000);
  // Reading temperature or humidity takes about 250 milliseconds!
  // Sensor readings may also be up to 2 seconds 'old' (its a very slow sensor)
  float hum = myDHT->readHumidity();
  // Read temperature as Celsius (the default)
  float temp = myDHT->readTemperature();
  // Check if any reads failed and exit early (to try again).
  if (isnan(hum) || isnan(temp)) {
    Serial.println("Failed to read from DHT sensor!");
    delete myDHT;
    return;
  }
  Serial.print(hum);
  Serial.print(":");
  Serial.println(temp);
  delete myDHT;
}


void pin_mode(char t, int p) {
  switch (t) {
    // input
    case 'I':
      pinMode(p, INPUT);
      Serial.println(INPUT);
      break;
    // pullup
    case 'P':
      pinMode(p, INPUT_PULLUP);
      Serial.println(INPUT_PULLUP);
      break;
    // output
    case 'O':
      pinMode(p, OUTPUT);
      Serial.println(OUTPUT);
      break;
    case 'R':
      Serial.println(getPinMode(p));
      break;
  }
}


void loop() {
  while (Serial.available() > 0) {
    i = Serial.read();
    if (i != '<') {
      // invalid_command(tmp);
      break;
    }
    tmp = Serial.readStringUntil('>');
    if (tmp.length() != 7) {
      invalid_command(tmp);
      break;
      }
    c = static_cast<char>(tmp[0]);
    t = static_cast<char>(tmp[1]);
    pin = tmp.substring(2, 4);
    val = tmp.substring(4, 7);
    Serial.print(arduino_id);
    Serial.print('%');  // 1
    p = pin.toInt();
    v = val.toInt();

    // only reply pin_number if a pin is involved
    if (c != 'z') {
      Serial.print(p);
      Serial.print("%");  // 2
    }

    switch (c) {
      // handle special commands
      case 'z':
        switch (t) {
          case 'z':
            Serial.print("free_mem");
            Serial.print("%");
            Serial.println(freeMemory());
            break;
          case 'v':
            Serial.print("version");
            Serial.print("%");
            Serial.println(firmware_version);
        }
        break;
      // handle native analog and digital pins
      case 'A':
      case 'D':
        analog_actor_sensor(c, t, tmp, p, v);
        break;
      // handle setPinMode
      case 'M':
        pin_mode(t, p);
        break;
      case 'w':
      case 'W':
        // handle OneWire connections
        // DallasTemperature on OneWire
        onewire(p, v);
        break;
      case 'S':
        // handle sensors
        dhtsensor(p, v);
        break;
    }  // main command switch
  }  // pin type switch
}  // while serial
  // loop
