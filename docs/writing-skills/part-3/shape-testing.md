# Shape Testing (Mode B): A React Worked Example

> **Disclaimer: AI-generated research**
>
> This document was researched and written by an AI coding assistant on
> 2026-09-09. It illustrates the "Mode B" shape-testing method from
> `bulletproofing-design.md` (same directory) using a **fictional** React
> skill, fixture, and results table — the numbers are invented (modeled on
> real dispatch-prompt wording results from the superpowers spec) to
> demonstrate the method, not measured data. Verify against the linked
> primary sources before citing or relying on this document.

## The mechanic

One self-contained request that tempts the failure, generate the artifact,
inspect what came back. No workspace needed for the pure version: system
prompt = the skill with the guidance variant under test, user message = the
task fixture, output = the code. The only subtleties are (1) the request
must contain the *temptation*, and (2) you score the produced code with
greps plus a manual read.

## What "wrong shape" means

"Shape" is a property of the **artifact the agent produces**, not of the
decisions it makes. The agent *did* the task — followed the process,
invoked the right skill, produced the deliverable — but the deliverable
itself is malformed. Canonical examples from the superpowers spec:

- A dispatch prompt that **re-types spec values** into the prompt instead
  of referencing them (bloated, and the copies drift from the source)
- A review report that **narrates instead of citing** (prose summary
  instead of file:line evidence)
- A plan with **placeholders** ("TBD", "add appropriate error handling")
- A verdict **buried** at the bottom instead of leading the response

The agent complied with every behavioral rule; the *output contract* is
what failed.

## Why multiple choice can't measure it

| | Mode A (discipline) | Mode B (shape) |
|---|---|---|
| Observable | A **decision** — did the agent skip the required action? | An **artifact** — does the composed output match the contract? |
| Multiple choice works? | Yes — "choose A, B, or C" exposes the decision under pressure without doing real work | No — it measures *recognition*, not *production* |

The recognition/production gap is the whole problem: an agent can
correctly identify which of three dispatch prompts is well-shaped and
*still* produce a bloated one when composing under a competing incentive
("make the prompt self-contained" is what tempts restating the spec — the
incentive only exists during generation). The failure lives in the act of
composition, so the test has to make the agent compose.

## Worked example: a fictional React skill

`react-component-conventions` — house style for a codebase. The shape rule
under test: **styling lives in a co-located CSS module, never inline**.

Why this rule makes a good example: the model's training prior pulls hard
toward inline styles and single-file self-containedness. That prior *is*
the competing incentive — the exact hazard shape where prohibitions
backfire.

## The fixture (user message)

Engineered to tempt two specific wrong shapes:

```
Write a React component called `PriceTag` for our store UI.

- Props: name (string), price (number), salePrice (optional number)
- Shows the product name and price; when on sale, shows the old price
  struck through next to the sale price, plus a "SALE" badge
- The badge turns a darker red on hover

Respond with the complete file(s), each prefixed by its path.
```

Two built-in temptations:

1. **"Complete file(s)" as one self-contained ask** → the model wants a
   single self-contained artifact → inline `style={{}}`.
2. **The hover state** → impossible with inline styles → the model must
   either produce real CSS (right shape) or reach for the classic wrong
   shape: an `onMouseEnter`/`useState` hover hack.

If the fixture doesn't contain a temptation like this, all variants will
score clean and you've learned nothing — the same way a pressure scenario
without pressure proves nothing.

## The test

One fresh API call per sample, 5 reps per variant. System prompt = the
full skill with one of these swapped into the styling section:

| Arm | Guidance |
|---|---|
| V0 control | *(styling section absent)* |
| V1 prohibition | "Never use inline styles or `style` props. No Tailwind classes." |
| V2 recipe | "Every component ships as two files: `Name.tsx` and `Name.module.css`. All class names come from `import styles from './Name.module.css'`. Interactive states (hover, focus, active) are CSS pseudo-classes." |
| V3 recipe + nuance | V2 + "…unless a style is truly one-off." |

## Scoring the artifacts

Inspect the generated TypeScript/CSS directly. Grep for triage, then read
every hit by hand:

```python
MARKERS = {
    "inline_style":      r"style=\{\{",                    # wrong shape
    "hover_hack":        r"onMouseEnter|onMouseLeave",     # wrong shape
    "raw_string_class":  r'className="',                   # bypasses the module
    "css_module_import": r"import styles from",            # right shape
    "module_css_block":  r"PriceTag\.module\.css",         # second file exists
    "default_export":    r"export default",                # separate house-style rule
}
```

The manual read matters: a sample that writes `// don't use style={{}}
here` trips the `inline_style` grep without being a violation. And since
the recipe demands *two* artifacts, check the response contains both the
`.tsx` and the `.module.css` block — multi-file output is fine in a
single-shot text response as long as the fixture asks for path-prefixed
files.

## Plausible results (fictional, modeled on real dispatch-prompt data)

| Arm | inline styles | hover hack | CSS module | Shape across 5 reps |
|---|---|---|---|---|
| V0 control | 4/5 | 2/5 | 1/5 | 4 different structures — high variance |
| V1 prohibition | 1/5 | **4/5** | 1/5 | failure **displaced**, not fixed |
| V2 recipe | 0/5 | 0/5 | 5/5 | all 5 reps: same two-file shape |
| V3 recipe + nuance | 2/5 | 0/5 | 5/5 | noisy — reps disagree on "one-off" |

V1 is the instructive row: the prohibition *did* suppress the banned
token, but the hover requirement still had to go somewhere — so the
failure migrated into `useState` mouse-event hacks, a strictly worse shape
than the one that was banned. That's the composition-prohibition backfire
in code form: **you can't negotiate away an incentive, only give it a
sanctioned outlet.** V2 wins not because it forbids more but because it
states what the output *is*, leaving nothing to negotiate. V3 shows the
nuance clause reopening the negotiation.

## Two refinements

- **Code gives a stronger scorer than regex.** Because the artifact is
  compilable, level up: write each sample's files into a sterile workspace
  and run `tsc --noEmit` and `eslint` over them. That's the session-based
  variant of the harness — real fixtures on disk, tool-using agent,
  `opencode run --dir <ws>`. More expensive per sample, but "does it
  compile and lint" is an objective shape signal no regex matches. The
  grep-triage + manual-read version is the cheap first pass; the
  compile-pass version is what to trust for a rule intended to ship.
- **Variance check applies to code too.** Five reps producing five
  different file structures means the wording isn't binding even if every
  individual file looks plausible — the instability is only visible by
  comparing reps, which is why single samples lie.

## Tool calls and context-digging

A natural objection to the self-contained-request design: how do you know
the agent won't start making tool calls and burn cycles digging for
context about the hypothetical situation on your system?

### Raw API call: structurally impossible

The harness call registers no tools:

```python
resp = client.messages.create(
    model=PRODUCTION_MODEL,
    system=SKILL_TEMPLATE.replace("{{GUIDANCE}}", guidance),
    messages=[{"role": "user", "content": fixture}],
)
```

The Anthropic API only gives a model tools if you register them in the
request. No `tools` array → the model can only emit text. It cannot read
files, search, or run anything, because there is literally no mechanism
for it. The worst it can do is *narrate* intent ("First, let me look at
the existing components...") — which costs nothing and is itself data: if
many samples say that, your fixture feels context-starved and the outputs
reflect guesswork, not the guidance's effect. That's a signal to fix the
fixture, not the guidance.

This is also *why* fixtures must be self-contained by construction — the
same rule trigger-testing applies to queries ("no references to files or
context that don't exist in a bare workspace"). With no tools, a reference
to "our store UI" can't cause a detour; with tools, it will.

### Session-based sampling: bounded, not eliminated

If you run the sample through a real harness (`opencode run`) because you
want compiler scoring or you're testing a tool-mediated rule, then an
agent told to write a component "for our store UI" will happily burn its
budget globbing for existing components, reading `package.json`, and
interviewing your `node_modules`. The countermeasures:

1. **Sterile workspace.** Evals run with `--dir <ws>` pointed at a temp
   dir — there is nothing to find. The digging terminates immediately
   against an empty sandbox, and the source repo is invisible.
2. **Restricted agent.** Same pattern as trigger-testing's
   `trigger-evaluator`: define the eval agent with a minimal toolset (or
   none) and treat an agent-fallback warning as an abort, never a silent
   run under the default agent.
3. **The "do not attempt to read them" marker.** `README.md` in this
   directory already documents this: fictional artifact paths in scenario
   prompts are marked illustrative precisely to prevent tool-probing
   detours. The convention exists because the detour was observed.
4. **Timeout/step cap as the floor.** A run that burns its budget probing
   ends as void/timeout — bounded waste. A *cluster* of timeouts means the
   fixture or infrastructure is wrong, not the guidance. Investigate
   conditions instead of scoring.

### When you deliberately keep tools

Tools are off unless the thing under test is itself tool-mediated. Two
cases where you'd keep them:

- **The rule is about tool behavior** — "read the file before editing
  it", "run the linter before committing". You can't observe
  read-before-edit without tools. Then you *seed* the workspace with the
  real context files, so the agent's digging terminates somewhere true
  instead of probing a void — the workspace fixture replaces the prompt
  fixture.
- **Compiler-as-scorer** — you want `tsc --noEmit` / `eslint` run over the
  produced files, so the sampler has to write them to disk.

Decision rule: **default to the raw API call (no tools, no workspace);
escalate to a seeded sterile workspace only when the rule or the scorer
requires it.**

## Sources

- `docs/writing-skills/part-3/micro-tests.md` (this repo — harness method,
  doctrine table)
- `docs/writing-skills/part-3/bulletproofing-design.md` (this repo — Mode B
  definition and iteration budget)
- https://github.com/obra/superpowers/blob/main/skills/writing-skills/SKILL.md
  ("Match the Form to the Failure")
- https://github.com/obra/superpowers/blob/main/docs/superpowers/specs/2026-06-10-positive-instruction-redesign-design.md
  (composition-prohibition backfire results this example is modeled on)
