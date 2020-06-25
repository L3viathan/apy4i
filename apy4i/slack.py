import hashlib
import contextvars
from urllib.parse import parse_qs
import asks
from quart import request, jsonify, abort
from .storage import Log
from .auth import signing_secret


rq_data = contextvars.ContextVar("rq_data")


@signing_secret("SLACK_SIGNING_SECRET")
async def slack():
    from . import slack_commands

    data = await request.get_data()
    data = {k: v[0] for (k, v) in parse_qs(data.decode("utf-8")).items()}
    rq_data.set(data)
    async with Log("requests") as l:
        await l.log(data)
    user = data["user_name"]
    text = data["text"]

    command, _, rest = text.partition(" ")

    return await getattr(slack_commands, command, slack_commands.default_command)(
        user, rest
    )


async def in_channel(text, hide_sender=False):
    json_reply = {"response_type": "in_channel", "text": text}
    if hide_sender:
        return await respond(json_reply)
    return jsonify(json_reply)


async def ephemeral(text):
    return await respond({"response_type": "ephemeral", "text": text})


async def attachment(hide_sender=False, public=True, **kwargs):
    response_type = "in_channel" if public else "ephemeral"
    json_reply = {
        "response_type": response_type,
        "attachments": [{"fallback": "<New message>", **kwargs}],
    }
    if hide_sender:
        return await respond(json_reply)
    return jsonify(json_reply)


async def respond(data):
    await asks.post(rq_data.get()["response_url"], json=data)
    return "No content", 204
