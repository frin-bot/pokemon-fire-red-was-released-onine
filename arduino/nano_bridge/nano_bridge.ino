#include <SoftwareSerial.h>

// Nano D10 receives from Micro TX1. Nano D11 transmits to Micro RX1.
const uint8_t MICRO_RX_PIN = 10;
const uint8_t MICRO_TX_PIN = 11;
const long BAUD_RATE = 57600;

SoftwareSerial microSerial(MICRO_RX_PIN, MICRO_TX_PIN);

void setup() {
  Serial.begin(BAUD_RATE);
  microSerial.begin(BAUD_RATE);
}

void loop() {
  while (Serial.available() > 0) {
    microSerial.write(Serial.read());
  }

  while (microSerial.available() > 0) {
    Serial.write(microSerial.read());
  }
}

