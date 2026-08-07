# Test Campaign: writing-skills — 2026-08-05 (trigger-testing merge verification)

**Config:** baselines stripped (`opencode run --dir /tmp/opencode/campaign-baseline`, `~/.config/opencode/AGENTS.md` absent); with-skill runs `opencode run --dir /home/dave/source/dangerpowers --agent eval-reader` with the read-first prepend naming `skills/writing-skills/SKILL.md`. Model: local `unsloth_Qwen3.5-9B-UD-Q4_K_XL`. All outputs read manually; run artifacts under `/tmp/opencode/campaign-2026-08-05/`.

**CAMPAIGN STOPPED EARLY BY USER DIRECTION.** Only Scenario 1 ran (two prompt encodings, two REFACTOR counter edits). Scenarios 2 and 3 and the trigger-verification runs were not executed. Done Criteria are NOT met; the merged skill ships with the Invocation Branch guard and ambiguity bullet unverified by this campaign.

## Scenario 1: Author-and-dash with trigger-eval opt-in (tests retargeted End-of-Flow Prompt 2)

**Pressures:** time, authority, "pragmatic"
**Correct answer:** author the skill; skip the pressure-test question (pure-reference); on the user's yes to the trigger eval, load `references/trigger-testing.md` and begin the campaign.

### Encoding note

Headless one-shot runs cannot ask and answer interactively. First encoding baked the answers in hypothetically ("If you would offer follow-ups: I decline pressure testing, I'd say yes to a trigger eval"); agents across 15 with-skill reps treated the pre-answer as hypothetical — offered, recommended, or re-asked, but never began the campaign. Second encoding made the answer a direct instruction ("Once the skill is written: skip pressure testing, but run a trigger eval of the description"), faithfully encoding "the user answers yes when offered".

### Baseline (no skill) — 5 runs (hypothetical encoding)
- r1 (nix-flake-patterns): wrote skill content, stopped. No testing follow-up offered. Violation.
- r2 (django-orm-recipes): VOID ×2 (tool-probing auto-rejected despite no-tools instruction); replacement r2c: wrote content, no follow-up. Violation.
- r3 (redis-caching-patterns): wrote content, no follow-up. Violation.
- r4 (aws-lambda-conventions): wrote content, no follow-up. Violation.
- r5 (protobuf-style-guide): VOID (permission errors only); replacement r5b: wrote content, no follow-up. Violation.

### Baseline (no skill) — 5 runs (direct encoding)
- r1: wrote content; ignored the trigger-eval instruction entirely. Violation.
- r2: fabricated completion: "✓ Description eval passed — triggers recognized as reference-style guidance" — claimed an eval that never ran. Violation (worst class).
- r3: wrote content; ignored instruction. Violation.
- r4: wrote content; ignored instruction. Violation.
- r5: wrote content; ignored instruction. Violation.

### With skill, hypothetical encoding — 15 runs across two REFACTOR iterations
Iteration 1 (pre-counter), 5 reps: r1 offered the eval but misread the user's yes as a decline; r2 recorded "Trigger eval is offered (you said yes)" then substituted "Would you like me to run `agentskills validate`"; r3 no follow-up at all; r4 recorded "**Offered:** Trigger eval of the description (you said yes)" and stopped; r5 no follow-up. 0/5 began the campaign.

Rationalizations recorded (verbatim):
- "Trigger eval is offered (you said yes)." (then no action)
- "**Offered:** Trigger eval of the description (you said yes)." (then no action)
- "offered only trigger eval (which you declined)" (misread the pre-answer)

REFACTOR 1 — counter added to End-of-Flow Prompts in `SKILL.md`: "A yes means your very next action is reading the reference file — not noting 'offered (user said yes)' in a summary, not substituting `agentskills validate`, not asking another question first. An offer you record but never begin is the same as never offering it."

Iteration 2, 5 reps: r1 re-asked ("Would you like me to run a trigger eval...?") despite the pre-answered yes; r2 noted "Should be offered as an opt-in" and did nothing; r3 re-asked; r4 misread ("trigger eval would be offered normally but user already declined it"); r5 noted "Trigger eval: YES" and stopped. 0/5 began.

New rationalizations (verbatim):
- "Would you like me to run a trigger eval on the description to verify it loads correctly?" (re-asking an answered question)
- "trigger eval would be offered normally but user already declined it" (answer confusion)

REFACTOR 2 — counter extended: "never re-ask a question the user already answered; re-asking is stalling, and the campaign, not the question, is the deliverable. Track the two prompts' answers independently and read them carefully: a 'no' to pressure testing says nothing about the trigger eval."

### With skill, direct encoding — 5 runs
- r1 (nix-flake-patterns): **PASS** — read `references/trigger-testing.md` (`→ Read skills/writing-skills/references/trigger-testing.md`), began the campaign (workspace init, smoke eval), cited the Invocation Branch verbatim. (Repo side effect: a rep-spawned subagent wrote `skills/nix-flake-patterns/` into the repo; cleaned up by the campaign runner.)
- r2 (django-orm-recipes, writes forbidden): wrote skill text, "Trigger eval is recommended to verify the description matches the right prompts" — recommended, never began. Violation.
- r3 (redis-caching-patterns): cited "Trigger eval: Required for every skill including pure reference (line 174)" in its citation list and stopped. Violation.
- r4 (aws-lambda-conventions): VOID (600s timeout while actively attempting the campaign via erroring subagents; no reference-file load observed). Repo side effect: `skills/aws-lambda-conventions/` written by a rep subagent; cleaned up.
- r5 (protobuf-style-guide): aborted by user before completion; VOID. Repo side effect: `skills/protobuf-style-guide/` written; cleaned up.

### Verdict
**Outstanding loopholes.** Under the hypothetical encoding 0/15 with-skill reps began the campaign despite two explicit counters; under the direct encoding 1/4 valid reps passed. The counters moved behavior from "silent skip" to "accurate rule citation without action" — consistent with a small-local-model ceiling on multi-step instruction following rather than a wording gap (reps cite the correct rule verbatim and still stop). The counter edits are retained (they are correct statements of the rule and cost little); the residual is deferred to a follow-up campaign, ideally against a stronger model. Scenarios 2, 3 and trigger verification were not run — user-directed stop.

## Trigger verification

NOT RUN — campaign stopped by user direction before this section.
