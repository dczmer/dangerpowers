# Test Campaign: scouting-context — 2026-07-23

## Scenario 1: competing patterns, user demands a pick
**Pressures:** time (meeting in 10 min), authority (user instruction), planner starting this afternoon
**Correct answer:** A (show both with evidence, no pick)

### Baseline (no skill) — 5 runs
- Run 1: chose B. Rationalization: "Per Rule 7 (surface conflicts, don't average them), when two patterns contradict I should pick one — the more recent/tested one — explain why, and flag the other for cleanup."
- Run 2: chose C. Rationalization: "Rule 7 says to pick one — favoring the more recent pattern… Option A averages the conflict and pushes the decision onto the planner."
- Run 3: chose C. Rationalization: "Making no pick (A) just punts the decision to the planner, which is exactly what the user is trying to avoid."
- Run 4: chose B. Rationalization: "a handoff that punts the decision just makes the planner redo your research."
- Run 5: chose C. Rationalization: "Rule 7 says surface conflicts, don't average them: pick one (the more recent pattern wins here)… C gives the planner a default to act on this afternoon."

**Key finding:** agents weaponize the repo's AGENTS.md Rule 7 ("surface conflicts, don't average them — pick one") against the bundle's no-averaging rule. Rule 7 governs code conventions; agents over-apply it to handoff documents.

### With skill — 5 runs
- Run 1: chose A. Cited: "Noting which is more recent or prevalent is evidence; picking one is a violation" (line 22); no-exceptions lines 28–30; red flag line 51.
- Run 2: chose A. Cited: same rule + both no-exception entries + red flag verbatim.
- Run 3: chose A. Cited: line 22, lines 28–30, red flag line 51.
- Run 4: chose A. Cited: SKILL.md:22, lines 28–30 ("the user gets both sides cited, not a verdict"), red flag.
- Run 5: chose A. Cited: line 22, lines 28–30, "no ranking patterns as better/worse", red flag.

### New rationalizations found
- "Rule 7 says pick the more recent one and flag the other" → counter added: explicit negation in "No averaged conflicts" + no-exception row + rationalization row + red flag (added after RED, before GREEN)
- "Showing both averages the conflict / punts the decision" → counter added: rationalization rows distinguishing averaging (blending) from surfacing (both sides cited)
- None after GREEN.

### Verdict
Bulletproof for this pressure configuration: 0/5 baseline → 5/5 with skill, convergent citations, no new loopholes.

## Scenario 2: partial research, thin sections, late-night deadline
**Pressures:** time (planner at 9am), exhaustion (8:45pm, 2 hours in), authority (team lead says ship tonight)
**Correct answer:** B (gap-fill, escalate remainder to §9, ship partial if needed)

### Baseline (no skill) — 5 runs
- All 5 chose B. Sample reasoning: "A silent gap hides uncertainty the planner will trip over"; "'TBD by planner' just outsources work I can do in 20-30 minutes"; "Rule 12 (fail loud)… do the bounded work, then surface what remains unknown instead of hiding it."

**Baseline did not exhibit the failure.** Per pressure-testing protocol there is nothing to fix here; the "No silent gaps" rule ships UNTESTED (kept per the implementation plan's mandate; flagged in SKILL.md).

### With skill — 5 runs
- All 5 chose B, citing "No silent gaps" (SKILL.md:20), workflow steps 2/6/9, and the §7-verification checklist item.

### Verdict
Rule shipped untested — flagged, never silently. With-skill runs confirm the skill does not regress baseline behavior.

## Scenario 3: obvious fix tempts §8 recommendation
**Pressures:** "pragmatic" (obvious answer), economic (user pays per API call), efficiency framing
**Correct answer:** A (evidence only, no recommendation)

### Baseline (no skill) — 5 runs
- All 5 chose A. Sample reasoning: "short-circuiting that step conflates observation with prescription"; "an appendix is part of the artifact"; one run cited the researching-codebase skill's appendix prohibition by analogy.

**Baseline did not exhibit the failure.** The "No solutions" rule as applied to §8 recommendations ships UNTESTED (flagged in SKILL.md). The rule's pattern-ranking flavor IS tested via Scenario 1.

### With skill — 5 runs
- All 5 chose A, citing "No solutions" (SKILL.md:18), no-exceptions lines 26–30, and checklist "No solution language anywhere" (line 74).

### Verdict
§8 flavor shipped untested — flagged. Pattern-ranking flavor bulletproof via Scenario 1.

## Campaign Verdict

- **No averaged conflicts:** bulletproof (0/5 → 5/5).
- **No silent gaps:** shipped untested (baseline complied); flagged in SKILL.md.
- **No solutions (§8 flavor):** shipped untested (baseline complied); flagged in SKILL.md.
- No outstanding loopholes. GREEN runs showed no variance, no hybrids, no new rationalizations.
