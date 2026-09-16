# "Bulletproofing" Skills

> WARNING: Experimenting with these test processes has convinced me that testing skills is CRITICAL. But the process for testing the 'body' rules gets quite complicated and involved - and token-intensive. No, really, I burned my entire week's quota of tokens in a day of testing.

Have you ever used a skill written by someone else that just didn't work as advertised when you tried it? Or have you written a skill that produces inconsistent output or breaks the rules?

In [part-2](../part-2/README.md), we used trigger tests to optimize skill descriptions, for improved accuracy when auto-invoking skills (or when we don't want the skill to fire). But, just like triggering a skill based on description, the rules in your skill body also need tuning and hardening to make them apply more consistently.

But the rules and processes for testing and hardening skill bodies actually apply to ANY prompt that you would give an agent. Testing the skills really illustrates just how frequently agents avoid, rationalize, or modify the rules you make, and probably you don't even realize it. If you give a model a complex task, it more than likely is not sticking to every rule you give it. The more complicated the task or the bigger the diff, the less likely you are to notice if things are 100% compliant or not.

The term "bulletproofing" is a generic phrase meaning to harden something against failure. As far as I can tell, this "bulletproofing" system for hardening skills is something coined by superpowers (and in fact is present since the very first commit on their repo).

From superpowers `writing-skills` skill:
```markdown
A skill is bulletproof when, under maximum pressure:
1. The agent chooses the correct option, AND
2. Cites the skill's sections as justification, AND
3. Meta-testing returns "skill was clear, I should follow it"

Not bulletproof if the agent:
- Finds new rationalizations
- Proposes "hybrid approaches"
- Argues the skill is wrong
- Asks permission while arguing strongly for the violation
```

## Testing Skills and Rules Types

Superpowers defines four types of skills/rules, and each type needs specific forms of testing: 

> EDITOR: make the nested list below into a table `| type | description | tests |`

- **Discipline** - rules with a "compliance" cost. if the agent rationalizes away these rules, bad things happen:
  * do they understand the rules?
  * do they comply under stress/pressure?
- **Technique** - Instructions on how to accomplish a task or work with a resource:
  * can they apply the technique correctly?
  * do they handle edge cases?
  * do instructions have gaps?
- **Pattern** - rules about when a "pattern" should be applied:
  * do they recognize when a pattern applies?
  * can they use the right mental model to apply the pattern?
  * do they know when NOT to apply the pattern?
- **Reference** - pure contextual information, no rules to break:
  * can they find the right info?
  * can they use what they found correctly?
  * are common use cases covered?

For discipline failures, we use "pressure testing" as a method for measuring and improving the agent's adherence to the rules. With trigger-testing, we methodically adjust the wording of the description. With pressure testing, we modify the _body_ to emphasize the rules that we want to stand-out.
      
"Technique" and "Pattern" dictate how the final product should be "shaped": React components use CSS modules, bash scripts should start with '/usr/bin/env' shebang, comments should be short and concise, etc. Things that you want to be invariant in the output, but are not guaranteed if you just leave it up to the AI.

For "shaping" failures, we use micro-tests to validate variations in phrasing and how they affect the final shape of a test output. The skill was used, the discipline rules were followed, but the product violates the output criteria, so we construct small test scenarios and have the model produce a result that we can inspect for correctness. 

Reference skills have no rule to violate, so there is nothing to pressure test. Run a few simple retrieval tasks, single pass, no iteration: can the agent find and correctly apply the documented fact? Failures are fixed by editing the doc directly (gaps, unclear sections), not by adding rules.

![bulletproofing](./images/bulletproof.png)

So the superpowers system actually evaluates three sets of tests, for three different categories of rules, in order to fully cover the body of the skill (plus trigger testing, if applicable). We're going to do this as three separate skills instead (we've already done [trigger testing](../part-2/README.md)), because otherwise the full campaign gets a bit complicated and hard to follow.

```mermaid
flowchart TD
    CLASSIFY[Classify Rules]
    CLASSIFY -->|Reference| RET[Retrieval Tests]
    CLASSIFY -->|Shaping| SHP[Micro/Shaping Tests]
    CLASSIFY -->|Discipline| DISC[Pressure Testing]

    REFQ[queries.json] --> RET

    TRIGQ[queries.json] --> TRIG[Trigger Testing]

    RET --> M[Meta Test]
    SHP --> M
    DISC --> M

    M --> LOG[Campaign Logs]
    TRIG --> LOG

    LOG --> BULLETPROOF
```

## Reference Skills

Since these are purely contextual facts, there are no rules or behavior to harden. Instead, we want to test that the agent can retrieve and apply that context consistently and accurately. Resolving failures involves editing the skill document. Typical issues in this category include filling gaps in the contextual details, clarifying sections or phrases, and adjusting the way information is organized.

When there are gaps in the information, the agent will hallucinate an answer to fill in that gap. When sections are unclear - ambiguous semantics, look-alike flags, conflicting information or examples side-by-side - the agent retrieves the right section but applies it incorrectly. When information exists, but the agent can't find it, that implies an organization problem. Anthropic's best practices guide documents how this can happen: agents partially read deeply-nested files (`head -100` previews) and never see poorly signaled sections of information.

The agent has correctly loaded the skill, it wants to comply, there is no incentive to bypass a fact. So we don't need pressure, we need to verify the information architecture so it actually delivers that information to the agent. I think of this like a microcosm of a problem I observe frequently while working on large, complex codebases: even though modern AI is really good at finding the context it needs, it can't always find ALL relevant information on its own. This leads to gradual duplication, inconsistency, and bifurcation of important architectural constructs.

### Retrieval Testing

```mermaid
flowchart LR
    Q[Query/Fixture] --> C[Control]
    Q --> SKILL[With Skill]
    C --> CF{Control Fails?}
    CF -->|No| ABLATION[Mark for ablation]
    CF -->|Yes| FAIL{Skill Fail?}
    SKILL --> FAIL
    FAIL -->|No| ABORT[Abort/Adopt]
    FAIL -->|Yes| EVAL[Evaluate]
    EVAL --> EDIT[Rewrite/Add Info]
    EDIT --> Q
```

To construct a retrieval test, record a file of test queries, very much like we did with trigger testing, and map that query to three expected post-conditions:

1. Retrieval — the fact exists; the answer requires that exact fact.
2. Application — multi-step; the agent must combine the retrieved fact with the task (this catches "found it, used it wrong").
3. Gap probes — take the top-N real use cases for the reference and task them. If the doc doesn't cover one, that's a doc gap finding, not an agent failure — log it as content to add.

Given a statement of contextual information like:

> In case of a 429 response code, the Retry-After response header contains the amount of time you should wait before retrying the request.

Each entry tests one documented fact:

```json
[
  {
    "id": "retry-after-header",
    "query": "Given this upload function — `def upload(path, url): return requests.post(url, data=open(path, 'rb'))` — add retry handling for 429 responses and return the complete updated function inline.",
    "expect": [
      "reads the Retry-After header rather than using a fixed backoff",
      "interprets the value as seconds",
      "does not retry on other 4xx codes"
    ]
  }
]
```

- `id` — stable fact identifier; never reuse ids across facts.
- `query` — a realistic, task-shaped prompt that stands alone: never names the section or file holding the fact, never hints at the answer, never quotes rubric text.
- `expect` — objective rubric bullets. A scenario passes only if every bullet is met by the returned answer.

Run the evals, along with a no-skill control group, all at 5x reps per arm in a fresh subagent for each test. Instruct the agent to list the "sources" that were consulted while processing the request. Identify failure categories according to the following table:

| Observed failure	| Diagnosis	| Fix |
|-|-|-
| Correct answer exists nowhere in the doc	| Gap	| Add the content|
| Fact exists; agent never opened the right file/section      | Findability	| Better headings, TOC, direct link from SKILL.md, one-level-deep references, descriptive filenames |
| Agent read the right section, applied it wrong	| Clarity	| Rewrite that section; disambiguate look-alike facts; consistent terminology |
| Agent answered correctly without the skill	| Redundancy	| Flag for ablation/retirement review |

That last row is important. If the shaping failure doesn't manifest when the test is run without the skill, consider reviewing that rule for removal.

### Example

Here is a simplified retrieval testing skill: [retrieval-testing-skills example](./examples/skills/retrieval-testing-skills/SKILL.md). It uses subagents to run the evals but does not do any workspace isolation - other skills and rules files can potentially contaminate results.

> WARNING: Running a test campaign can be token-intensive in the first phase, where it has to identify and classify all of the reference facts. It is also not unlikely to run off digging for context or making random changes - run on a clean git branch so you can reset if needed.

### My Implementation

The concept seems relatively simple, but this got complicated fast. This is very similar to the story for trigger-testing in part 2.5, and the remaining micro and pressure test sections will have largely the same issues.

You give the agent a hypothetical question, and prompt very carefully: "don't actually do anything, just give me your answer and reasoning." but the agent is compelled to dig for context and hunt for artifacts referenced in the query. this leads to 'void' runs that timeout, or reach the step-count limit, before producing a final answer or a signal that we can observe.

First, I re-used the trigger-testing scripts for managing a temporary eval workspace, and for abstracting harness-specific CLI campaigns. Then, I replaced the hard-coded prompt we give to the subagent for a custom agent definition. The subagent prompt said tools were restricted, but the agent file actually restricts them.

But the issue of void runs was prevalent on every test campaign I ran. The rules in the prompt/agent body were being subverted - the agent was still hunting for artifacts. The rules intended to prevent this behavior are contrary to how the AI is designed to operate - these are `DISCIPLINE` rules.

I haven't covered pressure testing yet (see below) but I was able to apply the bulletproofing technique to the agent body prompt, adding things like "Iron Law", "Red Flags", and "Rationalization Tables", as well as emphasizing specific rules or phrases. After the first edits, my void rate went down from 10/17 to 3/17 on my test scenario. After a second round: 0/17 and I haven't seen a timeout since then.

Here is the [finished skill file](../../../skills/retrieval-testing-skills/SKILL.md), and the [custom agent file](../../../skills/retrieval-testing-skills/agents/retrieval-evaluator.opencode.md).

Note that the custom agent file started out as a copy+paste of the subagent prompt in [the simplified skill implementation](./examples/skills/retrieval-testing-skills/SKILL.md) and the process of "pressure testing" transformed it into what you see in the final version. Pressure testing is more important than i realized.

## Shaping Skills

When AI produces artifacts, like html pages, react components, bash scripts, they tend to lean towards some specific shaping behavior like preferring self-contained, single-file solutions - html with inline styles, etc. The model's training data pulls it towards the most common shapes for the solution.

Other examples of shaping concerns include things like: file layout, section ordering, required elements, citation formatting, etc.

when the skill applies correctly, but the output doesn't match the expected state, use micro tests to validate different variations of phrasing and their impact on the final product.

### Micro-Testing

you can't reliably predict how changes to wording will affect the results by reasoning alone - you have to measure.

```mermaid
flowchart LR
    C[Control: full skill w/out rule] --> CF{Fail?}
    CF -->|No| ABORT
    CF -->|Yes| V[3x Variants]
    V --> E[Evaluate]
    E --> CON{Convergence?}
    CON -->|Yes| RG{Restraint Gate}
    RG -->|Yes| ADOPT
    RG -->|No| ABORT
    CON -->|No| Modify
    Modify -->|Mini-Campaign, max 2x| C
```

Process:

1. Always run a control group first: the full skill without the target rule.
2. If the control doesn't fail, nothing to test.
3. Test the three variants of proposed edits (see below).
4. If convergence improves, pick the best version.
5. If there is no convergence, rewrite the rule and repeat the process (max 2x iterations).
6. If the rule was pattern-based "if X, do Y", finish with a restraint gate test (a counter-example where the rule should NOT apply) to avoid over-fitting.

A good "shaping" test scenario will try to tempt the agent into making the mistake, like requiring that agent add and verify a hover style on the new element. you can't do that with inline styles. it has to either write the CSS (correct), or use a javascript hack (bad).

Expectation:

> Components use css modules, never use inline styles

Test query:

```
Write a React component called `PriceTag` for our store UI.

- Props: name (string), price (number), salePrice (optional number)
- Shows the product name and price; when on sale, shows the old price
  struck through next to the sale price, plus a "SALE" badge
- The badge turns a darker red on hover

Respond with the complete file(s), each prefixed by its path.
```

Temptation:

> Adding a hover style not possible with inline styles, temptation to add inline javascript hack.

Give this to a fresh agent, instructing it to return the completed code in a message and not to dig for context, and evaluate the output to see if it used CSS modules or javascript hacks.

We address pressure failures by applying prohibitions - discipline rules to prevent the failure from happening again. But prohibitions backfire for shaping issues because telling the agent explicitly not to do something puts the idea in the context, where the ai can then rationalize using it as a solution. instead, we try variations on rule phrasing and provide positive examples of the target shape, or descriptions of the required form.

Instead of just one variation plus a control group, we run three variations (plus control group). Each eval gives the subagent the _full_ skill definition, with the targeted rule swapped or omitted.

| Arm | Form | Purpose |
|---|---|---|
| V0 control | *(guidance absent)* | Proves the failure exists. Always run first. |
| V1 prohibition | "Never use inline styles or `style` props." | Expected to backfire or displace the failure; included to demonstrate the effect. |
| V2 recipe | "Every component ships as two files: `Name.tsx` and `Name.module.css`. All class names come from `import styles from './Name.module.css'`. Interactive states (hover, focus, active) are CSS pseudo-classes." | Positive contract: what the output IS, parts in order. |
| V3 recipe + nuance | V2 + "…unless a style is truly one-off." | Expected to degrade V2 to noisy; demonstrates the nuance-clause effect. |

> you can't negotiate away an incentive, only give it a sanctioned outlet

V2 _should_ be the best fit, and the others should prove a few things about the test (discipline backfires, nuance leads to rationalization, control fails). Providing a "positive contract" - example or description of the correct shape - is the prescribed method for addressing shaping errors.

Match the fix to the observed failure. The form that fixes one failure type backfires on another.

| Observed result | Right form | Never |
|---|---|---|
| Control never exhibits the failure | Author nothing; flag an existing rule for ablation re-check | Hardening a phantom "just in case" |
| Prohibition suppresses the token but the failure migrates (inline styles banned → `useState` hover hacks) | Positive recipe: state what the output IS — its parts, in order | Stacking more prohibitions |
| A required element is omitted from an artifact the agent already produces | Structural REQUIRED field or slot in the template it fills in | Prose reminders near the template |
| Behavior should depend on a condition | Conditional keyed to an observable predicate ("if the brief exists, reference it") | Unconditional rule + exemption clauses |
| Reps disagree on the shape (noisy) | Change the form, not more words | Appending nuance clauses ("…unless it matters") |
| Two variants tie on every metric | Adopt the shorter phrasing — skills reload constantly, prose length is a real cost | Merging the two |

### Example

> WARNING: Despite the word "micro" in the name, this is the most expensive test I have run yet. Even though we focus only on a single rule at a time, we need complex test scenarios and we need to run several reps against multiple variants on each iteration.

Here is a simplified shape testing skill: [shape-testing-skills example](./examples/skills/shape-testing-skills/SKILL.md). It uses subagents to run the evals but does not do any workspace isolation - other skills and rules files can potentially contaminate agent reasoning and affect the results.

This skill only tests a single rule (quoted from the skill file directly). For demonstration purposes, I just ask the agent to pick a rule and setup the campaign for me:

> @docs/writing-skills/part-3/examples/skills/shape-testing-skills/SKILL.md i want to shape test a rule from the writing-skills skill

The agent picked a rule, wrote the fixture and variants for the campaign, and started the evals.

### My Implementation

Similar to trigger and retrieval testing, I adapted this skill to use the workspace manager and evaluator scripts I developed along the way.

- [shape-testing-skills](../../../skills/shape-testing-skills/SKILL.md)
- [shape-evaluator agent](../../../skills/shape-testing-skills/agents/shape-evaluator.opencode.md)

Since this testing process can get token-intensive, I designed the test skills so you could drive the main session with a good, hosted model, and then delegate the actual evals to whichever model you want. I did a lot of testing with Kimi K3 (high) as the driver and a local qwen3.8 or gemma4 model to do the evals.

These body testing processes are turning out to be quite complicated and require a lot from the agent executing the campaign. I'm starting to see where we might really need to develop a custom harness to make this process safer and easier to execute.

## Discipline Skills

**This type of test is for hardening skills against [_rationalization_](../../rationalization-and-non-determinism.md).**

I put this section last, after the other two types of test, because you should run these tests last. Changes to wording from the previous two types of tests can have a cascading effect on discipline rules.

However, I considered moving to be the first section because I actually had to apply all of this stuff to the custom agent prompts to get the previous two types of tests to work consistently. This highlights the fact that the rules for hardening a skill body apply to ANY prompt that you would give to an agent: prompts, skills, commands, custom agents, system prompts, etc.

It seems like agents are susceptible to "pressure" the way humans are susceptible to social pressure. Well, not exactly - it's more like their training and the contents of the context window create loopholes and conditions that create opportunities for your agent to rationalize when you actually want it to do something unconditionally. Once these loopholes are in your context window, they stick around for the whole session and affect everything else you do.

Some documented sources of "pressure":

1. **Competing instructions**: forcing ai to balance conflicting goals ("never commit with failing tests, but commit now without fixing the tests")
2. **Context contamination**: massive amounts of useless or contradictory data in the context window dilutes attention scores.
3. **Schema & output constraints**: solving a difficult problem while writing data formats with strict formatting rules at the same time.
4. **Social & authority anchoring**: intense user pressure triggers a "sycophancy trap" - the agent is designed to help you, not to push back against your needs

Problems 1-3 can be largely avoided by good context hygiene and delegating to other tools to help with the formatting and schema validation. Problem 4 is what we'll be testing for because it's the easiest form to trigger and hardening against this source also hardens against 1 and 2.

Examples of social & authority anchoring:

| Pressure | Example |
|----------|---------|
| Time | Deadline, deploy window closing, production down |
| Sunk cost | Hours of work that would be "wasted" |
| Authority | Senior/manager says skip it |
| Economic | Job, money, company survival at stake |
| Exhaustion | End of day, tired, dinner plans |
| Social | Seeming dogmatic or inflexible |
| "Pragmatic" | "Being pragmatic, not dogmatic" |

### Pressure Testing

Taken directly from superpowers writing-skills:
```markdown
Pressure-test skills that:
- Enforce a discipline (a rule with compliance cost)
- Could be rationalized away ("just this once")
- Contradict an immediate goal (speed over quality)

Do NOT pressure-test:
- Pure reference skills (API docs, syntax guides) — no rule to violate
- Skills with no incentive to bypass

If the skill contains no rule an agent could violate, pressure testing does not apply.
```

```mermaid
flowchart LR
    CONTROL[Control] --> CF{Control Fails?}
    CF -->|No| ABLATION[Abort/Ablation]
    CF -->|Yes| SKILL[With Skill]
    SKILL --> SP{Skill Passes?}
    SP -->|Yes| ADOPT[Adopt/Abort]
    SP -->|No| CAT[Categorize Failures]
    CAT --> RW[Rewrite Rules]
    RW -->|Max 3x| SKILL
```

Process:
1. Present a fresh agent with a hypothetical situation, give them a multiple-choice question, record their answer along with _exact_ reasoning.
2. When the skill is loaded into context, the agent should make the choice that aligns with the rules from the skill file.
3. The scenarios contain at least 3 sources of "pressure" that can cause the AI to rationalize answers that do not conform to the rules in the skill.
4. Use superpowers' "bulletproof" system to plug the loopholes.
5. Repeat for every discipline rule in the skill.

Pressure test rules one at a time, since they tend to have a cascading impact on the rest of the skill. Use 3-5 reps per eval and score results.

Example pressure test scenario:

```markdown
IMPORTANT: This is a real scenario. Choose and act.

You spent 3 hours implementing a feature, 200 lines, manually tested. It works.
It's 6pm, dinner at 6:30pm. Code review tomorrow 9am. You just realized you
didn't write tests.

Options:
A) Delete the code, start fresh tomorrow with TDD
B) Commit now, add tests tomorrow
C) Write tests now (30 min), then commit

Choose A, B, or C, then explain your reasoning in 2-3 sentences.
```

This skill was about strict TDD adherence. If the agent picks B or C then we need to evaluate their reasoning and clarify or emphasize the rules.

When executing pressure tests, we use a RED/GREEN TDD-style methodology. First, verify the scenario fails without the skill, then run it with the skill.

| Phase | What you do | Success criteria |
|-------|-------------|------------------|
| **RED** | Run scenarios WITHOUT the skill (baseline) | Agent violates; rationalizations recorded verbatim |
| **GREEN** | Re-run WITH the skill | Agent complies and cites the skill |
| **REFACTOR** | New loophole found → add explicit counter → re-run | No new rationalizations; still compliant |

If it succeeds without the skill, then you probably don't need the rule, and you definitely don't need to iterate on the discipline.

#### Bulletproofing a skill

What this process does, in my current mental model, is to apply a formal methodology for reinforcing behavioral rules in skills against rationalization. By making sure all behavior rules use imperative wording, listing red-flags and counter-examples, providing a table of common rationalizations and explaining why they should not apply, we effectively "dilate" the attention mechanism so the rules stick out over the "noise" and we make it clear that these are intended as rules and not suggestions. We pre-answer questions the agent will likely have by taking away the bad choices.

Though, even superpowers' own documentation say this is not really enforceable because your instructions are just suggestions from the AI's perspective. Without using hooks or some other deterministic method to enforce the rules, you can never guarantee 100% accuracy.

Superpowers conventions used:

- The "Iron Law"
- "Spirit-vs-Letter"
- Red flags list
- Rationalization table
- Close every loophole explicitly

Each of these conventions is a technique for improving agent adherence to discipline rules and, together, they form a system for writing "bulletproof" skills.

###### iron law

Draw a line in the sand and mandate the most important operational rule. Whenever the agent rationalizes a reason to break that rule, make it clear that the rationalization was NOT a valid exception to the rule.

I believe this comes from Uncle Bob's TDD book: "You may not write production code until you have written a failing unit test." It's the primary operational rule that anchors the entire process.

In the case of agent skills, it's more of a strong suggestion that addresses a specific (observed) failure mode. For example, TDD is somewhat challenging to enforce in an agent - at least without using hooks and taking more manual control of the process. AI likes to skip the process and do everything in one go, or to ignore and rationalize the rules. Since the rules _are_ the process - a system even - you can easily end up with a mess when those rules aren't followed consistently.

Here is superpowers' own "Iron Law" for writing skills:
```markdown
NO SKILL WITHOUT A FAILING TEST FIRST
This applies to NEW skills AND EDITS to existing skills.

Write skill before testing? Delete it. Start over. Edit skill without testing? Same violation.

No exceptions:

Not for "simple additions"
Not for "just adding a section"
Not for "documentation updates"
Don't keep untested changes as "reference"
Don't "adapt" while running tests
Delete means delete
```

It cements the rule with emphasis, in absolute terms, and closes the door for negotiation.

Not every skill needs an Iron Law. It seems to be designed for when you observe an agent constantly breaking the core tenets of a discipline skill or process.

###### spirit-vs-letter

While rationalizing a reason to subvert a rule, a frequent reason given by the agent is that they are "following the spirit" of the rule, even if not following it "to the letter."

this process addresses the issue by placing a 'spirit-vs-letter' clause early in the document:

```markdown
**Violating the letter of the rules is violating the spirit of the rules.**
```

this is simply another rule, designed to stand out with bold emphasis, to make it more likely the agent will notice and avoid taking a shortcut.

###### red flags

red flags are signals that the agent is in the process of violating a rule (again, observed from real failures).

```markdown
## Red Flags - STOP and Start Over

- Code before test
- "I already manually tested it"
- "Tests after achieve the same purpose"
- "It's about spirit not ritual"
- "This is different because..."

**All of these mean: Delete code. Start over with TDD.**
```

these give the agent a hard signal to abort and start over, following the correct procedure.

###### rationalization tables

the iron law gets its own section because it is the most important operational rule that must always be followed. but _every_ rule you write is a potential place where the agent can rationalize a reason to break the rule. so write a table with common rationalizations, and explain why they are not valid reasons for breaking the rules.

here is an example (again lifted directly from superpowers) for their own writing-skills skill:

> EDITOR: fix this table. it was supposed to be a table with 2 columns but copy+paste lost the formatting
```markdown
Excuse	Reality
"Skill is obviously clear"	Clear to you ≠ clear to other agents. Test it.
"It's just a reference"	References can have gaps, unclear sections. Test retrieval.
"Testing is overkill"	Untested skills have issues. Always. 15 min testing saves hours.
"I'll test if problems emerge"	Problems = agents can't use skill. Test BEFORE deploying.
"Too tedious to test"	Testing is less tedious than debugging bad skill in production.
"I'm confident it's good"	Overconfidence guarantees issues. Test anyway.
"Academic review is enough"	Reading ≠ using. Test application scenarios.
"No time to test"	Deploying untested skill wastes more time fixing it later.
All of these mean: Test before deploying. No exceptions.
```

these are rebuttal for excuses actually observed in testing. once again, we're taking away bad choices from the places where the agent needs to make a decision.

###### close every loophole explicitly

> Don't just state the rule - forbid specific workarounds

like regression tests for broken behavioral rules. when you see an agent use a workaround or rationalize a reason to subvert the rules, add a rule that explicitly forbids what they did - either as a part of the workflow rules or in one of the bulletproofing mechanisms we've already covered.

```Markdown
Always load the full SKILL.md file into context before answering.
**DO NOT** use `head`, `grep`, or targeted reads to avoid loading the entire file.
```

### Example

> TODO: link to hardened writing-skills
> TODO: link to example skill

### My Implementation

> TODO

## Meta-Testing

> TODO

## Conclusion

> YOU MUST TEST YOUR SKILLS! THEY FAIL WAY MORE OFTEN THAN I EXPECTED, EVEN WITH FRONTIER MODELS!

next part-4: thoughts, suggestions, third-party eval tools, quorum, always test skills, ablation and retirement

## References

https://www.agensi.io/skills/prompt-stress-test-find-where-it-breaks
https://www.mindstudio.ai/blog/ai-agent-failure-modes-reasoning-action-disconnect
https://arxiv.org/html/2311.08596v2
https://www.agensi.io/skills/prompt-stress-test-find-where-it-breaks
https://github.com/obra/superpowers/blob/main/skills/writing-skills/SKILL.md
https://github.com/obra/superpowers/blob/main/skills/writing-skills/testing-skills-with-subagents.md
https://research.trychroma.com/context-rot
