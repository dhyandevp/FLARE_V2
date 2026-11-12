/************************************************************
 FLARE V2 - ESP32 + Blynk sensor publisher
 Sensors:
   HC-SR04 TRIG -> GPIO 5
   HC-SR04 ECHO -> GPIO 18 THROUGH A VOLTAGE DIVIDER
   Rain sensor AO -> GPIO 34
   Soil moisture sensor AO -> GPIO 35

 Blynk datastreams (Integer, min 0, max 100):
   V0 = water level percentage
   V1 = relative rain percentage
   V2 = relative soil moisture percentage

 IMPORTANT:
 - HC-SR04 ECHO can output 5V. ESP32 GPIO is NOT 5V tolerant.
   Keep the resistor voltage divider on ECHO.
 - Calibrate the dry/wet raw values for your own modules.
 - This is a demonstration prototype, not an official warning system.
************************************************************/

#define BLYNK_TEMPLATE_ID   "TMPL_REPLACE_WITH_YOUR_TEMPLATE_ID"
#define BLYNK_TEMPLATE_NAME "FLOOD MONITORING SYSTEM"
#define BLYNK_AUTH_TOKEN    "PASTE_YOUR_BLYNK_DEVICE_AUTH_TOKEN"

#include <WiFi.h>
#include <BlynkSimpleEsp32.h>

char ssid[] = "YOUR_WIFI_NAME";
char pass[] = "YOUR_WIFI_PASSWORD";

const int TRIG_PIN = 5;
const int ECHO_PIN = 18;
const int RAIN_PIN = 34;
const int SOIL_PIN = 35;

const float SENSOR_HEIGHT_CM = 20.0;

// Initial calibration values from the current FLARE prototype.
// Recheck with your own sensor and actual dry/wet tests.
const int RAIN_DRY_RAW = 3500;
const int RAIN_WET_RAW = 1200;
const int SOIL_DRY_RAW = 3000;
const int SOIL_WET_RAW = 1400;

BlynkTimer timer;

float clampPercent(float x) {
  if (x < 0) return 0;
  if (x > 100) return 100;
  return x;
}

float readDistanceCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(3);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  // 30 ms timeout; returns 0 if no echo is received.
  unsigned long duration = pulseIn(ECHO_PIN, HIGH, 30000UL);
  if (duration == 0) return -1;
  return duration * 0.0343f / 2.0f;
}

float readWaterPercent() {
  float distance = readDistanceCm();
  if (distance < 0 || distance > SENSOR_HEIGHT_CM + 5.0f) {
    return -1; // invalid reading; do not publish it
  }
  float pct = ((SENSOR_HEIGHT_CM - distance) / SENSOR_HEIGHT_CM) * 100.0f;
  return clampPercent(pct);
}

float readRainPercent() {
  int raw = analogRead(RAIN_PIN);
  // This sensor usually gives lower raw values when wet.
  float pct = (float)(RAIN_DRY_RAW - raw) * 100.0f /
              (float)(RAIN_DRY_RAW - RAIN_WET_RAW);
  return clampPercent(pct);
}

float readSoilPercent() {
  int raw = analogRead(SOIL_PIN);
  // This example assumes lower raw values mean wetter soil.
  float pct = (float)(SOIL_DRY_RAW - raw) * 100.0f /
              (float)(SOIL_DRY_RAW - SOIL_WET_RAW);
  return clampPercent(pct);
}

void sendReadings() {
  float water = readWaterPercent();
  float rain = readRainPercent();
  float soil = readSoilPercent();

  Serial.println("----- FLARE V2 -----");
  if (water >= 0) {
    Serial.printf("Water level: %.0f%%\n", water);
    Blynk.virtualWrite(V0, (int)roundf(water));
  } else {
    Serial.println("Water level: INVALID (check HC-SR04 wiring/target)");
  }

  Serial.printf("Rain: %.0f%%\n", rain);
  Serial.printf("Soil moisture: %.0f%%\n", soil);

  Blynk.virtualWrite(V1, (int)roundf(rain));
  Blynk.virtualWrite(V2, (int)roundf(soil));
}

void setup() {
  Serial.begin(115200);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  digitalWrite(TRIG_PIN, LOW);

  analogReadResolution(12); // ESP32 ADC: normally 0..4095

  Blynk.begin(BLYNK_AUTH_TOKEN, ssid, pass);

  // Read and publish every 3 seconds.
  timer.setInterval(3000L, sendReadings);
}

void loop() {
  Blynk.run();
  timer.run();
}
