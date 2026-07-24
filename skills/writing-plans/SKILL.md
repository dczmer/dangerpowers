---
name: writing-plans
description: Use when research findings or a context bundle exist and an implementation plan is needed before changing code; also use when tempted to plan with unresolved open questions, write plan steps that say what to do without showing how, leave a pattern conflict unpicked, or edit anything other than the plan file while planning. Keywords: implementation plan, plan, phases, PLANS, planning, plan approval.
---

# Writing Plans

You are the decider the upstream skills refused to be. Research mapped the territory; the bundle surfaced conflicts without picking. You pick — and every question is resolved before the plan is final.

## Input Contract

Primary input: a path to a `context-bundle.md`, plus the original request or spec block.

If no bundle is provided: proceed anyway. Record `source_bundle: none` in the frontmatter and fill what the bundle would have fed with your own targeted reads. Where evidence stays thin, resolve it in step 2 of the workflow — never ship a plan on thin evidence.

## The Iron Rules

**No open questions in a final plan.** `[needs-human]` → ask the user. `[needs-deeper-research]` → targeted reads. A plan with an unresolved question is a draft; do not present it for approval.

**No placeholders.** A step that changes code shows the code or the exact signature. "Add appropriate error handling", "TBD", "similar to Phase N" are plan failures, not plans.

**Conflicts are picked, not averaged.** Bundle §6 lists variations; the plan's Decisions section records each pick with its rationale. A plan that silently adopts one of two conflicting patterns hid a decision from the user.

**Verification commands are real.** They come from bundle §7 or are verified against the repo (package.json scripts, Makefile, CI config). Never invented.

**Read-only except the plan file.** Planning changes nothing else in the project.

**Violating the letter of these rules is violating the spirit of the rules.**

**Untested rules:** all of the above shipped without baseline pressure scenarios. Grow the rationalization table as violations are observed.

### Rationalizations

| Excuse | Reality |
|--------|---------|
| "The open question won't affect the implementation" | Then resolving it costs one message. Ask. |
| "The implementer can fill in the details" | A plan that delegates its decisions is a wish, not a plan. |
| "The two patterns are equivalent, no need to record the pick" | The bundle flagged a conflict; the user approved a plan, not a coin flip. Record it. |
| "The test command is obvious" | Bundle §7 was verified against the repo. "Obvious" commands are how plans fail on phase one. |

### Red Flags - STOP

- "I'll note the question in the plan and let implementation decide"
- "This phase just needs appropriate tests"
- "Pattern A is clearly right, no need to explain"
- "I'm sure the repo has a standard test command"

## Workflow

1. Read the bundle FULLY, plus the research findings it cites. Note §6 conflicts and §9 open questions.
2. Resolve every open question: ask the user, or targeted reads. Never re-run full research — the bundle already compressed it.
3. Propose a phase outline (one line per phase) to the user. Get buy-in on phasing and granularity before writing details.
4. Write the plan to `PLANS/YYYY-MM-DD-<kebab-description>.md` per `references/plan-template.md`. `PLANS/` lives at the project root and is committed to source control. Build the file incrementally; it is the only file you may write.
5. Run the plan checklist below. Fix failures before presenting.
6. Present the plan location for approval. Iterate on feedback with surgical edits; do not rewrite the plan for a scoped change.

## Phase Granularity

A phase is the smallest unit with its own verification gate: automated and manual success criteria, plus a pause for human confirmation before the next phase. Do not decompose phases into step-level task sequences (write test / run test / implement / commit) — that granularity belongs to execution, and plans that carry it rot the moment implementation deviates.

## Plan Checklist

- [ ] Frontmatter complete (verbatim request, source paths, commit, branch)
- [ ] Context section explains why this change is being made
- [ ] Every bundle constraint (§8) respected or explicitly excluded in What We're NOT Doing
- [ ] Every bundle conflict (§6) resolved in Decisions with rationale
- [ ] No placeholders: scan for "TBD", "TODO", "appropriate", "similar to", "etc."
- [ ] Every phase: exact file paths, automated + manual criteria with repo-verified commands
- [ ] Names and signatures used in later phases match earlier phases
- [ ] Provenance: bundle and research paths recorded in References
