# Writing Skills Deep Dive - Part 2.5: Developing a Better Harness

## Remaining Concerns

These are the issues with that I'm most concerned with:

- Contamination from other skills
- Runaway workflows
- AI math and counting
- Portability
- Stats confidence and sample sizes
- Artifact management

### TLDR; Design Decisions to Address Concerns

- Run CLI with parameters to control sources of contamination (mostly)
- Run from temp directory to isolate from actual project source
- Use a script to drive the eval loop, score results, and any other math or counting
- Use a strategy pattern to map an eval description to harness-specific CLI command
- Use simple, static 10x reps (no bumps, dynamic reps, etc)
- Use a train/validate partition (if >10 cases)
- Apply Wilson intervals to pad the small sample size
- Use fresh query sanity check to make sure we haven't overfit our test queries
- Put a cap on the number of iterations the optimization loop can run
- Create per-skill directories to manage artifacts and campaign logs, and a manifest file to track test status of the skill
    
### Contamination from other skills

When we test software, it's important to test in a stable, consistent environment where conditions are exactly the same between runs. Otherwise you can't count on your results to be consistent or accurate. You can't know for sure if the change you made actually fixed the issue or if something in your test environment affected the behavior to make it pass, or was the reason it failed on the last run.

Other skills from your project, global settings, or plugins and extensions contain description text which is in your system prompt on every run. These descriptions can influence agent reasoning and affect decision making, possibly causing it to not load your skill or to load another skill.

You may not consider this a problem for testing skills, since you would probably intend to use your skill in your normal agent load-out, where it will live along-side other skills and extensions you use from day-to-day. It's also somewhat difficult to solve this completely without writing a custom harness that ignores your global settings and skills (~/.agents, ~/.claude, etc).

My approach is to use the CLI to launch a headless agent session and use parameters to disable as many sources of contamination as possible. I also run the agent instance from a temporary directory so it doesn't automatically pick up any local repository-defined skills or settings and so it doesn't accidentally start making changes to my source.

When using opencode, I can't really prevent it from loading global configuration and skills at startup (you could mess with XDG environment variables to point to a fake ~/.config location, but that has other problems). But I can disable all plugins and extensions with a `--pure` argument.

### Runaway Workflows

Some skills just provide information to keep in context, that the AI can use when making its own decisions later. Other skills drive a workflow or procedure. What happens when your trigger test loads a skill that tries to run a workflow that does actual work?

In the best case scenario, it burns a bunch of extra tokens and makes each test eval take exponentially longer to run. In the worst case, it makes a bunch of changes you didn't want. If the test query you gave it makes no sense for its current state, and the state of the current working directory, the AI still has to try to "solve" your problem. It doesn't know this was a test, so it starts reasoning and rationalizing about what you wanted and digging through your host system for context. This leads to nonsense edits and changes to your project (or your host system if you don't have good guardrails in place).

My solution for solving this issue is to manage a "test workspace" in a temporary directory, and to copy out the skill under test to this workspace, but only the frontmatter part and not the body. When the test triggers the skill, the skill does nothing because it has no body content and no workflow to launch.

Another mitigation I use is to write a custom agent definition that limits tool calls to only "skill" and "read", and has a system prompt that tells the agent that it can't use any tools and should just load the skill and report. This is not 100% portable, as support for custom agents is harness-specific and they don't have standard frontmatter schemas from harness to harness.

I also cap the number of turns the agent can take at 3 and run the eval reps with a 30s timeout to handle anything that gets past those other layers.

### AI Math and Counting

On a good day, your agent would write stats to files on disk and/or write a program to drive the parts that require counting and math. On a bad day it will just rely on inference alone and produce inaccurate results.

We can take that decision away by writing a deterministic script to drive the campaign and do the math and looping. In fact, we should try to do as much of the deterministic stuff with scripting as we possibly can, and only use the AI for decision making and semantic evaluation.

### Portability

I'd like to support opencode, Claude Code, and pi, at minimum.

This has been a difficult problem so far. Even though "agentskills" is a standard, the way you use tools, CLI commands, custom agents, deal with contamination sources are all different. Some agents may not even support all of the options and concepts we want to include.

I'm using the standard `.agents/skills` layout inside of the temporary workspace directory because most harnesses support this standard. That makes the harness-specific directory layout issue easier.

The other issues is translating a description of a test eval into a harness-specific CLI command. The solution I chose for this was to factor-out an "evaluator" object from the test harness and implement a strategy pattern. Each target harness has it's own evaluator implementation with it's own `evaluate` method. The evaluator turns a list of general eval parameters into a specific CLI command and parses the results to return a standard verdict response.

### Stats, Confidence, and Sample Size

This is another "how hard do you want to make it" question. For most of us, a simple campaign that shows a majority of passes over a set of X reps is enough. In the world of ML and training, you would want as many samples and repetitions as possible to refine your results into a number you can be confident about.

I'm pretty content with the 10x reps to give better confidence than the recommended starting point of 3 reps. 10x reps are more likely to give a better sample than 3, but even that is probably a miniscule sample size compared to what we'd need to be confident when the results are not repeated perfect scores across multiple models.

Some techniques used in ML training evals involve dynamically altering the eval plan to add reps and introducing more complicated math and statistics concepts that I am not that familiar with myself. I'm choosing to keep the simple, static 10x loop and apply Wilson Confidence Intervals to pad out the results.

Since this is sampling results across an infinite source set, running the entire trigger testing campaign repeatedly gets us closer and closer to a number that you could bet on. We don't plan to bet on these results, we just need a decent approximation.

But even a single campaign could require looping over the entire test suite mulitple times, as it optimizes the description

Testing against the exact same queries repeatedly ensures the description is well-tuned for those specific queries. But one technique from ML we can borrow to vary out tests is the "train/validate" split: Split queries into two groups, optimize the description based on observed failures from the 'train' set, verify improved descriptions against the 'validate' set of queries. You still end up testing all of the queries in your list, just some are tested for tuning the description and others are the final test of the improved description.

One more point here: you don't want the optimization loop to run forever if it gets stuck. Put a cap on the number of iterations the loop can make and pick the best result from the campaign.

### Artifact Management

You are going to want to save your set of test queries, so you can reuse them on future campaigns and so you can add more cases to them over time.

You also should keep some kind of record that the target skill has had a successful trigger-test run (don't ship without evals), along with the score it received. I don't know if it's necessary to keep a full history of every past campaign but you should at least keep the previous run for reference.

So you will need some place to store these artifacts and keep them organized. I chose the following:

1. A 'test workspace' in a separate directory to manage all artifacts. I have been using a 'skills-workspace' directory as a sibling directory to the main 'skills' directory, with subdirectories for each skill. Anthropic uses a `skills/<SKILL_NAME>-workspace` convention. I'm not sure if it matters, and there isn't an industry standard.
2. Keep a top-level `manifest.json` that maps the version (checksum of the skill file) to the date and score of it's last run. If the skill file changes, the checksum will change and we'll know it needs another test campaign.
3. I expect to run other types of tests later, so I'm using subdirectories for organizing the type of test: `skills-workspace/writing-skills/trigger-test/`. The manifest file should also support mapping multiple test types to the skill file version.
4. Keep the test queries in a file called `queries.json` under that `trigger-test` subdirectory.
5. Keep results from previous campaign runs under `trigger-test/campaigns`.

When we are running the optimization loop, we also have to keep track of the score from all previous iterations of the current campaign, along with the version of the description they changed, so we can compare and select the best one at the end. This can be done in memory or in a temporary folder.

## Flirting with Harness Engineering

Do we need a custom harness? Not really. Coding agent harnesses have largely assimilated the best innovations from popular custom harnesses and provide enough utility that we can execute most coding-related tasks without writing our own harness. Custom agents, skills, headless agent sessions with command line arguments, hooks, and harness-specific extensions give you all the seams you need for most tasks.

My take on harness engineering is that we should apply it when we need the following:
1. You want to cleanly separate deterministic actions from actions that require inference. I think you should always try to do this as much as possible.
2. You want to automate a task that requires some sort of action or interaction that the agent isn't good at. For most things you can just write a skill, but some things are hard to fix with prompting, like tightly integrated math and asking the AI to do something that requires strategy.

For number 1, you can usually do this with the options provided by your coding agent and by deterministic actions delegating to scripts. It only gets complicated when you have complex situations like an agent session calling a script that invokes a headless CLI client, that runs a script that invokes an agent, ... The only reason you would do something so convoluted is because you need to mix deterministic actions between/around points where you need inference. Then you need a custom agent implementation.

For number 2, you might be surprised how often you run into this (if you pay attention). One example I have encountered was an experiment to write a skill that plays connect-4 against a computer controlled opponent and self-optimized the skill until it could beat/tie a "minimax" implementation. The problem was that the AI had trouble reading the board, identifying the coordinates of opponent pieces and open spaces, and picking coordinates for its own moves. It seems that the coordinate detection process involves splitting the contents of the target row into a list of terms, then comparing them by index to the labels row to identify the cell. But due to issues with tokenizing text when the white-space IS content, the AI would frequently choose nonsense coordinates and accuse the game of changing the board.

A custom harness using something like langchain would give you ultimate control. You can write a deterministic program and call the LLM directly whenever you need inference. You can write every deterministic step with python or typescript (don't worry, you can still use AI to write the deterministic code).

The draw-back to using a custom harness is that it doesn't actually replicate your real harness' routing or system prompt. This is a test about the harness invoking a tool, which is heavily dependant on your system prompt and how your agent does tool calls. You can use harness-specific SDKs, but I'm aiming for something more portable while still matching the real harness environment as much as possible.

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

Only parts 1, 2, 5a, and 6 require an LLM at all. Using an LLM to control the looping and math is unreliable, and scripting the rest of the steps makes the process faster,  more efficient, and _free_.

## Design

High-level Design:

- Skill:
    * Resolves campaign parameters
    * (Optionally) generates initial eval queries and/or fresh-check queries
    * Generates the train/validate split from input file
    * Analyzes failures and revises the description
    * Calls a script to manage the campaign workspace
    * Calls a script to execute a run of evals and collect responses
    * Runs fresh-query sanity check from a file of canned queries
    * Writes the campaign log and other artifacts
- Workspace Manager Script:
    * Initialize a temporary workspace directory and return its path
    * Sync the target skill (stub) and any configuration or custom agents to the workspace
    * Check the status of the workspace and determine if it is up-to-date or out-of-sync.
    * Compares scores across runs and picks winner
- Evaluator script and evaluator strategy:
    * Implements harness-specific CLI command and argument mapping
    * Calculates results and applies confidence intervals
    * Provides a configurable way to run a single eval query (you can parameterize just about anything)
    * Runs from the temporary workspace to prevent leakage of project-specific skills
    * (Ideally) runs the agent harness in a 'pure' mode, without any extensions or plugins.

We'll build and test the workspace manager, then build and test the evaluator script while manually managing the workspace. Then we tie it all together with the skill and implement the optimization loop.

### Workspace Manager Script

This seems like the logical place to start. It's the foundation and building block of our test setup and the "stubbing" stops my number one concern, runaway workflows.

Write a good "help" menu so the agent can work with the script accurately based on high-level instructions.

```
usage:
  trigger-test.sh init
  trigger-test.sh sync --skill NAME --source DIR --workspace DIR
  trigger-test.sh status --skll NAME --source DIR --workspace DIR
  trigger-test.sh cleanup --workspace DIR

init    creates one campaign workspace and prints its path on stdout.
sync    copys the source skill (front-matter only) to the target workspace,
        along with any other required resources for the campaign.
        run after every description change to sync the stub file.
status  provides an easy way to verify the workspace is in a a valid state
        and that the skill stub file matches the current version of the real
        skill description.
cleanup removes the workspace (--workspace or $TRIGGER_TEST_WORKSPACE).
```

[Link to completed script](../../../skills/trigger-testing-skills/scripts/workspace-manager.sh)

Important note when writing scripts: validate and catch failures and show the exact error reason, so the agent can self-correct. An opaque "error happened" message is not helpful.

### Evaluator Script Implementation

The evaluator script has a few moving pieces and a couple of custom data structures. As always, I try to use as few dependencies as possible, outside of the python standard library.

> IMPORTANT NOTE: This was my design input for a minimal slice of this full script. This is not what the final product for this phase looks like. See [the actual script](../../../skills/trigger-testing-skills/scripts/evaluator.py) for the actual implementation. Use this section only as context for the desired approach and important design concerns.

Starting with the 'inner' workings of the evaluator, create a script that runs a series of eval reps over a single query in an existing and pre-synced workspace.

My initial sketch:

```mermaid
classDiagram
    class Evaluator {
        +str skill
        +str query
        +Path workspace
        +str|None model
        +str|None effort
        +str[] train_set
        +str[] validate_set
        +str fresh_query
        +EvalStrategy strategy

        +eval_batch(int reps) : Results
        -score_results(): double
    }
    class EvalStrategy {
        +evaluate(str skill, str query, Path workspace, str model=None, Effort effort=None) : Verdict
    }
    class Results {
        +str description
        +str query
        +double score
        +Verdict[] verdicts
    }
    class Verdict {
        +bool triggered
        +str reasoning
    }
    
    Results o-- Verdict
    EvalStrategy --> Verdict
    Evaluator *-- EvalStrategy
    Evaluator --> Results
```

Classes without any functions can be simple `dataclasses` and the EvalStrategy can just be a function that matches a protocol/interface. We also need an enum to shape the possible input values for "effort":

For the target of an opencode-specific EvalStrategy, here are the relevant opencode cli command arguments:

```bash
opencode \
    # start from workspace directory
    --dir WORKSPACE \
    # disable all plugins and extensions
    --pure \
    # select model and reasoning/effort (optional)
    --model MODEL \
    --variant EFFORT \
    # use json structured output where possible
    --format json \
    # verbose output so we can see reasoning and other info
    --print-logs \
    --log-level INFO \
    # auto-approve - this is dangerous, we'll fix it a bit later
    --auto \
    QUERY
```

If 'effort' and/or 'model' are not used, they are not included in the command.

I fed my agent this document as an input and had it design the first version. We had a few rounds of refinement and the agent validated (or invalidated) some of my assumptions. Notably, we made some changes to the arguments for the opencode command and we added parallel reps and a smoke test rep. Another big change is that the AI decided to implement a more complicated form of the confidence interval calculation, which I chose to allow.

Here's the implementation plan for this phase: [phase-1-evaluator-script-plan](./phase-1-evaluator-script-plan.md)

And here is an example of a manual run using the script on an existing workspace:
```bash
python3 skills/trigger-testing-skills/scripts/evaluator.py run \
    --skill writing-skills --workspace /tmp/trigger-test.Zp8Q9DCdzj \
    --query "turn this outline into a skill" --expect trigger \
    --model kimi-for-coding/k3 --variant minimal --reps 3; \
    echo "exit=$?"
# trigger test: writing-skills
# workspace: /tmp/trigger-test.Zp8Q9DCdzj
# model: kimi-for-coding/k3  variant: minimal  reps: 3  timeout: 30s
# [rep   1] started
# [rep   1] completed: triggered
# [rep   2] started
# [rep   3] started
# [rep   2] completed: triggered
# [rep   3] completed: not-triggered
# 
# query: "turn this outline into a skill"   expected: trigger
#   run   1: triggered      pass
#   run   2: triggered      pass
#   run   3: not-triggered  fail
#   summary: 2 pass / 1 fail / 0 void (3 runs)  wilson95: [0.208, 0.939]  score: 0.208
# exit=0
```

### Implementing the Campaign and Skill

High-level outline of how the skill works:

- Resolve required parameters from the user prompt
- Create and sync a new workspace
- Offer to create queries.json and some initial queries, if not exists
- Verify the queries are actionable (see "Actionable Queries" below)
- Split queries.json into "train" and "validate" sets

Then start the outer campaign loop (max 3 iterations, early exit on a perfect train round):

- For each 'train' query:
    * Call the evaluator script to run X (default 10) reps of the eval
    * Collect the results
    * Write a log with the query, current description, and train score
- If there are no train failures, exit the loop early
- Analyze failures and refine the description
- Repeat this outer loop until reach max iterations

After the evaluation loop is done:

- Select a winner (highest train score across iterations)
- Check the winning description against the 'validate' set (once — the held-out exam)
- Run a fresh query sanity check (generate one on-demand for now)
- Log the result
- If the sanity check failed, stop. Do not start the entire loop again. Never use a fresh query for training.

At this point, we're just logging to standard out. In the next phase, we will implement better artifact management.

#### Actionable Queries

Some queries, like "turn this outline into a skill", WOULD trigger our target skill, but since no actual outline exists, they will instead timeout while trying to figure out what outline we're talking about, or else give up and never invoke the skill.

For a query to be 'actionable' it must reference something real so the agent doesn't get stuck. In the case of the "outline" above, fabricate an outline of some process and write it to a file in the workspace, then reference it by name.

If the target query is not reasonably actionable, or if it's not actually a request that an agent would process (like a statement that doesn't ask for any action), then reject it and surface to the user. Offer to revise the query and explain why it's not acceptable.

#### Implementation

Like the previous phase, I fed my design and this document (along with the trigger-testing guide) to the agent to develop a plan and iterate on the details.

Here is the plan file that was created: (phase-2-campaign-and-skill-plan)[./phase-2-campaign-and-skill-plan.md].




### Custom Agent

### Artifact Management

### Trigger-Testing my `writing-skills` Skill

### Conclusion
