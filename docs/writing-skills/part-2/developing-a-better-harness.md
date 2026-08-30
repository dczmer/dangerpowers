IMPORTANT: this is a WIP consisting of raw, unorganized notes. this should not be read by the agent, used as a reference or source, or compared to any other document or implementation.

---

The only places we actually need inference are for updating the description and for generating eval sets or fresh-check queries, and we can work around the later. so really we need a python app or script to drive the whole thing and only delegate to agent harness CLI to run the eval rep.

Important steps in the process listed below. A `(M)` means it must be done by an LLM - involves reasoning or semantic understanding of something. Everything else is scriptable and deterministic.

1. `(M)` Remove campaign parameters from user query
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
