FLARE V2 — Local laptop website + existing Blynk cloud

FILES
- app.py: local Flask server; keeps the Blynk token out of browser JavaScript
- templates/index.html: dashboard website
- FLARE_V2_Blynk_ESP32.ino: example ESP32 publisher code
- requirements.txt: Python dependencies

A. BLYNK SETUP
1. In Blynk Console, open the template/device used by your ESP32.
2. Create (or confirm) three Integer datastreams:
   V0 Water level (%), minimum 0, maximum 100
   V1 Rain intensity (%), minimum 0, maximum 100
   V2 Soil moisture (%), minimum 0, maximum 100
3. If your current firmware already uses different virtual pins, change PINS in app.py
   and the matching Blynk.virtualWrite pins in your ESP32 code.
4. Copy your Device Auth Token from the device's Device Info. Do not share it publicly.

B. ESP32 CODE
1. Open FLARE_V2_Blynk_ESP32.ino in Arduino IDE.
2. Install the "Blynk" library from Library Manager and install/select your ESP32 board.
3. Replace the template ID, Wi-Fi name/password and Blynk device auth token.
4. Check the calibration values near the top against your actual sensor readings.
5. Keep the HC-SR04 ECHO voltage divider between ECHO and GPIO18. Do not connect 5V ECHO directly to ESP32.
6. Upload and open Serial Monitor at 115200 baud. Confirm the device is online in Blynk.

C. LAPTOP WEBSITE
1. Install Python 3 if it is not already installed.
2. Open Command Prompt in this folder.
3. Run: py -m pip install -r requirements.txt
4. In app.py, replace PASTE_YOUR_BLYNK_DEVICE_AUTH_TOKEN_HERE with the same device token.
   Keep app.py private; it contains a credential. The token is not sent to the browser.
5. Run: py app.py
6. Open http://127.0.0.1:5000 in your laptop browser.
7. Keep the Command Prompt open while presenting. The ESP32 and laptop both need internet access.

TROUBLESHOOTING
- Invalid token: recopy the Device Auth Token from the correct Blynk device.
- No datastream for V0/V1/V2: create the datastreams or update the pin mappings.
- Old/stale values: confirm ESP32 is online and publishing to the same device/template.
- Website says it cannot reach Blynk: check laptop internet and firewall.
- Percentages look wrong: use Serial Monitor to record raw ADC values in dry/wet conditions and update calibration.
- If your existing firmware already works, you can keep it and only ensure it publishes 0–100 values to V0, V1 and V2; you do not have to replace it with the example sketch.

DEMO SAFETY
The thresholds on the website are illustrative. Soil moisture, rain and a small ultrasonic water-level prototype cannot reliably predict real floods or landslides. Describe the result as a prototype risk indication and follow official alerts.
