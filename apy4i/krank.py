from urllib.parse import parse_qs
from operator import sub

from quart import request, jsonify
from .storage import Log, Store
from .utils import elo, timestamp

PLAYER_HTML = """
<span class="player" title="{0}" style="background-image: url(avatars/{0}.jpeg);"></span>
"""
BEATS_HTML = "⚔️"


async def klog_html():
    return await klog(html=True)


async def ktable():
    async with Store("krank") as ranks:
        async with Store("krank_hidden") as hidden:
            return jsonify({k: v for (k, v) in ranks.items() if k not in hidden})


async def klog(html=False, last=8):
    entries = list(Log("krank"))[-last:]
    if html:
        return "<br><br>".join(
            "".join(
                (
                    "".join(PLAYER_HTML.format(winner) for winner in log["winners"]),
                    BEATS_HTML,
                    "".join(PLAYER_HTML.format(loser) for loser in log["losers"]),
                    " (±",
                    str(abs(sub(*log["winners"][0]))),
                    ")",
                )
            )
            for log in entries
        )
    return jsonify(entries)


async def ksubmit():
    data = await request.get_data()
    data = {k: v[0] for (k, v) in parse_qs(data.decode("utf-8")).items()}
    winners = data["winners"].split(",")
    losers = data["losers"].split(",")
    async with Store("krank") as ranks:
        win_scores_pre = {winner: ranks.get(winner, 1000) for winner in winners}
        lose_scores_pre = {loser: ranks.get(loser, 1000) for loser in losers}
        plus, minus = elo(win_scores_pre, lose_scores_pre, "a")
        win_scores_post = {
            winner: score + plus for winner, score in win_scores_pre.items()
        }
        lose_scores_post = {
            loser: score + minus for loser, score in lose_scores_pre.items()
        }
        ranks.update(**win_scores_post, **lose_scores_post)
    async with Log("krank") as l:
        await l.log(
            {
                "ts": timestamp(),
                "winners": {
                    winner: [win_scores_pre[winner], win_scores_post[winner]]
                    for winner in win_scores_pre
                },
                "losers": {
                    loser: [lose_scores_pre[loser], lose_scores_post[loser]]
                    for loser in lose_scores_pre
                },
            }
        )
    return 204, "No content"