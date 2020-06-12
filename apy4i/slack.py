import os
import hashlib
import hmac
from urllib.parse import parse_qs
import asks
from quart import request, jsonify, abort
from .storage import Log


def verify_token(body):
    ts = request.headers.get("X-Slack-Request-Timestamp")
    signature = request.headers.get("X-Slack-Signature")
    version = b"v0"
    payload = b":".join((version, ts, body))
    h = hmac.new(os.environ.get("SLACK_SIGNING_SECRET"), payload, hashlib.sha256)
    assert h.hexdigest() == signature


async def slack():
    from . import slack_commands

    data = await request.get_data()
    verify_token(data)
    data = parse_qs(data.decode("utf-8"))
    async with Log("requests") as l:
        l.log(data)
    user = data["user_name"]
    text = data["text"]
    token = data["token"]

    # no Optional[str] equals Ellipsis:
    if token != os.environ.get("SLACK_TOKEN", ...):
        abort(403)

    command, _, rest = text.partition(" ")

    return await getattr(slack_commands, command, slack_commands.default_command)(
        user, rest
    )


async def in_channel(text, hide_sender=False):
    json_reply = {"response_type": "in_channel", "text": text}
    if hide_sender:
        await respond(json_reply)
        return "No content", 204
    return jsonify(json_reply)


async def ephemeral(text):
    await respond({"response_type": "ephemeral", "text": text})


async def attachment(hide_sender=False, public=True, **kwargs):
    response_type = "in_channel" if public else "ephemeral"
    json_reply = {
        "response_type": response_type,
        "attachments": [{"fallback": "<New message>", **kwargs}],
    }
    if hide_sender:
        await respond(json_reply)
        return "No content", 204
    return jsonify(json_reply)


async def respond(data):
    return await asks.post((await request.json)["response_url"], json=data)
