---
artifact: implementation-report
date: 2026-07-27
plan: /home/dave/source/dangerpowers/PLANS/2026-07-27-writing-skills-trigger-optimization-plan.md
phase: 1
status: DONE
git_commit_start: 10b1e35b519429c00875c10c5ff360e8279382ee
git_commit_end: <filled after commit>
---

# Phase 1: writing-skills Trigger Optimization — Implementation Report

## Summary

The writing-skills skill was augmented with trigger-optimization methodology: a new heavy on-demand reference `references/trigger-optimizing.md`, a new `## Trigger Optimization` section in `SKILL.md` (inserted between `## Testing Discipline Skills` and `## Checklist`), and a new `**Trigger Optimization:**` checklist subcategory after `**Testing (discipline skills only):**`. All edits match the plan's Changes 1–3 verbatim (verbatim insertion text for Changes 2 & 3; the detailed section spec for Change 1). All six of the plan's Final Verification commands (plan lines 305–312) pass against the working tree. `references/pressure-testing.md` and the existing test-campaign logs are byte-identical to HEAD. The phase is committed.

A prior interrupted run returned `status: BLOCKED` based on a misread of the plan's Final Verification line 308 — it substituted a generic `grep -c 'test-campaigns/\|trigger-evals/' SKILL.md` (expected `0`) for the plan's actual command, which is a narrowed regex matching only **dated** filenames (`test-campaigns/20YY-MM-DD-...md`, `trigger-evals/20YY-MM-DD-...json`, `trigger-evals/...-fresh.json`) and which deliberately preserves generic destination-path mentions like `trigger-evals/train.json` and the bare `test-campaigns/` directory. Run as written, the gate prints `ok` (verified below). The plan is internally consistent; this run re-litigates nothing and reconciles to the plan's verbatim text.

## Changes Made

#### 1. New reference file `trigger-optimizing.md`
**File**: `skills/writing-skills/references/trigger-optimizing.md` (new)
**Changes**: Created the heavy on-demand reference modeled on `pressure-testing.md`'s section flow and length (177 lines, ≤220 target). No YAML frontmatter. Opens with `# Trigger Optimizing` / `**Load this reference when:** ...`. Contains every section listed in Change 1:
- `## Scope` — separate-axis principle, applies to all skill types (reference not exempt), relationship to pressure testing.
- `## Trigger Eval Query Design` — ~20 queries; should-trigger axes table (phrasing formality, explicitness, detail level, complexity); **near-miss** negatives with the rejection of weak negatives; realism tips (file paths, personal context, specific details, casual language, typos).
- `## Train/Validation Split` — ~60/40, shuffled, fixed across iterations; `trigger-evals/train.json` + `trigger-evals/validation.json`; validation pass rate selects the best iteration.
- `## The Optimization Loop` — ≤5 iterations, four steps, failure-class remediation table, never-paste-keywords rule (cross-ref `SKILL.md:53`), 1024-char recheck every iteration, fresh-query sanity check.
- `## opencode Harness` — verified invoke + detection snippet + verbatim eval-loop bash skeleton + pass criterion (>0.5 over ≥3 reps; ≥5 for borderline) + stop-early tip.
- `## Contamination Rules` — three rules verbatim (no `XDG_CONFIG_HOME` stripping; verify global `~/.config/opencode/AGENTS.md` empty; cross-skill visibility is expected).
- `## Done Criteria` — train pass, validation-best, fresh-query pass, ≤1024 chars.
- `## Common Mistakes` — 7-row table.
- `## Results Log Format` — the two optional `## Trigger evals` and `## Fresh-query sanity check` sections; `-trigger` suffix convention; `trigger-evals/` directory convention (JSON arrays of `{"query","should_trigger"}`, committed, NOT gitignored).

#### 2. New `## Trigger Optimization` section in `SKILL.md`
**File**: `skills/writing-skills/SKILL.md`
**Changes**: Inserted the verbatim block from Change 2 (plan lines 222–237) between the end of `## Testing Discipline Skills` and `## Checklist`: the `**The Trigger Eval Rule: NO DESCRIPTION SHIPS WITHOUT A PASSING EVAL SET.**` declaration, the axis-separation paragraph, the `**No exceptions:**` list, the untested-description recording sentence, and the `**REQUIRED:** See references/trigger-optimizing.md` pointer in Style A. Confirmed placement via `grep -q` (presence of `## Testing Discipline Skills`, `## Trigger Optimization`, `## Checklist` in order — CMD 4 below).

#### 3. New `**Trigger Optimization:**` checklist subcategory in `SKILL.md`
**File**: `skills/writing-skills/SKILL.md`
**Changes**: Inserted the verbatim three-item `**Trigger Optimization:**` subcategory from Change 3 (plan lines 244–249) after `**Testing (discipline skills only):**` at end of file.

#### 4 & 5. Automated Verification runs
**File**: no file change
**Changes**: Ran the two validation commands. Both PASS (see Verification table).

## Verification

Every Final Verification command from plan lines 305–312, run exactly as written against the working tree (post-edit, pre-commit):

| # | Command | Result |
|---|---------|--------|
| 1 | `.venv/bin/agentskills validate skills/writing-skills` | PASS — `Valid skill: skills/writing-skills` |
| 2 | `for d in skills/*/; do .venv/bin/agentskills validate "$d"; done` | PASS — every skill prints `Valid skill: ...` (13/13) |
| 3 | `grep -Eq 'test-campaigns/20[0-9]{2}-[0-9]{2}-[0-9]{2}-[a-z-]+\.md\|trigger-evals/20[0-9]{2}-[0-9]{2}-[0-9]{2}-[a-z-]+\.json\|trigger-evals/[a-z-]+-fresh\.json' skills/writing-skills/SKILL.md && echo "rule-violation" \|\| echo "ok"` | PASS — prints `ok` |
| 4 | `grep -q '## Trigger Optimization' SKILL.md && grep -q '## Checklist' SKILL.md && grep -q '## Testing Discipline Skills' SKILL.md` | PASS — exit 0, no output |
| 5 | `test -f skills/writing-skills/references/trigger-optimizing.md` | PASS — exit 0 |
| 6 | `grep -q '"name":"writing-prds"' <(opencode run --dir /home/dave/source/dangerpowers --format json "help me write a PRD for a new feature that adds caching to our API" 2>&1) && echo harness-ok` | PASS — prints `harness-ok` |

Relevant output excerpts:

```text
$ agentskills validate skills/writing-skills
Valid skill: skills/writing-skills

$ for d in skills/*/; do agentskills validate "$d"; done
Valid skill: skills/executing-plans
Valid skill: skills/isolating-worktrees
Valid skill: skills/iterating-plans
Valid skill: skills/plan-to-execution
Valid skill: skills/prd-to-plan
Valid skill: skills/project-bootstrap-nix
Valid skill: skills/prompt-shaping
Valid skill: skills/researching-codebase
Valid skill: skills/scouting-context
Valid skill: skills/writing-plans
Valid skill: skills/writing-prds
Valid skill: skills/writing-quick-plans
Valid skill: skills/writing-skills

$ grep -Eq '...dated-filename regex...' skills/writing-skills/SKILL.md && echo "rule-violation" || echo "ok"
ok

$ test -f skills/writing-skills/references/trigger-optimizing.md; echo $?
0

$ grep -q '"name":"writing-prds"' <(opencode run --dir /home/dave/source/dangerpowers --format json "..." 2>&1) && echo harness-ok
harness-ok
```

Byte-identity check (Manual Verification item 5):

```text
$ git diff HEAD -- skills/writing-skills/references/pressure-testing.md
(exit 0, no output — byte-identical to HEAD)

$ git diff HEAD -- skills/writing-skills/test-campaigns/
(exit 0, no output — byte-identical to HEAD)
```

Manual Verification items (human-confirmed) — NOT checked off; listed for the controller:

- [ ] `references/trigger-optimizing.md` exists, opens with `# Trigger Optimizing` + `**Load this reference when:**`, contains all sections listed in Change 1
- [ ] `SKILL.md` contains `## Trigger Optimization` between `## Testing Discipline Skills` and `## Checklist`, with the parallel Iron Law declaration, the `**No exceptions:**` list, and the `**REQUIRED:** See references/trigger-optimizing.md` pointer
- [ ] `SKILL.md` Checklist contains a `**Trigger Optimization:**` subcategory after `**Testing (discipline skills only):**` with exactly the three items listed in Change 3
- [ ] `SKILL.md` contains no test/campaign status or verdict text and no references to **specific** campaign or eval files (only dated filenames forbidden; generic destination-path mentions allowed)
- [ ] `references/pressure-testing.md` and existing test-campaign logs byte-identical to pre-plan state — verified above (diff empty)
- [ ] No file under any other skill's directory touched
- [ ] Harness sanity snippet prints `harness-ok` — verified above

## Deviations

None. Changes 1–3 were applied exactly as the plan specifies, verbatim where the plan gave verbatim text. The reference file's section content was written to the detailed spec (the plan gives a section-by-section description rather than verbatim text for Change 1); the section list, ordering, and substantive content all match. No improvisation was applied. The harness sanity snippet (Manual Verification item 7) was run as part of Final Verification CMD 6 — it is also listed in the plan's Final Verification block (line 311), so running it was required, not a scope expansion.

## Issues & Concerns

None. The prior interrupted run's BLOCKED claim was based on a misread of Final Verification line 308; the actual command (a narrowed regex matching only dated filenames) prints `ok` as expected. No mismatch exists between the plan's Changes and its Verification.

## Follow-ups

- Run the first writing-skills trigger-optimization campaign as a separate follow-up (this plan deliberately does not run one).
- Human review of the seven Manual Verification items above.

## Files committed

- `skills/writing-skills/references/trigger-optimizing.md` (new)
- `skills/writing-skills/SKILL.md` (edited — section insert + checklist subcategory)
- `PLANS/2026-07-27-writing-skills-trigger-optimization-phase-1-report.md` (this report)

Not touched (verified byte-identical to HEAD): `skills/writing-skills/references/pressure-testing.md`, `skills/writing-skills/test-campaigns/*`. No file under any other skill's directory was touched. The plan file `PLANS/2026-07-27-writing-skills-trigger-optimization-plan.md` is untracked in the working tree and was not staged by this phase (it is the dispatcher's concern, not part of phase-1 file ownership).