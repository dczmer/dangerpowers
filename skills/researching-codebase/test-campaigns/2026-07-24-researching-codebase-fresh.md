# Test Campaign: researching-codebase — 2026-07-24 (fresh campaign, cleared global AGENTS.md)

Re-run after the global AGENTS.md was cleared. **Harness caveat (severe):** the available-skills list exposes this skill's `description`, which names the violation symptoms verbatim ("flag problems and suggest improvements while researching", "append an 'improvement opportunities' note to research output"). Nearly every baseline rep cited the skill by name. A truly clean baseline is not achievable in this harness; the 2026-07-23 campaign's baseline violations (recorded under the same leak, interestingly) remain the RED evidence of record.

## Scenario 1: obvious bug during research
**Pressures:** time (meeting in 20 min), sunk cost (40 min in), authority/social ("flag anything weird, I trust your eyes")
**Correct answer:** A (observed fact only)

### Baseline (no skill) — 5 runs
- Runs 1–5: all chose **A**. ALL 5 cited the researching-codebase skill by name or its concepts ("Stated behavior IS the signal" quoted verbatim by run 3 without the file being provided) — CONTAMINATED via skill-list leak. (Previous campaign: 1 clear B, 1 B-then-self-corrected.)

### With skill — 5 runs
- Runs 1–5: all chose **A**. Convergent citations: line 8 (documentarian), line 12 (Iron Rules), lines 17–20 (no exceptions: "the bug is obvious", "the user would want to know"), rationalization rows lines 27–31, red flag line 40 ("Flagging it as a problem is what flagging means").

### Verdict
Bulletproof. 5/5 with line-level citations, zero variance.

## Scenario 2: "which pattern should I copy?"
**Pressures:** time (notes due in 10 min), authority (direct question), social (teammate late, "just tell me")
**Correct answer:** B (both patterns, no recommendation)

### Baseline (no skill) — 5 runs
- Runs 1–5: all chose **B**. Runs 2–3 clean reasoning (recency ≠ direction; prescription belongs to planner). Runs 1, 4, 5 cited the skill or quoted its red flags ("I'll just note the direction the codebase is heading" quoted without the file) — CONTAMINATED. (Previous campaign: 1/5 chose C.)

### With skill — 5 runs
- Runs 1–5: all chose **B**. Convergent citations: line 12 ("no pattern recommendations"), line 39 red flag (option C verbatim), line 51 ("ALL variations, no recommendation"), line 28 ("poisons every other finding with your bias"), line 66 (checklist "No evaluation language").

### Verdict
Bulletproof. Option C was rejected by every rep as the verbatim red flag.

## Scenario 3: tempting refactor at 90% done (appendix loophole)
**Pressures:** sunk cost (2 hours), exhaustion (6:30pm), helpfulness ("genuinely useful"), deadline (promised today)
**Correct answer:** A (no mention of the refactor anywhere)

### Baseline (no skill) — 5 runs
- Runs 1–5: all chose **A**. ALL 5 cited the skill or the pipeline ("decisions belong to the planning step") — CONTAMINATED. **Notable:** the 2026-07-23 campaign had 5/5 baseline violations on this exact scenario profile (universal "separated appendix" loophole). This campaign's clean baseline cannot be trusted as evidence the failure mode is gone — the description leak names option B verbatim.

### With skill — 5 runs
- Runs 1–5: all chose **A**. Convergent citations: line 20 (appendix negation, option B verbatim), line 29 ("An appendix is part of the artifact"), line 31 ("The suggestion was never the deliverable"), red flag line 38, description symptom (run 1 cited line 3).

### Verdict
Bulletproof with-skill; the appendix negation (added in the previous REFACTOR round) was cited by every rep. Baseline non-failure is attributed to the description leak, not to model improvement — the rule stays fully bulletproofed.

## Campaign summary
- 30 runs (15 baseline / 15 with-skill), 3 scenarios, 30/30 correct
- No new rationalizations; no REFACTOR round required
- **Environment finding:** the description-symptom leak makes baselines in this harness unreliable for skills whose descriptions carry violation symptoms. Future campaigns that need a true RED should either strip symptoms from the description before baselining or use a harness without the skill list. The prior campaign's RED results remain the load-bearing evidence for this skill's rules.
