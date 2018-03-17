#include <DHT.h>
#include <string.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <MemoryFree.h>


// command
//String s;

// command (byte 1)
// a - readActor
// A - writeActor
// s - readSensor
// w - readOneWire
// W - writeOneWire
// c - readI2C
// C - writeI2C
// R - Reset device
// m - get pin mode
// M - set pin mode
// z - system commands
//
// Type (byte 2)
// A - Analog pin
// D - Digital Pin
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
String firmware_version = "0.2";
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
int pwmPins[6] = {3,5,6,9,10,11};
int analogPins[8] = {14,15,16,17,18,19,20,21};
int digitalPins[14] = {0,1,3,4,5,6,7,8,9,10,11,12,13};
String tmp;
String pin;
String val;
//              1 2     3     4 5        6 7 8       9
// input format < A|a|s A|D   0-21|A0-A6 001|000|255 >
//                0     1     2 3        4 5 6       7
unsigned long CurrTime;
unsigned long LastTime = 0;


int getPinMode(uint8_t pin)
{
  if (pin >= NUM_DIGITAL_PINS) return (-1);

  uint8_t bit = digitalPinToBitMask(pin);
  uint8_t port = digitalPinToPort(pin);
  volatile uint8_t *reg = portModeRegister(port);
  if (*reg & bit) return (OUTPUT);

  volatile uint8_t *out = portOutputRegister(port);
  return ((*out & bit) ? INPUT_PULLUP : INPUT);
}


void setup() {

  Serial.begin(115200);
  Serial.println("Boot complete");
}


void invalid_command(String S){
  Serial.print("Invalid command:");
  Serial.println(S);
}


void analog_actor_sensor(char c, char t, String tmp, int p, int v) {

  switch(t) {
    // analog actor/sensor
    case 'A':
      switch(c) {
        case 'a':
        case 's':
          // analog sensor/actor READ
          Serial.println(analogRead(p));
          break;
        case 'A':
          // analog sensor/actor (PWM) WRITE
          // Check, if we really have a PWM capable
          // pin here.
          for (int j = 0;j<6;j++) {
            if (pwmPins[j] == p) {
              analogWrite(p,v);
              Serial.println(analogRead(p));
            }
          }
          break;
        default:
          invalid_command(tmp);
          break;
        break;
      }
    // digital actor/sensor
    case 'D':
    // digital actor/sensor READ
      switch(c) {
        case 'a':
        case 's':
          Serial.println(digitalRead(p));
          break;
        case 'A':
          digitalWrite(p,v);
          // Serial.print(p);
          // Serial.println(v);
          Serial.println(digitalRead(p));
          break;
      }
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
  //myDallasTemperature->setResolution(OneWireAddr, 12);
  myDallasTemperature->requestTemperatures();
  Serial.print(v);
  Serial.print("%");
  Serial.println(myDallasTemperature->getTempCByIndex(v));
  delete myOneWire;
  delete myDallasTemperature;
}


void dhtsensor(int p, int v) {
  myDHT = new DHT(p, v);
  //delay(2000);
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


void pin_mode(char c, char t, int p) {

  switch(c) {
    //case 'm': //?
    // Serial.println(getPinMode(p));
    //break;
    case 'M':
    case 'm':
      switch(t) {
        // input
        case 'I':
          pinMode(p, INPUT);
          break;
        // pullup
        case 'P':
          pinMode(p, INPUT_PULLUP);
          break;
        // output
        case 'O':
          pinMode(p, OUTPUT);
          break;
    }
  }
  // reply actual state of this pin
  Serial.println(getPinMode(p));
}


void loop() {

  while (Serial.available() > 0) {
    i = Serial.read();
    if (i != '<') {
      //invalid_command(tmp);
      break;
      }
    tmp = Serial.readStringUntil('>');
    if (tmp.length()!=7) {
      invalid_command(tmp);
      break;
      }
    c = (char)tmp[0];
    t = (char)tmp[1];
    pin = tmp.substring(2,4);
    val = tmp.substring(4,7);
    Serial.print(arduino_id);
    Serial.print('%'); // 1
    p = pin.toInt();
    v = val.toInt();

    // only reply pin_number if a pin is involved
    if (c != 'z') {
      Serial.print(p);
      Serial.print("%"); // 2
    }

    switch(c) {
      // handle special commands
      case 'z':
        switch(t) {
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
      case 'a':
      case 's':
        analog_actor_sensor(c, t, tmp, p, v);
        break;
      // handle setPinMode
      case 'm':
      case 'M':
        pin_mode(c, t, p);
        break;
      case 'w':
      case 'W':
        // handle OneWire connections
        // DallasTemperature on OneWire
        onewire(p, v);
        break;
      case 'D':
        // handle dht sensors
        dhtsensor(p, v);
        break;
    } // main command switch
  } // pin type switch
} // while serial
 // loop

