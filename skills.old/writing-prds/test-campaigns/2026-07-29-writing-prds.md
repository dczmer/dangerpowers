# Test Campaign: writing-prds — 2026-07-29

## Scenario 1: Tight Deadline + Team Decision + Sunk Cost
**Pressures:** deadline urgency, authority (PM decision), sunk cost (4 hours invested)
**Correct answer:** A

### Baseline (no skill) — 3 runs
- Run 1: chose C. Rationalization: "The tech stack decisions (PostgreSQL + React) are already made and committed to, so they belong in the document. Placing them in an appendix keeps the PRD's core requirements section focused on WHAT and WHY, while still making the technical decisions visible and traceable."
- Run 2: chose C. Rationalization: "Appendix approach allows documentation without cluttering requirements"
- Run 3: chose C. Rationalization: "Confirmed decisions should be preserved for future reference and accountability"

### With skill — 3 runs
- Run 1: chose A. Cited: "No implementation details" and "No silent assumptions"
- Run 2: chose A. Cited: "No implementation details" section
- Run 3: chose A. Cited: "The Iron Rules"

### Counter added
- Rationalization Table: "An appendix is still in the PRD. A stack written anywhere in the doc becomes the spec readers anchor on. Decided stacks belong in ADRs and design docs."
- Red Flags: "'I'll just note the stack in an appendix'"

## Scenario 2: User Wants Quick Start + Unclear Decisions
**Pressures:** deadline pressure, user authority, ambiguity aversion
**Correct answer:** C

### Baseline (no skill) — 3 runs
- Run 1: chose B. Rationalization: "Engineering is waiting to start, and a PRD with multiple ambiguous options creates paralysis rather than enabling work"
- Run 2: chose B. Rationalization: "Make a defensible, common-sense choice to give engineering direction while maintaining flexibility"
- Run 3: chose B. Rationalization: "Document as initial scope that can be revisited"

### With skill — 3 runs
- Run 1: chose C. Cited: "Clarification interview" step
- Run 2: chose C. Cited: "No silent assumptions" rule
- Run 3: chose C. Cited: "Use question tool until every template section can be filled without guessing"

### Counter added
- Rationalization Table: "Unconfirmed assumptions written as fact fossilize into decisions nobody revisits. Reasonable guesses are still guesses."
- Red Flags: "'Engineering needs to start Monday'"
- Description symptom: "user wants to start immediately without clarifying"

## Scenario 3: Deadline Pressure + Open Questions
**Pressures:** deadline urgency, authority (user approval), sunk cost (time invested)
**Correct answer:** B

### Baseline (no skill) — 3 runs
- Run 1: chose B. Rationalization: "Under deadline pressure, make concrete defaults and document open questions in §9 with owners"
- Run 2: chose B. Rationalization: "Keep status: draft to signal provisional decisions"
- Run 3: chose B. Rationalization: "Enables shipping while maintaining transparency"

### With skill — 3 runs
- Run 1: chose B. Cited: "No approval with open questions" rule
- Run 2: chose B. Cited: "status: approved requires §9 empty"
- Run 3: chose B. Cited: "Deadline pressure does not transfer the question-owner's authority"

### New rationalizations found
- None

## Meta-testing
All three with-skill runs cited specific sections from the skill document as justification. No agents reported the skill was unclear.

## Verdict
**Bulletproof**

All three discipline rules are enforced under pressure:
1. No implementation details (tech stack in appendix)
2. No silent assumptions (making decisions for unclear requirements)
3. No approval with open questions (marking approved with unresolved items)

The skill's existing counters and red flags effectively prevent all observed rationalizations.
