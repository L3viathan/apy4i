from quart import Blueprint, request, abort, jsonify
from chordy.song import Song
from chordy.chord import Chord

views = Blueprint("chords", __name__)


@views.route("/convert", methods=["POST"], defaults={"format": "tex"})
@views.route("/convert/<format_>", methods=["POST"], defaults={"format_": "html"})
async def convert(format_):
    if format_ not in ["html", "txt", "tex"]:
        abort(405)
    data = await request.json
    song = Song.from_file(data["lines"])
    song.title = data.get("title")
    return getattr(song, f"to_{format_}")(flags=data.get("flags", ""))

@views.route("/detect/<path:chord>")
async def detect(chord):
    chord = chord.rstrip("/")
    if not Chord.is_chord(chord):
        return (404, "No such chord found")
    chord = Chord.from_string(chord)
    return jsonify({
        "tone": chord.tone,
        "minor": chord.minor,
        "bass": chord.bass,
        "modifiers": chord.modifiers,
        "optional": chord.optional,
    })
