---
name: playing-connect-4
description: Use when the user asks to play connect 4, connect-4, or start a game against a computer opponent. Drives a full game to completion over HTTP and reports the win, loss, or draw.
---

# Playing Connect 4

## Overview

Play connect 4 to completion against a computer opponent over a simple HTTP API. You are "X", the opponent is "O"; the game ends when a player connects 4 discs horizontally, vertically, or diagonally.

## Constraints

- Require a hostname and port (e.g. `127.0.0.1:8000`) before starting; prompt the user if missing.
- Use `curl` for all requests. Run `curl HOST:PORT/help` for endpoint details.
- Start every new game with `/new` to clear the board.
- Query `/board` before every move. Move only on your turn; poll `/board` until it is your turn.
- Discs stack from the bottom of a column. A move that leaves a gap in the column is illegal.

## Verification

- [ ] Game started via `/new` on the user-provided host and port
- [ ] Every move was preceded by a fresh `/board` query showing your turn
- [ ] Final board shows a win, loss, or draw; outcome reported to the user
