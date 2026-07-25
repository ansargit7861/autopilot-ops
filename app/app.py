"""
AutoPilot Ops - Demo Application
A minimal service used to demonstrate the CI/CD + self-healing pipeline.
The /simulate-crash and /simulate-load endpoints exist purely to trigger
alerts so the auto-remediation bot has something real to react to.
"""

import os
import time
import random
from flask import Flask, jsonify

app = Flask(__name__)

START_TIME = time.time()
VERSION = os.environ.get("APP_VERSION", "1.0.0")


@app.route("/")
def home():
    return jsonify({
        "service": "autopilot-ops-demo",
        "version": VERSION,
        "uptime_seconds": round(time.time() - START_TIME, 2)
    })


@app.route("/health")
def health():
    return jsonify({"status": "healthy"}), 200


@app.route("/ready")
def ready():
    return jsonify({"status": "ready"}), 200


@app.route("/simulate-crash")
def simulate_crash():
    """Intentionally kills the process to trigger a CrashLoopBackOff,
    so the remediation bot can detect and auto-restart it."""
    os._exit(1)


@app.route("/simulate-load")
def simulate_load():
    """Burns CPU for a few seconds to trigger HPA scaling / high-CPU alerts."""
    end = time.time() + 5
    x = 0
    while time.time() < end:
        x += random.random() ** 2
    return jsonify({"status": "load generated", "result": x})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
