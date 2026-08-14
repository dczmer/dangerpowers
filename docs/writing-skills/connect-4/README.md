A couple of simple multi-player games that the AI can play against a computer opponent by creating and optimizing skills to control how it plays the game.

The games are implemented as a single-session web server and the player (the AI) interacts by making GET requests to the running server. The '/help' endpoint provides instructions for play and a reference of available commands and arguments.

The games implement an opponent "strategy" selection: for example: random moves, heuristic based moves, minimax. A plan for later is to implement a strategy that backs to another LLM or agent harness to implement the computer's moves.

Then we can use these games to develop skills and also battle one AI model and prompt against another. Very exciting.

Plan of action:
1. `part-1`:
  a. write a skill definition by hand, keep concise and direct
  b. write a skill definition by using the part-1 version of writing-skills
  c. write a skill definition without writing-skills, by telling the AI to check '/help' to get the basic instructions and telling it to start a new game and then play to win. (NOTE: these are "solved" games. prevent the AI from searching the internet for solutions or this won't be very interesting)
  d. compare the behavior of all 3 skills by running best of 5 matches against the computer, for each opponent strategy, and using both a weak local model and a frontier model for comparison.
  e. select a winning skill to take to the next level (part-2)
2. `part-2`:
  a. augment writing-skills and add trigger-testing support
  b. run a trigger testing campaign on writing-skills
  c. run a trigger testing campaign on the new skill
  d. not very exciting, but the next part will be more interesting
3. `part-3`:
  a. augment writing-skills and add pressure-testing support
  b. run a pressure test campaign on the writing-skills skill
  c. run a pressure test campaign on the new skill
  d. write a ralph-loop to auto-optimize the new skill
  e. run campaigns using the new skill vs. the computer opponent
  f. curious to see if the advanced AI models will try to do anything interesting, like trying to exploit the server or searching for solutions on the internet.
