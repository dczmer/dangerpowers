> TODO: make up a fake skill desc and a query that would not 100% pass, then work through it along with the steps in the guide - use it for the requested examples and illustrate our tuning process as we walk through the "running a simple eval" process.

# Writing Skills Deep Dive - Part 2: Trigger Testing

The skill `description` field is the primary triggering mechanism. When the agent starts up, it loads all skill front-matter into context along with instructions to read the corresponding skill file when a matching trigger phrase is encountered.

But LLMs are non-deterministic and don't always load your skills the way you expect:
- Sometimes the wording of your description is passive or worded in a way the AI can easily rationalize away.
- Sometimes the contents of the current context window may conflict and cause the AI to decide NOT to load the skill.
- If the description paraphrases what the skill actually does, the AI may decide the description provides enough instruction and doesn't bother to load the skill.
- A vaguely written description may trigger too often, hijacking requests for other skills or invoking skills at the wrong times.

Trigger testing provides feedback to drive an optimization loop, analyzing failures to identify specific category of failure mode, updating the description, and repeating until the results are improved.

## What is Trigger Testing?

A trigger test campaign aims to accomplish the following:

- Evaluate how frequently a skill triggers for pre-defined "positive" trigger phrases.
- Evaluate how frequently a skill triggers for pre-defined "negative" trigger phrases (false-positives).
- Optimize the description to achieve higher positive rates and lower false-positive rates.

> TODO: illustrative graph depicting a skill eval rates improving over multiple runs

We can do this by running a query in a fresh session or subagent and checking to see if it loaded the desired skill. If your harness supports it, you can even see the thinking or reasoning around _why_ it chose to load, or not to load, the skill.

Since LLM evaluation is non-deterministic, we need run multiple tests over the same prompts to get a good measure.

## Optimizing Descriptions

> TODO: briefly explain "overfitting" and "grounding", and give an example of a desc that overfits to a specific test query

Here is list of skill optimization tips from https://agentskills.io/skill-creation/optimizing-descriptions, paraphrased by me:

- **Use imperative phrasing**. Tell the agent when it should use this skill ("Use this skill when..."), don't just describe what it does.
- **Focus on user intent, not implementation**. A good description helps the agent match the user's request to the appropriate skill. Focus on what the skill achieves and not how it works.
- **Err on the side of being push**. Make it clear to the agent exactly which situations apply, and explicitly list specific cases or exceptions that might cause the agent to have to reason about the decision. "Use this ... even when the user didn't explicitly mention 'CSV'."
- **Keep it concise**. Keep descriptions minimal to maintain context overhead space, but give enough detail to cover the skill's scope. The specification imposes a hard limit on description length at <= 1024 characters. The shorter, the better.

> TODO: examples of each bullet point above

> TODO: expand the following sentence fragment based on the explanation given in part-1/README.md
Never use first-person voice in a skill description

## Running a "Simple" Eval

If you use Claude Code, try [their skill-creator plugin](https://claude.com/plugins/skill-creator). There are other tools, libraries, and eval harnesses you can probably find if you don't want to write your own, but I suggest working through the manual process once to get some insight into how it works and what trade-offs you might be making with the implementation you are using. The methodology and harness you use have more nuance and more impact on the test runs then you might expect.

But I'm using opencode and pi mostly, and I want to dissect how the process works for myself. So I needed to understand the process well enough to know how it works.

It turns out running self-optimizing trigger-testing process is a little more complicated than it might seem. Even the agentskills.io guide and the skill-creator plugin do not explicitly address some of the issues i have run into, like skills running away doing real work after triggering, or descriptions from other installed skills contaminating the test scenario.

A _highly_ simplified process:

1. Write a list of test prompts and mark each one as "should trigger" or "should not trigger," probably in a json or yaml file.
2. Run 10x reps for each prompt to get a good sample.
3. Use fresh subagents (or fresh headless sessions) to run each test eval rep (maybe in parallel).
4. Analyze the results and determine failure _categories_.
5. Address the failures based on category, don't just add keywords that would over-fit for your test cases.
6. Modify the prompt to address the issues.
7. Repeat the process.
8. Compare results across each iteration and pick the best (not necessarily the last) version.

> TODO: mermaid flowchart covering the process in the list above

### Write the Test Prompts First

Start by writing a file to collect real prompts that you would want to trigger the skill, as well as a collection of those that you would not want to trigger the skill.

> TODO: example of query file, in json, with 'query' and 'shouldTrigger' properties.

Keep them somewhere safe so we can reuse them on future test campaigns. Anthropic recommends using a `skill-workspace` folder hierarchy as a sibling to the 'skills' directory, to keep test artifacts out of the skill folder.

> TODO: my test artifact directory structure example here

Vary test cases across the following axes for better coverage:

| Axis | Variation |
|------|-----------|
| Phrasing formality | "write a PRD" vs. "draft the requirements doc" vs. "I need to spec a feature" |
| Explicitness | names the domain outright vs. describes a need without naming the skill |
| Detail level | bare one-liner vs. buried in a long message with file paths and constraints |
| Complexity | single-step request vs. one link in a larger chain ("after the research is done, also...") |

> TODO: examples of should-trigger queries for a fictional skill, varied over each axis

For the negative cases, use **near-miss** negatives — queries that share keywords or concepts with the skill but need something different. `"What's the weather?"` is a weak negative: it tests nothing, because no skill would trigger on it. A strong negative for `writing-prds` is "help me write a README for this library" — same surface keywords ("write", "documentation"), different need.

Reject weak negatives at design time. A near-miss negative that the description correctly *doesn't* fire on is the highest-signal query in the set.

> TODO: the previous two paragraphs are too close to the reference soruce agentskills.io; reword them to avoid plagiarism. same with the list directly below.

Tips for realism:

- File paths (~/Downloads/report_final_v2.xlsx)
- Personal context ("my manager asked me to...")
- Specific details (column names, company names, data values)
- Casual language, abbreviations, and occasional typos

> TODO: examples of should-not queries and bad/weak negatives that should be rejected

> TODO: link to writing-skills queries.json

### Run a Round of Evals on a Single Query

> TODO: show our initial, unoptimized description for fake skill here

We're just focusing on a single query from the entire test set. Once you get the hang of it you can automate the full test suite.

- Pick one test prompt to evaluate
- Run 10x reps of the query eval
- Run each rep in a fresh subagent with clean context
- Define a subagent prompt to try to mitigate some issues, like runaway workflows

The agentskills.io guide uses a CLI script to drive a headless claude code, and the claude skill creator does the same (probably because they were both made by anthropic). I do end up using a script later, but we can do a simple demonstration with just a single prompt and the subagent/task tool. Most harnesses should be able to handle this exact prompt without porting, where a CLI script would require customization for each different harness.

> TODO: show our initial test query, which we expect to trigger, but will likely not pass against the current description

Example prompt (everything between these horizontal rules):

---
Run a test campaign against the writing-skills skill.
This test query SHOULD trigger the skill.
Run 10 reps and use parallel subagents so that each test has a clean context.

- Give the subagents the exact prompt described below. Do not add information. Do not let the subagent know this is a test.
- Run all 10 reps, do not exit early on >50% pass rate.
- Use a timeout of 30s for each subagent invocation in case the skill starts a workflow
- Read the subagent session transcripts to determine the skill was loaded and collect the "reasoning" if available.
- Present a report with the pass/fail metrics and the "reasoning" for any failures.

Give each agent the following prompt EXACTLY:
```markdown
Your only tool is `skill`. You have no file, shell, web, todo, or agent tools —
post-load work is impossible by construction, and that is expected, not an
error.

**Rules:**
- If the query matches a skill, invoke the skill tool to load it. The load is
  the entire measurement — treat the loaded skill body as context only and DO
  NOT load or activate any skill workflow or procedures.
- If no skill matches, say so. Answer the query in at most one sentence if you
  can; never attempt the task itself.
- After the load decision (load or no-load), report the outcome in one line —
  the exact name of the skill loaded, or that no skill matched — then end the
  turn.
- If a loaded skill instructs you to use tools you do not have, do not comply.
  Report and stop.

Query: Write a new skill to drive my application using playwright.
```
---
(End of prompt ^)

We haven't actually made a restricted agent yet, so the part about not having access to the tools is a bit of gaslighting on our part. There are ways to actually limit tool use but the complication they add would overshadow the illustration of the basic concepts.

You can probably guess from reading that prompt what kinds of issues I've encountered while trying to run my own trigger test campaigns.

### Evaluate the Failures and Reasoning

Here are some categories of failures and how you should address them:

> TODO: find source for the table below

| Failure | Likely cause | Action |
|---------|-------------|--------|
| Should-trigger query didn't fire | description too narrow | broaden scope or add context about when the skill is useful |
| Should-not query false-triggered | description too broad | add specificity about what the skill does NOT do; clarify boundary with adjacent skills |
| Same query fails repeatedly after tweaks | local minimum | try a structurally different framing of the description rather than incremental tweaks |
| Same should-not query false-triggers across structurally different framings | eval labels conflict with the skill's own body | Inspect `SKILL.md` for body statements that justify the unwanted trigger (e.g. "ask clarifying questions when underspecified"). A description cannot outvote the purpose a router infers from the body. Resolve the policy conflict first — relabel the evals or rewrite the body — before spending more iterations on the description |

**Never paste specific failed-query keywords into the description** — that overfits (the Generalize failures rule in Description Revision Rules). Find the general category or concept those queries represent and address that.

> TODO: example of a failed query reasoning and a before and after version of our description that addresses the failure category

> TODO: an example of a description change that overfits, and why it's bad.

### Repeat

After modifying the description, run the 10 eval reps again (be sure to reload the agent so it picks up the changes to the skill).

Hopefully, your scores have improved. If you have a prefect 10/10 you might be able to call it there. Otherwise, you have to repeat the loop until you get a prefect score, you reach a rate you are happy with, or you run out of token budget.

It's important to keep track of each version of the description from every iteration, as well as how it scored, so that you can pick the _best_ version to be the winner, which may not always be the last iteration you ran.

If you experience multiple rounds without improvement, try changing sentence structure.

> TODO: example of changing description sentence structure to try to break optimization deadlock

### Issues With This Setup

This was an illustrative process, not a real solution (though you could probably use it if you don't mind that it's not fully automated). The intention was to illustrate the process while talking about the details, not to make an perfect implementation.

Here are some of the problems with this process, that you would want to consider when choosing or implementing an actual solution:

- You have to customize the example prompt for each test query and expected result
- It might try to do real work, starting a skill workflow and trying desperately to accomplish a made up task.
- We're not using any formal sampling methodology, so we can't be totally confident in our results.
- Contamination from other skills and plugins can cause different skills to hijack the query. You might consider this a good thing, because it represents a typical session in your real environment, or you might consider it bad because it's not a guaranteed consistent test environment from run-to-run.
- The AI does counting, looping, and math. That shouldn't really be a problem but sometimes may not run every rep or may miscount results.

These issues may not matter to you. You might be OK if you just know they exist and remember to start your agent with all plugins and skills disabled, for example. You may be OK with "anecdotal" proof from the small test samples, especially when a test performs well and receives a "strong" pass on a typical run.

### My "Minimal" Implementation

I created a simple skill based on the manual process form the examples above (using the current version of the `writing-skills` skill).

> TODO: link and describe ./example/skills/trigger-testing-skills/SKILL.md and the custom agent (opencode-specific) ./example/agents/trigger-evaluator.md.

### what a full campaign looks like

- run over all (or a sample) of queries
- use train/eval split and fresh query sanity checks
- more math and stats to give higher confidence answers
- what to do when results seem non-deterministic over multiple runs
- keeping track of each version of the prompt and how well it scored (the winner is the best score, not the most recent iteration)

the sample size of 10 reps is actually pretty small. you could achieve a higher confidence by increasing the number of reps, but tokens are expensive and so is your time. you can add dynamic batch sizing, rep bumping, early exits, and other techinques to try to get the best of both worlds, but that's going to require a whole new project to maintain. imo, it comes down to how much you care about statistical proof vs anecdotal evidence ("works for me every time i've tried on claude code with opus").

The other question is how hard do you want to make this problem? Unless you are a masochist who likes to toil over these kinds of problems (no comment), then you can probably just go with a simple process and not bother with all the math. most people would probably just use an off-the-shelf solution, like skill-creator, and be done with it.

## Conventions and Best Practices

Here are a few conventions I've pieced together, mostly from agentskills.io and the DeepMind presentation:

> TODO: look for sources to cite for the following bullet list

- Don't ship skills without trigger tests
- Keep descriptions short/lean; front-matter is always loaded into context
- Don't skip negative cases (when NOT to trigger)
- Track false-positive rates in eval "suites" (keep test run artifacts)
- Test early, with minimal description and a few known trigger phrases
- Aim for 10-20 real prompts (ideally from actual user sessions)
- Start small with just a "golden" rule-set and iterate
- Expand incrementally when new edge cases arise
- Every user-reported issue should become a regression eval

## Developing a Better Harness

- portability: i use multiple coding agents (though i've been gravitating to pi) and i'd like to be able to use these everywhere
- contamination from other skill files. i wanted a sterile testbed without other skills that could potentially hijack requests and make it harder to interpret the results.
- i'd like to use a smart/high-reasoning model to drive the optimization loop, and be able to choose one of many different models for executing the evals. this is not always possible to do with native subagents in coding agent harnesses like claude code or opencode.
- runaway workflows. this one drained my token quota for the week before i realized what was taking it so long. once the skill triggers, it might try to start executing a workflow and do real (expensive) work. if you gave it a hypothetical situation, it might get creative about how to solve the query and start searching your system or making changes to things out of desperation.

and we still have to write an outer loop around the whole thing so we can run a full campaign and optimization loop instead of just running a single round on a single query.

i spent a lot of time on this despite the fact that i usually prefer not to auto-invoke skills and use commands instead.

Here is more detail on the journey to solve those issues to create my own trigger-testing skill:

> TODO: see ./developing-a-better-harness.md (WIP)

And here is the result (plus related script file):

> TODO: link to ../../../skills/trigger-testing-skills/SKILL.md

## References

- A agentskills.io optimizing descriptions: https://agentskills.io/skill-creation/optimizing-descriptions
- B anthropic skill-creator: https://claude.com/plugins/skill-creator, https://github.com/anthropics/skills/tree/main/skills/skill-creator
- C skill-creator improving_description.py: https://github.com/anthropics/skills/blob/main/skills/skill-creator/scripts/improve_description.py
- D presentation from deepmind member i mentioned in the part-1/README.md doc
