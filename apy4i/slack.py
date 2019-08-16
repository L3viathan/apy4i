from quart import request, abort


slack_commands = {}


async def default_command(user, text):
    abort(400, "Unknown command")


async def slack():
    data = await request.json
    user = data["user_name"]
    text = data["text"]
    token = data["token"]

    # TODO: check token

    command, _, rest = text.partition(" ")

    # TODO: ephemeral vs. in_channel
    return await slack_commands.get(command, default_command)(user, rest)
