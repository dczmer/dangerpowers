NOTE: the only places we actually need inference are for updating the description and for generating eval sets or fresh-check queries, and we can work around the later. so really we need a python app or script to drive the whole thing and only delegate to agent harness CLI to run the eval rep.

## artifact management

- save test run output so you can track the history and progress across rounds of optimization
- use a template so the campaign log is always consistently formatted and contains the same required info
- if you use the train/eval split methodology, you need to keep the full query list in something like queries.json. the train/eval files are different per run - you can .gitignore them and include their contents in the campaign log
- keep track of which skills have been trigger-tested; dont ship without testing, and keep track of the test scores for later attempts at improvement
- you may want to run other types of tests (pressure tests, other evals) so consider a standardized layout for test fixtures and artifacts

## Eval Harness

here is where things start to get interesting... we need to run many iterations of tests against a collection of "should trigger" and "should not trigger" phrases and determine if the cases are passing.

concerns:
- ai is non-deterministic. some skills might fire inconsistently across different reps of the same test
- contamination from other skills or extensions may alter behavior in unexpected ways
- each supported harness has it's own unique system prompt, tools, and routing behavior
- agents likely to actually start executing workflows instead of just reporting they triggered the skill
- if agents start running workflows, then you have to worry about isolation and preventing undesired changes, especially outside of the repo root
- can be token intensive and take a long time, especially if it ends up running real workflows

the easiest thing you could do to get started:
1. gather a few "should" and "should not" cases
2. prompt your agent to run each one 10x
3. if a run passes >50%, then pass
4. else update the description and run another round, repeat

but:
- a full campaign of runs for each test case would fill your agent context
- context from previous runs would leak and color the results of subsequent reps
- descriptions from other skills, agents.md files, other plugins can contaminate or alter behavior unexpectedly
- risks actually launching workflows. agents get confused by hypothetical test scenarios, start digging around your system...
- dissonance between system prompt (i am a coding agent) vs task (i am a trigger test evaluator) - the system prompt becomes a distractor
- ai does all the counting and math. ai can't do math. it might be smart enough to make a script, but not reliably on every run
- stats and confidence:
    * enough cases and reps to be statistically significant?
    * what happens with 5/5 splits?
    * is 6/4 or 7/3 a good proof that it's optimized or just random luck?

### stats and confidence

maybe the easiest to address, but at the cost of more tokens, time, and more complicated math.

- multiple rounds of each campaign to see clear passing over multiple iterations (multiplying the entire campaign effort X times)
- "bumping" adding more reps to a run when there is a tie or near tie
- some statistical model for sampling, like wilson 95

these solutions multiply the number of runs and evals exponentially

- bail early if can detect pass/success for a run
- start with smaller sets and only grow to full size of not 100% pass rate - sacrifice stat confidence with "good enough" measurement

### too much context and context leak

use fresh subagents for each test run:
- very easy
- isolated from main session context, previous/subsequent runs
- highly portable between harnesses
- ai still does math and counting
- still leaks from other skills, rules files, extensions
- you can't really predict what other instructions the agent will give to each subagent invocation; it might leak things it observes or try to help the subagents "succeed"

fresh subagents but with no extensions, rule files, plugins:
- solves leak sources but also requires manual process to prepare correct environment
- hard to isolate from global rules files (you can override XDG vars but causes other issues)

use a cli app or custom harness in python/ts
- full control over sources of leaks
- harder, adds dependencies, needs maintenance
- ai can do the math and deterministic steps well
- harness specific cli commands not directly portable

custom harness w/ langchain/etc:
- solves all the leakage problems cleanly:
    * full control over leak sources
    * can drive and count deterministically and only use the LLM for the test assertions
- more complicated, adds more dependencies, needs maintenance and updates
- portable: users just need install harness-specific langchain packages
- does not match the actual target harnesses:
    * doesn't match actual harness system prompt
    * doesn't match actual harness routing rules
    * tool names and schemas don't match (with harness sdk they can but also a portability concern)
    * reverse-engineering these things means tracking a rapidly moving target

### AI doing math and counting

give the agent a tool it can use to record stats and do the calculations
- probably need a new skill and some testing to make sure it uses the tool correctly and doesn't decide to just circumvent your rules

drive the campaign batches with a script that does the counting and math
- fully deterministic and doesn't waste tokens on managing the loop and calculations
- requires that the runs are launched by cli (or find some crazy IPC back to the main harness)

### avoiding actual work (my personal specialty)

prompts, skills, agents or a combination thereof:
- custom agents can limit tool use (only 'skill' tool), give custom system prompt. in some harnesses you can also limit the max number of calls a session can make. agent configs are not fully portable between harnesses.

creating a temp workspace and installing skill "stubs"
- "stubs" (only the front-matter part) prevent the skill from actually doing ANYTHING
- but requires a clean workspace where only the stubs are found
- requires a script + cli approach

### My solution

### third-party eval harnesses to consider

## how to improve a description based on eval results

