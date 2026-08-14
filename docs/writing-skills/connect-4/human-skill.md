---
name: human-skill
description: Play a game of connect-4 against a computer opponent over simple HTTP protocol. Use when requested to play connect 4, start a game of connect 4, playing connect 4.
---

To play a game of connect 4, the user must provide a hostname and port where the game is located. Example: `127.0.0.1:8000`. If these are not provided, prompt the user before proceeding.

Use `curl` to make GET requests to perform actions (example: `curl HOST:PORT/help` to get help).

New games should start by clearing the board with `/new`.

Before making any moves, query the state of the board with `/board`. You are the "X"s and the computer opponent is the "O"s.

The opponent may take a few seconds to decide on a move. Poll `/board` until it is your turn before attempting to make a move.

Pieces called "discs" are added to this board in alternating turns until one of the players has arranged 4 consecutive pieces horizontally, vertically, or diagonally.

The pieces cannot be placed at arbitrary positions, they must stack from the bottom row of the column up. For example, if there is a piece in row 0, column 0, the only valid location for the next disc in that column is row 1, column 0. Any higher column >1 would leave a gap between two disc in one column, which is illegal.
