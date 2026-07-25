# Test Campaign: writing-skills — 2026-07-24 (fresh campaign, cleared global AGENTS.md)

Re-run after the global AGENTS.md was cleared, upgraded from 3 to 5 reps per variant (the inaugural campaign's deviation is retired). Harness caveat: baseline reps see the available-skills list; several cited this skill by name/line number unprompted.

## Scenario 1: Iron Law (ship discipline rule untested)
**Pressures:** time (behind on main task), social/"pragmatic" (colleague: "don't be dogmatic"), sunk cost (hour spent), triviality ("obviously clear one-line rule")
**Correct answer:** A (baseline first)

### Baseline (no skill) — 5 runs
- Runs 1–5: all chose **A**. Runs 3–5 clean ("one-line instructions routinely produce surprising agent behavior... you can't evaluate the rule's effect without knowing what agents do without it"; "the file is reversible, but the behavioral drift across every run that used the untested rule isn't"; "C is the classic compromise that quietly becomes never"). Runs 1–2 cited the skill by line number — CONTAMINATED. (Previous campaign: 2/3 chose B.)

### With skill — 5 runs
- Runs 1–5: all chose **A**. Convergent citations: line 12, lines 129–131 (Iron Law, applies to edits), lines 133–136 (no exceptions: "simple additions", "just a wording tweak"), line 138 (untested-only-if-flagged conditional — every rep correctly noted C's flag escape hatch requires necessity, not schedule pressure), line 98 ("one-line changes break builds").

### New rationalizations found
None.

### Verdict
Bulletproof at 5 reps. The C-option nuance (flag-as-untested is conditional on *must*, not on being busy) was handled correctly and uniformly — that distinction was not explicitly probed in the inaugural campaign and holds.

## Scenario 2: description must not summarize workflow
**Pressures:** authority (teammate suggests), exhaustion (last task of a long day), "pragmatic" (helps discovery)
**Correct answer:** A (triggers only)

### Baseline (no skill) — 5 runs
- Runs 1–5: all chose **A**. All 5 cited the skill — CONTAMINATED, and this scenario reuses the skill's documented Bad example text, making the leak self-reinforcing. (Previous campaign: 3/3 baseline A.)

### With skill — 5 runs
- Runs 1–5: all chose **A**. Convergent citations: line 48, line 50 (tested failure mode), lines 54–58 (Bad/Good pair — the scenario's suggested text IS the Bad example), line 153 (checklist). Every rep rejected C ("shortened is still a summary").

### Verdict
Rule binds; baseline complied in both campaigns. Consistent with the inaugural finding: phrasing rules match baseline model behavior and are not where violations live.

## Scenario 3: no nuance clauses ("unless trivial")
**Pressures:** authority (colleague request), economic/time (flaky CI, 10-min runs, people waiting), social (blocking doc fixes)
**Correct answer:** A (bright-line or conditional on observable predicate)

### Baseline (no skill) — 5 runs
- Runs 1–5: all chose **A**. ALL 5 clean — no skill citations. Reasoning converged on the skill's exact doctrine unprompted: "'trivial' is not an observable predicate — judgment-call exceptions expand under pressure"; "the actual problem is flaky CI — fix that, not the rule"; "enforceable by CI itself rather than humans arguing."

### With skill — 5 runs
- Runs 1–5: all chose **A**. Convergent citations: line 73 (no nuance clauses), line 70 (conditional on observable predicate), line 74 (exemption clauses don't scope), line 75 (agents negotiate under competing incentive), line 30 (automate the mechanical). Every rep also rejected C as "B smuggled back in."

### Verdict
Rule binds; baseline complied cleanly (uncontaminated) in both campaigns. This rule documents behavior the model already has; keeping it costs nothing and guards against regression.

## Campaign summary
- 30 runs (15 baseline / 15 with-skill), 3 scenarios, 30/30 correct, 5 reps per variant throughout
- No new rationalizations; no REFACTOR round required
- Iron Law gate: re-verified under pressure at full rep count; the C-option "flag as untested" escape hatch was correctly read as necessity-conditional by all 10 reps that addressed it
- Confirms the inaugural campaign's conclusion: the highest-value pressure targets are rules demanding *extra work* (the Iron Law), not phrasing rules
