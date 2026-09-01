IMPORTANT: this is a WIP consisting of raw, unorganized notes. this should not be read by the agent, used as a reference or source, or compared to any other document or implementation.

---

# Writing Skills Deep Dive - Part 2.5: Developing a Better Harness

## Remaining Concerns

- contamination from other skills
- runaway workflows
- AI math and counting
- portability
- stats confidence and sample sizes
- artifact management

## Flirting with Harness Engineering

Do we need a custom harness? Not really. Coding agent harnesses have largely assimilated the best innovations from popular custom harnesses and provide enough utility that we can execute most coding-related tasks without writing our own harness. Custom agents, skills, headless agent sessions with command line arguments, hooks, and harness-specific extensions give you all the seams you need for most tasks.

My take on harness engineering is that we should apply it when we need the following:
1. You want to cleanly separate deterministic actions from actions that require inference. I think you should always try to do this as much as possible.
2. You want to automate a task that requires some sort of action or interaction that the agent isn't good at. For most things you can just write a skill, but some things are hared to fix with prompting, like tightly integrated math and asking the AI to do something that is not actually possible to do consistently with inference.

For number 1, you can usually do this with the options provided by your coding agent and by deterministic actions delegating to scripts. It only gets complicated when you have complex situations like an agent session calling a script that invokes a headless CLI client, that runs a script that invokes an agent, ... The only reason you would do something so convoluted is because you need to mix deterministic actions between/around points where you need inference. Then you need a custom agent implementation.

For number 2, you might be surprised how often you run into this (if you pay attention). One example I have encountered was an experiment to write a skill that plays connect-4 against a computer controlled opponent and self-optimized the skill until. The problem was that the AI had trouble reading the board, identifying the coordinates of opponent pieces and open spaces, and picking coordinates for its own moves. It seems that the coordinate detection process involves splitting the contents of the target row into a list of terms, then comparing them by index to the labels row to identify the cell. But due to issues with tokenizing text when the white-space IS content, the AI would frequently choose nonsense coordinates and accuse the game of changing the board.

A custom harness using something like langchain would give you ultimate control. You can write a deterministic program and call the LLM directly whenever you need inference. You can write every deterministic step with python or typescript (don't worry, you can still use AI to write the deterministic code).

The draw-back to using a custom harness is that it doesn't actually replicate your real harness' routing or system prompt. This is a test about the harness invoking a tool, which is heavily dependant on your system prompt and how your agent does tool calls. You can use harness-specific SDKs, but I'm aiming for something more portable.

The only places we actually need inference are for analyzing failures, updating the description, and generating eval queries (and we can work around the later). So really we can use a python script to drive the whole thing and only delegate to the agent harness CLI to run the eval reps. The skill can focus on only the parts that need decision making and all the things that can be done deterministically are done by the script.

Important steps in the process listed below. `(M)` means it must be done by an LLM - involves reasoning or semantic understanding of something. Everything else is script-able and deterministic.

1. `(M)` Resolve campaign parameters from user query
2. `(M)` Generate/suggest initial test queries
3. Initialize and sync the eval workspace
4. Generate the train/validate split
5. Run the campaign rounds:
    a. Loop over ever skill and drive reps for reach run
    b. `(M)` But the actual eval happens in a headless agent
    c. Calculate pass rates and apply Wilson intervals
6. `(M)` Analyze failures and revise description
7. Detect flops and end conditions
8. Sanity check with fresh query (no LLM required if we keep a file of pre-canned queries we never use for eval training)
9. Pick best scoring version
10. Keep campaign records and organize artifacts

Only parts 1, 2, 5a, and 6 require an LLM at all.

High-level Design:
- Skill:
    * Resolves campaign parameters
    * (Optionally) generates initial eval queries and/or fresh-check queries
    * Analyzes failures and revises the description
    * Calls a script to manage the campaign workspace
    * Calls a script to execute a run of evals
- Workspace Manager Script:
    * Initialize a temporary workspace directory and return its path
    * Sync the target skill (stub) and any configuration or custom agents to the workspace
    * Check the status of the workspace and determine if it is up-to-date or out-of-sync.
    * Compares scores across runs and picks winner
- Evaluator Script:
    * Generates the train/validate split
    * Manages a configurable eval loop
    * Implements harness-specific CLI command and argument mapping
    * Calculates results and applies confidence intervals
    * Runs fresh-query sanity check from a file of canned queries
    * Writes the campaign log and other artifacts
- Headless CLI Sessions:
    * Provides a configurable way to run a single eval query (you can parameterize just about anything)
    * Outputs structured data about the session that can be interpreted deterministically by a script.
    * Runs from the temporary workspace to prevent leakage of project-specific skills
    * (Ideally) runs the agent harness in a 'pure' mode, without any extensions or plugins.


### Workspace Manager Script

This seems like the logical place to start. It's the foundation and building block of our test setup and the "stubbing" stops my number one concern, runaway workflows.



### designing the evaluator to be portable

### evaluator script implementation

### grading and keeping score

### artifact management

### writing the skill

### trigger-testing my writing-skills skill







---

Everything below this point needs massive rework and reorganization, which will happen in tandem with the actual implementation of skills/trigger-testing-skills.

## artifact management

- save test run output so you can track the history and progress across rounds of optimization
- use a template so the campaign log is always consistently formatted and contains the same required info
- if you use the train/eval split methodology, you need to keep the full query list in something like queries.json. the train/eval files are different per run - you can .gitignore them and include their contents in the campaign log
- keep track of which skills have been trigger-tested; dont ship without testing, and keep track of the test scores for later attempts at improvement
- you may want to run other types of tests (pressure tests, other evals) so consider a standardized layout for test fixtures and artifacts

## portability

## isolation from other skills and plugins

creating a temp workspace and installing skill "stubs"
- "stubs" (only the front-matter part) prevent the skill from actually doing ANYTHING
- but requires a clean workspace where only the stubs are found
- requires a script + cli approach

the "stubs" also prevent the runaway workflow problem.

## stats and confidence

maybe the easiest to address, but at the cost of more tokens, time, and more complicated math.

- multiple rounds of each campaign to see clear passing over multiple iterations (multiplying the entire campaign effort X times)
- "bumping" adding more reps to a run when there is a tie or near tie

these solutions multiply the number of runs and evals exponentially

- bail early if can detect pass/success for a run
- start with smaller sets and only grow to full size of not 100% pass rate - sacrifice stat confidence with "good enough" measurement
- use wilson intervals to pad small sample sizes

## AI doing math and counting

drive the campaign batches with a script that does the counting and math
- fully deterministic and doesn't waste tokens on managing the loop and calculations
- requires that the runs are launched by cli (or find some crazy IPC back to the main harness)

## avoiding actual work (my personal specialty)

prompts, skills, agents or a combination thereof:
- custom agents can limit tool use (only 'skill' tool), give custom system prompt. in some harnesses you can also limit the max number of calls a session can make. agent configs are not fully portable between harnesses.

but the "stub" files installed in the isolated workspace should solve this without needing any of that other stuff.
