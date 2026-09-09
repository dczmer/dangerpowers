# Micro-Tests in Skill Authoring: What They Are, Why They Exist, and How to Apply Them

> **Disclaimer: AI-generated research**
>
> This document was researched and written by an AI coding assistant on
> 2026-09-09. It is based on files in the public `obra/superpowers`
> repository (the `writing-skills` SKILL.md and the design spec
> `docs/superpowers/specs/2026-06-10-positive-instruction-redesign-design.md`).
> The `writing-release-notes` skill, its fixture, and its results table are
> a **fictional illustration** — the numbers are invented (modeled on real
> results from the spec) to demonstrate the method, not measured data.
> Verify against the linked primary sources before citing or relying on
> this document.

## What a micro-test is

A micro-test is a **cheap, single-shot experiment on the wording of skill
guidance**, run before you commit to a phrasing. The structure:

- **One fresh-context sample per call** — a raw API call or a single-shot
  subagent. System prompt = the *realistic context the guidance will live
  in* (the full skill or prompt template, never the guidance in isolation);
  user message = a task that tempts the failure you're trying to prevent.
- **5+ reps per phrasing variant**, because single samples lie — LLM output
  is non-deterministic.
- **Always a no-guidance control arm** — the same task with no guidance at
  all.
- **Programmatic scoring + manual reading** — grep for unambiguous markers,
  then read every flagged match by hand.

It's the fast inner loop of the RED-GREEN-REFACTOR cycle for skills. Full
pressure scenarios (subagent campaigns with combined pressures) are the
final gate, but per the superpowers spec they cost ~$12 and ~50 min per
run; a micro-test sample costs ~$0.15–0.30 and takes seconds. Analogy:
**micro-tests are unit tests for wording; pressure scenarios are
integration tests for discipline.**

## Why they're needed

1. **Wording effects are counterintuitive.** The flagship real result: on
   dispatch-prompt guidance, a *prohibition* ("don't restate the brief")
   made agents re-type **4.4** spec values on average — **worse than no
   guidance at all** (3.6) — while a *positive recipe* scored 3.0 with zero
   variance. You cannot reliably predict this by reasoning about it; you
   have to measure.
2. **The control arm tells you when to stop.** In the writing-plans
   placeholder test, all 40 runs — *including the no-guidance control* —
   produced zero placeholders. Conclusion: current-generation models don't
   exhibit the failure, so no guidance was authored. Without a control
   you'd harden against a phantom.
3. **Non-determinism.** One run proving nothing cuts both ways — one
   success doesn't validate a phrasing, one failure doesn't condemn it.
   Hence 5+ reps.
4. **Variance is itself a metric.** When wording lands, reps converge on
   the same shape. Five different interpretations across five reps means
   the wording isn't binding — tighten the *form* before adding more words.
5. **Automated scoring lies.** Superpowers' own notes: one flagged
   "violation" was the agent correctly *quoting* the prohibition; a
   negation-detection heuristic mislabeled another. So: grep to triage,
   read to verdict.

## How to apply them

The procedure:

1. **Name the failure and the exact wording under test.** Variants might
   be: control, prohibition, positive recipe, recipe + nuance clause.
2. **Build the call realistically.** System prompt = the whole skill with
   the variant embedded; user = a mid-workflow task engineered to tempt the
   failure. Use the model that will actually consume the skill in
   production, at default temperature.
3. **Run the control first.** If the control doesn't exhibit the failure,
   stop — there is nothing to fix.
4. **5+ reps per variant, one sample per call.** Don't ask for five drafts
   in one prompt — the completions anchor each other.
5. **Score with greps for unambiguous markers, then manually read every
   match.**
6. **Judge on convergence, not just averages.** Adopt a variant only if it
   beats the current wording on your metric without regressing others.

And the doctrine superpowers derived from these tests (which form to reach
for):

| Form | Verdict |
|---|---|
| Tripwires (phrase-level self-checks on concrete tokens) | Work |
| Recognition tables (red flags / rationalizations, read at decision time) | Work |
| Discrete-directive prohibitions ("do not ask X to do Y"), no competing incentive | Work |
| **Composition prohibitions** ("don't restate", "never narrate") when the model has its own agenda for the output | **Backfire** — use a positive recipe |
| Recipe + nuance clause ("…unless it matters") | Degrades a winning recipe to noisy |
| Ties | Go to the shorter phrasing |

**Limits:** micro-tests verify wording only. For discipline skills (iron
rules), they do *not* replace full pressure scenarios — and they're N/A for
pure reference skills, where there's no rule to violate.

## Fictional worked example

*(The skill, fixture, and numbers below are invented for illustration.)*

Imagine a skill `writing-release-notes`:

```yaml
---
name: writing-release-notes
description: Use when drafting user-facing release notes from merged commits
---
```

**Failure you're worried about:** the agent pastes commit-message-style
lines with internal ticket IDs (`PLAT-1201: fix null deref`) into
user-facing notes. The competing incentive: including IDs feels *helpful
and traceable* — exactly the composition-prohibition hazard shape.

**Fixture (user message):** a task engineered to tempt the failure:

```
Draft the release notes for v2.4.0 from these merged commits:

a1b2c3d PLAT-1201 Fix crash when importing CSVs with empty headers
e4f5g6h PLAT-1187 Add dark mode toggle to settings
i7j8k9l PLAT-1203 refactor: extract billing retry logic into helper
m0n1o2p PLAT-1199 Security: patch XSS in comment rendering
q3r4s5t PLAT-1210 Improve search ranking for partial matches
...
```

**Variants** (embedded in the full skill as the system prompt):

| Arm | Guidance |
|---|---|
| V0 control | *(nothing)* |
| V1 prohibition | "Never include internal ticket IDs in release notes." |
| V2 recipe | "Each entry is: (1) one sentence of user-visible impact, (2) who it affects, (3) what the user should do differently, if anything." |
| V3 recipe + nuance | V2 + "…unless the ticket ID is important." |

**Harness sketch** (one call per sample, 5 reps each):

```python
import re, anthropic

client = anthropic.Anthropic()
REPS = 5

for name, guidance in VARIANTS.items():
    for rep in range(REPS):
        resp = client.messages.create(
            model="claude-opus-4-8",      # the model that will consume the skill
            max_tokens=2000,
            system=SKILL_TEMPLATE.replace("{{GUIDANCE}}", guidance),
            messages=[{"role": "user", "content": TASK}],  # the commits fixture
        )
        text = resp.content[0].text
        ids = re.findall(r"\b[A-Z]{2,}-\d+\b", text)   # triage metric
        save(name, rep, text, len(ids))                # then READ every output
```

**Plausible results** (modeled on the real dispatch-prompt numbers):

| Arm | Avg ticket IDs | Shape across 5 reps | Verdict |
|---|---|---|---|
| V0 control | 3.6 | Wildly varying formats | failure exists → proceed |
| V1 prohibition | 4.2 | One rep adds a "Ticket:" column "for traceability" | **backfire** |
| V2 recipe | 0.0 | All 5 reps converge on the same 3-part shape | **adopt** |
| V3 recipe + nuance | 1.8 | Each rep decides "important" differently | nuance reopens negotiation |

Ship V2. Note the control did its job first: if V0 had produced 0 ticket
IDs, you'd have stopped and written nothing.

## Second example: discipline skill (first pass only)

For a fictional `running-database-migrations` skill with iron rule `NO
MIGRATION WITHOUT A FRESH BACKUP`, a micro-test can cheaply check whether
the *phrasing binds at all*: mild-temptation task ("staging DB, deploy
window closes in 10 minutes, run the migration"), soft-wording vs
iron-rule-form variants, 5 reps, metric = does the agent back up first, and
do the 5 outputs converge. If the iron-rule form converges on
backup-first, you've validated the wording cheaply. But you **still run
the full pressure scenario** (time + sunk cost + authority, 3+ combined
pressures) as the final gate — micro-tests don't prove compliance under
maximum pressure, and the writing-skills checklist says exactly that.

## Sources

- https://github.com/obra/superpowers/blob/main/skills/writing-skills/SKILL.md
  ("Micro-Test Wording Before Full Scenarios", "Match the Form to the
  Failure", deployment checklist)
- https://github.com/obra/superpowers/blob/main/docs/superpowers/specs/2026-06-10-positive-instruction-redesign-design.md
  (harness method, dispatch-prompt results table, phrasing doctrine,
  writing-plans null result, per-sample cost figures)
