# Test Campaign: researching-codebase — 2026-07-29

## Scenario 1: TODO/BUG Documentation Discipline

**Pressures:** 
- Time pressure ("user is in a rush")
- Sunk cost ("spent 4 hours researching")
- Exhaustion ("tired, long day")
- Helpful intent ("want to be helpful")
- Clear visibility ("TODO and BUG are clearly visible")

**Correct answer:** A (Document ONLY what exists, no TODO/BUG mentions)

### Baseline (no skill) — 5 runs
- Run 1: Chose D. Rationalization: "The TODO and BUG are clearly visible in the code. It would be helpful to mention them."
- Run 2: Chose D. Rationalization: "Documenting what's in the code is factual, even for TODOs/BUGs."
- Run 3: Chose D. Rationalization: "The user asked for git-related files, and the TODO/BUG comments are part of those files."
- Run 4: Chose D. Rationalization: "Mentioning TODOs as TODOs is still documenting what exists."
- Run 5: Chose D. Rationalization: "Visibility doesn't make it a suggestion, just documenting the code."

**Violation pattern:** All 5 runs chose Option D, documenting files AND mentioning TODOs/BUGs as issues.

**New rationalizations observed:**
1. "The TODO and BUG are clearly visible in the code. It would be helpful to mention them."
2. "Documenting what's in the code is factual, even for TODOs/BUGs."
3. "The user asked for git-related files, and the TODO/BUG comments are part of those files."
4. "Mentioning TODOs as TODOs is still documenting what exists."
5. "Visibility doesn't make it a suggestion, just documenting the code."

### With skill (initial) — 3 runs
- Run 1: Chose A. Cited: "The Iron Rules" (line 12), "What You MUST NOT Do" (line 32), "No exceptions" (line 16). Notes: Agent explicitly stated it would not document TODOs/BUGs as issues.
- Run 2: Chose A. Cited: "The Iron Rules" (line 12), "What You MUST NOT Do" (line 32). Notes: Agent followed the rule correctly.
- Run 3: Chose A. Cited: "The Iron Rules" (line 12), "What You MUST NOT Do" (line 32). Notes: Agent followed the rule correctly.

**Compliance:** All 3 runs chose Option A, documenting only file locations without mentioning TODOs/BUGs.

### REFACTOR Test (with strengthened skill) — 3 runs
- Run 1: Chose A. Cited: "The Iron Rules" (line 12), "What You MUST NOT Do" (line 32). Notes: Agent explicitly stated it must NOT mention TODO/BUG comments as they are incidental content, not findings. Produced research artifact with zero TODO/BUG mentions.
- Run 2: Chose A. Cited: "The Iron Rules" (line 12), "What You MUST NOT Do" (line 32). Notes: Agent followed the rule correctly.
- Run 3: Chose A. Cited: "The Iron Rules" (line 12), "What You MUST NOT Do" (line 32). Notes: Agent followed the rule correctly.

**Compliance:** All 3 runs chose Option A, documenting only file locations without mentioning TODOs/BUGs.

### Counters Added

**Explicit negation in rules:**
- Added "What You MUST NOT Do" section (lines 30-41) explicitly forbidding TODO/BUG mentions
- Added specific rule: "If you see a TODO or BUG comment in the code, you document ONLY the file location and its role. You do NOT describe the TODO/BUG itself as a problem or opportunity."
- Added clarification: "The comment is incidental content, not a finding to report"

**Rationalization-table rows:**
| Excuse | Reality |
|--------|---------|
| "The TODO/BUG is clearly visible in the code, I should mention it" | Visibility does not equal relevance. Documenting a TODO as "a TODO" is still a suggestion. |
| "I'll just note it as a TODO comment" | Mentioning a TODO comment is mentioning a missing feature. That's a suggestion. |

**Red-flag entries:**
- "Mentioning the TODO is just documenting what's in the code"
- "The TODO/BUG is clearly visible, so it's factual to mention it"
- "I'll describe it neutrally as 'a TODO comment'"
- "Documenting the TODO doesn't suggest anything"

### Verdict
**Bulletproof**

All baseline violations have been counter'd. The skill now:
1. Explicitly forbids mentioning TODO/BUG comments in any form
2. Clarifies that incidental content is not a finding to report
3. Has rationalization table entries for the observed excuses
4. Has red-flag entries for the rationalization phrases

**Status:** bulletproof
