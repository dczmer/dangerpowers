---
artifact: implementation-report
date: 2026-07-30
plan: PLANS/2026-07-30-extract-testing-skills-plan.md
phase: 3
status: DONE
git_commit_start: ae4f817b41a18be5aa007227dfb1059c7d2b23af
git_commit_end: 6163c31386fb0825abd93b81b3833dddb2d969c9
---

# Phase 3: Revise writing-skills, remove extracted references, update AGENTS.md — Implementation Report

## Summary

Applied all four exact old→new replacements in `skills/writing-skills/SKILL.md` (two `**REQUIRED:**` pointers → manual-invocation redirects; two checklist blocks → user-direction items), `git rm`'d both extracted reference files, and replaced `AGENTS.md:13` with the user-confirmed prose. All four automated criteria pass. The diff was verified hunk-by-hunk against the plan: only the four intended regions changed; the Iron Law, Trigger Eval Rule, no-exceptions lists, exemptions, untested-recording rules, status rule, and frontmatter description are byte-for-byte unchanged (confirmed via `git diff HEAD` showing only the four intended hunks).

## Changes Made

#### 1. Testing Discipline Skills pointer + Trigger Optimization pointer + both checklist blocks
**File**: `skills/writing-skills/SKILL.md`
**Changes**: Replaced `:153` pointer with the plan's "Testing is part of the skill-creation process, but the agent does not run it." redirect to `pressure-testing`; replaced `:168` pointer with the equivalent redirect to `trigger-testing`; replaced the Testing checklist block (`:197-203`) and Trigger Optimization checklist block (`:205-211`) with the plan's exact new text. All other content unchanged (Changes Required items 1-4).

#### 2. Deleted extracted reference files
**File**: `skills/writing-skills/references/pressure-testing.md`, `skills/writing-skills/references/trigger-optimizing.md`
**Changes**: `git rm` of both files per Changes Required item 5. The `references/` directory is now absent from `skills/writing-skills/` (only `SKILL.md` and `test-campaigns/` remain).

#### 3. AGENTS.md Pressure Test Pollution edit
**File**: `AGENTS.md`
**Changes**: Replaced line 13 with "When the user runs test campaigns via the pressure-testing or trigger-testing skills, watch for two contamination sources in baseline runs:" — the user-confirmed edit per the plan's Decisions table. Skills now named by name only, no path.

## Verification

| Criterion | Command | Result |
|-----------|---------|--------|
| Reference files gone | `test ! -e skills/writing-skills/references/pressure-testing.md && test ! -e skills/writing-skills/references/trigger-optimizing.md` | PASS |
| Skill validation passes | `.venv/bin/agentskills validate skills/writing-skills` | PASS |
| No dangling path references | `grep -rn "writing-skills/references" skills/ agents/ AGENTS.md NOTES.md` | PASS (no output, exit=1) |
| No filename references to removed files | `grep -rn "trigger-optimizing\.md\|references/pressure-testing\.md" skills/ agents/ AGENTS.md NOTES.md` | PASS (no output, exit=1) |

Output excerpts:

```text
$ .venv/bin/agentskills validate skills/writing-skills
Valid skill: skills/writing-skills

$ grep -rn "writing-skills/references" skills/ agents/ AGENTS.md NOTES.md; echo "exit=$?"
exit=1

$ grep -rn "trigger-optimizing\.md\|references/pressure-testing\.md" skills/ agents/ AGENTS.md NOTES.md; echo "exit=$?"
exit=1
```

Self-check of manual criteria (mechanical inspection only; human confirmation still required):

- Iron Law (`:140`), Trigger Eval Rule (`:157`), both no-exceptions lists, pure-reference exemption, untested-recording rules, status rule: `git diff HEAD` shows zero changes outside the four intended hunks — byte-for-byte unchanged. Consistent with PASS.
- Pure-reference exemption asymmetry: Testing block header still reads "discipline skills only" and its first item carries "(skipped only for pure-reference skills with no violable rule)"; Trigger block item reads "applies to every skill, including pure reference". Consistent with PASS.
- Both remaining testing pointers state testing is part of the process, name `pressure-testing`/`trigger-testing` to run manually, and say "Never begin any campaign step as part of authoring"; the checklist items instruct telling the user, not performing. No sentence instructs the agent to perform a campaign step. Consistent with PASS.
- `AGENTS.md:13` names the skills by name only, no path. Consistent with PASS.
- Frontmatter description (`:3`) and Frontmatter/Description YAML safety sections (`:43-70`) appear in no diff hunk — unchanged. Consistent with PASS.

Manual Verification items (unchecked, for the human):

- [ ] The Iron Law and Trigger Eval Rule mandate text is byte-for-byte unchanged
- [ ] The pure-reference exemption asymmetry survives: pressure-testing checklist block says "discipline skills only" with the pure-reference skip; trigger block says "every skill, including pure reference"
- [ ] Every remaining testing reference in `writing-skills` states testing is part of the process and names a skill (`pressure-testing` / `trigger-testing`) to run manually; no sentence instructs the agent to perform a campaign step
- [ ] The `AGENTS.md` Pressure Test Pollution section names the skills by name only — no path
- [ ] `writing-skills` frontmatter description and Frontmatter/Description YAML safety sections are unchanged (description best practices stay in place)

## Deviations

None.

## Issues & Concerns

None.

## Follow-ups

- Human confirmation of the five Manual Verification items above (mechanical self-check suggests all pass).
- Phase 4 (integrated content-accounting audit) can proceed once manual criteria are confirmed.
