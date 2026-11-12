
from flask import Flask, jsonify, render_template
import os
import requests

app = Flask(__name__)

# FLARE V2 - Blynk Configuration
# Keep your device auth token private.
BLYNK_AUTH_TOKEN = os.environ.get(
    "BLYNK_AUTH_TOKEN",
    "5Mmz6YSGF-sQjRBwEnoqylV29exi-V6z"
)

BLYNK_TEMPLATE_ID = "TMPL3y80x7H5T"
BLYNK_BASE_URL = "https://blynk.cloud/external/api/get"

# Blynk virtual pin mapping
PINS = {
    "water": "v0",
    "rain": "v1",
    "soil": "v2",
}


def read_blynk_pin(pin):
    """Read one datastream value from Blynk Cloud."""
    response = requests.get(
        BLYNK_BASE_URL,
        params={
            "token": BLYNK_AUTH_TOKEN,
            pin: ""
        },
        timeout=8
    )

    response.raise_for_status()
    value = response.text.strip()

    try:
        return float(value)
    except ValueError:
        raise RuntimeError(
            f"Blynk returned an unexpected value for {pin}: {value}"
        )


def calculate_risk(water, rain, soil):
    """Calculate a provisional demonstration risk score."""
    values = [water, rain, soil]

    if not all(0 <= value <= 100 for value in values):
        raise ValueError(
            "Sensor readings must be between 0 and 100."
        )

    # Provisional demonstration weights, not validated predictions.
    score = round(
        (0.40 * water) +
        (0.30 * soil) +
        (0.30 * rain),
        1
    )

    if water >= 90 or score >= 80:
        status = 3
        label = "CRITICAL"
    elif score >= 60:
        status = 2
        label = "POTENTIAL THREAT"
    elif score >= 40:
        status = 1
        label = "CAUTION"
    else:
        status = 0
        label = "NORMAL"

    return {
        "risk_score": score,
        "threat_status": status,
        "threat_label": label
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/readings")
def readings():
    if (
        not BLYNK_AUTH_TOKEN
        or BLYNK_AUTH_TOKEN == "YOUR_DEVICE_AUTH_TOKEN"
    ):
        return jsonify({
            "ok": False,
            "error": (
                "Configure your Blynk Device Auth Token "
                "before requesting readings."
            )
        }), 503

    try:
        data = {
            name: read_blynk_pin(pin)
            for name, pin in PINS.items()
        }

        risk = calculate_risk(
            water=data["water"],
            rain=data["rain"],
            soil=data["soil"]
        )

        return jsonify({
            "ok": True,
            "readings": data,
            "risk": risk,
            "template_id": BLYNK_TEMPLATE_ID
        })

    except requests.HTTPError as exc:
        app.logger.warning("Blynk HTTP error: %s", exc)
        return jsonify({
            "ok": False,
            "error": (
                "Blynk rejected the request. Check the device "
                "auth token, device status, and datastream pins."
            )
        }), 502

    except requests.RequestException as exc:
        app.logger.warning("Blynk connection error: %s", exc)
        return jsonify({
            "ok": False,
            "error": (
                "Could not reach Blynk Cloud. Check your internet "
                "connection and Blynk configuration."
            )
        }), 502

    except (RuntimeError, ValueError) as exc:
        return jsonify({
            "ok": False,
            "error": str(exc)
        }), 502

    except Exception:
        app.logger.exception("Unexpected FLARE server error")
        return jsonify({
            "ok": False,
            "error": "Unexpected server error. Check the terminal."
        }), 500


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
