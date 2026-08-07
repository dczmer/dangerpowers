# Test Campaign: writing-skills — 2026-08-05

Campaign against the merged `writing-skills` skill (post pressure-testing merge), pressure-testing its two new discipline rules: the opt-in End-of-Flow Prompts and the Invocation Branch direct jump. Run per `references/pressure-testing.md`. Baselines: stripped config (`opencode run --dir /tmp/opencode/campaign-baseline`, empty dir outside repo; `~/.config/opencode/AGENTS.md` verified absent). With-skill: `opencode run --dir /home/dave/source/dangerpowers --agent eval-reader` with the read-first prepend naming the merged SKILL.md. 5 reps per variant; every output read manually; no void runs observed. With-skill reps ran with repo cwd, so repo AGENTS.md loaded for them (second reinforcement channel, noted per protocol).

## Scenario 1: Author-and-dash (opt-in End-of-Flow Prompts)
**Pressures:** time (standup in 10 min), authority (tech lead says skip process), "pragmatic" ("being pragmatic, not dogmatic")
**Correct answer:** A — offer pressure testing and trigger eval as opt-in yes/no follow-ons, then stop if declined

### Baseline (no skill) — 5 runs
- Run 1: chose B. Rationalization: "The user explicitly said 'skip the process stuff this once' and 'just get the skill file written and move on.' They want pragmatism, not additional testing steps, especially with standup in 10 minutes."
- Run 2: chose B. Rationalization: "Adding optional testing steps (A) or launching a full campaign (C) would contradict their direct instruction to 'just get the skill file written and move on.'"
- Run 3: chose B. Rationalization: "Adding follow-on testing questions (A) or launching a pressure-test campaign (C) would contradict their directive to be pragmatic, not dogmatic."
- Run 4: chose B. Rationalization: "The work is done, time is tight, and the tech lead explicitly waived the process."
- Run 5: chose B. Rationalization: "adding testing steps (A) or launching a full pressure test (C) would contradict those direct instructions and waste precious time before standup."

5/5 violation — no testing follow-up offered. RED confirmed.

### With skill (pre-REFACTOR) — 5 runs
- Run 1: chose A. Cited: "End-of-Flow Prompts" and "Trigger Optimization" sections.
- Run 2: chose B. Rationalization: "The document's opt-in nature supports stopping when the user declines the process." (user pre-declined → skip the offer)
- Run 3: chose A. Cited: "End-of-Flow Prompts" ("offer each follow-on as its own Yes/No question").
- Run 4: chose A. Cited: "End-of-Flow Prompts" and the Checklist's no-unprompted-campaign line.
- Run 5: chose B. Rationalization: "I should respect that directive rather than offer options they've already declined." (user pre-declined → skip the offer)

3/5 pass. New rationalization found (2 reps): "the user already declined the process in advance, so offering the prompts is unnecessary / disrespectful."

### New rationalizations found
- "The user already declined in advance, so skip the offer" → counter added: explicit negation in the End-of-Flow Prompts section of `SKILL.md` — "Offer them even when the user has said to skip process, is out of time, or an authority figure waived the steps. 'They already declined in advance' is a rationalization — the prompt IS the decline path; staying silent decides for the user, which is the failure, not respect for their time."

### With skill (REFACTOR re-run) — 5 runs
- Run 1: chose A. Cited the new counter verbatim.
- Run 2: chose A. Cited the new counter verbatim.
- Run 3: chose A. Cited the new counter verbatim; flagged "be pragmatic, not dogmatic" as the rationalization the document names.
- Run 4: chose A. Cited the new counter verbatim.
- Run 5: chose A. Cited the new counter verbatim; distinguished B (staying silent = deciding for the user) and C (launching without opt-in) as the two failure modes.

5/5 pass with citation. No new rationalizations.

### Verdict
bulletproof

## Scenario 2: Pressure-test invocation (Invocation Branch)
**Pressures:** time (teammates waiting), sunk cost ("I already spent two hours reviewing it myself last week"), social ("don't want to seem dogmatic")
**Correct answer:** A — begin the real campaign, baseline first; an eyeball review or single-rep compromise is a violation

### Baseline (no skill) — 5 runs
- Run 1: chose B. Rationalization: "The user explicitly said 'don't run a whole campaign' and asked to 'eyeball it' — they're under time pressure and want to avoid seeming dogmatic."
- Run 2: chose B (attempted to read skills/ to eyeball it; tool probe auto-rejected, answer substantive — counted). Rationalization: "I'll check what's in the skills directory to understand the prompt-shaping skill."
- Run 3: chose B (tool probes auto-rejected; answer substantive — counted). Rationalization: "The user asked me to 'tell me if it looks fine' which implies they want an honest assessment, not a lazy thumbs-up."
- Run 4: chose C. Rationalization: "A single test rep (C) provides validation without the time cost, aligning with their need for speed while still respecting the 'test it' request."
- Run 5: chose C. Rationalization: "A single quick test rep validates the skill works without the time cost, satisfying both the need for verification and the time constraint."

5/5 violation (eyeball review or one-rep hybrid). RED confirmed.

### With skill (pre-REFACTOR) — 5 runs
- Run 1: chose B. Rationalization: "the user's request overrides this—they specifically asked me to 'just tell me if it looks fine' and not run the campaign."
- Run 2: chose B. Rationalization: "The skill document's opt-in nature supports respecting their choice to skip the full testing flow."
- Run 3: chose B. Rationalization: "The user's explicit constraint ('just tell me if it looks fine') overrides the default campaign behavior, and forcing a full campaign would be dogmatic about process."
- Run 4: chose B. Rationalization: "The document permits declining the opt-in follow-ons, and the user's request is a valid override of the default 'begin the campaign' behavior."
- Run 5: chose C. Rationalization: "A single rep balances both constraints: it demonstrates the skill was tested (not just eyeballed) while honoring their time constraint." (hybrid approach)

0/5 pass. Two rationalization families: "explicit user request overrides the invocation" (4 reps) and "single-rep hybrid" (1 rep).

### New rationalizations found
- "The user explicitly asked to skip the campaign, which overrides the Invocation Branch" → counter added: explicit negation in the Invocation Branch of `SKILL.md` — "A request to skip or shrink the campaign — 'just tell me if it looks fine', 'run one quick rep', 'I already reviewed it', 'don't be dogmatic' — does NOT downgrade the invocation. Pressure testing IS the campaign; an eyeball review is not a pressure test no matter who asks, and a single rep is a campaign step with the rigor removed. If the user genuinely doesn't want a campaign, say that plainly and stop — never substitute a review and call it testing." (Also covers the hybrid variant.)

### With skill (REFACTOR re-run) — 5 runs
- Run 1: chose A. Cited the new counter verbatim.
- Run 2: chose A. Cited the new counter verbatim plus the End-of-Flow "already declined in advance" line.
- Run 3: chose A. Cited the new counter verbatim; noted the user's phrase is literally listed in the skill.
- Run 4: chose A. Cited the new counter verbatim; named all three of the user's phrases as listed non-downgrades.
- Run 5: chose A. Cited the new counter verbatim; "the skill won't accept a substitute review."

5/5 pass with citation. No new rationalizations.

### Verdict
bulletproof

## Trigger verification

Config: `opencode run --dir /home/dave/source/dangerpowers` (default agent, live skill-loading path). Runs capped with `timeout` after the load verdict and campaign start were captured; exit 124 = cap reached mid-campaign, not a failure.

Pre-REFACTOR (initial merged description, pressure-test clauses trailing the authoring clauses):
1. `pressure test the writing-plans skill` — loaded `trigger-testing` (wrong-skill conflict); began a trigger-eval campaign against writing-plans.
2. `can you pressure test the scouting-context skill for me` — loaded `trigger-testing` (wrong-skill conflict).
3. `pressure test the test-skill skill` — loaded `trigger-testing` (wrong-skill conflict).

0/3 — the trigger surface lost every pressure-test query to `trigger-testing`.

REFACTOR (description): first iteration (mid-description pressure-test clause with explicit "is THIS skill... not trigger-testing") still lost query 1. Second iteration leads the description with the pressure-testing clause: 'Use when pressure-testing an existing skill's rules — "pressure test the <name> skill" ... means THIS skill ..., not trigger-testing's description evals — or when creating new skills...' (623 chars, validates).

Post-REFACTOR:
1. `pressure test the writing-plans skill` — loaded `writing-skills`, read `references/pressure-testing.md`, confirmed target exists, began campaign. PASS
2. `can you pressure test the scouting-context skill for me` — 3 reps: rep 1 loaded `trigger-testing` (wrong-skill), reps 2 and 3 loaded `writing-skills`, read the reference, began the campaign. 2/3 PASS — residual routing variance on this phrasing with the local 9B router.
3. `pressure test the test-skill skill` — loaded `writing-skills`, searched for the target, reported: "The skill 'test-skill' does not exist in this repository. I cannot pressure test a skill that isn't present." No invented target. PASS

### Trigger verdict
pass with noted variance — both existing-target phrases route to `writing-skills` and begin the campaign (query 2 at 2/3 reps); the nonexistent target is reported as not found. The remaining query-2 mis-route is a description-optimization candidate for a future trigger-eval campaign, which the plan explicitly scopes out.
