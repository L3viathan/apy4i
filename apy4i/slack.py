import requests
from quart import request, jsonify


async def slack():
    from apy4i import slack_commands

    data = await request.json
    user = data["user_name"]
    text = data["text"]
    token = data["token"]

    # TODO: check token

    command, _, rest = text.partition(" ")

    return await getattr(
        slack_commands, command, slack_commands.default_command
    )(user, rest)


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
    # TODO: asyncify
    requests.post((await request.json)["response_url"], json=data)
