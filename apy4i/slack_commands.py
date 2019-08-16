from quart import abort
from apy4i.slack import in_channel

async def say(user, text):
    return await in_channel(text, hide_sender=True)

async def test(user, text):
    return ("No content", 204)

async def default_command(user, text):
    abort(400, "Unknown command")
