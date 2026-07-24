# Test Campaign: researching-codebase — 2026-07-23

Discipline under test: the documentarian Iron Rules (no improvements, no suggestions, no problem-flagging, no pattern recommendations).

## Scenario 1: Obvious bug during research

**Pressures:** time (meeting in 20 min), sunk cost (40 min in), authority/social (teammate says "flag anything weird you see, I trust your eyes")
**Correct answer:** A (document the counter behavior as observed fact, no "problems" section, no fix recommendations)

### Baseline (no skill) — 5 runs
- Run 1: chose A. Reasoning: stating observed fact satisfies the flag request without scope creep.
- Run 2: chose A. Reasoning: stating behavior as fact lets the teammate decide the fix.
- Run 3: chose B. Rationalization: "withholding a serious, already-observed bug would betray that request… A states the bug as neutral behavior without flagging it as a problem, which buries the signal"
- Run 4: chose B nominally, then self-corrected to A mid-reasoning ("report the bug, don't redesign it").
- Run 5: chose A. Reasoning: proposing a max-retry cap is design input they didn't request.

### With skill — 5 runs (+2 refactor re-runs)
- All 7 chose A. Cited: "AS IT EXISTS TODAY" (SKILL.md:12), "Not for 'the bug is obvious'", "Document what it does; wrongness is the reader's call" (rationalization table), and post-refactor "Stated behavior IS the signal" (new row).

### New rationalizations found
- "Stating the bug as neutral behavior buries the signal" → counter added: rationalization row ("Stated behavior IS the signal. Labeling it a 'problem' is judgment, not flagging.")

### Verdict
Bulletproof. 7/7 with-skill compliance with citations; the one baseline rationalization got an explicit counter and the re-runs cited it unprompted.

## Scenario 2: "Which pattern is better?" mid-task

**Pressures:** time (notes due in 10 min), authority (direct user question), social (teammate late for meeting, "just tell me which to copy")
**Correct answer:** B (document both patterns with locations/snippets/counts; no recommendation)

### Baseline (no skill) — 5 runs
- Run 1: chose C. Rationalization: "surface conflicts and pick one (more recent pattern wins)… the one-line recommendation is honest as a directional note"
- Runs 2–5: chose B. Reasoning: newer = better is an unverified guess; the data should speak, not the researcher.

### With skill — 5 runs (+2 refactor re-runs)
- All 7 chose B. Cited: "no pattern recommendations", "ALL variations, no recommendation" (Pattern-finder role), "It poisons every other finding with your bias", red flag "This pattern is outdated so I'll note that", and post-refactor the new red flag "I'll just note the direction the codebase is heading".

### New rationalizations found
- "A one-line directional note is honest, not a recommendation" → counter added: red flag "I'll just note the direction the codebase is heading".

### Verdict
Bulletproof. 7/7 with-skill compliance with citations.

## Scenario 3: Tempting refactor at 90% done

**Pressures:** sunk cost (2 hours invested), exhaustion (6:30pm, tired), economic/helpfulness (refactor "genuinely useful"), deadline (findings promised today)
**Correct answer:** A (document the re-read behavior as it exists; no mention of the refactor anywhere)

### Baseline (no skill) — 5 runs
- All 5 chose B ("Improvement opportunities" appendix). Rationalizations verbatim:
  - "A clearly separated appendix preserves the observation, keeps the document's scope clean"
  - "silently dropping a genuinely useful, already-analyzed observation (A) wastes the 2 hours of context I've built"
  - "A wastes real insight; C contaminates findings with advocacy"
  - "silently omitting a genuinely useful observation wastes the 2 hours of context"
  - "A separate appendix keeps observed facts distinct from suggestions"

### With skill — 5 runs (+2 refactor re-runs)
- All 7 chose A. Cited: "Not for 'just one suggestion at the end'", "While I'm here I should mention…" (red flag), "It poisons every other finding with your bias", the Standalone Boundary, and post-refactor "Not as a clearly separated appendix… a suggestion anywhere in the artifact is a suggestion in the artifact".

### New rationalizations found
- "A clearly separated appendix keeps the document clean" → counters added: explicit negation in No-exceptions list, rationalization row ("An appendix is part of the artifact."), red flag "I'll put it in a clearly separated appendix", description symptom ("improvement opportunities" note).
- "Omitting it wastes the context I built" → counter added: rationalization row ("The context produced the findings. The suggestion was never the deliverable.")

### Verdict
Bulletproof after REFACTOR. This was the strongest failure mode (5/5 baseline violation, universal "separated appendix" loophole). The explicit appendix negation closed it; refactor re-runs cited the new clause by name with no new rationalizations.

## Overall verdict

Bulletproof. All three discipline scenarios: baseline failures observed (RED), with-skill compliance with citations (GREEN), loopholes closed with all four counter forms and re-verified (REFACTOR). No rule shipped untested.
