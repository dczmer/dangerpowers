---
name: executing-plans
description: Use when an approved implementation plan in PLANS/ is ready to execute, when dispatched as a subagent to implement a single phase of a plan, or when tempted to edit code outside your assigned phase, silently deviate from the plan when the code doesn't match it, edit the plan file while running in parallel with other executors, or report done without verification evidence. Keywords: execute plan, implement plan, run phase, PLANS, plan execution, implementer subagent, phase implementation.
---

# Executing Plans

You are handed one phase of an approved plan. The plan is the spec, your phase is the scope, and the report is the deliverable. Sibling phases may be executing in parallel right now — the plan file is shared state you do not own, and the files outside your phase belong to someone else.

## Input Contract

Three inputs, all required before any work:

1. A path to a `status: approved` plan in `PLANS/`
2. The phase number to execute
3. A report file path

Reports live in `PLANS/` beside the plan, named `<plan-base>-phase-<N>-report.md`, where `<plan-base>` is the plan filename minus the `-plan.md` suffix. If a dispatcher did not provide the report path, derive it yourself from this convention. One report file per phase per invocation — never append to or edit another phase's report.

If any of the three is missing, ask for it. If the plan is `status: draft`, stop — execution requires human approval, and any edit voids it (see iterating-plans).

**Mode is determined by who gave you the report path.** A report path provided by a dispatching controller means subagent mode: the plan file is read-only and you report which criteria passed. If you are the interactive top-level agent executing for the user directly, you may check off that phase's Automated Verification items yourself.

## The Iron Rules

**One phase per invocation.** Do not start the next phase, do not "finish up" a previous one, do not check off criteria for any phase but your own.

**Touch only files listed in your phase's Changes Required.** That list is your file ownership — it is what makes parallel execution safe. A needed fix outside the list is a report item, never an edit.

**The plan file is read-only in subagent mode.** Parallel executors editing shared checkbox state produce lost updates and merge conflicts. Report criterion results; the controller flips the boxes.

**Never check off Manual Verification items.** A human confirms those, in every mode.

**Every automated criterion runs and passes before you report DONE.** Run the commands exactly as written in the plan — they were repo-verified at planning time. A criterion that fails for reasons outside your scope is a report item, not a pass and not a silent skip.

**A plan-vs-reality mismatch stops you.** When the code doesn't match what the plan says, do not improvise a deviation and do not force the plan through. Report BLOCKED with the mismatch protocol below.

**Read files fully.** No limit/offset on any file in your phase's Changes Required. Partial reads are how implementers break invariants they never saw.

**Commit only if the plan or your dispatcher instructs it.** Otherwise leave the working tree changes and list every changed file in the report.

**Violating the letter of these rules is violating the spirit of the rules.**

### Rationalizations

| Excuse | Reality |
|--------|---------|
| "This one-line fix in another file unblocks my phase" | That file may belong to a phase running in parallel right now. Report it; don't touch it. |
| "The plan's approach is clearly wrong, my way is better" | A human approved the plan, not your improvisation. Mismatch → BLOCKED with the protocol below. |
| "Flipping one checkbox is harmless" | Two executors flipping boxes in the same file is a lost update. In subagent mode the plan is read-only, no exceptions. |
| "The code is obviously right; the test command is slow" | DONE without green verification is a claim, not a result. Run it. |
| "I only need the relevant part of the file" | The invariant you break will be in the part you skipped. Read it fully. |
| "Phase N+1 is tiny, I'll do it while I'm here" | Its files may be owned by another executor. One phase per invocation. |
| "The failing check is unrelated to my changes, I'll note it and report DONE" | Unrelated failures are DONE_WITH_CONCERNS with evidence, never DONE. |

### Red Flags - STOP

- "I'll just fix this thing in a file outside my phase"
- "The plan says X but the code does Y — I'll adapt quietly"
- "I'll update the plan checkboxes so the controller doesn't have to"
- "Verification mostly passed"
- "I skimmed the file; the change is localized"
- "Manual testing looks fine to me, checking it off"

## Workflow

1. Read the plan FULLY, plus the provenance artifacts in its References (`source_prd`, `source_bundle`, `source_research`). Absorb Context, Decisions, and What We're NOT Doing — they are the intent you serve when the letter of the plan meets reality.
2. Confirm `status: approved`. Note existing checkmarks: trust that checked work is done; investigate only if something seems off. If your phase's report file already exists, the phase was already executed — verify its claims against the repo and report rather than redo the work.
3. Read every file in your phase's Changes Required — fully.
4. Implement the phase per Changes Required. Follow the plan's intent while adapting to what you find; where you genuinely cannot, that is a mismatch (below), not an improvisation opportunity.
5. Run every Automated Verification criterion. Fix failures within your file ownership and re-run. Failures caused by files outside your ownership: gather evidence, do not fix, report.
6. Write the full report to the report file (contract below).
7. Final message per the report contract. In interactive mode, also check off the phase's passed Automated Verification items in the plan file.

## Mismatch Protocol

When the code can't be made to match the plan, stop and report BLOCKED:

```
Issue in Phase [N]:
Expected: [what the plan says]
Found: [actual situation, file:line]
Why this matters: [explanation]

How should I proceed?
```

The plan may have drifted since approval — say so explicitly when the evidence points that way; that routes the human to iterating-plans.

## Report Contract

Write the full report to the report file per `references/report-template.md` — the template is the canonical structure; every section is required and "None" is a valid entry. The report covers: what was implemented, files changed, each automated criterion with command + result + output evidence, deviations, issues, and follow-ups. The frontmatter `status` must match your final-message status.

Then report back with ONLY (under 15 lines — the detail lives in the report file):

- **Status:** DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
- Commits created (short SHA + subject), or "uncommitted changes in working tree"
- One-line verification summary (e.g. "5/5 automated criteria passing")
- Your concerns, if any
- The report file path

If BLOCKED or NEEDS_CONTEXT, put the specifics in the final message itself — the controller acts on it directly. Use DONE_WITH_CONCERNS if you completed the work but doubt its correctness or saw failures outside your scope. Use BLOCKED if you could not complete the phase. Use NEEDS_CONTEXT if information the plan and artifacts don't contain is required. Never silently produce work you're unsure about — bad work is worse than no work, and you will not be penalized for escalating.

## Boundary

This skill ends at the report. Do not review your own work as a gate (a reviewer is the controller's concern), do not dispatch anything, do not start the next phase, do not merge. Branch and worktree isolation, checkbox updates, and per-phase review belong to the orchestration layer, not to you.

---

> **Status:** pressure-tested GREEN-only (see `test-campaigns/2026-07-25-executing-plans.md`): 20/20 with-skill runs compliant under pressure, but RED was never demonstrated — baselines run from this repo are polluted (agents see the pipeline rules in AGENTS.md and discover this skill). Rules remain flagged until clean-environment baselines confirm the failures exist without the skill.
