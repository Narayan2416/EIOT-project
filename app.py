import math
import os
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request


history=[]

mean =[31.325, 54.575, 44.575]
scale= [ 5.90079444, 11.88357585, 11.88357585]

ROOT = Path(__file__).resolve().parents[1]
WEIGHTS_PATH = ROOT / "model_weights.txt"


def _parse_float(pattern: str, text: str) -> float:
    m = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    if not m:
        raise ValueError(f"Could not parse model weight with pattern: {pattern}")
    return float(m.group(1))


def load_weights() -> dict[str, float]:
    text = WEIGHTS_PATH.read_text(encoding="utf-8", errors="ignore")
    w1 = _parse_float(r"w1\s*\(temperature.*?\)\s*:\s*([-+]?\d+(?:\.\d+)?)", text)
    w2 = _parse_float(r"w2\s*\(humidity.*?\)\s*:\s*([-+]?\d+(?:\.\d+)?)", text)
    w3 = _parse_float(r"w3\s*\(soil.*?\)\s*:\s*([-+]?\d+(?:\.\d+)?)", text)
    b = _parse_float(r"bias\s*:\s*([-+]?\d+(?:\.\d+)?)", text)
    return {"w1": w1, "w2": w2, "w3": w3, "bias": b}


WEIGHTS = load_weights()


def sigmoid(z: float) -> float:
    # numerically stable sigmoid
    if z >= 0:
        ez = math.exp(-z)
        return 1.0 / (1.0 + ez)
    ez = math.exp(z)
    return ez / (1.0 + ez)


def predict_irrigation(temperature: float, humidity: float, soil: float) -> dict[str, Any]:
    z = WEIGHTS["w1"] * temperature + WEIGHTS["w2"] * humidity + WEIGHTS["w3"] * soil + WEIGHTS["bias"]
    prob = sigmoid(z)
    irrigate = prob > 0.5
    return {
        "temperature": float(temperature),
        "humidity": float(humidity),
        "soil": float(soil),
        "z": float(z),
        "probability": float(prob),
        "decision": "IRRIGATE_ON" if irrigate else "IRRIGATE_OFF",
        "irrigate": irrigate,
        "threshold": 0.5,
        "weights": WEIGHTS,
    }


@dataclass
class LastReading:
    received_at_unix: float
    source: str
    temperature: float
    humidity: float
    soil: float
    probability: float
    decision: str


LAST_READING: LastReading | None = None


app = Flask(__name__)


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "weights_loaded": True, "weights_path": str(WEIGHTS_PATH)})


@app.post("/api/predict")
def api_predict():
    payload = request.get_json(silent=True) or request.form or {}
    try:
        temperature = float(payload.get("temperature"))
        humidity = float(payload.get("humidity"))
        soil = float(payload.get("soil"))
        temperature = (temperature - mean[0]) / scale[0]
        humidity = (humidity - mean[1]) / scale[1]
        soil = (soil - mean[2]) / scale[2]
    except Exception:
        return jsonify({"ok": False, "error": "Send temperature, humidity, and soil (numbers)."}), 400

    result = predict_irrigation(temperature=temperature, humidity=humidity, soil=soil)
    return jsonify({"ok": True, "result": result})


@app.post("/api/esp32/reading")
def api_esp32_reading():
    """
    ESP32 posts JSON:
      { "temperature": 31.2, "humidity": 48.7, "device_id": "esp32-1" }
    """
    payload = request.get_json(silent=True) or {}
    try:
        temperature1 = float(payload.get("temperature"))
        humidity1 = float(payload.get("humidity"))
        soil1 = float(payload.get("soil"))
        temperature = (temperature1 - mean[0]) / scale[0]
        humidity = (humidity1 - mean[1]) / scale[1]
        soil = (soil1 - mean[2]) / scale[2]
    except Exception:
        return jsonify({"ok": False, "error": "JSON must include numeric temperature, humidity, and soil."}), 400

    device_id = str(payload.get("device_id") or "esp32")
    result = predict_irrigation(temperature=temperature, humidity=humidity, soil=soil)

    global LAST_READING
    
    res= LastReading(
        received_at_unix=time.time(),
        source=device_id,
        temperature=temperature1,
        humidity=humidity1,
        soil=soil1,
        probability=result["probability"],
        decision=result["decision"],
    )
    LAST_READING= res

    history.append(asdict(res))
    if len(history) > 20:
        history.pop(0)

    return jsonify({"ok": True, "result": result})


@app.get("/api/esp32/latest")
def api_esp32_latest():
    if LAST_READING is None:
        return jsonify({"ok": True, "latest": None})
    return jsonify({"ok": True, "latest": asdict(LAST_READING)})

@app.get("/api/esp32/history")
def api_esp32_history():
    return jsonify({"ok": True, "history": history})

def main():
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
