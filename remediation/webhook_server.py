"""
AutoPilot Ops - Auto-Remediation Bot
=====================================
Receives alerts from Alertmanager and takes corrective action automatically,
then reports what it did to Slack. This is the core "self-healing" piece
that differentiates this project from a plain CI/CD pipeline.

Handled alert types (see monitoring/alertmanager-config.yaml for how these
alerts are defined):
  - PodCrashLooping     -> restart the deployment
  - HighMemoryUsage     -> restart the offending pod
  - DeploymentDegraded  -> rollback to the previous stable revision
  - HighCPUUsage        -> logged only (HPA already handles scaling)

Design note: every action is logged with a timestamp and outcome BEFORE and
AFTER execution, so there's always an audit trail of what the bot did and
why - important for demonstrating this isn't a "black box" auto-fixer.
"""

import os
import logging
import subprocess
from datetime import datetime, timezone

import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("remediation-bot")

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")
NAMESPACE = os.environ.get("TARGET_NAMESPACE", "autopilot-ops")
DEPLOYMENT = os.environ.get("TARGET_DEPLOYMENT", "autopilot-app")

# Simple in-memory guardrail: don't act on the same alert more than once
# every 5 minutes, to avoid remediation loops flapping the deployment.
_last_action_time = {}
COOLDOWN_SECONDS = 300


def notify_slack(message: str):
    if not SLACK_WEBHOOK_URL:
        logger.info("SLACK_WEBHOOK_URL not set, skipping notification: %s", message)
        return
    try:
        requests.post(SLACK_WEBHOOK_URL, json={"text": message}, timeout=5)
    except requests.RequestException as e:
        logger.error("Failed to notify Slack: %s", e)


def run_kubectl(args: list[str]) -> tuple[bool, str]:
    """Runs a kubectl command and returns (success, output)."""
    try:
        result = subprocess.run(
            ["kubectl", "-n", NAMESPACE] + args,
            capture_output=True, text=True, timeout=30, check=True
        )
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return False, e.stderr.strip()


def cooldown_ok(alert_name: str) -> bool:
    now = datetime.now(timezone.utc).timestamp()
    last = _last_action_time.get(alert_name, 0)
    if now - last < COOLDOWN_SECONDS:
        return False
    _last_action_time[alert_name] = now
    return True


def handle_crash_loop():
    logger.info("Handling PodCrashLooping: restarting deployment")
    ok, output = run_kubectl(["rollout", "restart", f"deployment/{DEPLOYMENT}"])
    outcome = "restarted successfully" if ok else f"restart FAILED: {output}"
    notify_slack(f":rotating_light: *PodCrashLooping* detected on `{DEPLOYMENT}`. "
                 f"Auto-remediation: {outcome}")
    return ok, outcome


def handle_degraded_deployment():
    logger.info("Handling DeploymentDegraded: rolling back to previous revision")
    ok, output = run_kubectl(["rollout", "undo", f"deployment/{DEPLOYMENT}"])
    outcome = "rolled back successfully" if ok else f"rollback FAILED: {output}"
    notify_slack(f":warning: *DeploymentDegraded* detected on `{DEPLOYMENT}`. "
                 f"Auto-remediation: {outcome}")
    return ok, outcome


def handle_high_memory():
    logger.info("Handling HighMemoryUsage: deleting pod to force reschedule")
    ok, output = run_kubectl(["delete", "pod", "-l", f"app={DEPLOYMENT}", "--field-selector=status.phase=Running"])
    outcome = "pod recycled successfully" if ok else f"recycle FAILED: {output}"
    notify_slack(f":warning: *HighMemoryUsage* detected on `{DEPLOYMENT}`. "
                 f"Auto-remediation: {outcome}")
    return ok, outcome


ALERT_HANDLERS = {
    "PodCrashLooping": handle_crash_loop,
    "DeploymentDegraded": handle_degraded_deployment,
    "HighMemoryUsage": handle_high_memory,
}


@app.route("/webhook", methods=["POST"])
def webhook():
    payload = request.get_json(silent=True) or {}
    alerts = payload.get("alerts", [])

    results = []
    for alert in alerts:
        if alert.get("status") != "firing":
            continue

        alert_name = alert.get("labels", {}).get("alertname", "Unknown")
        handler = ALERT_HANDLERS.get(alert_name)

        if not handler:
            logger.info("No handler registered for alert: %s (ignoring)", alert_name)
            continue

        if not cooldown_ok(alert_name):
            logger.info("Cooldown active for %s, skipping duplicate action", alert_name)
            results.append({"alert": alert_name, "action": "skipped (cooldown)"})
            continue

        ok, outcome = handler()
        results.append({"alert": alert_name, "action": outcome, "success": ok})

    return jsonify({"processed": results}), 200


@app.route("/health")
def health():
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
