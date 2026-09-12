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

> EDITOR: diagram/image of a skill file (box containing a very simple example skill with a name, description frontmatter, and one reference, one discipline, and one shaping rule. indicate the entire document uses conventions from writing-skills with a big angle bracket "Conventions from writing-skills: {" on the left. circle the description in the document, draw a line to a box on the right with "Discipline\nTrigger Testing (queries file)". circle the reference statement and draw similar line to box with "Reference\nRetrieval Test (queries file)". circle the discipline rule and draw a similar line to "Discipline\nPressure Test (extrapolated)". circle the shaping rule and make a line to "Shaping\nMicro-Test (extrapolated).


## Testing Skills and Rules Types

Superpowers defines four types of skills/rules, and each type needs specific forms of testing: 

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

So the superpowers system actually evaluates three of tests, for three different categories of rules, in order to fully cover the body of the skill. We're going to do this as three separate skills instead, because otherwise the full campaign gets a bit complicated and hard to follow.

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

> WARNING: Running a test campaign can be token-intensive in the first phase, where it has to identify and classify all of the reference facts.

If you want to run a test campaign and are afraid of the token burn, you could run this once to generate the queries file and then remove the "inventory" instructions from the skill file to test repeatedly without paying the full cost each time. Or you could use a cheaper model to tune the skill and then run once with a frontier model as a final check.
