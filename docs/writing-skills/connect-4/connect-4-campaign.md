---
name: connect-4-campaign
description: Use when you need to run a connect 4 campaign.
---

STRATEGY_FILE is the name of the instructions file the user requested to use for the campaign (prompt user if not specified). STRATEGY_FILE must be a real .md file that exists on disk.

GAME_HOST is the name and port number of the target server specified by the user (default "127.0.0.1:8000").

Play a series of 10 games against the game server at GAME_HOST.

Play every game in the series, do not stop when you have enough games to win the series.

Each game **MUST** be run a **FRESH** subagent session (`subagent_type: general`) - DO NOT REUSE SUBAGENT SESSIONS!, using the `task` tool, to keep the main session context clean and prevent context contamination between games. Run games sequentially, never in parallel.

Give these exact instructions to each subagent:
```
Read the entirety of STRATEGY_FILE into context.
Curl `/help` for instructions on how to play.
Play a single game of connect 4 against the opponent at GAME_HOST.
Always use `curl -s` when interacting with the game server.
Do not make multiple attempts to win - if you lose, you lose.
After every turn, explain why you made that choice and what is your strategy.
Play until the game is completed and print your report.
Do not stop. Do not prompt the user. Keep going until your job is completed.
Only play **ONE** attempt and then report the following:
- number of times the agent failed to capitalize on a winning scenario
- number of times the opponent failed to capitalize on a winning scenario
- any issues interacting with the game server
- any issues interpreting the board state, reading coordinates, or identifying the location of a piece on the board.
- any invalid moves (gaps, occupied spaces, out of bounds)
```

Track each game (1-10) progress, and the final analysis phase, with the `todo` tool (11 todo items).

Keep track of wins, losses, and draws.

When all games have been completed, analyze the sessions of all subagents used in the campaign and generate a report containing:
- number of games played, won, lost, tied
- number of moves by player/computer
- number of times the agent failed to capitalize on a winning scenario
- number of times the opponent failed to capitalize on a winning scenario
- any issues interacting with the game server
- any issues interpreting the board state, reading coordinates, or identifying the location of a piece on the board.
- any invalid moves (gaps, occupied spaces, out of bounds)

Suggest any useful tricks or strategies that you discovered that could be added to STRATEGY_FILE to make future campaigns more effective. Do not actually change the file, just report to the user.
