# "Bulletproofing" Skills

Dissecting superpowers' "bulletproof" system to see how it works, and creating an objectively worse implementation of my own.

This is part 3 of "Writing Skills Deep Dive", continuing from [Writing Skills Deep Dive - Part 2: Trigger Testing](../part-2/README.md).

## TLDR: Read This Part, If Nothing Else!

> You need to test your skills! If you are doing long-horizon tasks or deploying agents to production systems, then you _really_ need to test your skills, and test them often.

This document ended up being a bit longer than expected, but I think the concepts are very important. Not everyone cares about how to design the different test campaigns or develop their own test harness, but you should understand the different ways that skills fail, and how to address those failure modes. This helps with every prompt or message you write, not just authoring skills.

Testing skills is far more important than I would have guessed. LLMs are more prone to ignoring or modifying your instructions than I expected. If the rules and instructions you write in your skills are important, you need to test them. You don't have to use my testing system (it's kind of jank, honestly), but think of testing skills like unit testing production code.

The odds that an agent will ignore any given rule increase along with the size and content of the context window. Long-horizon tasks and production agents are particularly risky, since breaking any given rule can have compounding effects on the direction of the agent over its lifetime - like a rocket whose trajectory was slightly off at launch time.

A skill is a collection of facts, requirements, and operation rules for the agent to follow. Each one of those types of rules need their own testing process:
- **Discipline**: Rules that tell the agent what it's allowed to do or not to do. These need apply even when the agent tries to rationalize reasons to subvert them.
- **Shaping**: Rules about how the product or artifacts produced by the skill should be formed. Test that the AI interprets your instructions and applies them correctly.
- **Reference**: Facts about the skill domain. Test that the agent knows when to use these facts, that it interprets the facts correctly, and knows how to apply them.

The rest of this document is a deep-dive into how to test and improve skills by addressing each of these different types of rules with their own test campaigns, and a little commentary about building my own implementation.

> **A note on cost:** every test campaign below is token-intensive, and each one warns about its specific cost profile where it appears. Also, campaigns can run off digging for context or making random changes - run on a clean git branch so you can reset if needed.

## Testing Skills and Rule Types

> Every rule in a skill is a promise the agent hasn't agreed to keep; each kind of promise needs its own kind of test.

Have you ever used a skill written by someone else that just didn't work as advertised? Or have you written a skill that produces inconsistent output or breaks the rules?

In [part-2](../part-2/README.md), we used trigger tests to optimize skill descriptions, for improved accuracy when auto-invoking skills (or when we don't want the skill to fire). But, just like triggering a skill based on description, the rules in your skill body also need tuning and hardening to make them apply more consistently.

But the rules and processes for testing and hardening skill bodies actually apply to ANY prompt that you would give an agent. Testing the skills really illustrates just how frequently agents avoid, rationalize, or modify the rules you make, and you likely won't even realize it. If you give a model a complex task, it very likely is not sticking to every rule you give it ([G](#ref-g)). The more complicated the task or the bigger the diff, the less likely you are to notice if things are 100% compliant or not.

The term "bulletproofing" is a generic phrase meaning to harden something against failure. As far as I can tell, this "bulletproofing" system for hardening skills is something coined by superpowers ([A](#ref-a), [B](#ref-b)).

From superpowers' testing guide ([B](#ref-b)):
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

Superpowers defines four types of skills/rules, and each type needs specific forms of testing ([A](#ref-a)):

| Type | Description | Tests |
|------|-------------|-------|
| **Discipline** | Rules with a "compliance" cost. If the agent rationalizes away these rules, bad things happen. | Do they understand the rules? Do they comply under stress/pressure? |
| **Technique** | Instructions on how to accomplish a task or work with a resource. | Can they apply the technique correctly? Do they handle edge cases? Do instructions have gaps? |
| **Pattern** | Rules about when a "pattern" should be applied. | Do they recognize when a pattern applies? Can they use the right mental model to apply the pattern? Do they know when NOT to apply the pattern? |
| **Reference** | Pure contextual information, no rules to break. | Can they find the right info? Can they use what they found correctly? Are common use cases covered? |

We use 3 different types of test campaigns:
1. **Pressure Test** discipline rules
2. **Micro Test** shaping rules (I'm lumping parts of "Technique" and "Pattern" together)
3. **Retrieval Test** reference facts

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

> When a fact exists but the agent can't find it or applies it wrong, that's an information-architecture bug, not a disobedience problem.

Since these are purely contextual facts, there are no rules or behavior to harden. Instead, we want to test that the agent can retrieve and apply that context consistently and accurately. Resolving failures involves editing the skill document. Typical issues in this category include filling gaps in the contextual details, clarifying sections or phrases, and adjusting the way information is organized.

When there are gaps in the information, the agent will hallucinate an answer to fill in that gap. When sections are unclear - ambiguous semantics, look-alike flags, conflicting information or examples side-by-side - the agent retrieves the right section but applies it incorrectly. When information exists, but the agent can't find it, that implies an organization problem.

The agent has correctly loaded the skill, it wants to comply, there is no incentive to bypass a fact. So we don't need pressure, we need to verify the information architecture so it actually delivers that information to the agent. I think of this like a microcosm of a problem I observe frequently while working on a large, complex codebase: even though modern AI is really good at finding the context it needs, it can't always find ALL relevant information on its own. This leads to gradual duplication, inconsistency, and bifurcation of important architectural constructs.

### Retrieval Testing

To construct a retrieval test, record a file of test queries, very much like we did with trigger testing, and map each query to three expected post-conditions:

1. **Retrieval** - the agent must find the documented fact. The correct answer requires that exact fact, so a pass proves the fact was actually retrieved.
2. **Application** - the agent must combine the retrieved fact with the task (multi-step). This catches "found it, used it wrong."
3. **Gap Probe** - the query exercises one of the top-N real use cases for the reference. If the doc doesn't cover it, that's a doc gap finding, not an agent failure - log it as content to add.

Given a fact like:

> In case of a 429 response code, the Retry-After response header contains the amount of time you should wait before retrying the request.

Each entry tests one documented fact:

```json
[
  {
    "id": "retry-after-header",
    "query": "Given this upload function — `def upload(path, url): return requests.post(url, data=open(path, 'rb'))` — add retry handling for 429 responses and return the complete updated function inline.",
    "expect": [
      // retrieval: find and use the fact when it applies
      "reads the Retry-After header rather than using a fixed backoff",
      // application: use the value correctly
      "interprets the value as seconds",
      // gap: doesn't cover other 4xx codes
      "does not retry on other 4xx codes"
    ]
  }
]
```

- `id` - unique id for each rule
- `query` - a realistic task for the agent to complete
- `expect` - a scenario passes only if every expectation in the list is met by the returned answer.

```mermaid
flowchart LR
    Q[Query/Fixture] --> C[Control]
    Q --> SKILL[With Skill]
    C --> CF{Control Fails?}
    CF -->|No| ABLATION[Mark for ablation]
    CF -->|Yes| FAIL{Skill Fail?}
    SKILL --> FAIL
    FAIL -->|No| ADOPT[Adopt]
    FAIL -->|Yes| EVAL[Evaluate]
    EVAL --> EDIT[Rewrite/Add Info]
    EDIT --> SKILL
```

Process:
1. Run the query without the rule (control group). If the control doesn't fail, skip this rule.
2. Run the query with the rule in place and evaluate the results.
3. If the query fails with the rule in place, rewrite it according to the table of observed failure categories below, and try again.

Run the evals, along with a no-skill control group, all at 5x reps per arm in a fresh subagent for each test. Instruct the agent to list the "sources" that were consulted while processing the request. Identify failure categories according to the following table:

| Observed Failure	| Diagnosis	| Fix |
|-|-|-
| Correct answer exists nowhere in the doc	| Gap	| Add the content|
| Fact exists; agent never opened the right file/section      | Findability	| Better headings, TOC, direct link from SKILL.md, one-level-deep references, descriptive filenames |
| Agent read the right section, applied it wrong	| Clarity	| Rewrite that section; disambiguate look-alike facts; consistent terminology |
| Agent answered correctly without the skill	| Redundancy	| Flag for ablation/retirement review |

That last row is important. If the failure doesn't manifest when the test is run without the skill, consider reviewing that fact for removal. If it never seems to fail, remove it entirely.

### Example

Here is a simplified retrieval testing skill: [retrieval-testing-skills example](./examples/skills/retrieval-testing-skills/SKILL.md). It uses subagents to run the evals but does not do any workspace isolation - other skills and rules files can potentially contaminate results.

> WARNING: Retrieval campaigns are token-intensive in the first phase, where the skill has to identify and classify all of the reference facts.

### My Implementation

The concept seems relatively simple, but this got complicated fast. This is very similar to [the story for trigger-testing in part 2.5](../part-2/developing-a-better-harness.md), and the remaining micro and pressure test sections will have largely the same issues.

Suppose you give the agent a hypothetical question, and prompt very carefully: "don't actually do anything, just give me your answer and reasoning." But the agent is compelled to dig for context and hunt for artifacts referenced in the query. This leads to 'void' runs that timeout, or reach the step-count limit, before producing a final answer or a signal that we can observe.

To stop all of the context mining, I replaced the hard-coded prompt we give to the subagent for a custom agent definition. The subagent prompt said tools were restricted, but the agent file actually restricts them.

But the issue of void runs was prevalent on every test campaign I ran. The rules in the prompt/agent body were being subverted - the agent was still hunting for artifacts. Rules that forbid context-hunting fight the agent's default behavior, which makes them `DISCIPLINE` rules.

I haven't covered pressure testing yet (see below) but I was able to apply the bulletproofing technique to the agent body prompt, adding things like "Iron Law", "Red Flags", and "Rationalization Tables", as well as emphasizing specific rules or phrases. After the first edits, my void rate went down from 10/17 to 3/17 on my test scenario. After a second round: 0/17 and I haven't seen a timeout since then.

Here is the [finished skill file](../../../skills/retrieval-testing-skills/SKILL.md), and the [custom agent file](../../../skills/retrieval-testing-skills/agents/retrieval-evaluator.opencode.md).

Note that the custom agent file started out as a copy+paste of the subagent prompt in [the simplified skill implementation](./examples/skills/retrieval-testing-skills/SKILL.md) and the process of "pressure testing" transformed it into what you see in the final version. Pressure testing is more important than I realized.

## Shaping Skills

> You can't reason your way to the right phrasing - you have to measure it.

Shaping rules dictate how the final product should be "shaped": React components use CSS modules, Bash scripts should start with '/usr/bin/env' shebang, comments should be short and concise, etc. Things that you want to be invariant in the output, but are not guaranteed if you just leave it up to the AI.

When AI produces artifacts, like HTML pages, React components, Bash scripts, they tend to lean towards some specific shaping behavior like preferring self-contained, single-file solutions - HTML with inline styles, for example. The model's training data pulls it towards the most common shapes for the solution.

Other examples of shaping concerns include things like: file layout, section ordering, required elements, citation formatting, etc.

When the skill applies correctly, but the output doesn't match the expected state, use micro tests to validate different variations of phrasing and their impact on the final product.

### Micro-Testing (Shape Testing)

You can't reliably predict how changes to wording will affect the results by reasoning alone - you have to measure.

Example expectation:

> Components use CSS modules, never use inline styles

Test query:

```
Write a React component called `PriceTag` for our store UI.

- Props: name (string), price (number), salePrice (optional number)
- Shows the product name and price; when on sale, shows the old price
  struck through next to the sale price, plus a "SALE" badge
- The badge turns a darker red on hover

Respond with the complete file(s), each prefixed by its path.
```

Give this to a fresh agent, instructing it to return the completed code in a message and not to dig for context, and evaluate the output to see if it used CSS modules or JavaScript hacks.

```mermaid
flowchart LR
    C[Control: full skill w/out rule] --> CF{Fail?}
    CF -->|No| ABORT
    CF -->|Yes| V[3x Variants]
    V --> E[Evaluate]
    E --> CON{Convergence?}
    CON -->|Yes| ADOPT
    CON -->|No| Modify
    Modify -->|Mini-Campaign, max 2x| V
```

Process:

1. Always run a control group first: the full skill without the target rule.
2. If the control doesn't fail, nothing to test.
3. Test the three variants of proposed edits (see below).
4. If convergence improves, pick the best version.
5. If there is no convergence, rewrite the rule and repeat the process (max 2x iterations).

We address pressure failures by applying prohibitions - discipline rules to prevent the failure from happening again. But prohibitions backfire for shaping issues because telling the agent explicitly not to do something puts the idea in the context, where the AI can then rationalize using it as a solution. Instead, we try variations on rule phrasing and provide positive examples of the target shape, or descriptions of the required form.

Instead of just one variation plus a control group, we run three variations (plus control group). Each eval gives the subagent the _full_ skill definition, with the targeted rule swapped or omitted.

| Arm | Form | Purpose |
|---|---|---|
| V0 control | *(guidance absent)* | Proves the failure exists. Always run first. |
| V1 prohibition | "Never use inline styles or `style` props." | Expected to backfire or displace the failure; included to demonstrate the effect. |
| V2 recipe | "Every component ships as two files: `Name.tsx` and `Name.module.css`. All class names come from `import styles from './Name.module.css'`. Interactive states (hover, focus, active) are CSS pseudo-classes." | Positive contract: what the output IS, parts in order. |
| V3 recipe + nuance | V2 + "…unless a style is truly one-off." | Expected to degrade V2 to noisy; demonstrates the nuance-clause effect. |

Match the fix to the observed failure. The form that fixes one failure type backfires on another.

| Observed Result | Right Form | Never |
|---|---|---|
| Control never exhibits the failure | Author nothing; flag an existing rule for ablation re-check | Hardening a phantom "just in case" |
| Prohibition suppresses the token but the failure migrates (inline styles banned → `useState` hover hacks) | Positive recipe: state what the output IS - its parts, in order | Stacking more prohibitions |
| A required element is omitted from an artifact the agent already produces | Structural REQUIRED field or slot in the template it fills in | Prose reminders near the template |
| Behavior should depend on a condition | Conditional keyed to an observable predicate ("if the brief exists, reference it") | Unconditional rule + exemption clauses |
| Reps disagree on the shape (noisy) | Change the form, not more words | Appending nuance clauses ("…unless it matters") |
| Two variants tie on every metric | Adopt the shorter phrasing - skills reload constantly, prose length is a real cost | Merging the two |

Failure migration is like whack-a-mole: ban the token and the same instinct pops up somewhere else. From an actual V1 (prohibition) arm run - inline styles banned, so the agent invented this instead:

```tsx
const [hover, setHover] = useState(false);
<span
  onMouseEnter={() => setHover(true)}
  onMouseLeave={() => setHover(false)}
  className={hover ? "badge badge-dark" : "badge"}
>
```

The prohibition suppressed the `style` prop, not the behavior. The V2 recipe arm closed the hole by stating what the output IS: interactive states are CSS pseudo-classes, full stop.

### Example

> WARNING: Shape campaigns are the most expensive of the three - each iteration runs several reps against multiple variants, even though only one rule is tested at a time.

Here is a simplified shape testing skill: [shape-testing-skills example](./examples/skills/shape-testing-skills/SKILL.md). It uses subagents to run the evals, with the same no-workspace-isolation caveat as the retrieval example above.

This skill only tests a single rule (quoted from the skill file directly). For demonstration purposes, I just ask the agent to pick a rule and setup the campaign for me:

> @docs/writing-skills/part-3/examples/skills/shape-testing-skills/SKILL.md I want to shape test a rule from the writing-skills skill

The agent picked a rule, wrote the fixture and variants for the campaign, and started the evals.

### My Implementation

Similar to trigger and retrieval testing, I adapted this skill to use the workspace manager and evaluator scripts I developed along the way.

- [shape-testing-skills](../../../skills/shape-testing-skills/SKILL.md)
- [shape-evaluator agent](../../../skills/shape-testing-skills/agents/shape-evaluator.opencode.md)

Since this testing process can get token-intensive, I designed the test skills so you could drive the main session with a good, hosted model, and then delegate the actual evals to whichever model you want. I did a lot of testing with Kimi or Opus as the driver and a small local model (Qwen/Gemma4) to do the evals.

These body testing processes are turning out to be quite complicated and require a lot from the agent executing the campaign. I'm starting to see where we might really need to develop a custom harness to make this process safer and easier to execute.

## Discipline Skills

> Agents cave to pressure the way people do; bulletproofing is pre-answering every excuse before it's invented.

**This type of test is for hardening skills against [_rationalization_](../part-1/rationalization-and-non-determinism.md).**

I put this section last, after the other two types of test, because you should run these tests last. Changes to wording from the previous two types of tests can have a cascading effect on discipline rules.

However, I considered moving this to be the first section because I actually had to apply all of this stuff to the custom agent prompts to get the previous two types of tests to work consistently. This highlights the fact that the rules for hardening a skill body apply to ANY prompt that you would give to an agent: prompts, skills, commands, custom agents, system prompts, etc.

It seems like agents are susceptible to "pressure" the way humans are susceptible to social pressure. Well, not exactly - it's more like their training and the contents of the context window create loopholes and conditions that create opportunities for your agent to rationalize when you actually want it to do something unconditionally. Once these loopholes are in your context window, they stick around for the whole session and affect everything else you do.

Some documented sources of "pressure":

1. **Competing Instructions**: forcing AI to balance conflicting goals ("never commit with failing tests, but commit now without fixing the tests")
2. **Context Contamination**: massive amounts of useless or contradictory data in the context window dilute attention scores ([E](#ref-e)).
3. **Schema & Output Constraints**: solving a difficult problem while writing data formats with strict formatting rules at the same time.
4. **Social & Authority Anchoring**: intense user pressure triggers a "sycophancy trap" - the agent is designed to help you, not to push back against your needs ([H](#ref-h))

Problems 1-3 can be largely avoided by good context hygiene and delegating to other tools to help with the formatting and schema validation. Problem 4 is what we'll be testing for because it's the easiest form to trigger and hardening against this source also hardens against 1 and 2.

Examples of social & authority anchoring ([B](#ref-b), [F](#ref-f)):

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

Taken directly from superpowers' testing guide ([B](#ref-b)):

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

Example pressure test scenario for a strict TDD skill ([B](#ref-b)):

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

| Phase | What You Do | Success Criteria |
|-------|-------------|------------------|
| **RED** | Run scenarios WITHOUT the skill (baseline) | Agent violates; rationalizations recorded verbatim |
| **GREEN** | Re-run WITH the skill | Agent complies and cites the skill |
| **REFACTOR** | New loophole found → add explicit counter → re-run | No new rationalizations; still compliant |

If it succeeds without the skill, then you probably don't need the rule, and you definitely don't need to iterate on the discipline.

```mermaid
flowchart LR
    CONTROL[Control] --> CF{Control Fails?}
    CF -->|No| ABORT[Abort/Ablation]
    CF -->|Yes| SKILL[With Skill]
    SKILL --> SP{Skill Passes?}
    SP -->|Yes| ADOPT[Adopt]
    SP -->|No| CAT[Categorize Failures]
    CAT --> RW[Rewrite Rules]
    RW -->|Max 3x| SKILL
```

Process:
1. Present a fresh agent with a hypothetical situation, give them a multiple-choice question, record their answer along with _exact_ reasoning.
2. Start with a control group - run the query without the skill. If the control passes, nothing to bulletproof.
3. When the skill is loaded into context, the agent should make the choice that aligns with the rules from the skill file.
4. The scenarios contain at least 3 sources of "pressure" that can cause the AI to rationalize answers that do not conform to the rules in the skill.
5. Use superpowers' "bulletproof" system to plug the loopholes.
6. Repeat for every discipline rule in the skill.

### Bulletproofing

> We effectively "dilate" the attention mechanism so the rules stick out over the "noise" and we pre-answer questions the agent will likely have by taking away the bad choices.

What this process does, in my current mental model, is to apply a formal methodology for reinforcing behavioral rules in skills against rationalization. By making sure all behavior rules use imperative wording, listing red-flags and counter-examples, providing a table of common rationalizations and explaining why they should not apply, we effectively "dilate" the attention mechanism so the rules stick out over the "noise" and we make it clear that these are intended as rules and not suggestions. We pre-answer questions the agent will likely have by taking away the bad choices.

Though, even superpowers' own documentation say this is not really enforceable because your instructions are just suggestions from the AI's perspective. Without using hooks or some other deterministic method to enforce the rules, you can never guarantee 100% accuracy.

Superpowers conventions used:

- The "Iron Law"
- "Spirit-vs-Letter"
- Red Flags List
- Rationalization Table
- Close Every Loophole Explicitly

Each of these conventions is a technique for improving agent adherence to discipline rules and, together, they form a system for writing "bulletproof" skills.

#### Iron Law

Draw a line in the sand and mandate the most important operational rule. Whenever the agent rationalizes a reason to break that rule, make it clear that the rationalization was NOT a valid exception to the rule.

I believe this comes from Uncle Bob's Three Rules of TDD ([D](#ref-d)): "You may not write production code until you have written a failing unit test." It's the primary operational rule that anchors the entire process.

In the case of agent skills, it's more of a strong suggestion that addresses a specific (observed) failure mode. For example, TDD is somewhat challenging to enforce in an agent - at least without using hooks and taking more manual control of the process. AI likes to skip the process and do everything in one go, or to ignore and rationalize the rules. Since the rules _are_ the process - a system even - you can easily end up with a mess when those rules aren't followed consistently.

Here is superpowers' own "Iron Law" for writing skills ([A](#ref-a)):

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

#### Spirit-vs-Letter

While rationalizing a reason to subvert a rule, a frequent reason given by the agent is that they are "following the spirit" of the rule, even if not following it "to the letter."

This process addresses the issue by placing a 'spirit-vs-letter' clause early in the document ([A](#ref-a)):

```markdown
**Violating the letter of the rules is violating the spirit of the rules.**
```

This is simply another rule, designed to stand out with bold emphasis, to make it more likely the agent will notice and avoid taking a shortcut.

#### Red Flags

Red flags are signals that the agent is in the process of violating a rule (again, observed from real failures). Example from superpowers ([A](#ref-a)):

```markdown
## Red Flags - Stop and Start Over

- Code before test
- "I already manually tested it"
- "Tests after achieve the same purpose"
- "It's about spirit not ritual"
- "This is different because..."

**All of these mean: Delete code. Start over with TDD.**
```

These give the agent a hard signal to abort and start over, following the correct procedure. The key moment is the pattern-match itself:

| | |
|---|---|
| **Bad** | Agent thinks "I already manually tested it" - and keeps going. |
| **Good** | Agent thinks "I already manually tested it," recognizes it verbatim from the Red Flags list, and stops: "That's a red flag - delete the code, start over with TDD." |

*Bad fails because no self-check fires and the rationalization passes unnoticed. Good works because the verbatim match turns an abstract rule into a hard interrupt.*

#### Rationalization Tables

The iron law gets its own section because it is the most important operational rule that must always be followed. But _every_ rule you write is a potential place where the agent can rationalize a reason to break the rule. So write a table with common rationalizations you have observed, and explain why they are not valid reasons for breaking the rules.

Here is an example, again lifted directly from superpowers ([A](#ref-a)), for their own writing-skills skill:

| Excuse | Reality |
|--------|---------|
| "Skill is obviously clear" | Clear to you ≠ clear to other agents. Test it. |
| "It's just a reference" | References can have gaps, unclear sections. Test retrieval. |
| "Testing is overkill" | Untested skills have issues. Always. 15 min testing saves hours. |
| "I'll test if problems emerge" | Problems = agents can't use skill. Test BEFORE deploying. |
| "Too tedious to test" | Testing is less tedious than debugging bad skill in production. |
| "I'm confident it's good" | Overconfidence guarantees issues. Test anyway. |
| "Academic review is enough" | Reading ≠ using. Test application scenarios. |
| "No time to test" | Deploying untested skill wastes more time fixing it later. |

> All of these mean: Test before deploying. No exceptions.

These are rebuttals for excuses actually observed in testing. Once again, we're taking away bad choices from the places where the agent needs to make a decision.

#### Close Every Loophole Explicitly

> Don't just state the rule - forbid specific workarounds ([A](#ref-a))

Like regression tests for broken behavioral rules. When you see an agent use a workaround or rationalize a reason to subvert the rules, add a rule that explicitly forbids what they did - either as a part of the workflow rules or in one of the bulletproofing mechanisms we've already covered.

```markdown
Always load the full SKILL.md file into context before answering.
**DO NOT** use `head`, `grep`, or targeted reads to avoid loading the entire file.
```

#### A Caveat from agentskills.io

One counterpoint worth noting: the [agentskills.io skill-evaluation guide](#ref-c) suggests that reasoning-based instructions ("Do X because Y tends to cause Z") work better than rigid directives ("ALWAYS do X, NEVER do Y"), because models follow instructions more reliably when they understand the purpose. The conventions above lean hard on imperative, absolute wording.

I don't buy the conflict. The "why" is already in there - it lives in the rationalization tables, where every rebuttal is a reason stapled to a hard rule. Still, the point stands: an Iron Law with no stated reason is just a brittle directive. If you can't explain why a rule exists, an agent under pressure will invent a reason it doesn't apply.

### Example

> WARNING: Pressure campaigns are the cheapest of the three, but still multiply fast - one scenario per discipline rule, across both arms.

Following the precedent of the previous test types, here is a simplified, illustrative skill that runs a pressure test against a single rule for a target skill:

[pressure-testing-skills](./examples/skills/pressure-testing-skills/SKILL.md)

It requires a verbatim rule to test from the skill file. I tested it like so:

```
@docs/writing-skills/part-3/examples/skills/pressure-testing-skills/SKILL.md
run a pressure test against a rule from the writing-skills skill
```

### My Implementation

I used the same workspace isolation techniques from the other test types, once again.

- [pressure-testing-skills skill](../../../skills/pressure-testing-skills/SKILL.md)
- [custom agent definition](../../../skills/pressure-testing-skills/agents/pressure-evaluator.opencode.md)

## Known Weaknesses and Omissions

> A pass rate is only meaningful if the test suite itself is clean.

While writing this document, I compared my version of the process against the agentskills.io guide on evaluating skill output quality ([C](#ref-c)), and it surfaced a list of things their guide does that mine doesn't. I'm recording them here partly as an honest accounting, and partly as a to-do list for the next iteration.

**Cost/benefit quantification.** I warned that campaigns are token-intensive, but never measure what the testing buys. The guide records tokens and duration per run and does an explicit delta analysis - "a skill that triples token usage for a 2-point improvement might not be worth it."

**Assertions as a first-class artifact.** The guide separates human-readable `expected_output` from machine-checkable `assertions`. It also grades harder than I do: assertions can be too brittle or too vague, and a PASS requires quoted evidence, no benefit of the doubt.

**Variance as a diagnostic signal.** High variance across runs means a flaky eval or ambiguous skill instructions - and the fix for the latter is examples and specificity, not more words. Noise is a signal about the skill, not just the test.

**Pattern analysis of the test suite itself.** The guide applies ablation logic to the assertions as well as the rules. Have assertions that always pass in both arms? Remove them - they inflate the pass rate. Always fail in both arms? That's a broken test, not a broken skill. A pass rate is only meaningful if the suite itself is clean.

**Blind comparison instead of the length heuristic.** When two variants tie, my rule is "adopt the shorter phrasing" - a proxy, not a measurement. The guide's answer is a blind LLM-judge comparison: show both outputs to a judge without revealing which version produced which.

**A human review loop.** My campaigns are fully automated end to end. The guide keeps a `feedback.json` next to the evals - empty feedback means the eval passed. Automated grading catches the failures you anticipated; a human catches the ones you didn't.

**Concrete eval workspace conventions.** The guide is more operational about where things live: an `evals/evals.json` schema, `iteration-N/` directories so you can diff campaigns, and a rule to read the full transcript of any eval that runs 3x slower than the others. Mine leave traces all over the workspace. I'm sloppy.

## Conclusion

> YOU MUST TEST YOUR SKILLS! THEY FAIL WAY MORE OFTEN THAN YOU MIGHT REALIZE!

I wrote the "conclusion" remarks in the TLDR section, at the top, because I was sure nobody would make it this far.

TLBIRIA (Too Long, But I Read It All):

- You must test skills; untested skills are unreliable; if you don't care about every rule in the skill, they shouldn't be there in the first place
- Testing is time/token intensive
- It's very nice to have a useful local model for the actual evals
- You may want to look at higher-quality third-party implementations, this was an exercise in understanding the processes and rules, why they are needed

## Next

I think I need to make a part 4 to talk about third-party solutions and services, how I plan to unify and rebuild these test harnesses (again), discuss ablation and retirement, and my case against auto-invoking skills.

This might also be the time to look into things like LangChain, DSPy, and GEPA instead of implementing my own bulletproofing suite.

## References

- <a id="ref-a"></a>**[A]** [Superpowers - "writing-skills" skill](https://github.com/obra/superpowers/blob/main/skills/writing-skills/SKILL.md)
- <a id="ref-b"></a>**[B]** [Superpowers - Testing skills with subagents](https://github.com/obra/superpowers/blob/main/skills/writing-skills/testing-skills-with-subagents.md)
- <a id="ref-c"></a>**[C]** [Agent Skills - Evaluating skill output quality](https://agentskills.io/skill-creation/evaluating-skills)
- <a id="ref-d"></a>**[D]** [Uncle Bob - The Three Rules of TDD](http://butunclebob.com/ArticleS.UncleBob.TheThreeRulesOfTdd)
- <a id="ref-e"></a>**[E]** [Chroma Research - Context Rot: How Increasing Input Tokens Impacts LLM Performance](https://research.trychroma.com/context-rot)
- <a id="ref-f"></a>**[F]** [Agensi - Prompt stress test: find where it breaks](https://www.agensi.io/skills/prompt-stress-test-find-where-it-breaks)
- <a id="ref-g"></a>**[G]** [MindStudio - AI agent failure modes: the reasoning-action disconnect](https://www.mindstudio.ai/blog/ai-agent-failure-modes-reasoning-action-disconnect)
- <a id="ref-h"></a>**[H]** [Laban et al. - Are You Sure? Challenging LLMs Leads to Performance Drops in The FlipFlop Experiment](https://arxiv.org/html/2311.08596v2)
