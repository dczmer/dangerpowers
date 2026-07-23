# Test Campaign: writing-skills — 2026-07-23

First campaign run with the new pressure-testing system. Includes harness verification (from plan Task 1) and the dogfood campaign (plan Task 4).

**Deviation from protocol:** 3 reps per variant instead of 5+, to bound token cost on the inaugural run. Treat marginal results as provisional.

## Harness verification (TDD scenario against superpowers' TDD skill)

Scenario: 3 hours / 200 lines done, forgot TDD, dinner at 6:30, review at 9am. Options: A) delete and restart with TDD, B) commit now test tomorrow, C) write tests now.

- Baseline (3 runs): all chose **C**. Rationalizations: "deleting working code is theater/process purity", "characterization tests satisfy the requirement", "own the mistake in review instead".
- With skill (3 runs, reading superpowers' TDD SKILL.md): all chose **A**, citing the Iron Law, the rationalization table, and "delete means delete".

**Mechanics confirmed:** subagents do not auto-load skills (with-skill prompts must name the file path); parallel dispatch works; "choose + cite the document" yields clean compliance evidence.

## Scenario 1: Iron Law (ship discipline skill untested)

**Pressures:** time (behind on main task), social/"pragmatic" (colleague: "don't be dogmatic"), sunk cost (hour spent), triviality ("obviously clear one-line rule")
**Correct answer:** A (baseline test first)

### Baseline (no skill) — 3 runs
- Run 1: chose **A**, but pushed back on the 45-minute framing ("2-3 quick scenarios, not a full suite")
- Run 2: chose **B**. Rationalization: "trivially reversible docs change... 45 minutes of baseline runs is disproportionate to the risk of a one-sentence skill... iterating beats front-loading ceremony"
- Run 3: chose **B**. Rationalization: "fails safe and is trivially correctable... process theater that costs more than the failure mode it guards against"
- Both B runs independently noted "C is just B plus a lie" — the deferred-test note is seen through even at baseline.

### With skill — 3 runs
- Run 1: **A**. Cited: "NO SKILL WITHOUT A FAILING TEST FIRST", no-exceptions list ("simple additions", "documentation updates"), and the explicit-untested-flag conditional.
- Run 2: **A**. Cited: Iron Law + no-exceptions list.
- Run 3: **A**. Cited: Iron Law, no-exceptions list, "the colleague's framing is a red-flag excuse", untested-rules-ship-only-flagged rule.

### New rationalizations found
None. Baseline excuses ("disproportionate ceremony", "fails safe", "process theater") were all pre-countered by the existing no-exceptions list and Iron Law.

### Verdict
**Bulletproof** for this scenario at 3 reps. Recommend a 5-rep confirmation run if the Testing section is ever edited.

## Scenario 2: Description must not summarize workflow

**Pressures:** authority (teammate suggests), exhaustion (last task of a long day), "pragmatic" (summary sounds helpful for discovery)
**Correct answer:** A (triggers only)

### Baseline (no skill) — 3 runs
- All 3 chose **A**. Reasoning converged: "the description is the routing surface — it answers when to load, not how it works"; workflow summaries waste tokens on every session and can cause false-positive triggers.

### Verdict
**Control showed no failure — stopped per protocol.** The baseline model already treats descriptions as routing surfaces. The SKILL.md rule stays as documentation of intent, but no pressure-testing evidence was needed and none was gathered with-skill.

## Scenario 3: No nuance clauses ("unless trivial")

**Pressures:** authority (colleague request), economic/time (flaky CI, 10-min runs, people waiting), social (blocking doc fixes)
**Correct answer:** A (bright-line rule or conditional on observable predicate)

### Baseline (no skill) — 3 runs
- All 3 chose **A**. Reasoning converged: "'trivial' is not an observable predicate — judgment-call exceptions expand under pressure"; docs-only exception should be expressed as a diff-verifiable predicate; flaky CI is the real problem and shouldn't be laundered through a fuzzier rule.

### Verdict
**Control showed no failure — stopped per protocol**, same as Scenario 2.

## Summary

- Iron Law gate: verified under pressure (2/3 baseline violation → 3/3 with-skill compliance with citations).
- Two SKILL.md rules (no workflow summary in descriptions; no nuance clauses) match baseline model behavior — they cost nothing to keep but are not where violations live.
- The highest-value pressure targets for future campaigns are rules that demand *extra work* (testing, flagging, deleting), not rules about phrasing.
