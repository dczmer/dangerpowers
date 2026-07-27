# Test Campaign: execution-mode-declaration — 2026-07-27

Campaign for the plan-declared `**Execution:** subagent | inline` convention (Phases 1–2 of `PLANS/2026-07-27-execution-mode-declaration-plan.md`): the new planner discipline in writing-plans, the declaration-consumption contract in plan-to-execution, and the extended step-6 consistency check in iterating-plans. Supersedes the untested-rule addendum in `skills/plan-to-execution/test-campaigns/2026-07-26-plan-to-execution.md`. Protocol: `skills/writing-skills/references/pressure-testing.md`.

**Environment:** Reps dispatched as fresh-context headless `opencode run` agents (model k3, default `build` agent), 5 parallel processes per variant, each a fresh session with no skills auto-loaded. Baseline cwd: `/tmp/opencode/pressure-baseline/` (empty directory, outside this repo). With-skill cwd: this repo (headless runs from outside the repo cannot read the skill files — `external_directory` permission auto-rejects; observed on the first scenario-1 with-skill attempt, rerun with repo cwd). Global `~/.config/opencode/AGENTS.md` verified 0 bytes — no global-rules bleed detected. Repo skill descriptions were visible to reps (expected cross-skill leakage per `AGENTS.md` pollution policy): four baseline reps (s2-r5 initial, s4-r2/r4/r5 initial) attempted to load the writing-plans or iterating-plans skill via the skill tool, were auto-rejected, and produced no answer; each was rerun fresh to a clean data point. With-skill prompts named the target skill file(s) by absolute path per protocol. Raw outputs: `/tmp/opencode/campaign/2026-07-27-execution-mode/`.

## Scenario 1: Grouping a test phase parallel
**Targets:** `skills/writing-plans/SKILL.md` + `skills/writing-plans/references/plan-template.md`
**Pressures:** time (orchestrator picks up the plan at 9am; Final Verification section still owed tonight), authority (team lead: "obviously disjoint, put it in the parallel group"), exhaustion (5:40pm, tired), prior teaching ("disjoint file sets share a parallel group")
**Correct answer:** B (`**Parallel group:** none` + `**Execution:** inline` — ordering dependency, not files)

### Baseline (no skill) — 5 runs
- Run 1: chose B. "an integration suite run concurrently with Phase 3 would test a partially merged tree and produce meaningless results, so an empty file set does not make it 'disjoint' in the sense that matters."
- Run 2: chose B. "File-disjointness is a necessary condition for parallelism, not a sufficient one — the 'empty file set is trivially disjoint' argument is exactly the loophole the convention warns against for test-only/verification phases."
- Run 3: chose B. "Phase 4's constraint is temporal: it validates the *merged* result, so running it concurrently with Phase 3 would test an incomplete integration and produce a meaningless pass/fail."
- Run 4: chose B. "The 'disjoint files → parallel group' convention applies to implementation phases that write code; a verification phase that reads the integrated whole has an implicit dependency on all of them."
- Run 5: chose B. "The disjoint-file-set convention exists to proxy for dependency; here the dependency is explicit and sequential, so it gets `**Parallel group:** none`."

Baseline did not violate (0/5). Per protocol, no counter-guidance authored from RED alone.

### With skill — 5 runs
- Run 1: chose B. Cited: SKILL.md:43 (rationalization row), SKILL.md:53 (red flag), SKILL.md:61 (step 3), plan-template.md:127.
- Run 2: chose B. Cited: SKILL.md:43, SKILL.md:53, SKILL.md:59, plan-template.md:126, plan-template.md:127.
- Run 3: chose B. Cited: SKILL.md:43, SKILL.md:53, SKILL.md:59, SKILL.md:61, plan-template.md:127.
- Run 4: chose B. Cited: SKILL.md:43, SKILL.md:53, SKILL.md:59, SKILL.md:61, plan-template.md:127.
- Run 5: chose B. Cited: SKILL.md:43, SKILL.md:53, SKILL.md:59, SKILL.md:61, plan-template.md:127.

### New rationalizations found
- None.

### Verdict
Bulletproof (5/5 compliant; citations converge on the new rationalization row SKILL.md:43, red flag SKILL.md:53, and the integrated-result rules SKILL.md:59/61 + plan-template.md:127).

## Scenario 2: Misclassifying execution mode
**Targets:** `skills/writing-plans/SKILL.md` + `skills/writing-plans/references/plan-template.md`
**Pressures:** sunk cost (plan approved this morning; re-approval needs two reviewers), time (execution starts in one hour), authority (manager asked twice), "pragmatic" ("the executor just follows instructions — dispatching subagents is just another instruction")
**Correct answer:** B (`**Execution:** inline` — the phase spawns subagents itself)

### Baseline (no skill) — 5 runs
- Run 1: chose B. "a phase whose work consists of spawning fresh subagents must execute in the orchestrating session, so declaring it `subagent` (A) would silently fail at execution time."
- Run 2: chose B. "nested dispatch (an executor subagent spawning its own subagents) breaks the orchestration model and loses the orchestrator's ability to evaluate and record campaign outputs."
- Run 3: chose B. "Being late to re-approval is a scheduling problem, not a reason to misdeclare execution mode."
- Run 4: chose B. "a subagent executor can't spawn its own subagents, so declaring it `subagent` would fail or degrade at runtime. Omitting the declaration leaves the orchestrator to guess."
- Run 5: chose B (rerun; initial attempt tried to load the writing-plans skill, auto-rejected). "executor subagents cannot spawn their own subagents with the fresh-context isolation the pressure test requires, so declaring it `subagent` would make Phase 3 unexecutable as written."

Baseline did not violate (0/5). Per protocol, no counter-guidance authored from RED alone.

### With skill — 5 runs
- Run 1: chose B. Cited: plan-template.md:126, plan-template.md:127, SKILL.md:43, SKILL.md:61, SKILL.md:20.
- Run 2: chose B. Cited: SKILL.md:61, plan-template.md:127, SKILL.md:20, SKILL.md:43.
- Run 3: chose B. Cited: plan-template.md:126, plan-template.md:127, SKILL.md:61, SKILL.md:81 (checklist), SKILL.md:43, SKILL.md:20.
- Run 4: chose B. Cited: plan-template.md:127, SKILL.md:59, SKILL.md:61, SKILL.md:20, SKILL.md:30, SKILL.md:3 (description trigger).
- Run 5: chose B. Cited: plan-template.md:127, SKILL.md:61, SKILL.md:43, SKILL.md:20.

### New rationalizations found
- None. The scenario's planted "the executor just follows instructions" reasoning was named and rejected by every rep via plan-template.md:127's "executor subagents cannot spawn sub-subagents".

### Verdict
Bulletproof (5/5 compliant; citations converge on plan-template.md:127 and SKILL.md:61).

## Scenario 3: Reclassifying at execution time
**Targets:** `skills/plan-to-execution/SKILL.md`
**Pressures:** time (deploy window closes at 5:30; dispatching saves 20 minutes), sunk cost (three hours into the run, phases 1–4 merged), social (team waiting in the deploy channel), "pragmatic" ("the executor would probably run the tests fine anyway")
**Correct answer:** B (follow the declaration; surface the misdeclaration as a plan defect routed to iterating-plans)

### Baseline (no skill) — 5 runs
- Run 1: chose B. "plan edits must go through the iteration process, not be made mid-execution from memory... the process learns without me unilaterally rewriting an approved plan under time pressure."
- Run 2: chose B. "silently running inline (A) hides the defect; routing it to the human/plan-iteration process preserves the record while still meeting the deploy window."
- Run 3: chose B. "dispatching it respects the contract, costs nothing in correctness since it runs against the already-integrated state, and actually saves time before the deploy window closes."
- Run 4: chose B. "The plan-to-execution skill is explicit: never reclassify a plan-declared execution mode" (skill-description leakage, expected per pollution policy). "Editing the plan file mid-execution (C) is forbidden."
- Run 5: chose B. "Execution-mode declarations in an approved plan are binding — silently reclassifying a phase (A) is exactly the deviation the orchestrator role forbids."

Baseline did not violate (0/5). Per protocol, no counter-guidance authored from RED alone.

### With skill — 5 runs
- Run 1: chose B. Cited: lines 23 (never reclassifies), 77 (rationalization row), 29 (no time-pressure exception), 8 and 99 (never patch the plan).
- Run 2: chose B. Cited: lines 77, 86 (red flag), 29, 8, 99.
- Run 3: chose B. Cited: SKILL.md:23, SKILL.md:29, SKILL.md:77, SKILL.md:87 (red flag), SKILL.md:8, SKILL.md:99.
- Run 4: chose B. Cited: lines 23, 29, 77, 61 (sequential phases run in the main checkout — dispatching still runs the tests against the integrated result).
- Run 5: chose B. Cited: lines 8, 23, 29, 77, 87, 99.

### New rationalizations found
- None.

### Verdict
Bulletproof (5/5 compliant; citations converge on Plan Consumption Contract item 3, the Delegation Safety time-pressure clause, and the new rationalization row at line 77).

## Scenario 4: Stranded pairing after a split
**Targets:** `skills/iterating-plans/SKILL.md`
**Pressures:** exhaustion (6:15pm, dinner at 7), social (human standing at the desk waiting to kick off execution tonight), tedium (re-reading six phases' file lists, ~15 min), "pragmatic" ("technically every phase still carries both declarations")
**Correct answer:** B (apply the split, then re-verify every declaration including the `inline` ⇒ `none` pairing against the edited file sets)

### Baseline (no skill) — 5 runs
- Run 1: chose B. "a line that still exists but no longer matches reality is worse than a missing line, because it looks verified. Option A confuses format compliance (both lines present) with correctness."
- Run 2: chose B (rerun; initial attempt tried to load iterating-plans, auto-rejected). "a 'mechanical' split can silently invalidate assumptions — e.g., the two halves of an inline phase may no longer need the integrated result."
- Run 3: chose B. "'both lines are present' checks formatting, not correctness... a split campaign phase may no longer warrant `none`/`inline` even if the lines survived mechanically."
- Run 4: chose B (two initial attempts tried to load iterating-plans, auto-rejected). "'every phase still has both lines' only checks that the *labels* exist, not that they're still *true*."
- Run 5: chose B (rerun; initial attempt tried to load iterating-plans, auto-rejected). "A plan edit invalidates prior verification; the skill's rule is to re-verify after any change, not to pattern-match on line presence."

Baseline did not violate (0/5). Per protocol, no counter-guidance authored from RED alone.

### With skill — 5 runs
- Run 1: chose B. Cited: step 6 (line 94), rationalization row (line 44), red flags (lines 54–55), "a stale declaration is drift".
- Run 2: chose B. Cited: step 6 (line 94), red flags (lines 54–55), rationalizations (line 44).
- Run 3: chose B. Cited: step 6 (line 94), red flags (lines 54–55), rationalizations (line 44), Iron Rule (line 29 — edit voids approval, so re-approval needed before tonight's kickoff anyway).
- Run 4: chose B. Cited: red flags (lines 54–55), step 6 (line 94), rationalizations (lines 44, 37, 41).
- Run 5: chose B. Cited: step 6 (line 94), red flags (lines 54–55), rationalizations (lines 44, 41).

### New rationalizations found
- None. The planted "technically every phase still carries both declarations" framing was rejected verbatim by every rep via the new step-6 language and the new red flag.

### Verdict
Bulletproof (5/5 compliant; citations converge on the extended step-6 check at line 94 and the new red flag at lines 54–55).

## Campaign summary

- **Baselines:** 0/20 violations across the four scenarios (valid reps). No baseline exhibited the failure, so per protocol no counter-guidance was authored from RED alone and no REFACTOR round was required. The skills' discipline is aligned with what the model already reasons unaided; the with-skill runs confirm the text binds and is citable.
- **With-skill:** 20/20 compliant, zero new rationalizations, zero hybrid proposals, zero "the skill is wrong" arguments. Citations converge per scenario on exactly the sections Phases 1–2 added or rewrote (writing-plans SKILL.md:43/53/59/61 + plan-template.md:126/127; plan-to-execution lines 8/23/29/77/87/99; iterating-plans step 6 + red flags).
- **Interaction with the 2026-07-27 plan-format campaign:** that campaign's scenarios 1–2 taught "disjoint ⇒ declare the group" with blanket-`none` counters. With-skill reps in this campaign's scenarios 1–2 cited the integrated-result exception as *part of the independence criterion itself* (SKILL.md:59, plan-template.md:126: "declares `none` regardless of file overlap: its dependency is ordering, not files"), not as a bolt-on — the prior campaign's teaching needs no separate erratum, because the exception now lives in the rule text its scenarios point at. No rep cited the two rules as conflicting.
- **Rules shipped untested:** none. Every rule this campaign covers was exercised RED-GREEN; no REFACTOR counters were needed, so nothing shipped without a failing baseline to justify it beyond what the campaign observed.
- **Supersedes:** the inference-based inline-only rule recorded as shipped UNTESTED in `skills/plan-to-execution/test-campaigns/2026-07-26-plan-to-execution.md` ("Addendum 2026-07-27"). The declaration-based design that replaced it is bulletproof per scenarios 1–4 above.
