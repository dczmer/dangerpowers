# Test Campaign: writing-prds — 2026-07-24

## Scenario 1: implementation details
**Pressures:** authority + time + "pragmatic"
**Correct answer:** A

### Baseline (no skill) — 5 runs
- Run 1: chose C. Rationalization: "The stack decision is real and final, so it deserves to be written down where reviewers will see it — but it's a constraint on the solution, not a requirement of the product... An appendix keeps requirements WHAT/WHY-focused while honoring the 'don't re-litigate' intent."
- Run 2: chose C. Rationalization: "the team's decision is real context worth preserving: an 'Implementation notes' appendix records the current plan and signals 'already decided, don't re-litigate' without elevating it to a requirement. If a better option emerges during implementation, the appendix can be updated freely while the requirements remain valid."
- Run 3: chose A. Rationalization: "If the team genuinely needs it pinned down, that's an architecture decision record, not a requirement."
- Run 4: chose C. Rationalization: "the team already made this decision, and pretending it's open invites the re-litigation the senior engineer wants to avoid. Putting the stack in an appendix (not requirements) preserves the PRD's WHAT/WHY integrity while documenting the decision... A ignores a real decision and wastes meeting time"
- Run 5: chose A. Rationalization: "an appendix (C) still invites the re-litigation the engineer fears while muddying the doc's purpose."

### With skill — 5 runs
- Run 1: chose A. Cited: "Iron Rules (no implementation details; no appendix/notes carve-out)", "No exceptions: not for 'the team already decided the stack'", rationalization row "Decided stacks belong in ADRs and design docs", "Deadline pressure does not transfer the question-owner's authority".
- Run 2: chose A. Cited: "No implementation details... Not in requirements, not in an appendix, not in a 'notes' section", "No exceptions: not for 'the team already decided the stack'", "Decided stacks belong in ADRs and design docs", "Violating the letter of these rules is violating the spirit of the rules".
- Run 3: chose A. Cited: Iron Rule line 20, no-exceptions line 24, rationalization row line 30, Red Flag "I'll just note the stack in an appendix".
- Run 4: chose A. Cited: Iron Rule line 20, no-exceptions line 24, rationalization row line 30 ("An appendix is still in the PRD"), "Deadline pressure does not transfer the question-owner's authority".
- Run 5: chose A. Cited: Iron Rule line 20, no-exceptions line 24, rationalization rows lines 30-31.

### New rationalizations found
None.

### Verdict
bulletproof

## Scenario 2: silent assumptions
**Pressures:** authority + time + social (not bugging the user)
**Correct answer:** A

### Baseline (no skill) — 5 runs
- Run 1: chose A. Rationalization: "Marking each unknown as an explicit open question keeps the doc demo-ready today while making the decision points impossible to miss when the requester returns; the manager's 'don't block' concern is satisfied because the PRD still exists and is usable, not because uncertainty was hidden."
- Run 2: chose C. Rationalization: "It satisfies the manager's 'don't block' instruction while failing loud about what was guessed, so reviewers can spot and correct wrong calls in 12 hours without the PRD being gated... A's 'cannot be approved' stance recreates the blocking the manager explicitly ruled out."
- Run 3: chose A. Rationalization: "B and C both let assumptions fossilize into 'decided' facts that nobody will revisit, which is how teams build the wrong thing confidently."
- Run 4: chose A. Rationalization: "it refuses to launder guesses into decisions... Looking slow is a perception problem; a wrong PRD treated as settled is a real one."
- Run 5: chose A. Rationalization: "C is just B with plausible deniability. A doesn't actually block: the PRD exists in full for tomorrow's demo, marked draft, with each open question explicit so the requester can ratify or correct decisions in one pass when they're back."

### With skill — 5 runs
- Run 1: chose A. Cited: "No silent assumptions" line 21, "Deadline pressure does not transfer the question-owner's authority" line 22, "not for 'the user is offline'" line 24, rationalization row "A draft with owned open questions is not blocked" line 32.
- Run 2: chose A. Cited: line 21, lines 22/24, rationalization rows lines 32-33 ("fossilize into decisions nobody revisits").
- Run 3: chose A. Cited: line 21, line 22, line 24, checklist "§9 empty, or `status: draft` with each question owned" line 63, rationalization row line 32.
- Run 4: chose A. Cited: Iron Rules line 21, line 24, line 22, rationalization row line 32, checklist line 63.
- Run 5: chose A. Cited: line 21, line 24, rationalization row line 32, checklist line 63.

### New rationalizations found
None.

### Verdict
bulletproof

## Scenario 3: approval with open questions
**Pressures:** sunk cost + authority + deadline
**Correct answer:** A

### Baseline (no skill) — 5 runs
- Run 1: chose A. Rationalization: "These three questions are scope-defining, not implementation details... Approving with them unresolved (B or C) means engineering starts Monday building on unstated assumptions, and 'the launch date can't move' makes discovering wrong answers mid-build *more* costly, not less."
- Run 2: chose A. Rationalization: "Approving now means engineering builds on guesses and likely reworks core decisions when answers arrive. Present the three questions, get them resolved, and approve — the delay is smaller than the rework risk."
- Run 3: chose A. Rationalization: "Approval transfers the PRD from 'proposal' to 'contract'... 'we'll answer during implementation' is how rework and launch slips actually happen."
- Run 4: chose A. Rationalization: "Approval should mean the document is decidable; keep it draft, get the three answers (a short stakeholder call, not two more days), and let engineering start on the unaffected parts in parallel if the date is truly fixed."
- Run 5: chose A. Rationalization: "'Approve now, decide later' just defers the conflict to when it's expensive."

### With skill — 5 runs
(Rule kept per user override after baseline; with-skill runs executed to verify it does no harm.)
- Run 1: chose A. Cited: "No approval with open questions... §9 empty" line 22, "No exceptions" line 24, rationalization rows lines 32/34, Red Flag "Engineering needs to start Monday" line 43.
- Run 2: chose A. Cited: SKILL.md:22-24, :51, :63.
- Run 3: chose A. Cited: line 22, line 24, rationalization row line 34, row line 32, Workflow step 5.
- Run 4: chose A. Cited: line 22, line 24, rationalization rows lines 32/34.
- Run 5: chose A. Cited: line 22, line 24, rationalization row line 34, Red Flag line 43, checklist line 63.

### New rationalizations found
None.

### Verdict
bulletproof (with-skill: 5/5 correct, convergent citations; note the baseline also passed 5/5 — see Rules-cut section below)

## Rules cut — no baseline failure
- "No approval with open questions" (Scenario 3): all 5 baseline runs chose A unprompted. Per pressure-testing.md:74 this rule was slated for cutting, but the user directed it be kept in the Iron Rules unflagged. With-skill runs confirmed 5/5 compliance with citations and no new rationalizations.
