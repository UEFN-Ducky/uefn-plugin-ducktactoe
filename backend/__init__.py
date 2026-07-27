"""Duck-Tac-Toe — live tic-tac-toe the Ducky agent can play via MCP tools."""

from __future__ import annotations

import json
import time
from typing import Any

PLUGIN_ID = "ducktactoe"
CACHE_KEY = "state"
MARKERS = ("X", "O")
WIN_LINES = (
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (0, 3, 6),
    (1, 4, 7),
    (2, 5, 8),
    (0, 4, 8),
    (2, 4, 6),
)


def empty_board() -> list[str]:
    return [""] * 9


def winner_of(board: list[str]) -> str | None:
    for a, b, c in WIN_LINES:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    if all(board):
        return "draw"
    return None


def new_state(*, agent_marker: str = "O") -> dict[str, Any]:
    am = str(agent_marker or "O").strip().upper()
    if am not in MARKERS:
        am = "O"
    human = "X" if am == "O" else "O"
    return {
        "board": empty_board(),
        "turn": "X",  # X always opens
        "human_marker": human,
        "agent_marker": am,
        "winner": None,
        "status": "playing",
        "move_count": 0,
        "updated_at": time.time(),
    }


def public_view(state: dict[str, Any]) -> dict[str, Any]:
    board = list(state.get("board") or empty_board())
    while len(board) < 9:
        board.append("")
    board = [str(c or "") for c in board[:9]]
    return {
        "board": board,
        "board_rows": [board[0:3], board[3:6], board[6:9]],
        "turn": str(state.get("turn") or "X"),
        "human_marker": str(state.get("human_marker") or "X"),
        "agent_marker": str(state.get("agent_marker") or "O"),
        "winner": state.get("winner"),
        "status": str(state.get("status") or "playing"),
        "move_count": int(state.get("move_count") or 0),
        "open_cells": [i for i, c in enumerate(board) if not c],
    }


def apply_move(state: dict[str, Any], cell: int, marker: str) -> dict[str, Any]:
    """Return a new state after placing ``marker`` at ``cell`` (0–8). Raises ValueError."""
    if str(state.get("status") or "") != "playing":
        raise ValueError(f"game already over (winner={state.get('winner')})")
    m = str(marker or "").strip().upper()
    if m not in MARKERS:
        raise ValueError("marker must be X or O")
    turn = str(state.get("turn") or "X")
    if m != turn:
        raise ValueError(f"not {m}'s turn (turn={turn})")
    try:
        idx = int(cell)
    except (TypeError, ValueError) as exc:
        raise ValueError("cell must be an integer 0–8") from exc
    if idx < 0 or idx > 8:
        raise ValueError("cell must be 0–8 (row-major)")
    board = list(state.get("board") or empty_board())
    while len(board) < 9:
        board.append("")
    board = [str(c or "") for c in board[:9]]
    if board[idx]:
        raise ValueError(f"cell {idx} is already occupied by {board[idx]}")
    board[idx] = m
    w = winner_of(board)
    next_turn = "O" if turn == "X" else "X"
    return {
        **state,
        "board": board,
        "turn": next_turn if w is None else turn,
        "winner": w,
        "status": "over" if w is not None else "playing",
        "move_count": int(state.get("move_count") or 0) + 1,
        "updated_at": time.time(),
    }


def _load_state() -> dict[str, Any]:
    from frontend.ui_web.plugin_host_api import cache_get

    raw = cache_get(PLUGIN_ID, CACHE_KEY)
    if not isinstance(raw, dict) or not raw.get("board"):
        return new_state()
    return dict(raw)


def _save_state(state: dict[str, Any]) -> None:
    from frontend.ui_web.plugin_host_api import cache_set

    cache_set(PLUGIN_ID, CACHE_KEY, dict(state))


def _tool_json(payload: dict[str, Any], pretty: bool = False) -> str:
    try:
        from backend.json_util import tool_json

        return tool_json(payload, pretty=pretty)
    except Exception:
        indent = 2 if pretty else None
        return json.dumps(payload, ensure_ascii=False, indent=indent)


def register(api) -> None:
    """Register Duck-Tac-Toe MCP tools on the app FastMCP via api.tool()."""

    @api.tool(intent=r"\b(tic.?tac.?toe|ducktactoe|duck.?tac.?toe)\b", listener=False)
    def ducktactoe_new_game(agent_marker: str = "O", pretty: bool = False) -> str:
        """Start a new Duck-Tac-Toe game against the human in the plugin panel.

        X always opens. Default: human=X, agent=O. Pass agent_marker=\"X\" to let
        the agent go first. Open the Duck-Tac-Toe panel so the human can click.
        """
        state = new_state(agent_marker=agent_marker)
        _save_state(state)
        view = public_view(state)
        view["ok"] = True
        view["message"] = (
            f"New game — you are {state['agent_marker']}, human is {state['human_marker']}. "
            f"Turn: {state['turn']}."
        )
        return _tool_json(view, pretty=pretty)

    @api.tool(listener=False)
    def ducktactoe_state(
        wait_for_my_turn: bool = False,
        timeout_s: float = 20.0,
        pretty: bool = False,
    ) -> str:
        """Read the live Duck-Tac-Toe board (and optionally wait for the agent's turn).

        When wait_for_my_turn is true, blocks (sleep-loop on cache) until it is the
        agent's turn, the game ends, or timeout_s elapses — so you can wait for the
        human's click without spamming tool calls.
        """
        deadline = time.time() + max(0.5, min(float(timeout_s or 20.0), 60.0))
        agent = None
        while True:
            state = _load_state()
            view = public_view(state)
            agent = view["agent_marker"]
            if not wait_for_my_turn:
                view["ok"] = True
                view["waited"] = False
                return _tool_json(view, pretty=pretty)
            if view["status"] != "playing" or view["turn"] == agent:
                view["ok"] = True
                view["waited"] = True
                view["timed_out"] = False
                return _tool_json(view, pretty=pretty)
            if time.time() >= deadline:
                view["ok"] = True
                view["waited"] = True
                view["timed_out"] = True
                view["message"] = "Still waiting for the human — try again."
                return _tool_json(view, pretty=pretty)
            time.sleep(0.25)

    @api.tool(listener=False)
    def ducktactoe_move(cell: int, pretty: bool = False) -> str:
        """Place the agent's marker on cell 0–8 (row-major: 0 top-left … 8 bottom-right).

        Only legal on the agent's turn with an empty cell. Returns the new board and
        winner/draw when the game ends.
        """
        state = _load_state()
        marker = str(state.get("agent_marker") or "O")
        try:
            state = apply_move(state, cell, marker)
        except ValueError as exc:
            view = public_view(state)
            view["ok"] = False
            view["error"] = str(exc)
            return _tool_json(view, pretty=pretty)
        _save_state(state)
        view = public_view(state)
        view["ok"] = True
        view["played"] = int(cell)
        view["played_marker"] = marker
        if view["winner"] == "draw":
            view["message"] = "Draw!"
        elif view["winner"]:
            view["message"] = f"{view['winner']} wins!"
        else:
            view["message"] = f"Played {marker} at {cell}. Human's turn."
        return _tool_json(view, pretty=pretty)

    api.log("Duck-Tac-Toe MCP tools registered")


def _self_check() -> None:
    s = new_state(agent_marker="O")
    assert s["human_marker"] == "X" and s["agent_marker"] == "O" and s["turn"] == "X"
    s = apply_move(s, 0, "X")
    assert s["board"][0] == "X" and s["turn"] == "O"
    try:
        apply_move(s, 0, "O")
        raise AssertionError("occupied cell should fail")
    except ValueError:
        pass
    try:
        apply_move(s, 1, "X")
        raise AssertionError("wrong turn should fail")
    except ValueError:
        pass
    s = apply_move(s, 1, "O")
    s = apply_move(s, 3, "X")
    s = apply_move(s, 2, "O")
    s = apply_move(s, 6, "X")  # X wins col 0? board: X O O / X . . / X . . — yes
    assert s["winner"] == "X" and s["status"] == "over"
    try:
        apply_move(s, 4, "O")
        raise AssertionError("move after game over should fail")
    except ValueError:
        pass

    # Draw: X O X / X O O / O X X
    d = new_state()
    seq = [(0, "X"), (1, "O"), (2, "X"), (4, "O"), (3, "X"), (5, "O"), (7, "X"), (6, "O"), (8, "X")]
    for cell, m in seq:
        d = apply_move(d, cell, m)
    assert d["winner"] == "draw", d

    # Agent goes first as X
    a = new_state(agent_marker="X")
    assert a["agent_marker"] == "X" and a["human_marker"] == "O" and a["turn"] == "X"
    print("ducktactoe self-check OK")


if __name__ == "__main__":
    _self_check()
