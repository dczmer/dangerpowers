---
name: shaping-small-model-prompts
description: Use when writing or refining a prompt that will run on a small or local language model with weak or disabled reasoning. Covers interview-driven prompt design with decomposition, few-shot exemplars, and format contracts.
disable-model-invocation: true
metadata.opencode/slash: true
metadata.opencode/autoinvoke: false
---

# Shaping Small-Model Prompts

A small model with weak reasoning succeeds through demonstrated pattern and narrow scope, not instruction-following — the prompt must carry the reasoning the model lacks. Interview the user one question at a time, then emit a prompt file of minimal single-task phases.

The deliverable is a markdown file at `.dangerpowers/prompts/<task-slug>.md`, echoed in chat. Do not execute the task the prompts describe. Verification is user sign-off, not a live model run.

## When NOT to Apply

- The prompt targets a frontier or hosted model — use `prompt-shaping` instead.
- The user has a working prompt and wants a small tweak — edit it directly.
- The request is purely informational — there is nothing to design.

## Process

0. **Capture the target** — Ask for the model name/size, the context budget, and whether reasoning is enabled. Every drafting decision below depends on these.
1. **Classify the task** — extraction/classification, math/logic/symbolic, generation, or multi-step reasoning. The classification selects techniques from the rules below.
2. **Decompose** — Split any task with more than 2–3 steps into a phase chain, one task per phase. Never emit compound instructions.
3. **Interview one question at a time** — Ask a single focused question per turn until every Spec field is answered. Ask clarifying questions rather than writing a plan document. Elicit each field explicitly:
   - **Goal** — what should the model do?
   - **In scope** — what must the output cover?
   - **Out of scope** — what must the output avoid or ignore?
   - **Assumptions** — what are you taking for granted that the user should confirm?
   - **Success criteria** — what observable property of the output proves the prompt worked?
   - **Output format** — structure, length, style.
   - **Audience** — who or what consumes the output?
   - **Grounding context** — which facts or definitions must the prompt include?
   - **Failure cases** — what would a bad response look like?
   - **Target model** — name/size; reasoning enabled or disabled?
   - **Context budget** — how many tokens can the prompt plus input occupy?
   - **Decomposition plan** — the phases and their data flow.
   - **Exemplars** — the drafted input/output pairs (step 4).
   - **Format contract** — the labeled slots and stop condition.
   - **Verification method** — the mechanical check (see Technique Rules).
4. **Draft the exemplars** — For each phase that needs few-shot demonstration, draft 1–3 input/output pairs. Give reasoning phases worked chains-of-thought, not bare answers. Present the exemplars inside the Spec block.
5. **Emit the Spec block for sign-off** — Present the filled Spec block and ask the user to confirm or correct it. The interview converges on user sign-off, not on your confidence.
6. **Write the prompt file** — On confirmation, write `.dangerpowers/prompts/<task-slug>.md` following the template below and echo its full content in chat.

## Technique Rules

- **Decompose** when the task has more than 2–3 steps — one prompt per step, outputs feeding forward.
- **Add few-shot exemplars** when the output must match a format, tone, or task structure — 1–3 pairs, drafted by you, confirmed by the user.
- **Show worked chains-of-thought** in exemplars when the task is math, logic, or symbolic — the method is demonstration, not appending "think step by step".
- **Always end with a format contract** — labeled slots (`Answer: ___`) and a stop condition; small models drift from schemas.
- **Front-load every prompt** — task statement first, minimal context; shared material lives once in the file's Shared context section.
- **Add a self-consistency harness note** when a phase is high-stakes reasoning — `<!-- harness: run 3 samples, majority-vote -->` in the phase header.
- **Require mechanical verification** — the Verification method is a check a harness can run (regex, parse, diff, test); small models self-critique poorly.

## Spec Block

```markdown
## Spec
- **Goal:** ...
- **In scope:** ...
- **Out of scope:** ...
- **Assumptions:** ...
- **Success criteria:** ...
- **Output format:** ...
- **Audience:** ...
- **Grounding context:** ...
- **Failure cases:** ...
- **Target model:** ...
- **Context budget:** ...
- **Decomposition plan:** ...
- **Exemplars:** ...
- **Format contract:** ...
- **Verification method:** ...
```

## Prompt File Template

```markdown
# Prompt chain: <task title>

Target: <model>, reasoning <on|off>, <context budget> context.

## Run instructions (for the executing agent)

Run each phase in order. The Shared context and each phase's input are already in this conversation.

## Shared context

<facts and definitions every phase needs, written once>

## Phase N — <name>

Input: <what this phase receives, from where>
Output: <the format the next phase or the user expects>

<prompt block>
```

## Example

> **User**: "I need a prompt for my local qwen that pulls the product issues out of support transcripts and ranks them"
>
> **Agent**: "Understood — target is a small local model, so I'll design this as a phase chain. First: which model exactly, and is reasoning enabled?"
>
> *(interview continues, one question per turn, through the Spec fields)*
>
> **Agent**: *(emits filled Spec block; exemplars below included; user confirms)*
>
> **Agent** writes `.dangerpowers/prompts/rank-support-issues.md`:

```markdown
# Prompt chain: rank support issues by frequency

Target: qwen3-4b, reasoning off, 8k context.

## Run instructions (for the executing agent)

Run each phase in order. The Shared context and each phase's input are already in this conversation.

## Shared context

Transcripts are plain text, one per line: `[YYYY-MM-DD] customer: <message>`.
An "issue" is a defect or complaint about the product, not a feature request.

## Phase 1 — Extract issues

Input: the transcripts, pasted into the conversation by the user.
Output: one line per distinct issue, format `issue: <short label>`.

Extract every product issue from the transcripts below.
List each distinct issue once, using a short label.

Example:
Transcripts:
[2026-09-01] customer: the battery dies after an hour
[2026-09-02] customer: battery drains so fast, and the app crashes on login

issue: battery drains fast
issue: app crashes on login

Now extract the issues from the transcripts in this conversation.

Issues (one per line):
issue:
```

```markdown
## Phase 2 — Rank by frequency

Input: the output list from Phase 1.
Output: ranked list, format `1. <label> (<count>)`.
<!-- harness: run 3 samples, majority-vote -->

Count how many times each issue appears and rank them, most frequent first.
Work step by step like this example:

issue: battery drains fast
issue: app crashes on login
issue: battery drains fast

Counting: battery drains fast appears 2 times. app crashes on login appears 1 time.
Ranking: battery drains fast (2) ranks above app crashes on login (1).
Answer:
1. battery drains fast (2)
2. app crashes on login (1)

Now count the Phase 1 list.

Counting:
```

```markdown
## Verification

Run Phase 1 on `transcripts-sample.txt`; diff the output against
`expected-issues.txt`. Run Phase 2 on that output; check the result
matches `^\d+\. .+ \(\d+\)$` on every line and counts sum to the
Phase 1 line count.
```

## Gotchas

- Never repeat Shared context inside a phase — duplication burns the context window and drifts when edited in one place.
- Bare-answer exemplars teach the model to skip reasoning; reasoning phases show the work.
- Compound instructions are the failure mode this skill exists to prevent — split the phase instead of strengthening the wording.
- Fix format drift with slots and exemplars, not with stronger wording.
- Generated exemplars enter the file only after user confirmation at sign-off — a plausible-but-wrong exemplar is worse than none.
- Keep run instructions to a sentence or two — the small model executes them too, and preamble conditionals are the compound instructions this skill exists to avoid. Phase inputs stay in context in a single-session run; never add paste placeholders.

## Checklist

- [ ] Target captured (model, context budget, reasoning on/off) before any drafting
- [ ] Task classified; techniques selected per the Technique Rules
- [ ] Tasks over 2–3 steps decomposed; one task per phase; no compound instructions
- [ ] Asked one question per turn; no batched question lists
- [ ] Exemplars drafted with worked reasoning and confirmed at sign-off
- [ ] Every phase carries `Input:`/`Output:` contracts
- [ ] Every prompt is front-loaded and ends with a format contract and stop condition
- [ ] Verification method is mechanically checkable
- [ ] Spec block confirmed by the user before writing the file
- [ ] File opens with run instructions for the executing agent
- [ ] File written to `.dangerpowers/prompts/<task-slug>.md` and echoed in chat
