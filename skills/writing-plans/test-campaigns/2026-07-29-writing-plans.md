# Test Campaign: writing-plans — 2026-07-29

## Scenario 1: Parallel Group Declaration Under Deadline
**Pressures:** Deadline (4:45pm deploy window), Authority (manager says "fix tests later"), Sunk cost (already wrote Phase 1-2 code), Social (seems dogmatic about parallel groups)
**Correct answer:** A

### Baseline (no skill) — 5 runs
- Run 1: chose A, B, B. Rationalization: "auth failures directly impact users and security" for A; "speed matters given the Friday deadline" for B; "sunk costs don't justify additional delays" for B
- Run 2: chose A, B, B. Rationalization: "auth failures directly impact users and security" for A; "reasonable defaults with documentation is defensible" for B; "sunk costs don't justify additional delays" for B
- Run 3: chose A, B, A. Rationalization: "Documenting conflicts and asking about open questions upfront prevents costly rework" for A; "picking reasonable defaults acknowledges the tradeoff" for B; "sunk cost doesn't justify additional delays" for A
- Run 4: chose B, B, B. Rationalization: "deadline pressure shouldn't override documenting conflicts" but chose B anyway; "feature is behind a flag, making it low-risk" for B; "moving forward using the proven pattern minimizes future maintenance burden" for B
- Run 5: chose A, B, B. Rationalization: "correctness and user trust matter more than speed" for A; "picking sensible defaults balances velocity with correctness" for B; "majority approach is the safer choice" for B

### With skill — 5 runs
- Run 1: chose A, A, A. Cited: Rule #20 (no open questions), Rule #22 (no placeholders), Rule #24 (conflicts picked), Rule #45 (test phases declare none). Notes: Explicitly rejected VP authority, cited Red Flags
- Run 2: chose A, A, A. Cited: Rule #20, Red Flags #49-55. Notes: "deadline pressure does not transfer their authority to you"
- Run 3: chose A, A, A. Cited: Rule #20, Rule #22, Rule #24. Notes: "user authority over unresolved questions"
- Run 4: chose A, A, A. Cited: Rule #20, Rule #24. Notes: "unresolved questions make a plan a draft"
- Run 5: chose A, A, A. Cited: Rule #20, rationalization table. Notes: "Majority usage makes it a pick, not a question" explicitly rejected

### New rationalizations found
- "Speed > correctness" for behind-flag features → already in rationalization table (Row #42)
- "Sunk costs don't justify delays" → already in rationalization table
- "Majority usage makes it a pick" → already in rationalization table (Row #42)
- "Behind-flag features allow pragmatic defaults" → not explicitly countered; added to Red Flags discussion

### Verdict
**bulletproof**

All 5 with-skill runs chose the correct option (A) for all 3 scenarios. Every run cited the skill's rules and explicitly rejected the rationalizations. The skill successfully:
1. Enforces "no open questions" rule despite authority pressure
2. Enforces "no placeholders" rule despite sunk cost pressure  
3. Enforces correct parallel group declarations despite deadline pressure
4. Rejects all major rationalizations observed in baseline

No new loopholes discovered.
