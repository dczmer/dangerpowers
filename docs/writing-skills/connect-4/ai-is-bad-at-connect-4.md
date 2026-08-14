> TODO: `writing-skills/part-1` created a couple of basic skills to teach an agent how to interact with the game server, but doesn't get into adding strategy or behavior rules yet. I got a bit carried away trying to teach the AI to play the game and that lead to exceeding the scope of part-1. so i have trimmed that version down to just my observations - that version of the skill isn't very useful yet. this project will be where we really get into teaching the ai to play and fixing the issues that were causing scope creep in part-1.

Objective:
- Start with an optimized skill file describing how to play the game, but no strategy or behavioral rules (yet)
- Start with a 'campaign' skill or prompt to launch the individual games and analyze them for errors, mistakes, and strategy
- Update the skill to teach it new strategy and how to avoid problems

the main problem is that the AI - even the fancy frontier models - frequently fail to interpret the board, identify coordinates, or locate pieces from the plain text display of the game board.

i expect this is just something the AI is not good at. even adding JSON data for the AI didn't completely fix the issue (but seemingly made it less frequent).

i think this will be an illustration that we sometimes need to build new ways for the agent to interact with it's target/subject, so that it only has to do the reasoning/decision-making parts, and things like reading and analyzing the board need to be provided as high-level actions that the agent can use.

# Connect-4 Skill Comparison and Score Tracker

Compare the initial performance of three versions of a "connect-4" skill:
1. A simple prompt for a baseline (no skill)
2. A human written skill (not using writing-skills)
3. A human written skill (using writing-skills)
4. An AI written skill

The game implements multiple opponent player "strategies":
1. Completely random (it will pick a wining move if one is open, so not 100% random)
2. Heuristic-based
3. Minimax

Run series of 10x matches against each combination of:
1. Skills
2. Opponent strategies
3. Models: low-powered local model vs frontier model

We haven't implemented any behavioral rules or strategies yet - these skills are just about interacting with the game interface and leaving it up to the AI to figure out what to do. So I don't actually expect a lot of difference between how the various implementations perform.

I suspect that baseline prompt is probably sufficient and the skills will provide little value. But once we start training the skill with test evals, we'll start adding behavior rules and strategy that will improve the skills. That's something you can't do with just a prompt.

## Rules

Keep it very simple for this experiment:

1. Run a series of matches.
2. Every game runs in a new subagent with fresh context.
3. Every new game starts by starting a 'new' game.
4. Keep a record of wins, losses, and draws.
5. When the campaign is completed, display the win/loss/draw metrics to the user.

## Skill Implementations

### No AI (simple prompt)

As a baseline, see how well a simple prompt performs. Tell the AI where the game server is and how to check `/help`, then let it work out the rest on its own.

The prompt:
> there is a simple http-based connect-4 game running on 127.0.0.1:8000 that you can interact with by making GET requests using curl. start by curling the `/help` endpoint to get instructions. your objective is to beat the computer opponent in a best of 10 games tournament. run each new game in a general subagent, passing the instructions as context and instructing it to try to beat the computer in a single game (ONE ATTEMPT ONLY). play every game in the series - do not stop when you have one enough games to win the series. when the series is done, print a summary of wins, losses, and draws.

### Human Written Skill (not using writing-skills)

Hand-written skill file made by a human without much thought into optimizing, but (presumably) more concise and directed than an AI-generated skill.

Result: [human-skill.md](./human-skill.md)

(18 lines, 228 words)

### Human Written Skill (using writing-skills)

Hand-written skill that is optimized/scrubbed by the `writing-skills` skill we developed in this chapter.

Result: [with-writing-skills.md](./with-writing-skills.md)

(24 lines, 202 words)

The best way to judge this version of the skill is to open it side-by-side with [human-skill.md](./human-skill.md).

### AI Written Skill

Use a prompt to ask the AI to create a skill to play the game:

> there is a simple http-based connect-4 game running on 127.0.0.1:8000 that you can interact with by making GET requests using curl. start by curling the `/help` endpoint to get instructions. your objective is to write a new skill, called `ai-skill.md`, that will teach an agent how to play the game and interact with the server. do not worry about strategy, only the rules and process of using and interacting with the game. play one full game to observe behavior and constraints before writing the skill.

Result: [ai-skill.md](./ai-skill.md)

(74 lines, 720 words)

---

## Campaigns

### Campaign Skill

Let's create a custom skill to orchestrate a campaign and analyze the subagent session to see if it had issues and how well it played.

[connect-4-campaign.md](connect-4-campaign.md)

### vs Random Strategy

#### Local Qwen3.5-9b (4bit quant on 16GB VRAM)

| skill | W | L | Draws |
|-|-|-|-|
| no skill | 5 | 5 | 0 |
| `human-skill.md` | | | |
| `with-writing-skills.md` | | | |
| `ai-skill.md` | | | |

#### Game 10 (Final) - No Skill:

Loss (O wins) - Computer had 4 in a vertical column at column 4 (rows 0-3)

#### Kimi3 ('high' reasoning)

| skill | W | L | Draws |
|-|-|-|-|
| no skill | 10 | 0 | 0 |
| `human-skill.md` | | | |
| `with-writing-skills.md` | | | |
| `ai-skill.md` | | | |

### vs Heuristics Strategy

#### Local Qwen3.5-9b (4bit quant on 16GB VRAM)

| skill | W | L | Draws |
|-|-|-|-|
| no skill |   |   |   |
| `human-skill.md` | | | |
| `with-writing-skills.md` | | | |
| `ai-skill.md` | | | |

#### Kimi3 ('high' reasoning)

| skill | W | L | Draws |
|-|-|-|-|
| no skill |   |   |   |
| `human-skill.md` | | | |
| `with-writing-skills.md` | | | |
| `ai-skill.md` | | | |

### vs Minimax Strategy

#### Local Qwen3.5-9b (4bit quant on 16GB VRAM)

| skill | W | L | Draws |
|-|-|-|-|
| no skill |   |   |   |
| `human-skill.md` | | | |
| `with-writing-skills.md` | | | |
| `ai-skill.md` | | | |

#### Kimi3 ('high' reasoning)

| skill | W | L | Draws |
|-|-|-|-|
| no skill |   |   |   |
| `human-skill.md` | | | |
| `with-writing-skills.md` | | | |
| `ai-skill.md` | | | |

---

#### Notes

#### Smoke Test (First Attempts)

The first attempts at running these benchmarks failed in a surprising way: neither the local LLM or the frontier model could reliably "read" the board and identify cells by the correct coordinates.

An example from a real game:
```
| | | | | | | | 5
| | | | | | | | 4
| | | | | | | | 3
| | | | | | | | 2
| | | | | | | | 1
| | | |O| | | | 0
+-------------+
 0 1 2 3 4 5 6
your move (X).
```

The "O" is at column 3, row 0.
But the AI reasoning says:

> The board shows computer (O) in column 1, row 0.

So the AI couldn't detect which spaces were open or blocked, and it also couldn't correctly specify the coordinates of the cell where it wanted to move. So both models also made frequent invalid moves (specifying an occupied or invalid cell).

Some possible causes that popped into my head:
- LLMs can't count. Maybe it's trying to count row and column offsets?
- Confusion over the axis labels being bottom+right instead of top+left?
- Does this _need_ to be structured JSON? But models read markdown tables just fine...

I proposed these considerations to the frontier model, asking it to run a game first and observe what happens. It misread the board on the very first move.

It explained that it wasn't counting rows, it was comparing the string character-by-character with the off-screen axis label.

When trying to identify a cell inside of a given row, it would only look at this:
```
| | | |O| | | | 0
```
And compare it to this:
```
 0 1 2 3 4 5 6
```

The label row is not delimited by "|" and it doesn't contain that very last column, which is actually the x-axis label.

The thinking traces also showed that it didn't know what to do with " " values in a cell - it sometimes thought they were empty cells, other times it would think they were looking at a label column, or even seeing multiple columns as just one cell.

The solution we came up with was to move the labels to top and left, give the label cells borders, and use "·" characters instead of " " to represent an empty cell.

```
| - | 0 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|---|
| 5 | · | · | · | · | · | · | · |
| 4 | · | · | · | · | · | · | · |
| 3 | · | · | · | · | · | · | · |
| 2 | · | · | · | · | · | · | · |
| 1 | · | · | · | · | · | · | · |
| 0 | · | · | · | · | O | X | · |
```

I prefer this over the JSON solution because it's easy for me to read when I watch/review the campaigns or when I play against the computer directly.

After this change, even the crappy local model was able to identify coordinates with 100% accuracy.

#### No Skill (Prompt Only)

Opponent Strategy: `random`

Both models intuitively used the "play the center" strategy on every game.

##### Local Model

###### vs Random Strategy

Wins:   5
Losses: 5
Draws:  0

Knew to start in the center, but didn't show much strategy after that.

###### vs Heuristic Strategy

####### Run 1

Wins:   2
Losses: 8
Draws:  0

On the first run, the AI created a python script to play the game. It also had trouble interacting with the `/move` API and there were a few instances where it failed to read the board correctly.

The main orchestration agent didn't give the subagents any details about how to interact with the game or even how to get the `/help` info. Each session had to figure this out before they could start playing.

This is a good example of why we DO need a skill, especially when using free local models. A skill would ensure consistent instructions and context before each run and a skill can be modified so the agent "learns" how to play better.

####### Run 2

Wins:   1
Losses: 3
Draws:  0

This time the orchestrator gave the subagents better instructions and the games were much more competitive.

Still, it was too dumb to go for wins or blocks most of the time.

It also failed to read the board a few times. In one game it got caught in a doom loop constantly trying to move to an occupied space, then failing to read the board, then trying again..

I think we might need to try the JSON approach. Maybe the hybrid text + JSON solution.

I think this is enough to prove the non-skill version _isn't_ good enough, and a skill is probably required to give the local model a fighting chance.

##### Frontier Model

###### vs Random Strategy

Wins:   10
Losses: 0
Draws:  0

Most games, the random opponent wouldn't put up much of a fight and the AI could win in 4-6 turns.

But when the board started to get complicated, the amount of thinking that the agent had to do started increasing exponentially. It thought about setting up "double-threats" and it also worked through every possible move and whether the move results in a board that the AI could possibly win. Maybe I shouldn't have run with high reasoning enabled.

Oooh, after 10(!) minutes of thinking it said:
> You know what? The strategy only matters if the computer plays optimally. Looking at their past moves, it may be making playing randomly. I should push aggressively for a win and not worry about blocks.

And then it immediately won the game without a challenge.

The final report called the opponent "weak". Brutal.

#### human-skill

Using the `connect-4-campaign` skill to orchestrate and the `human-skill` skill to play.

##### Local Model


##### Frontier Model

###### vs Random Strategy

###### vs Heuristic Strategy

Wins:   6
Losses: 4
Draws:  0

- still having occasional issues reading coordinates on the board
- this time it was able to tell me that it attributed 2 losses, and one failed/invalid move to misreading the board.
- normally i ignore most of the thiking - the AI figures out a different way to the solution every time. but in this case it showed that the agent wasn't able to play the game effectively, so that ruins our entire eval strategy.

---

- record how many failed commands/requests, board read errors (better criteria for judging these skills)
- add json data at bottom of response: list of valid move coordinates, coordinates of pieces already on the board.
- new strategies: always block, only offense
- write artifacts, hand-offs with consistent templates, specific locations
- SKILL LEARNING: always poll directly before making move, ensure it's your turn. witnessed invalid moves because the AI tried to move based of a stale version of the board from while the opponent was thinking.
- need to "teach" it how to do things that it's bad at doing now. locating pieces, interpreting coordinates, looking for patterns on the board, etc. make a high-level interface for the model to interact with.
- since we're not testing strategy yet, what is probably more interesting is how effectively the different skills work with the game and avoid making mistakes. number of failed commands, incorrect coordinate reads, failed commands for games you lost, ...

- with JSON data fix:
  * local model:
    + human-skill:
      + vs. random: 9/1/0. pretty consistent by stacking 4 in column 3.
      + vs. Heuristic: 2/8/0. clearly room for improvement.
      + vs. minimax: 0/10/0.
    + with-writing-skills:
      + vs. random: 8/2/0
      + vs. Heuristic: 4/6/0
      + vs. minimax: 
      + at one point interpreted the board and decided the opponent had one, even though it was wrong. it should only go based on the message below the board, it said "your turn".

it just can't do it. the subagents keep incorrectly determining that the opponent won, restarting the game in a loop.
