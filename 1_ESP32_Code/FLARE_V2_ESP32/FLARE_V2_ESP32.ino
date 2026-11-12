/*
  ================================================================
   FLARE V2 - Flood & Landslide Monitor (LOCAL, NO BLYNK)
  ================================================================
   The ESP32 does everything itself:
     http://<ESP32-IP>/          -> dashboard website
     http://flare.local/         -> same (laptop, via mDNS)
     ws://<ESP32-IP>:81/         -> live data for website + Android app
     http://<ESP32-IP>/api/data  -> latest reading (JSON)
     http://<ESP32-IP>/api/history -> last 5 min (JSON)

   Libraries (Arduino IDE > Library Manager):
     - "WebSockets" by Markus Sattler   (you already have it)
   Built into the ESP32 core (nothing to install):
     - WiFi, WebServer, ESPmDNS

   Board: ESP32 Dev Module  |  Serial Monitor: 115200
  ================================================================
*/

#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <WebSocketsServer.h>
#include "dashboard_html.h"

// ================ WIFI SETTINGS =================
// ESP32, laptop and phone must be on this same network.
const char* WIFI_SSID = "YOUR_WIFI_OR_HOTSPOT_NAME";
const char* WIFI_PASS = "YOUR_WIFI_PASSWORD";
const char* HOSTNAME  = "flare";            // -> http://flare.local

// ================ SENSOR PINS ====================
const int TRIG_PIN = 5;
const int ECHO_PIN = 18;
const int RAIN_PIN = 34;
const int SOIL_PIN = 35;

// ================ WATER LEVEL ====================
const float SENSOR_HEIGHT_CM = 20.0;

// ================ CALIBRATION ====================
int rainDryRaw = 3500;
int rainWetRaw = 1200;

int soilDryRaw = 3000;
int soilWetRaw = 1400;

// ================ ALERT LIMITS (%) ===============
// Website + app read these from the ESP32, so change them only here.
const int FLOOD_LIMIT = 70;
const int RAIN_LIMIT  = 60;
const int SOIL_LIMIT  = 80;

// ================ TIMING / HISTORY ===============
const unsigned long READ_INTERVAL_MS = 2000;  // live update every 2 s
const uint8_t HISTORY_EVERY = 5;              // 5 x 2 s = 1 history bar / 10 s
const uint8_t HISTORY_SIZE  = 30;             // 30 bars = 5 minutes

// ================ SERVERS ========================
WebServer server(80);
WebSocketsServer webSocket(81);

// ================ STATE ==========================
struct Sample {
  int8_t water, rain, soil, risk;
  uint32_t ms;
};

Sample history[HISTORY_SIZE];
uint8_t historyCount = 0;
uint8_t historyHead = 0;
uint8_t readsSinceHistory = 0;

int latestWater = -1;
int latestRain = -1;
int latestSoil = -1;
int latestRisk = -1;
bool latestIsHistory = false;

bool floodWasActive = false;
bool rainWasActive = false;
bool soilWasActive = false;

unsigned long lastReadMs = 0;
unsigned long lastWifiCheckMs = 0;
bool wifiWasConnected = false;

// ================ ANALOG READING =================
int readAnalogAverage(int pin) {
  long total = 0;
  for (int i = 0; i < 10; i++) {
    total += analogRead(pin);
    delay(5);
  }
  return total / 10;
}

// ================ WATER DISTANCE =================
float readWaterDistanceCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(3);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  unsigned long duration = pulseIn(ECHO_PIN, HIGH, 30000UL);
  if (duration == 0) return -1.0;

  float distance = duration * 0.0343f / 2.0f;
  if (distance < 2.0f || distance > SENSOR_HEIGHT_CM) return -1.0;

  return distance;
}

// ================ WATER PERCENT ==================
int calculateWaterPercent(float distance) {
  if (distance < 0.0f || distance > SENSOR_HEIGHT_CM) return -1;

  float depth = SENSOR_HEIGHT_CM - distance;
  int percent = (int)(depth * 100.0f / SENSOR_HEIGHT_CM + 0.5f);
  return constrain(percent, 0, 100);
}

// ================ SENSOR PERCENT =================
int calculateSensorPercent(int raw, int dryRaw, int wetRaw) {
  if (dryRaw == wetRaw) return -1;

  float percent = 100.0f * (raw - dryRaw) / (float)(wetRaw - dryRaw);
  return constrain((int)(percent + 0.5f), 0, 100);
}

// ================ RISK SCORE =====================
// Same weighting the app used: water 40%, soil 30%, rain 30%
int calculateRisk(int water, int rain, int soil) {
  if (water < 0 || rain < 0 || soil < 0) return -1;
  float risk = water * 0.40f + soil * 0.30f + rain * 0.30f;
  return constrain((int)(risk + 0.5f), 0, 100);
}

// ================ SERIAL ALERTS ==================
void checkAlert(bool active, bool &previousState, const char *message) {
  if (active && !previousState) {
    Serial.print("ALERT: ");
    Serial.println(message);
  }
  previousState = active;
}

// ================ JSON BUILDERS ==================
// Live reading -> {"t":"live","water":45,...}
void buildLiveJson(char *buf, size_t size) {
  snprintf(
    buf, size,
    "{\"t\":\"live\",\"water\":%d,\"rain\":%d,\"soil\":%d,\"risk\":%d,"
    "\"h\":%d,\"lim\":[%d,%d,%d],\"rssi\":%d,\"up\":%lu,"
    "\"ip\":\"%s\",\"cl\":%d}",
    latestWater, latestRain, latestSoil, latestRisk,
    latestIsHistory ? 1 : 0,
    FLOOD_LIMIT, RAIN_LIMIT, SOIL_LIMIT,
    (int)WiFi.RSSI(),
    (unsigned long)(millis() / 1000UL),
    WiFi.localIP().toString().c_str(),
    (int)webSocket.connectedClients()
  );
}

// History -> {"t":"history","items":[[w,r,s,risk,ageSeconds],...]}
String buildHistoryJson() {
  String out;
  out.reserve(40 + historyCount * 28);
  out = "{\"t\":\"history\",\"items\":[";

  uint32_t now = millis();
  for (uint8_t i = 0; i < historyCount; i++) {
    uint8_t idx = (historyHead + HISTORY_SIZE - historyCount + i) % HISTORY_SIZE;
    const Sample &s = history[idx];

    if (i > 0) out += ",";
    out += "[";
    out += (int)s.water; out += ",";
    out += (int)s.rain;  out += ",";
    out += (int)s.soil;  out += ",";
    out += (int)s.risk;  out += ",";
    out += (now - s.ms) / 1000UL;
    out += "]";
  }

  out += "]}";
  return out;
}

void addHistorySample() {
  history[historyHead] = {
    (int8_t)latestWater, (int8_t)latestRain,
    (int8_t)latestSoil, (int8_t)latestRisk,
    (uint32_t)millis()
  };
  historyHead = (historyHead + 1) % HISTORY_SIZE;
  if (historyCount < HISTORY_SIZE) historyCount++;
}

// ================ WEBSOCKET EVENTS ===============
void webSocketEvent(uint8_t client, WStype_t type, uint8_t *payload, size_t length) {
  switch (type) {
    case WStype_CONNECTED: {
      Serial.printf("Client #%u connected (%s)\n", client,
                    webSocket.remoteIP(client).toString().c_str());

      // New viewer gets the last 5 minutes + the latest reading straight away
      String hist = buildHistoryJson();
      webSocket.sendTXT(client, hist);

      if (latestWater >= 0 || latestRain >= 0 || latestSoil >= 0) {
        char buf[260];
        bool wasHistory = latestIsHistory;
        latestIsHistory = false;          // don't add a duplicate bar
        buildLiveJson(buf, sizeof(buf));
        latestIsHistory = wasHistory;
        webSocket.sendTXT(client, buf);
      }
      break;
    }

    case WStype_DISCONNECTED:
      Serial.printf("Client #%u disconnected\n", client);
      break;

    case WStype_TEXT:
      // Nothing to receive yet (alarm handling is done in app/website)
      break;

    default:
      break;
  }
}

// ================ HTTP HANDLERS ==================
void handleRoot() {
  server.send_P(200, "text/html", DASHBOARD_HTML);
}

void handleApiData() {
  char buf[260];
  buildLiveJson(buf, sizeof(buf));
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.sendHeader("Cache-Control", "no-store");
  server.send(200, "application/json", buf);
}

void handleApiHistory() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.sendHeader("Cache-Control", "no-store");
  server.send(200, "application/json", buildHistoryJson());
}

void handleNotFound() {
  server.sendHeader("Location", "/");
  server.send(302, "text/plain", "");
}

// ================ SENSOR MONITORING ===============
void monitorSensors() {
  latestWater = calculateWaterPercent(readWaterDistanceCm());
  latestRain  = calculateSensorPercent(readAnalogAverage(RAIN_PIN), rainDryRaw, rainWetRaw);
  latestSoil  = calculateSensorPercent(readAnalogAverage(SOIL_PIN), soilDryRaw, soilWetRaw);
  latestRisk  = calculateRisk(latestWater, latestRain, latestSoil);

  // every HISTORY_EVERY readings -> one history bar
  readsSinceHistory++;
  latestIsHistory = false;
  if (readsSinceHistory >= HISTORY_EVERY) {
    readsSinceHistory = 0;
    addHistorySample();
    latestIsHistory = true;
  }

  Serial.printf("Water: %d%%  Rain: %d%%  Soil: %d%%  Risk: %d%%  Viewers: %d\n",
                latestWater, latestRain, latestSoil, latestRisk,
                (int)webSocket.connectedClients());

  if (latestWater >= 0) checkAlert(latestWater >= FLOOD_LIMIT, floodWasActive, "FLOOD WARNING: Water level is high!");
  if (latestRain  >= 0) checkAlert(latestRain  >= RAIN_LIMIT,  rainWasActive,  "RAIN ALERT: Rain sensor is wet.");
  if (latestSoil  >= 0) checkAlert(latestSoil  >= SOIL_LIMIT,  soilWasActive,  "SOIL ALERT: Soil moisture is high.");

  // Send to every connected website / app
  if (webSocket.connectedClients() > 0) {
    char buf[260];
    buildLiveJson(buf, sizeof(buf));
    webSocket.broadcastTXT(buf);
  }
}

// ================ WIFI ===========================
void printAddresses() {
  Serial.println();
  Serial.println("========================================");
  Serial.print  ("  Wi-Fi connected. ESP32 IP: ");
  Serial.println(WiFi.localIP());
  Serial.print  ("  Website : http://");
  Serial.println(WiFi.localIP());
  Serial.printf ("  Or      : http://%s.local\n", HOSTNAME);
  Serial.println("  App     : type the IP above, tap Connect");
  Serial.println("========================================");
}

void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.setHostname(HOSTNAME);
  WiFi.setSleep(false);            // faster, steadier WebSocket
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  Serial.print("Connecting to Wi-Fi");
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    if (millis() - start > 30000UL) {
      Serial.println("\nWi-Fi failed for 30 s - restarting ESP32");
      ESP.restart();
    }
  }
  wifiWasConnected = true;
  printAddresses();
}

void watchWiFi() {
  if (millis() - lastWifiCheckMs < 5000UL) return;
  lastWifiCheckMs = millis();

  bool connected = WiFi.status() == WL_CONNECTED;
  if (!connected && wifiWasConnected) {
    Serial.println("Wi-Fi lost - reconnecting...");
    WiFi.reconnect();
  }
  if (connected && !wifiWasConnected) printAddresses();
  wifiWasConnected = connected;
}

// ================ SETUP ==========================
void setup() {
  Serial.begin(115200);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(RAIN_PIN, INPUT);
  pinMode(SOIL_PIN, INPUT);
  digitalWrite(TRIG_PIN, LOW);
  analogReadResolution(12);

  Serial.println();
  Serial.println("FLARE V2 - local website + app (no Blynk)");

  connectWiFi();

  if (MDNS.begin(HOSTNAME)) {
    MDNS.addService("http", "tcp", 80);
    Serial.printf("mDNS started: http://%s.local\n", HOSTNAME);
  }

  server.on("/", handleRoot);
  server.on("/api/data", handleApiData);
  server.on("/api/history", handleApiHistory);
  server.onNotFound(handleNotFound);
  server.begin();
  Serial.println("Website started on port 80");

  webSocket.begin();
  webSocket.onEvent(webSocketEvent);
  Serial.println("WebSocket started on port 81");

  Serial.println("FLARE monitoring started!");
}

// ================ MAIN LOOP ======================
void loop() {
  server.handleClient();
  webSocket.loop();
  watchWiFi();

  if (millis() - lastReadMs >= READ_INTERVAL_MS) {
    lastReadMs = millis();
    monitorSensors();
  }
}
