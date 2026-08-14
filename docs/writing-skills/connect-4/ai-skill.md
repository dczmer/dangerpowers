---
name: ai-skill
description: Use when playing the HTTP Connect-4 game served on 127.0.0.1:8000 — when the user says "play connect 4", "play the game", or asks you to interact with the local game server. Explains the endpoints, board format, coordinates, turn flow, and error responses. Does not cover strategy.
---

# Playing HTTP Connect-4

## Overview

A plain-text Connect-4 game over HTTP at `http://127.0.0.1:8000`, played with `curl` GET requests. You are `X`, the computer is `O`. All responses are plain text. Re-fetch instructions anytime with `curl -s http://127.0.0.1:8000/help`.

## Endpoints

| Endpoint | Purpose |
|---|---|
| `/new` | Start a new game. A coin flip decides who moves first; the response tells you. Resets any game in progress. |
| `/move?col=C&row=R` | Place your `X` at column `C`, row `R`. |
| `/board` | Show the board and whose turn it is. `/state` is an alias. |
| `/help` | Show the rules and endpoint list. |

## Board Format

- 7 columns (0-6) labeled in the footer, 6 rows (0-5) labeled at the right edge.
- Rows are numbered **bottom-up**: row 0 is the bottom row, row 5 the top.
- Example board (X at col 3 row 0, O at col 0 row 0):

```
| | | | | | | | 5
| | | | | | | | 4
| | | | | | | | 3
| | | | | | | | 2
| | | | | | | | 1
|O| | |X| | | | 0
+-------------+
 0 1 2 3 4 5 6
your move (X).
```

- The last line is the status. Possible statuses: `your move (X).`, `opponent thinking...`, `game over: X wins.`, `game over: O wins.` (a draw is also reported as a `game over` line).

## Turn Flow

1. `curl -s http://127.0.0.1:8000/new` and read who goes first.
2. If the computer goes first, the board shows `opponent thinking...` — poll `/board` (every ~2-3 seconds) until the status becomes `your move (X).`.
3. Choose an empty cell that is legally supported (see Move Rules) and `curl -s "http://127.0.0.1:8000/move?col=C&row=R"`.
4. A legal move returns the updated board ending in `opponent thinking...`.
5. Poll `/board` until the computer's `O` appears and the status is `your move (X).` again.
6. Repeat until a `game over` status appears.
7. After game over, further `/move` calls return `the game is over. start a new game to play again.` — call `/new` to play again.

## Move Rules

- You specify the exact cell, not just a column.
- A move is rejected if the cell is out of bounds, already occupied, or unsupported (the cell directly below it is empty). Discs stack from the bottom up, so the only legal cells are row 0 of any non-full column, or the cell directly on top of an existing stack.
- Quote the URL so the shell does not split on `&`.

## Error Responses (all plain text, no HTTP error codes to rely on)

| Response | Cause | Action |
|---|---|---|
| `invalid move. usage: /move?col=<0-6>&row=<0-5>` | Non-integer or missing col/row | Re-send with integer params |
| `invalid cell: out of bounds. columns are 0-6, rows are 0-5.` | Coordinate outside the grid | Pick col 0-6, row 0-5 |
| `invalid cell: already occupied.` | Cell has a disc | Pick an empty cell |
| `invalid cell: would leave a gap. discs must stack from the bottom up.` | Cell below is empty | Drop to the lowest empty row in that column |
| `your opponent is thinking. check back in a few seconds.` | Moved out of turn | Poll `/board` until your turn |
| `the game is over. start a new game to play again.` | Moved after game end | Call `/new` |

## Checklist

- [ ] Started the game with `/new` and noted who moves first.
- [ ] Every move used integer `col` 0-6 and `row` 0-5, with the URL quoted.
- [ ] Every move targeted the lowest empty cell of a column (no gaps).
- [ ] After each move, polled `/board` until `your move (X).` before moving again.
- [ ] Stopped on a `game over` status; used `/new` for a rematch.
