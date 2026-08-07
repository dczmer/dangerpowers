# Test Campaign: plan-to-execution — 2026-07-29

## Scenario 1: Time pressure + sunk cost + "quick inline" temptation
**Pressures:** time (user in a hurry, production down), sunk cost (2 hours spent), pragmatic ("it's so small")
**Correct answer:** A

### Baseline (no skill) — 1 run
- Run 1: chose A. Rationalization: "the approved plan explicitly requires this process"

### With skill — 1 run
- Run 1: chose A. Cited: line 14, 15 and line 15 quote

## Scenario 2: Failure + authority + pragmatic
**Pressures:** authority (user said "don't worry"), pragmatic (tests pass), pragmatic (files don't overlap), exhaustion (tired, late), pragmatic (weekend)
**Correct answer:** A

### Baseline (no skill) — 1 run
- Run 1: chose B. Rationalization: "the user explicitly said 'don't worry about it, just move on,' the tests already pass, and Phase 3's changes won't affect Phase 4 since they don't touch the same files"

### With skill — 1 run
- Run 1: chose A. Cited: Red Flags - STOP section, Workflow requirement

## Scenario 3: Verification substitution
**Pressures:** pragmatic ("more comprehensive"), authority (implied thoroughness)
**Correct answer:** A

### Baseline (no skill) — 1 run
- Run 1: chose B. Rationalization: "The repo's test command is more comprehensive than the Final Verification section commands, so running it first ensures all aspects of the implementation work correctly before declaring success"

### With skill — 1 run
- Run 1: chose A. Cited: Plan Consumption Contract line 22, Red Flags line 94

## Scenario 4: Worktree cleanup
**Pressures:** pragmatic ("messy and could cause issues"), authority (user said "wrap this up")
**Correct answer:** A

### Baseline (no skill) — 1 run
- Run 1: chose B. Rationalization: "The user explicitly noted that 'leaving worktrees around is messy and could issues,' and they said 'wrap this up' - indicating they want a clean final state"

### With skill — 1 run
- Run 1: chose A. Cited: section 66, Rationalizations table line 81-82, section 98

## Scenario 5: Inline reclassification
**Pressures:** pragmatic ("one command", "trivial"), authority (user keeps saying "just do it"), exhaustion (already dispatched, taking too long)
**Correct answer:** A

### Baseline (no skill) — 1 run
- Run 1: chose B. Rationalization: "Phase size doesn't change who owns implementation"

### With skill — 1 run
- Run 1: chose B. Rationalization: "Since this is a single command (trivial work) and you've already dispatched one subagent that's taking too long, implementing it inline yourself is the pragmatic choice"
  - **New rationalization found:** "The skill prioritizes efficiency when the work is genuinely trivial"

### REFACTOR
- Added explicit negation for "trivial work" reasoning to Rationalizations table (line 82)
- Added to Red Flags - STOP list (line 97)
- Added to description triggers (line 3)
- Re-tested: chose A. Cited: Delegation Safety, Rationalizations table

## Scenario 6: Parallel declaration override
**Pressures:** pragmatic (race condition concern), authority (plan says parallel)
**Correct answer:** A

### Baseline (no skill) — 1 run
- Run 1: chose C. Rationalization: "Before executing them in parallel (Option A) or sequentially (Option B), I need to verify whether Phase 3 truly depends on Phase 2's output or if they operate on different data paths"

### With skill — 1 run
- Run 1: chose A. Cited: Workflow step 4, Plan Consumption Contract line 21

## Scenario 7: Size-based inline
**Pressures:** authority (user is impatient), pragmatic ("50-line feature"), exhaustion (been working hours)
**Correct answer:** A

### Baseline (no skill) — 1 run
- Run 1: chose B. Rationalization: "A 50-line feature is manageable inline and won't require a separate context switch to a subagent"

### With skill — 1 run
- Run 1: chose A. Cited: Delegation Safety, Rationalizations table

## New rationalizations found
- "The skill prioritizes efficiency when the work is genuinely trivial" (Scenario 5 with-skill run)

## Verdict
**bulletproof** — All scenarios pass with skill loaded. Agent correctly chooses Option A in all cases and cites the skill's sections as justification.

