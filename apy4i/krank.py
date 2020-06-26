from quart import request, jsonify, Blueprint
from .storage import Log, Store
from .utils import elo, timestamp

views = Blueprint("krank", __name__)

PLAYER_HTML = """
<span class="player" title="{0}" style="background-image: url(avatars/{0}.jpeg);"></span>
"""
BEATS_HTML = "⚔️"


@views.route("/logs")
async def klog_html():
    return await klog(html=True)


@views.route("/table")
async def ktable():
    async with Store("krank") as ranks:
        async with Store("krank_hidden") as hidden:
            return jsonify({k: v for (k, v) in ranks.items() if k not in hidden})


@views.route("/log.json")
async def klog(html=False, last=8):
    entries = [entry async for entry in Log("krank")][-last:]
    if html:
        return "<br><br>".join(
            "".join(
                (
                    "".join(PLAYER_HTML.format(winner) for winner in log["winners"]),
                    BEATS_HTML,
                    "".join(PLAYER_HTML.format(loser) for loser in log["losers"]),
                    " (±",
                    str(log["value"]),
                    ")",
                )
            )
            for log in entries
        )
    return jsonify(entries)


@views.route("/submit", methods=["POST"])
async def ksubmit():
    data = await request.json
    winners = data["winners"]
    losers = data["losers"]
    async with Store("krank") as ranks:
        async with Log("krank") as l:
            win_scores_pre = {winner: ranks.get(winner, 1000) for winner in winners}
            lose_scores_pre = {loser: ranks.get(loser, 1000) for loser in losers}
            plus, minus = elo(
                list(win_scores_pre.values()),
                list(lose_scores_pre.values()),
                "a",
                rounding=True,
            )
            win_scores_post = {
                winner: score + plus for winner, score in win_scores_pre.items()
            }
            lose_scores_post = {
                loser: score + minus for loser, score in lose_scores_pre.items()
            }
            ranks.update(**win_scores_post, **lose_scores_post)
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
                    "value": plus,
                }
            )
    return "No content", 204
