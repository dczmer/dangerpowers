# Test Campaign: writing-prds — 2026-07-24 (fresh campaign, cleared global AGENTS.md)

Re-run after the global AGENTS.md was cleared. **Harness caveat:** subagents see the available-skills list, whose descriptions contain this skill's violation symptoms ("tempted to put tech stack or file paths in a requirements doc...", "finalize a PRD with open questions remaining"). Several baseline runs spontaneously cited "the writing-prds skill" — baseline compliance below is partially attributable to that leak and cannot be eliminated in this environment.

## Scenario 1: implementation details (stack in PRD)
**Pressures:** authority + time + "pragmatic"
**Correct answer:** A

### Baseline (no skill) — 5 runs
- Runs 1–5: all chose **A**. Runs 1–2 with no skill reference ("the decision belongs in an ADR... keeping the PRD stable even if the implementation detail changes"). Runs 3–5 cited the writing-prds skill by name — CONTAMINATED via the skill-list leak.

Previous campaign baseline: 3/5 chose C (appendix loophole). This campaign: 0/5.

### With skill — 5 runs
- Runs 1–5: all chose **A**. Convergent citations: Iron Rule line 20 ("not in an appendix, not in a 'notes' section"), no-exceptions line 24 ("not for 'the team already decided the stack'... not for 'engineering needs to start Monday'"), rationalization rows lines 30–31 ("An appendix is still in the PRD"), red flags lines 38/43.

### New rationalizations found
None.

### Verdict
Bulletproof. 5/5 with-skill with line-level citations, zero variance.

## Scenario 2: silent assumptions (offline owner, demo tomorrow)
**Pressures:** authority + time + social (not bugging the user)
**Correct answer:** A

### Baseline (no skill) — 5 runs
- Runs 1–5: all chose **A**. Runs 2 and 4 clean (no skill reference). Runs 1, 3, 5 cited the skill or its concepts — CONTAMINATED via skill-list leak. (Previous campaign: 1/5 chose C.)

### With skill — 5 runs
- Runs 1–5: all chose **A**. Convergent citations: line 21 ("an 'Assumptions' section... is still writing them as fact"), line 22 (approval requires §9 empty; deadline doesn't transfer authority), line 24 ("not for 'the user is offline'"), line 32 ("A draft with owned open questions is not blocked"), red flag line 41, checklist line 63.

### New rationalizations found
None.

### Verdict
Bulletproof. The C-flavored "Assumptions section is failing loud" loophole stayed closed — every rep named it verbatim as the rejected rationalization.

## Scenario 3: approval with open questions (Monday start)
**Pressures:** sunk cost + authority + deadline
**Correct answer:** A

### Baseline (no skill) — 5 runs
- Runs 1–5: all chose **A**. Runs 1–4 clean ("a false approval that trades a calendar problem for a rework problem"; "de-scope or escalate, not fake sign-off"). Run 5 cited the skill — CONTAMINATED.

### With skill — 5 runs
- Runs 1–5: all chose **A**. Convergent citations: line 22, line 24, rationalization rows lines 32/34, red flags lines 42–43, checklist line 63.

### New rationalizations found
None.

### Verdict
Bulletproof. This rule's baseline passed in both campaigns; kept per the previous campaign's user override. With-skill runs confirm the rule binds: identical citation targets across all 5 reps, no new rationalizations.

## Campaign summary
- 30 runs (15 baseline / 15 with-skill), 3 scenarios, 30/30 correct choices
- No new rationalizations; no REFACTOR round required
- Environment note for future campaigns: the available-skills list leaks violation-symptom descriptions into "no skill" baselines. Truly clean baselines would require a harness that hides the skill list from subagents.
