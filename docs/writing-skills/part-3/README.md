# "Bulletproofing" Skills

Have you ever used a skill written by someone else that just didn't work as advertised when you tried it? Or have you written a skill that produces inconsistent output or breaks the rules?

In [part-2](../part-2/README.md), we used trigger tests to optimize skill descriptions, for improved accuracy when auto-invoking skills (or when we don't want the skill to fire). But, just like triggering a skill based on description, the rules in your skill body also need tuning and hardening to make them apply more consistently.

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

Reference skills have no rule to violate, so there is nothing to bulletproof. Run a few simple retrieval tasks, single pass, no iteration: can the agent find and correctly apply the documented fact? Failures are fixed by editing the doc directly (gaps, unclear sections), not by adding rules.

> EDITOR: diagram/image of a skill file (box containing a very simple example skill with a name, description frontmatter, and one reference, one discipline, and one shaping rule. indicate the entire document uses conventions from writing-skills with a big angle bracket "Conventions from writing-skills: {" on the left. circle the description in the document, draw a line to a box on the right with "Discipline\nTrigger Testing (queries file)". circle the reference statement and draw similar line to box with "Reference\nRetrieval Test (queries file)". circle the discipline rule and draw a similar line to "Discipline\nPressure Test (extrapolated)". circle the shaping rule and make a line to "Shaping\nMicro-Test (extrapolated).

So the superpowers system actually evaluates three of tests, for three different categories of rules, in order to fully cover the body of the skill. We're going to do this as three separate skills instead, because otherwise the full campaign gets a bit complicated and hard to follow.

### Contamination and Artifact Hunting

> TODO: expand this section and frame it as the major challenge when implementing these tests, counter-intuitive for agents, discipline rules that need pressure testing and bulletproofing.

- more impactful than similar concern for trigger testing; global rules are highly likely to color agent reasoning during body tests
- can't avoid global agents/skills (move/rename those temporarily); would need custom harness perhaps, like langchain
- agents naturally want to dig for supporting information about artifacts mentioned in test query,leading to timeout, excessive tool calls, and step-limit cutoff

## Discipline Skills

### Pressure Testing

### Example

### My Implementation

## Reference Skills

Since these are purely contextual facts, there are no rules or behavior to harden. Instead, we want to test that the agent can retrieve and apply that context consistently and accurately. Resolving failures involves editing the skill document. Typical issues in this category include filling gaps in the contextual details, clarifying sections or phrases, and adjusting the way information is organized.

When there are gaps in the information, the agent will hallucinate an answer to fill in that gap. When sections are unclear - ambiguous semantics, look-alike flags, conflicting information or examples side-by-side - the agent retrieves the right section but applies it incorrectly. When information exists, but the agent can't find it, that implies an organization problem. Anthropic's best practices guide documents how this can happen: agents partially read deeply-nested files (`head -100` previews) and never see poorly signaled sections of information.

The agent has correctly loaded the skill, it wants to comply, there is no incentive to bypass a fact. So we don't need pressure, we need to verify the information architecture so it actually delivers that information to the agent. I think of this like a microcosm of a problem I observe frequently while working on large, complex codebases: even though modern AI is really good at finding the context it needs, it can't always find ALL relevant information on its own. This leads to gradual duplication, inconsistency, and bifurcation of important architectural constructs.

### Retrieval Testing

> EDITOR: mermaid diagram of the simple retrieval test campaign flow from ./examples/skills/retrieval-testing-skills/SKILL.md. only the important parts to show the campaign flow. omit the query detection and authoring, the facts.json file. try to keep it simple while illustrating the important concepts of the testing flow.

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

Run the evals, along with a no-skill control group. Instruct the agent to list the "sources" that were consulted while processing the request. Identify failure categories according to the following table:

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

> EDITOR: mermaid diagram of the simple shaping test campaign flow from ./examples/skills/shape-testing-skills/SKILL.md. only the important parts to show the campaign flow. try to keep it simple while illustrating the important concepts of the testing flow.

you can't reliably predict how changes to wording will affect the results by reasoning alone - you have to measure.

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

Here is a simplified shape testing skill: [shape-testing-skills example](./examples/skills/shape-testing-skills/SKILL.md). It uses subagents to run the evals but does not do any workspace isolation - other skills and rules files can potentially contaminate results.

This skill only tests a single rule (quoted from the skill file directly). For demonstration purposes, I just ask the agent to pick a rule and setup the campaign for me:

> @docs/writing-skills/part-3/examples/skills/shape-testing-skills/SKILL.md i want to shape test a rule from the writing-skills skill

The agent picked a rule, wrote the fixture and variants for the campaign, and started the evals.

### My Implementation

## Conclusion

next part-4: thoughts, suggestions, third-party eval tools, quorum

## References

https://www.agensi.io/skills/prompt-stress-test-find-where-it-breaks
https://www.mindstudio.ai/blog/ai-agent-failure-modes-reasoning-action-disconnect
https://arxiv.org/html/2311.08596v2
https://www.agensi.io/skills/prompt-stress-test-find-where-it-breaks
https://github.com/obra/superpowers/blob/main/skills/writing-skills/SKILL.md
https://github.com/obra/superpowers/blob/main/skills/writing-skills/testing-skills-with-subagents.md
https://research.trychroma.com/context-rot
