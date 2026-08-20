from __future__ import annotations

START = [
    list("rnbqkbnr"),
    list("pppppppp"),
    list("." * 8),
    list("." * 8),
    list("." * 8),
    list("." * 8),
    list("PPPPPPPP"),
    list("RNBQKBNR"),
]


def start_board() -> list[list[str]]:
    return [row[:] for row in START]


def sq_to_rc(sq: str) -> tuple[int, int]:
    return 8 - int(sq[1]), ord(sq[0]) - 97


def apply_move(board: list[list[str]], move: dict) -> list[list[str]]:
    r1, c1 = sq_to_rc(move["from"])
    r2, c2 = sq_to_rc(move["to"])
    nxt = [row[:] for row in board]
    nxt[r2][c2] = nxt[r1][c1]
    nxt[r1][c1] = "."
    return nxt


def board_at(moves: list[dict], ply: int) -> list[list[str]]:
    board = start_board()
    for move in moves[:ply]:
        board = apply_move(board, move)
    return board


def fen_pieces(board: list[list[str]]) -> str:
    return "/".join("".join(row) for row in board)
