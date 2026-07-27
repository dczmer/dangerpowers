---
name: iterating-plans
description: Use when a human has reviewed an existing plan in PLANS/ and returns with edits before execution starts, when time has passed since the plan was approved and the codebase may have drifted, or when tempted to edit a plan from memory, apply feedback without verifying the plan's facts still hold, silently absorb a change that invalidates the plan's source research, or treat an approved plan as still approved after editing it. Keywords: update plan, revise plan, plan is stale, edit plan before executing, plan feedback, stale file:line references.
---

# Iterating Plans

A human reviewed the full plan; time passed; they returned with edits before execution begins. Your job is two-fold: apply their edits surgically, and verify the plan's load-bearing facts against the codebase **as it is today** — projects move, and a plan written against last week's code rots. This skill is not the refinement loop during planning (that is writing-plans step 6); it runs after human review, before execution.

## Input Contract

Two inputs, both required before any edit:

1. A path to an existing plan in `PLANS/`
2. The requested edits (the human's feedback)

If either is missing, ask for it. Do not guess which plan they mean, and do not open a plan "just to check it" without feedback to work from.

## The Iron Rules

**Staleness is verified, never assumed.** Every load-bearing claim in the plan — file paths, `file:line` references, symbol names, verification commands, Current State assertions — is checked against the repo as it exists today by sub-agents, never from your memory of the codebase.

**Drift the user agreed to fix is fixed, not annotated.** A stale claim left in the plan with a note beside it is a stale plan. Either update the claim or get an explicit decision to leave it.

**Feedback doesn't transfer authority.** An edit that reopens a question resolved during planning (a Decisions-table pick, a scope exclusion) goes back to whoever owns that question. The person requesting the edit may not be that owner.

**Surgical edits only.** Preserve everything the feedback and the drift report don't touch. No drive-by improvements, no reformatting, no rewriting phases "while you're in there."

**Editing voids approval.** Any edit to a `status: approved` plan sets it back to `draft`. The plan is re-approved by a human before execution, not by you.

**Violating the letter of these rules is violating the spirit of the rules.**

### Rationalizations

| Excuse | Reality |
|--------|---------|
| "The plan is only a week old, nothing changed" | Then verification is cheap. Run it. |
| "I remember this file; no need to spawn a sub-agent" | Your memory is the staleness bug this skill exists to catch. |
| "The drift is unrelated to the requested edits, so I'll ignore it" | Ignore is silent. Surface it and let the user decide — that costs one message. |
| "I'll note the stale line numbers in a comment" | A note next to a wrong fact is a wrong plan. Fix it or get an explicit leave-it decision. |
| "The requested change is small, no need to re-check cross-phase consistency" | Small edits break symbol names and phase dependencies too. The checklist applies to every edit. |
| "The user approved this plan already; the edit is minor" | They approved the plan as written. Any edit makes it a different plan. Status returns to draft. |
| "Re-running research would be overkill" | Correct — and nobody asked you to. Targeted sub-agent verification is not re-research. |
| "I only renamed a phase — the parallel groups still look right" | Declarations are plan facts like file paths. Verify them against the edited Changes Required lists, never from how they look. |

### Red Flags - STOP

- "I'll just tweak the line numbers from what I remember"
- "This drift doesn't matter for the requested edit, skipping"
- "The bundle said X, so X is still true"
- "I'll leave the status as approved — the change is tiny"
- "While I'm editing Phase 2 I'll clean up Phase 3's wording"
- "The user asking for the edit can override the original decision owner"
- "I only renamed/split a phase — no need to re-check the Parallel group declarations"
- "I only renamed/split a phase — no need to re-check the execution-mode declarations"

## Workflow

1. **Read the plan FULLY**, plus the provenance artifacts named in its frontmatter (`source_prd`, `source_bundle`, `source_research`). These paths are stable — RESEARCH artifacts are uniquely named and committed.

2. **Staleness verification.** Extract the plan's load-bearing claims:
   - Every file path and `file:line` reference in Changes Required and Current State
   - Every symbol name introduced or modified by the plan
   - Every verification command in Success Criteria
   - Every Decisions-table pick that cites codebase evidence

   Spawn parallel ad hoc sub-agents (`explore` for existence/location checks, `general` for symbol and command verification), one focused area each, and have each claim reported as **accurate / drifted / gone**, with the current `file:line` for drifted items. Wait for all sub-agents.

3. **Present the drift report and classify the requested edits:**
   - *Editorial* — wording, granularity, formatting. Edit directly.
   - *Structural* — scope, phases, decisions. Check against bundle §6 conflicts and §8 constraints; update the Decisions table and What We're NOT Doing to match.
   - *Evidentiary* — needs understanding beyond the staleness checks. More targeted sub-agent research — never a full re-run of researching-codebase. If the edit invalidates bundle assumptions, say so and offer to route back through scouting-context/researching-codebase instead of silently absorbing it.

   Drift touching the requested edits is incorporated into them. Drift unrelated to the requested edits: surface it and ask whether to fix it in this pass or leave it.

   ```
   Drift found:
   - `src/auth/login.ts:42` (Phase 1) — drifted: now at src/auth/login.ts:57
   - `make check` (Phase 2) — gone: replaced by `make verify` in Makefile

   Your requested edits are structural: they change Phase 2's scope and require a Decisions-table entry.

   I plan to:
   1. <specific edit>
   2. <specific edit>

   Fix the unrelated drift in this pass, or leave it?
   ```

4. **Confirm before editing.** Present the understanding above and get user confirmation. Do not edit on assumption.

5. **Make surgical edits.** If the plan was `status: approved`, set `status: draft`.

6. **Re-run the plan checklist from writing-plans** against the whole plan — cross-phase name consistency, no placeholders, commands still repo-verified (now backed by step 2's evidence, not assumption). If the plan carries `**Parallel group:**` or `**Execution:**` declarations or a `## Final Verification` section and the edits added, removed, renamed, or split any phase, verify those too: every phase still carries both declarations, phases sharing a group still have disjoint Changes Required file sets and no output dependency, every `inline` phase still dispatches subagents itself or requires the integrated result and declares `**Parallel group:** none`, and the Final Verification commands still match the integrated result. A stale declaration is drift — fix it or get an explicit leave-it decision, like any other drift.

7. **Present a diff summary:** what the feedback changed, what drift was fixed, what drift was deliberately left. The plan awaits human re-approval before execution.

## Boundary

This skill ends when the updated plan passes the checklist and the diff summary is presented. Do not begin executing the plan, and do not chain into any other skill; the user decides what happens next.
