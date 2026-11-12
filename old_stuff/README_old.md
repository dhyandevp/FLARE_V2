# FLARE V2 — local website + app (no Blynk)

```
 ESP32 ──Wi-Fi──┬── Laptop browser : http://<ESP32-IP>  or  http://flare.local
                └── Android app    : type <ESP32-IP> → Connect
 (all three on the SAME Wi-Fi / hotspot, no internet or cloud needed)
```

## Folders
| Folder | What |
|---|---|
| `FLARE_V2_ESP32_Local/` | ESP32 sketch. Website is built into it (`dashboard_html.h`) |
| `FLARE_V2_Website/index.html` | Same dashboard as a file. Double-click it on the laptop, type the IP |
| `FLARE_V2/` (Android Studio) | App: `MainActivity.kt` + `assets/dashboard.html` |
| `backup_before_local/` | Your old MainActivity.kt + activity_main.xml |

## 1. ESP32
1. Arduino IDE → open `FLARE_V2_ESP32_Local/FLARE_V2_ESP32_Local.ino`
2. Library Manager: **WebSockets** by Markus Sattler. Blynk + ArduinoJson are no longer needed.
3. Set `WIFI_SSID` / `WIFI_PASS`
4. Board: ESP32 Dev Module → Upload → Serial Monitor 115200 → copy the IP

Wiring is unchanged: TRIG 5, ECHO 18, RAIN 34, SOIL 35.
Alert limits (`FLOOD_LIMIT`, `RAIN_LIMIT`, `SOIL_LIMIT`) are set ONLY in the sketch. The website and app read them from the ESP32.

## 2. Website (laptop)
Open `http://<ESP32-IP>` in Chrome/Edge. `http://flare.local` also works on Windows 10/11.
- Sound alarm: click anywhere on the page once (browsers block sound until you click).

## 3. App (phone)
Android Studio → open `FLARE_V2` → Run. Type the ESP32 IP → **Connect**. The app remembers the IP and reconnects automatically.

## Editing the design
Edit `dashboard.html`, then copy it to:
- `FLARE_V2/app/src/main/assets/dashboard.html` (app)
- `FLARE_V2_Website/index.html` (file version)
- Regenerate the ESP32 header: `python make_header.py`

## Data format (ws://IP:81)
```json
{"t":"live","water":45,"rain":12,"soil":30,"risk":31,"h":1,"lim":[70,60,80],"rssi":-55,"up":1234,"ip":"192.168.43.120","cl":2}
{"t":"history","items":[[w,r,s,risk,ageSeconds], ...]}
```
`-1` = sensor not reading. `h:1` = this reading was also saved as a history bar (every 10 s).
