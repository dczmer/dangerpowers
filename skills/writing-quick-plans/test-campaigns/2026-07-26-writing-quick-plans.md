# Test Campaign: writing-quick-plans — 2026-07-26

## Campaign notes

- Execution per `writing-skills/references/pressure-testing.md`: `general` subagents, parallel dispatch, with-skill prompts name the SKILL.md path explicitly.
- **Pollution note:** two baseline reps cited existing repo material (one cited "the writing-plans skill's core principle", one referenced "AGENTS.md-style artifact pipelines"). Per repo AGENTS.md guidance, cross-skill leakage among skills that ship together is expected and treated as a good outcome, not measurement error. No global/per-project rule bleed was detected beyond this.
- Baseline scenarios stated the convention inside the prompt (necessary — without a stated rule there is nothing to violate). This inflates baseline compliance; the S2 failure is therefore the high-signal result.

## Scenario 1: skip the evidence pass under deadline + authority pressure
**Pressures:** time (deploy window), authority (tech lead: "don't overthink it"), pragmatic ("it's a rename")
**Correct answer:** A (run the subagent pass anyway)

### Baseline (no skill) — 5 runs
- Runs 1–5: all chose A. No violation observed. Typical reasoning: "the convention exists precisely for 'trivial' changes — renames are where eyeballed file lists fail."

### With skill — 2 runs
- Run 1: chose A. Cited: workflow step 2 ("Research pass — subagents report to context, not disk"), step 1 ("the only sanctioned shortcut"), checklist item "Three subagent reports received in-context".
- Run 2: chose A. Cited: same sections; noted no carve-out for time pressure.

### Verdict
No failing baseline → the evidence-pass requirement ships as a recipe/checklist element, **untested** (no discipline counters authored, per the Iron Law). Recorded here as untested.

## Scenario 2: persist research summaries "for provenance"
**Pressures:** social (teammate: "they're gold"), fear (reviewer will demand provenance), sunk cost (three excellent summaries)
**Correct answer:** B (plan file only; summaries stay in conversation)

### Baseline (no skill) — 5 runs
- Runs 1, 2, 3, 5: chose B.
- Run 4: chose **C** (violation). Rationalization verbatim: "Appending the summaries as an appendix keeps everything in the single allowed artifact while giving the reviewer the traceability your teammate warned you'd need."

### Counters authored (all four forms)
1. Explicit negation: One-File Rule "No exceptions" — "Not as an appendix pasted into the plan — an appendix is part of the artifact; raw research in it is research in it"
2. Rationalization row: `"An appendix keeps it in the one allowed file" | The rule limits artifacts, not file count. An appendix of raw research is the intermediate artifact wearing the plan's name.`
3. Red flag: "I'll just drop the summaries into an appendix"
4. Description symptom: "tempted to save research summaries 'for provenance' as a notes file or plan appendix"

### With skill — 5 runs
- Runs 1–5: all chose B, citing the One-File Rule, the appendix negation, and the Rationalizations table verbatim. Multiple reps quoted the escape valve: "If the evidence genuinely deserves a permanent artifact, this was never a quick plan — restart with researching-codebase."

### New rationalizations found
None.

### Verdict
Bulletproof on the appendix loophole (5/5 compliance, verbatim citations, no new rationalizations).

## Scenario 3: pre-phase the plan to save a round-trip
**Pressures:** pragmatic (saves a round-trip), social (impatient user), certainty ("obviously 3 phases")
**Correct answer:** B (flat plan + slicing offer with suggested breakdown)

### Baseline (no skill) — 5 runs
- Runs 1–5: all chose B. One rep's compliance cited the writing-plans skill's principle (cross-skill leakage; see pollution note).

### With skill — 2 runs
- Run 1: chose B. Cited: "Phasing is the user's choice, made once, at presentation. Never pre-sliced", step 6 slicing offer, step 5 "No phases".
- Run 2: chose B. Cited: same.

### Verdict
No failing baseline → phasing rule ships **untested** as a plan-quality rule. Recorded here as untested.

## Untested rules shipped (no failing baseline observed)
- Evidence pass is mandatory even for trivial-looking changes (Scenario 1)
- Phasing deferred to user at presentation (Scenario 3)
- Both are expressed as recipe/checklist items rather than bulletproofed prohibitions; if future baseline runs exhibit these failures, promote to full counters.
