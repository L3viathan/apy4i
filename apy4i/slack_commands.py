from quart import abort
from .slack import in_channel, ephemeral, attachment
from .storage import Store
from .utils import elo

win_indicators = [
    "gewinnt",
    "besiegt",
    "wins",
    "defeats",
    "gewonnen",
    "gewinne",
    "gewinnen",
]
loss_indicators = [
    "verliert",
    "unterliegt",
    "loses",
    "lost",
    "verloren",
    "verliere",
]
draw_indicators = ["remis", "unentschieden", "ties", "tie"]
sim_indicators = ["test", "wenn", "hätte", "gewönne", "verlöre", "würde"]


async def say(user, text):
    return await in_channel(text, hide_sender=True)


async def test(user, text):
    return ("No content", 204)


async def default_command(user, text):
    abort(400, "Unknown command")


async def help(user, text):
    return await ephemeral("Available commands: ...")


async def _table(ranks, simulation=False):
    text = "\n".join(
        "{}: {}".format(k[:2] + "\u200c" + k[2:], ranks[k]["score"])
        for k in sorted(ranks, key=lambda x: ranks[x]["score"], reverse=True)
        if ranks[k].get("active", True)
    )
    kwargs = {
        "author_link": "https://github.com/L3viathan/schikanoeschen/blob/master/german.md",
        "author_name": "Offizielle Turnierregeln",
        "author_icon": "https://static.l3vi.de/book.png",
        "fallback": "<Ligatabelle>",
        "title": "Tabelle",
        "thumb_url": "https://static.l3vi.de/karten.png",
    }
    if simulation:
        kwargs.update(color="warning", hide_sender=True)
    return await attachment(text=text, **kwargs)


async def schika(user, text):
    tokens = [
        f"@{user}" if token in ("ich", "mich") else token
        for token in text.lower().split()
    ]
    async with Store("schika_ranks") as ranks:
        if not tokens:
            return await ephemeral(
                "Ich habe dich nicht verstanden. Bitte drücke dich klarer aus."
            )
        if text == "list":
            return await _table(ranks)
        if tokens[0] == "set":
            player = tokens[1]
            score = int(tokens[2])
            ranks[player] = {"score": score, "active": True}
            return await ephemeral(f"Score of {player} set to {score}.")

        players = [word for word in tokens if word in ranks]
        if len(players) == 2:
            a, b = players
            score_a = ranks[a]["score"]
            score_b = ranks[b]["score"]

            if any(tok in win_indicators for tok in tokens):
                delta_a, delta_b = elo(score_a, score_b, "a")
            elif any(tok in loss_indicators for tok in tokens):
                delta_a, delta_b = elo(score_a, score_b, "b")
            elif any(tok in draw_indicators for tok in tokens):
                delta_a, delta_b = elo(score_a, score_b, "draw")

            simulation = any(tok in sim_indicators for tok in tokens)
            if not simulation:
                ranks[a]["score"] = round(score_a + delta_a)
                ranks[b]["score"] = round(score_b + delta_b)
            return await _table(ranks, simulation=simulation)