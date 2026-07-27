---
name: writing-plans
description: Use when research findings or a context bundle exist and an implementation plan is needed before changing code; also use when tempted to plan with unresolved open questions, write plan steps that say what to do without showing how, leave a pattern conflict unpicked, pick a side of a team-standard or vendor question on the strength of usage counts, or edit anything other than the plan file while planning. Keywords: implementation plan, plan, phases, PLANS, planning, plan approval.
---

# Writing Plans

You are the decider the upstream skills refused to be. Research mapped the territory; the bundle surfaced conflicts without picking. You pick everything the evidence can settle — and every question is resolved before the plan is final. What evidence can't settle (team standards, vendor choices, anything whose answer lives in someone's head) goes to its owner. A resolved plan is one where every question has an answer from its rightful owner, not an answer from you.

## Input Contract

Primary input: a path to a context-bundle artifact (`RESEARCH/`), plus the original request or spec block.

A path to an approved PRD (`PRDS/`) is a primary input alongside the bundle: PRD §1 fills the plan's Context, PRD §2 Non-Goals fill What We're NOT Doing, PRD §8 fills Desired End State verification. Record `source_prd: <path>` in the frontmatter (`none` if absent).

If no bundle is provided: proceed anyway. Record `source_bundle: none` in the frontmatter and fill what the bundle would have fed with your own targeted reads. Where evidence stays thin, resolve it in step 2 of the workflow — never ship a plan on thin evidence.

## The Iron Rules

**No open questions in a final plan.** `[needs-human]` → ask the user. `[needs-deeper-research]` → targeted reads. A plan with an unresolved question is a draft; do not present it for approval. "The user" means the person with authority over the question, not whoever is asking for the plan; their deadline pressure does not transfer their authority to you. Usage counts are input to their decision, never a substitute for it.

**No placeholders.** A step that changes code shows the code or the exact signature. "Add appropriate error handling", "TBD", "similar to Phase N" are plan failures, not plans.

**Conflicts are picked, not averaged.** Bundle §6 lists variations; the plan's Decisions section records each pick with its rationale. A plan that silently adopts one of two conflicting patterns hid a decision from the user.

**Verification commands are real.** They come from bundle §7 or are verified against the repo (package.json scripts, Makefile, CI config). Never invented.

**Read-only except the plan file.** Planning changes nothing else in the project.

**Violating the letter of these rules is violating the spirit of the rules.**

### Rationalizations

| Excuse | Reality |
|--------|---------|
| "The open question won't affect the implementation" | Then resolving it costs one message. Ask. |
| "The implementer can fill in the details" | A plan that delegates its decisions is a wish, not a plan. |
| "The two patterns are equivalent, no need to record the pick" | The bundle flagged a conflict; the user approved a plan, not a coin flip. Record it. |
| "The test command is obvious" | Bundle §7 was verified against the repo. "Obvious" commands are how plans fail on phase one. |
| "Majority usage makes it a pick, not a question" | 3 of 5 services using X is evidence for a recommendation, not a decision. Recommend it in the question you ask. |
| "Approval is the checkpoint where they can veto my pick" | Approval reviews a resolved plan. A guess dressed as a decision gets rubber-stamped, not reviewed. |

### Red Flags - STOP

- "I'll note the question in the plan and let implementation decide"
- "This phase just needs appropriate tests"
- "Pattern A is clearly right, no need to explain"
- "I'm sure the repo has a standard test command"
- "The research points clearly one way, so asking is a formality"

## Workflow

1. Read the bundle FULLY, plus the research findings it cites. Note §6 conflicts and §9 open questions.
2. Resolve every open question: ask the user, or targeted reads. Never re-run full research — the bundle already compressed it.
3. Propose a phase outline (one line per phase) to the user. Get buy-in on phasing and granularity before writing details. The outline includes each phase's `**Parallel group:**` declaration — derive it from the phases' intended Changes Required file sets: phases may share a group only if their file sets are disjoint and neither consumes the other's output. When overlap is uncertain, declare `none`; sequential is the safe default.
4. Write the plan to `PLANS/YYYY-MM-DD-<kebab-description>-plan.md` per `references/plan-template.md`. The `-plan` suffix distinguishes plans from the `-report` files executing-plans writes beside them. `PLANS/` lives at the project root and is committed to source control. Build the file incrementally; it is the only file you may write.
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
- [ ] Every phase Overview carries a `**Parallel group:** <name> | none` line; phases sharing a group have disjoint Changes Required file sets and no output dependency
- [ ] `## Final Verification` section present — repo-verified commands, one per line, or `None`
