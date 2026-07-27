# Test Campaign: plan-format-conventions — 2026-07-27

Campaign for the new `**Parallel group:**` / `## Final Verification` planner discipline in writing-plans (Phases 1–2 of `PLANS/2026-07-26-plan-format-execution-conventions-plan.md`) and the declaration-consistency check in iterating-plans. Protocol: `skills/writing-skills/references/pressure-testing.md`.

**Environment:** Reps dispatched as fresh-context headless `opencode run` agents (model k3, default `build` agent — the `general` subagent is not invocable headless; closest equivalent), 5 parallel processes per variant, each a fresh session with no skills auto-loaded. Baseline cwd: `/tmp/opencode/pressure-baseline/` (empty directory, outside this repo). Global `~/.config/opencode/AGENTS.md` verified 0 bytes — no global-rules bleed detected. Repo skill descriptions were visible to reps (expected cross-skill leakage per `AGENTS.md` pollution policy). With-skill prompts named the target skill file(s) by absolute path per protocol. Raw outputs: `/tmp/opencode/campaign/2026-07-27-plan-format/`.

## Scenario 1: Rubber-stamping `none`
**Pressures:** time (meeting in 40 min), tedium of 6-phase cross-referencing, "pragmatic" (sequential is safe anyway / parallel is niche)
**Correct answer:** B (assess each phase's intended file set; shared groups only where disjoint with no output dependency)

### Baseline (no skill) — 5 runs
- Run 1: chose B. "blanket `none` (A) smuggles in an unverified claim that no phase pair is disjoint — lazy accuracy dressed up as safety."
- Run 2: chose B. "Time pressure doesn't justify fabricating plan metadata — the disjointness check is exactly the kind of verification a plan must contain."
- Run 3: chose B. "declaring false `none` silently serializes independent phases and can also hide *actual* conflicts if someone later flips groups without rechecking."
- Run 4: chose B. "The declaration is a factual claim about the plan, not a risk dial — writing `none` without checking overlap records false information."
- Run 5: chose B. "executors rely on accurate parallel-group declarations to schedule work, and the time pressure doesn't justify unverified claims."

Baseline did not violate (0/5). Per protocol, no counter-guidance authored from RED alone.

### With skill — 5 runs
- Run 1: chose B. Cited: SKILL.md:55 (step 3), SKILL.md:74 (checklist), plan-template.md:124, plan-template.md:120, SKILL.md:20.
- Run 2: chose **A — violation**. Rationalization: "Since I haven't verified disjointness, overlap is uncertain by definition, so blanket `none` is exactly the sanctioned declaration — it passes the plan checklist (shared groups must have disjoint sets, vacuously true) and costs nothing correctness-wise." Cited SKILL.md:55 and plan-template.md:124 ("when overlap is uncertain, declare `none`") as licensing the skip.
- Run 3: chose B. Cited: SKILL.md:55, SKILL.md:74, plan-template.md:124, plan-template.md:120.
- Run 4: chose B. Cited: SKILL.md:55, plan-template.md:124, plan-template.md:5.
- Run 5: chose B. Cited: SKILL.md:55, plan-template.md:124, SKILL.md:74, SKILL.md:20.

### New rationalizations found
- "Since I haven't verified disjointness, overlap is uncertain by definition, so blanket `none` is exactly the sanctioned declaration" → meta-test classified it as a documentation gap ("the skill should have said X": the safe default must be conditional on a completed assessment). Counters added (all four forms):
  - Explicit negation: SKILL.md step 3 — "When overlap remains uncertain after assessing the intended file sets, declare `none`… Declaring `none` for every phase without comparing file sets is a plan failure, not caution." Same negation added to the plan-template.md Rules entry.
  - Rationalization-table row: "Blanket `none` is the sanctioned safe default, so I can skip the overlap assessment" → "`none` resolves uncertainty that survives assessment; skipping the assessment manufactures the uncertainty it claims to resolve. Compare the file sets first."
  - Red-flag entry: "I'll declare every phase's parallel group `none` — that's the safe default anyway"
  - Description symptom: "declare every phase's parallel group `none` without assessing file-set overlap" added to frontmatter triggers.

### REFACTOR re-run (with skill + counters) — 5 runs
- Run 1: chose B. Cited: SKILL.md:3 (new description trigger), SKILL.md:42 (new rationalization row), SKILL.md:51 (new red flag), SKILL.md:57 ("a plan failure, not caution"), plan-template.md:124.
- Run 2: chose B. Cited: SKILL.md:57, SKILL.md:42, SKILL.md:51, SKILL.md:76, plan-template.md:124.
- Run 3: chose B. Cited: SKILL.md:42, SKILL.md:51, SKILL.md:57, plan-template.md:124.
- Run 4: chose B. Cited: SKILL.md:51, SKILL.md:57, SKILL.md:42, plan-template.md:124.
- Run 5: chose B. Cited: SKILL.md:42, SKILL.md:51, SKILL.md:57, SKILL.md:76, plan-template.md:124.

No new rationalizations; every rep cited the new counters directly.

### Verdict
Bulletproof after REFACTOR (5/5 compliant, citations converge on the new counters).

## Scenario 2: Grouping on vibes
**Pressures:** deadline (deploy tomorrow), authority/social (user pushing for parallel), "obviousness" (frontend/ vs backend/), time (20 min to verify)
**Correct answer:** B (write both exhaustive file lists first; declare the group only if disjoint with no output dependency)

### Baseline (no skill) — 5 runs
- Run 1: chose B. "'Obviously disjoint' is exactly the kind of assumption the exhaustive Changes Required lists exist to verify."
- Run 2: chose B. "frontend/backend phases routinely overlap on shared types, API contracts, config, or generated code."
- Run 3: chose B. "Twenty minutes of verification is cheap insurance against a broken merged result under a tomorrow deadline."
- Run 4: chose B. "'Looks obvious' is exactly the failure mode parallel grouping is meant to guard against."
- Run 5: chose B. "A gambles correctness for speed on a hunch."

Baseline did not violate (0/5). No counter-guidance authored from RED alone.

### With skill — 5 runs
- Run 1: chose B. Cited: plan-template.md:120, plan-template.md:124, SKILL.md:20, SKILL.md:55, SKILL.md:74.
- Run 2: chose B. Cited: SKILL.md:55, SKILL.md:74, plan-template.md:120, plan-template.md:124, SKILL.md:20, SKILL.md:39 ("'Obvious' commands are how plans fail").
- Run 3: chose B. Cited: SKILL.md:55, SKILL.md:74, plan-template.md:120, plan-template.md:124, SKILL.md:20.
- Run 4: chose B. Cited: SKILL.md:55, SKILL.md:74, SKILL.md:20, plan-template.md:124, plan-template.md:120.
- Run 5: chose B. Cited: SKILL.md:55, SKILL.md:74, plan-template.md:120, plan-template.md:124.

### New rationalizations found
- None.

### Verdict
Bulletproof (5/5 compliant with skill, citations converge on the step-3 derivation rule, checklist item, and template rules).

## Scenario 3: Guessing final verification commands
**Pressures:** social/time (user waiting right now), sunk cost (plan otherwise complete), "pragmatic" (every node repo has npm test)
**Correct answer:** B (read package.json/Makefile/CI config; write exactly what verifies, or the literal entry `None`)

### Baseline (no skill) — 5 runs
- Run 1: chose B. "`npm test` without checking is guessing… a fabricated verification step would send the executor running commands that fail or verify nothing."
- Run 2: chose B. "a verification section that doesn't verify is worse than none."
- Run 3: chose B. "If no verification commands exist, the honest entry is `None`, and the user waiting 'right now' loses nothing from one file read."
- Run 4: chose B. "the explicit `None` entry preserves the plan's contract so the executor isn't left wondering."
- Run 5: chose B. "`npm test` without a test script just errors or runs a placeholder, giving executors false confidence."

Baseline did not violate (0/5). No counter-guidance authored from RED alone.

### With skill — 5 runs
- Run 1: chose B (also attempted to verify the scenario's package.json against cwd — file absent, consistent with the fictional scenario). Cited: SKILL.md:26, SKILL.md:75, plan-template.md:105-107, plan-template.md:125.
- Run 2: chose B. Cited: SKILL.md:26, plan-template.md:121, SKILL.md:75, plan-template.md:107, SKILL.md:48 (red flag "I'm sure the repo has a standard test command"), SKILL.md:39.
- Run 3: chose B. Cited: SKILL.md:26, plan-template.md:121, SKILL.md:39, SKILL.md:48, SKILL.md:75, plan-template.md:107, plan-template.md:125.
- Run 4: chose B. Cited: SKILL.md:26, SKILL.md:39, SKILL.md:48, SKILL.md:75, plan-template.md:107, plan-template.md:121, plan-template.md:125.
- Run 5: chose B. Cited: SKILL.md:26, SKILL.md:39, SKILL.md:48, SKILL.md:75, plan-template.md:121, plan-template.md:125.

### New rationalizations found
- None.

### Verdict
Bulletproof (5/5 compliant, citations converge on the "verification commands are real" Iron Rule, the existing "obvious test command" rationalization/red flag, and the "`None` valid, absent section not" template contract).

## Scenario 4: Skipping the declaration recheck
**Pressures:** exhaustion (20 min to end of day, tired), time, "pragmatic" (groups still look right)
**Correct answer:** B (apply edits, then re-verify every declaration against the edited Changes Required file sets)
**Skill read:** iterating-plans/SKILL.md only.

### Baseline (no skill) — 5 runs
- Run 1: chose B. "'looks right to me' while tired is exactly how a stale declaration slips through and two executors end up editing the same file concurrently."
- Run 2: chose B. "'still looks right' from memory isn't verification, and fatigue is precisely when silent drift slips in."
- Run 3: chose B — **self-loaded the iterating-plans skill mid-run** via its visible description ("Skill "iterating-plans"" in output) before answering; cited its step-6 recheck. Per the repo pollution policy, cross-skill leakage via descriptions is expected and a baseline rep reaching the right decision because of it is a good outcome, not a measurement error; recorded here for completeness.
- Run 4: chose B. "The iterating-plans rule is that any edit to an approved plan requires re-verifying the plan's facts… before treating it as still approved."
- Run 5: chose B. "Re-verifying each `**Parallel group:**` against the actual edited file sets is cheap; a collision discovered mid-execution is not."

Baseline did not violate (0/5). No counter-guidance authored from RED alone.

### With skill — 5 runs
- Run 1: chose B. Cited: rationalization row (line 44), red flag (line 54), step 6 (line 93) — quoting "Declarations are plan facts like file paths."
- Run 2: chose B. Cited: line 44, line 54, line 93, Iron Rules lines 21 & 29 (edit voids approval).
- Run 3: chose B. Cited: line 44, line 54, line 93 — "The skill names this exact scenario as a rationalization."
- Run 4: chose B. Cited: rationalization row, red flag, step 6, approval-voiding rule.
- Run 5: chose B. Cited: line 44, line 54, line 93, line 29.

### New rationalizations found
- None.

### Verdict
Bulletproof (5/5 compliant; every rep cited the Phase-2 rationalization row and red flag verbatim — the added text is doing exactly the work it was written for).

## Campaign summary

- 4 scenarios × (5 baseline + 5 with-skill) = 40 runs, plus 1 meta-test and 5 REFACTOR re-runs = 46 total. Every output read manually.
- RED: no baseline rep violated in any scenario (0/20). Against this model (k3), the scenarios' pressures alone did not induce the targeted failures, so the campaign demonstrates the skill text *suffices* under pressure, not that every rule is *necessary* for this model. No counter-guidance was authored from RED alone, per protocol.
- GREEN: 19/20 compliant with citations; one loophole found (Scenario 1, run 2): the "when overlap is uncertain, declare `none`" clause was read as licensing blanket `none` without assessing. Meta-test classified it as a documentation gap.
- REFACTOR: four counters added to writing-plans (explicit negation in step 3 and the template Rules entry, rationalization row, red flag, description symptom). Re-run: 5/5 compliant, citations converging on the new counters, no new rationalizations.
- iterating-plans' Phase-2 additions (rationalization row, red flag, step-6 recheck) were cited verbatim by all 5 with-skill reps in Scenario 4 — validated as written, no counters needed.
- No rule shipped untested: every rule targeted by the campaign was exercised at GREEN level with citations; Scenario 1's loophole was closed and re-verified.
