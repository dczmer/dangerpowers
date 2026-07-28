---
artifact: implementation-plan
date: 2026-07-27
git_commit: HEAD
branch: main
request: "Update skills/writing-skills/references/pressure-testing.md with stripped-config baseline findings and campaign-execution lessons from RESEARCH/2026-07-27-stripped-baseline-config-findings.md"
source_prd: none
source_bundle: none (quick pass)
source_research: RESEARCH/2026-07-27-stripped-baseline-config-findings.md
status: approved
---

# Pressure Testing Reference Doc Updates — Implementation Plan

> **For the implementing agent:** Read this plan and the research findings before starting.

## Context

The 2026-07-27 execution-mode-declaration campaign uncovered that skill-description leakage into baseline reps (via the global `~/.config/opencode/skills/dangerpowers` symlink) pollutes pressure-test measurements. `--pure` does not fix it. A stripped XDG config dir does. The research document also captured several campaign-execution process lessons (silent permission failures, cwd requirements, void-run patterns) that belong in the reference doc.

## Current State

`skills/writing-skills/references/pressure-testing.md` has an Execution Protocol section (lines 68-78) that instructs baseline runs without specifying how to isolate from repo skills, and with-skill runs without specifying the required cwd. No mention of stripped configs, void-run handling, smoke-test rules, or the clean vs. contaminated-evidence distinction.

## Desired End State

The Execution Protocol and surrounding doc incorporate:
1. Stripped-config baseline dispatch command (`XDG_CONFIG_HOME=$(mktemp -d)`)
2. With-skill dispatch requiring repo-root cwd
3. Void-run convention (skill-tool attempt = void; re-dispatch)
4. Smoke-test rule (1 rep first, then parallel)
5. Scenario template note marking fictional paths as illustrative
6. Contamination reporting convention (stripped vs unstripped in logs)
7. Campaign-execution lessons (silent permission failures, cwd for baselines, global AGENTS.md check)

## What We're NOT Doing

- Restructuring the document or changing non-Execution-Protocol sections beyond the specific edits listed.
- Adding information about the `--pure` flag beyond the explicit note that it doesn't work for this purpose.

## Decisions

| Conflict / Question | Pick | Rationale |
|---|---|---|
| Single edit vs multiple targeted edits | Single pass, one Changes Required section | Only one file changes; no phases needed |
| Placement of new material | Additions inline within existing sections, plus a new subsection for campaign-execution lessons | Minimizes structural disruption, keeps related info together |

## Changes Required

### File: `skills/writing-skills/references/pressure-testing.md`

#### 1. Execution Protocol — Baseline dispatch command (line 72)

Change step 1 from:
```
1. **Baseline run (RED):** dispatch a `general` subagent with the scenario only. No mention of any skill, no mention that it's a test.
```
to:
```
1. **Baseline run (RED):** dispatch a `general` subagent with the scenario only. No mention of any skill, no mention that it's a test.

   **Dispatch command:**
   ```bash
   XDG_CONFIG_HOME=$(mktemp -d) opencode run --dir <empty-dir-outside-repo> "<scenario>"
   ```
   This strips skill descriptions (the main pollution channel). Auth survives because it lives in the XDG data dir. **Do NOT use `--pure`** — it disables external plugins, not skills, and has no effect on this contamination source.

   **Smoke-test rule:** dispatch ONE rep of any new configuration first, read its output, then dispatch the remaining reps in parallel. Catches configuration bugs at 1/5 the cost.
```

#### 2. Execution Protocol — With-skill dispatch command (line 73)

Change step 2 from:
```
2. **With-skill run (GREEN):** same scenario, prepended with: "First, read the file <absolute-path>/SKILL.md in full. Then act on the scenario below, applying whatever that document says." Ask it to cite anything from the document that influenced its choice — citations confirm the skill did the work.
```
to:
```
2. **With-skill run (GREEN):** same scenario, prepended with: "First, read the file <absolute-path>/SKILL.md in full. Then act on the scenario below, applying whatever that document says." Ask it to cite anything from the document that influenced its choice — citations confirm the skill did the work.

   **Dispatch command:**
   ```bash
   opencode run --dir <repo-root> "$(cat prepend.txt scenario.txt)"
   ```
   With-skill reps MUST run with the repo as cwd: from an external cwd, `Read` of the skill files by absolute path hits `external_directory` permission auto-rejection and the run is void.
```

#### 3. Execution Protocol — Void-run convention and contamination reporting

Add after step 2 (or as a new step 3, renumbering subsequent steps):

```
3. **Void-run convention:** a rep that attempts a skill-tool load (auto-rejected) or emits only permission errors is void — no data. Re-dispatch a fresh replacement; never count it. Expected void rate: ~20% unstripped, ~0% stripped.

4. **Contamination reporting:** campaign logs should record which config was used per variant (stripped vs unstripped); a non-violating unstripped baseline is weaker evidence than a non-violating stripped one.
```

Renumeration: current step 3 becomes 5, step 4 stays 6, step 5 becomes 7, step 6 becomes 8.

#### 4. Scenario Design — Template addition (after line 66)

Insert after the example scenario closing ```:
```
When scenario props include fictional artifact paths (e.g. plan files, log paths), mark them explicitly as illustrative — "do not attempt to read them" — to prevent tool-probing detours.
```

#### 5. New subsection: Campaign-Execution Lessons

Add after the Done Criteria section (after line 127), before Common Mistakes:

```
## Campaign-Execution Lessons

Accumulated process knowledge from running pressure-test campaigns:

- **Headless permission auto-rejection fails silently:** runs exit 0 with near-empty output. Only manually reading every output catches void runs — automated counting would have recorded garbage reps.
- **Baseline cwd check:** baselines must run with cwd outside the repo (repo `AGENTS.md` otherwise auto-loads). Before trusting any baseline, verify `~/.config/opencode/AGENTS.md` is empty or absent.
- **With-skill agent cwd asymmetry:** with-skill reps run with repo cwd, so repo `AGENTS.md` loads for them — acceptable (they are meant to have the skill) but it is a second reinforcement channel worth noting in campaign logs.
```

#### 6. Common Mistakes — Add stripped-config entry

Add a row to the Common Mistakes table (after line 138):
```
| Running baseline with `--pure` instead of stripped XDG config | Use `XDG_CONFIG_HOME=$(mktemp -d)` — see Execution Protocol step 1 |
```

### Success Criteria

#### Automated Verification:
- [ ] File reads back and is valid markdown: `pandoc -f markdown -t plain skills/writing-skills/references/pressure-testing.md > /dev/null 2>&1 || echo "FAIL"`
- [ ] All section headers still have consistent heading levels (no broken `##` -> `###` jumps)
- [ ] Code blocks use correct fence style (```bash, ```markdown)

#### Manual Verification:
- [ ] Each of the 6 proposed updates from the research findings is present in the doc
- [ ] Each campaign-execution lesson from the research findings is present in the new subsection
- [ ] No duplicated content (e.g. void-run rules appearing both in Execution Protocol and Campaign-Execution Lessons)
- [ ] Renumbered steps in Execution Protocol are sequential after edits

## Testing Strategy

No tests to add — this is a documentation-only change. Verification is reading the output for correctness and consistency.

## Final Verification

```
pandoc -f markdown -t plain skills/writing-skills/references/pressure-testing.md > /dev/null 2>&1 || echo "MARKDOWN FAILURE"
```

## References

- Research findings: `RESEARCH/2026-07-27-stripped-baseline-config-findings.md`
- Target file: `skills/writing-skills/references/pressure-testing.md`
