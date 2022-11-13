import uuid
from datetime import datetime, timedelta
import asks
from quart import Blueprint, request, abort, jsonify
from .storage import Store

views = Blueprint("alerts", __name__)

@views.route("/create", methods=["POST"])
async def create():
    data = await request.json
    now = datetime.utcnow()
    warning_at = now + timedelta(minutes=data.get("delay", 0))
    error_at = warning_at + timedelta(minutes=data.get("alert_delay", 45))
    alert_id = uuid.uuid4().hex
    alert = {
        "title": str(data["title"]),
        "description": str(data.get("description")),
        "warning_at": warning_at,
        "error_at": error_at,
        "warning_topic": str(data["topic"]),
        "error_topic": "vizuina-alerts",
        "status": "waiting",
    }
    async with Store("alerts") as alerts:
        alerts[alert_id] = alert
    return alert_id


@views.route("/list")
async def list():
    async with Store("alerts") as alerts:
        return alerts


@views.route("/resolve/<alert_id>")
async def resolve(alert_id):
    async with Store("alerts") as alerts:
        alerts.pop(alert_id)


@views.route("/beat")
async def beat():
    now = datetime.utcnow()
    async with Store("alerts") as alerts:
        for alert_id, alert in alerts.items():
            if alert["status"] == "waiting" and alert["warning_at"] <= now:
                await send(alert_id, alert, "warning")
                alert["status"] = "warned"
            elif alert["status"] == "warned" and alert["error_at"] <= now:
                await send(alert_id, alert, "error")
                alert["status"] = "errored"


async def send(alert_id, alert, severity):
    await asks.post(
        "https://ntfy.sh/{alert[severity + '_topic']}",
        json={
            "topic": alert[f"{severity}_topic"],
            "message": alert["description"],
            "title": alert["title"],
            "tags": [severity, *alert.get("tags", [])],
            "actions": [
                {
                    "action": "http",
                    "label": "Mark as resolved",
                    "url": f"https://apy4i.l3vi.de/alerts/resolve/{alert_id}",
                },
            ],
        },
    )
