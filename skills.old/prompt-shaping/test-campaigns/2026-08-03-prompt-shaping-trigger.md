# Test Campaign: prompt-shaping — 2026-08-03

## Trigger evals

### Iteration 1
- Description (≤1024 chars): Use ONLY when the user asks for help with the request itself — clarifying what they mean, expressing uncertainty ("not sure", "help me understand", "what should I do"), or making a hedged ask like "some kind of X" — and NOT when the user asks for work. A request to do something (write, fix, add, build, run, implement, refactor), however vague or incomplete, does NOT use this skill — do the work or ask one targeted question instead. Use this skill to restate intent and align on scope before executing, so misalignment costs a sentence instead of a wrong implementation.
- Train pass rate: 10/10 queries
- Validation pass rate: 8/8 queries
- Train failures: none
- Revision rationale: initial run with current description

### Selected iteration: 1 (validation pass rate 100%)

## Fresh-query sanity check
- 5 queries never used in optimization:
  - "I'm not sure if this is the right approach": loaded — pass
  - "help me understand what you mean by that": loaded — pass
  - "I need some kind of report generated": loaded — pass
  - "fix the authentication issue": not-loaded — pass
  - "implement the new feature": not-loaded — pass
- Pass rate: 5/5
