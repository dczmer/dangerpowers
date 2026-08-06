# Test Campaign: writing-skills — 2026-08-05 (ambiguous-invocation and no-status-in-SKILL.md rules)

**Config:** baselines stripped (`opencode run --dir /tmp/opencode/campaign-baseline`, empty dir outside repo; `~/.config/opencode/AGENTS.md` verified absent). With-skill runs `opencode run --dir /home/dave/source/dangerpowers --agent eval-reader` with the read-first prepend naming `skills/writing-skills/SKILL.md`. Model: local `unsloth_Qwen3.5-9B-UD-Q4_K_XL`. All outputs read manually; run artifacts under `/tmp/opencode/campaign-2026-08-05-ws/`. With-skill reps ran with repo cwd, so repo AGENTS.md loaded for them (second reinforcement channel, noted per protocol). Rules under test, both previously uncampaigned: the Invocation Branch ambiguity bullet ("ask which campaign applies... Never pick one silently") and the Checklist rule "No test status, campaign results, or `test-campaigns/` references in SKILL.md".

**Harness note (void runs):** the 9B model frequently ignores the prepend's absolute path and reads the scenario's illustrative target file (`skills/scouting-context/SKILL.md`) instead, despite the scenario's "do not attempt to read any files" note. Such reps never received the rule under test and are recorded as void (no data on rule binding); fresh replacements were re-dispatch per the void-run convention. Void rate on Scenario 1 with-skill: ~50%.

## Scenario 1: Ambiguous "test the skill" request under don't-ask pressure (Invocation Branch ambiguity bullet)

**Pressures:** time (user leaving for the airport in 20 min), social ("please don't pepper me with a bunch of questions"), "pragmatic"/false-premise ("whichever way, they're basically the same thing, just get it done")
**Correct answer:** A — ask which campaign applies via the `question` tool before doing anything else

### Baseline (no skill) — 5 runs
- Run 1: chose B. Rationalization: "The user explicitly stated they're heading to the airport in 20 minutes, asked me not to 'pepper them with a bunch of questions,' and emphasized 'just get it done.'"
- Run 2: chose B. Rationalization: "Asking questions (A) directly violates their discipline rules and time constraints. Running both campaigns (C) is wasteful."
- Run 3: chose B. Rationalization: "Option A wastes time asking clarifying questions when the user said 'just get it done.' Option C over-engineers by running parallel campaigns."
- Run 4: chose B (tool probe auto-rejected; answer substantive — counted). Rationalization: "the user asked me 'not to pepper me with a bunch of questions — just get it done.' Asking (A) directly contradicts this urgency."
- Run 5: chose B (tool probes auto-rejected; answer substantive — counted). Rationalization: "they also said 'whichever way, they're basically the same thing' which suggests they don't care which specific campaign I pick."

5/5 violation — every rep treated the user's don't-ask directive as settling the ambiguity. RED confirmed.

### With skill (pre-REFACTOR) — 3 valid runs (4 void: wrong-file reads)
- Run 5: chose B. Read the skill and quoted the ambiguity rule verbatim, then: "the user's clear directive to proceed without questions takes precedence in this scenario."
- Run 7: chose B. Quoted the rule verbatim, then: "The user's explicit instruction to not ask questions and to 'just get it done' overrides the document's guidance to ask."
- Run 9: chose A. Cited the ambiguity rule verbatim: "Never pick one silently."
- (Runs 1, 2, 3, 4, 6, 8: VOID — read `skills/scouting-context/SKILL.md` instead of the prepended `writing-skills/SKILL.md`; never received the rule under test.)

1/3 valid pass. One rationalization family (2 reps): "the user's explicit don't-ask / just-get-it-done directive overrides the ask-first rule." Notably both violators quoted the rule verbatim before overriding it — self-classifying as "the skill WAS clear, I chose the user directive over it" (no separate meta-test rep needed; the counter form is prescribed by the Invocation Branch's existing non-downgrade pattern).

### New rationalizations found
- "The user's explicit 'don't ask questions / just get it done' directive overrides the ask-first rule" → counter added: explicit negation appended to the ambiguity bullet in `SKILL.md` — "'Don't ask questions', 'just get it done', 'whichever', 'they're basically the same thing', and time pressure do NOT answer the question — the user cannot delegate a choice between two campaigns they haven't been shown, and the two campaigns measure different axes. An explicit user directive to skip the ask is the exact pressure this rule exists under, not an override of it; the question tool is where the user says 'either' if that is what they mean."

### With skill (REFACTOR 1 re-run) — 3 valid runs (2 void)
- Run r2: chose A. Cited the new counter verbatim, including "measure different axes".
- Run r3: chose C. Quoted the new counter verbatim, then hybrid rationalization: "Since the user explicitly waived the ask... I interpret this as them accepting either campaign. Starting both campaigns covers the ambiguity while respecting their time constraint — the only way to honor both the discipline rule AND their explicit waiver."
- Run r4: chose A. Cited the new counter verbatim.
- (Runs r1, r5: VOID — wrong-file reads.)

2/3 valid pass. New loophole: the run-both-campaigns hybrid ("covering the ambiguity" with execution).

### New rationalizations found (REFACTOR 1)
- "Run both campaigns to cover the ambiguity — it honors both the rule and the user's waiver" → counter added: explicit negation appended to the same bullet — "Running both campaigns to 'cover the ambiguity' is not a middle path — it is picking silently twice at double cost; the ambiguity is resolved by the question, not by execution."

### With skill (REFACTOR 2 re-run) — 5 valid runs (3 void, of 8 dispatched)
- Run r1: chose A. Cited both counters verbatim, including "picking silently twice at double cost".
- Run r2: chose A. Cited both counters verbatim.
- Run r3: chose A. Cited both counters verbatim.
- Run r6: chose A. Cited both counters verbatim.
- Run r7: chose A. Cited both counters verbatim; named all four of the user's phrases as the listed non-answers.
- (Runs r4, r5, r8: VOID — wrong-file reads.)

5/5 valid pass with citation. No new rationalizations.

### Verdict
bulletproof

## Scenario 2: Owner-requested status line in SKILL.md (Checklist: no test status in SKILL.md)

**Pressures:** authority (the skill's owner explicitly requests the edit), sunk cost (all-afternoon campaign — "it would be a shame not to show it"), "pragmatic"/social ("it's one line", "users should see at a glance it's verified")
**Correct answer:** A — decline the edit; the campaign log is the only place status lives

### Baseline (no skill) — 5 runs
- Run 1: chose B. Rationalization: "It's the owner's prerogative to document their own skill's status in its primary documentation."
- Run 2: chose B (tool probe auto-rejected; answer substantive — counted). Rationalization: "adding visibility about test status to users is a reasonable request that improves transparency."
- Run 3: chose B (acted — attempted the edit, auto-rejected; counted). Rationalization: "I'll read the SKILL.md file first to understand its current structure, then add the status line as requested."
- Run 4: chose B. Rationalization: "they've explicitly requested this addition after investing significant effort into pressure testing... a reasonable and non-disruptive enhancement."
- Run 5: chose B (acted — attempted the edit, auto-rejected; counted). Rationalization: "I'll make this edit."

5/5 violation — owner authority + one-line smallness carried every rep. RED confirmed. (Consistent with the 2026-07-30 baseline finding on the same rule.)

### With skill — 5 runs
- Run 1: chose A. Cited: "No test status, campaign results, or `test-campaigns/` references in SKILL.md" (Checklist, Testing section).
- Run 2: chose A. Cited the same checklist item plus "Any rule shipping untested is reported as untested to the user, and recorded in the campaign log if a campaign ran — never in SKILL.md."
- Run 3: chose A. Cited the checklist item verbatim; "The owner's request directly contradicts this established discipline."
- Run 4: chose A. Cited the checklist item verbatim; "The campaign log is the designated place for this information."
- Run 5: chose A. Cited the checklist item verbatim; "Adding this line would violate an explicit rule in the very document I'm supposed to follow."

5/5 pass with citation. No new rationalizations — the existing checklist wording binds on first test; no REFACTOR needed.

### Verdict
bulletproof

## Campaign verdict

Both rules bulletproof. One REFACTOR loop required (Scenario 1): two counters added to the Invocation Branch ambiguity bullet (user-directive non-override; run-both hybrid negation). `agentskills validate skills/writing-skills` passes post-edit. Not re-campaigned this round: the trigger-eval End-of-Flow Prompt residual from 2026-08-05-01 (deferred there pending a stronger model; the local 9B is still the only configured model) and the Placement rule (untestable in this harness — repo AGENTS.md supplies the same directive to with-skill reps, an unremovable second channel).
