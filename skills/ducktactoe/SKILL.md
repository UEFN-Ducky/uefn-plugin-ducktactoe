---
name: ducktactoe
description: "Play Duck-Tac-Toe live against the user in the UEFN-Ducky chat board — start a game, wait for their click, place moves via MCP tools"
license: All Rights Reserved
metadata:
  label: Duck-Tac-Toe
  version: 1
  author: Iliya Kovachki
  copyright: Copyright 2026 Iliya Kovachki
  allow_redistribute: false
  managed_by: uefn-ducky
  source_plugin_id: ducktactoe
---

# Duck-Tac-Toe — play live with the user

You and the human share a real board in the **Duck-Tac-Toe** chat (collapsible board aside). Your moves appear on their screen within ~300 ms. This is turn-based real-time: you wait for their click, then play.

This branded chat is for the **game first**. Messages like "i won", "your turn", "rematch", or anything about the board mean Duck-Tac-Toe — **not** the UEFN island / roguelike / Verse project. Call `ducktactoe_state` before assuming anything else.

They can turn on **Live** voice in this chat. **New game** on the board resets the cache and pings you. Winning and drawing clicks also ping you.

## Prerequisites

1. Plugin **ducktactoe** enabled (Settings → Store / MCPs).
2. Tools opted in for this chat under **Tools & MCPs**.
3. Human opens Duck-Tac-Toe (header duck) so the board aside + chat are visible.

## Tools (use these — do not invent board state)

| Tool | When |
|------|------|
| `ducktactoe_new_game(agent_marker?)` | Start / reset. Default you are **O** (human X opens). Pass `agent_marker="X"` to go first. |
| `ducktactoe_state(wait_for_my_turn?, timeout_s?)` | Read board. Set `wait_for_my_turn=true` to block until it's your turn (or game over / timeout). |
| `ducktactoe_move(cell)` | Place your marker. Cells **0–8** row-major: `0 1 2 / 3 4 5 / 6 7 8`. |

## Play loop

1. Call `ducktactoe_new_game` (or `ducktactoe_state` if a game is already going).
2. Tell the human the board is open and whose turn it is.
3. If it is **not** your turn: `ducktactoe_state(wait_for_my_turn=true, timeout_s=25)`.
4. When it's your turn: pick a cell from `open_cells`, call `ducktactoe_move(cell)`.
5. Narrate the move briefly in chat (e.g. "O in the center").
6. Repeat 3–5 until `status` is `over` (winner or draw). Then congratulate / offer rematch.

If `timed_out` is true, ask the human to click (or say if they want to stop) and wait again.

## Ambiguous chat ("i won", "nice", "again", …)

**First tool:** `ducktactoe_state` (no wait). React to that board. Do **not** grep Verse, search the project, or invent a roguelike / dungeon victory.

Only leave the game and touch UEFN/Verse when the human clearly asks for project work (e.g. "fix the spawner", "open random_room_system.verse").

## Strategy (keep it light)

Priority: **win now** → **block their win** → **center (4)** → **corner (0,2,6,8)** → side. Do not overthink; one move per turn.

## Don'ts

- Don't claim a move without calling `ducktactoe_move`.
- Don't spam `ducktactoe_state` without `wait_for_my_turn` while waiting for the human.
- Don't edit Verse / UEFN for game talk — the game is entirely in the plugin cache / chat board aside.
- Never claim a win or draw unless `ducktactoe_move` / `ducktactoe_state` returned `winner` / `status=over`. If a tool errors, do not invent board state — retry `ducktactoe_state` or ask the human.
- If chat says the human moved while you were talking: `ducktactoe_state` then play — the board is source of truth.
- These tools are host-cache only — they do **not** need the UEFN editor listener.
