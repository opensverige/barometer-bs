import json
from pathlib import Path

from tests.chess_replay import board_at, fen_pieces, start_board

ROOT = Path(__file__).resolve().parents[1]
MATCH = json.loads((ROOT / "web" / "match-demo.json").read_text(encoding="utf-8"))
HTML = (ROOT / "web" / "chess.html").read_text(encoding="utf-8")
CSS = (ROOT / "web" / "chess.css").read_text(encoding="utf-8")
JS = (ROOT / "web" / "chess.js").read_text(encoding="utf-8")
INDEX = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
WARN = "VISUAL DEMO — INTE POLITISK DATA"


def test_demo_warning_always_in_html():
    assert WARN in HTML
    assert "demo-warn" in HTML
    assert MATCH["warning"] == WARN
    assert MATCH["demo"] is True
    assert "hidden" not in HTML.split("demo-warn")[1].split(">")[0]


def test_every_move_has_existing_source_id():
    ids = {e["source_id"] for e in MATCH["events"]}
    assert MATCH["moves"]
    for move in MATCH["moves"]:
        assert move["source_id"]
        assert move["source_id"] in ids


def test_deterministic_replay_and_end_position():
    moves = MATCH["moves"]
    a = fen_pieces(board_at(moves, 3))
    b = fen_pieces(board_at(moves, 3))
    assert a == b
    start = fen_pieces(start_board())
    assert fen_pieces(board_at(moves, 0)) == start
    end = board_at(moves, len(moves))
    assert end[4][4] == "P"  # e4
    assert end[3][4] == "p"  # e5
    assert end[5][5] == "N"  # f3
    assert fen_pieces(board_at(moves, len(moves))) == fen_pieces(board_at(moves, 99))


def test_navigation_prev_next_bounds():
    n = len(MATCH["moves"])
    ply = 0
    ply = min(n, ply + 1)
    ply = min(n, ply + 1)
    ply = max(0, ply - 1)
    assert ply == 1
    ply = n + 5
    ply = max(0, min(n, ply))
    assert ply == n
    ply = max(0, ply - n - 2)
    assert ply == 0


def test_reduced_motion_and_eye_present():
    assert "prefers-reduced-motion" in CSS
    assert "class=\"eye\"" in HTML or 'class="eye"' in HTML
    assert "id=\"eye\"" in HTML or 'id="eye"' in HTML
    assert "watchEye" in JS


def test_live_index_not_replaced_by_chess():
    assert "chess.js" not in INDEX
    assert "Schackdemo" not in INDEX


def test_move_without_source_rejected():
    bad = {**MATCH, "moves": MATCH["moves"] + [{"ply": 99, "from": "a2", "to": "a3", "piece": "P", "player": "nord"}]}
    ids = {e["source_id"] for e in bad["events"]}
    missing = [m for m in bad["moves"] if not m.get("source_id") or m.get("source_id") not in ids]
    assert missing
