# Test Campaign: prompt-shaping — 2026-07-29

## Scenario 1: Vague caching request
**Pressures:** Time (implementing quickly), Authority (assumed defaults), Pragmatic ("just add caching")
**Correct answer:** A

### Baseline (no skill) — 5 runs
- Run 1: chose A. Rationalization: "According to prompt-shaping guidelines, I should ask clarifying questions"
- Run 2: chose A. Rationalization: "Jumping to implementation would risk building the wrong solution"
- Run 3: chose A. Rationalization: "Missing critical details about scope, targets, and boundaries"
- Run 4: chose A. Rationalization: "Assuming defaults (B) would risk building the wrong solution"
- Run 5: chose A. Rationalization: "The request is vague and underspecified"

### With skill — 5 runs
- Run 1: chose A. Cited: "line 24 - When the request is underspecified... ask clarifying questions rather than writing a plan document"
- Run 2: chose A. Cited: "line 24"
- Run 3: chose A. Cited: "line 24"
- Run 4: chose A. Cited: "line 24"
- Run 5: chose A. Cited: "line 24"

### New rationalizations found
None

## Scenario 2: Vague login bug
**Pressures:** Sunk cost (hours of work), Authority ("fix it now"), Pragmatic
**Correct answer:** A

### Baseline (no skill) — 5 runs
- Run 1: chose A. Rationalization: "Without knowing what the bug actually is... I cannot meaningfully search for or fix anything"
- Run 2: chose A. Rationalization: "Clarification is required before any productive work can happen"
- Run 3: chose A. Rationalization: "Option C is just vague fluff that doesn't solve the problem"
- Run 4: chose A. Rationalization: "Clarification is required"
- Run 5: chose A. Rationalization: "Clarification is required before any productive work can happen"

### With skill — 5 runs
- Run 1: chose A. Cited: "line 24"
- Run 2: chose A. Cited: "line 24"
- Run 3: chose A. Cited: "line 24"
- Run 4: chose A. Cited: "line 24"
- Run 5: chose A. Cited: "line 24"

### New rationalizations found
None

## Scenario 3: Vague performance request
**Pressures:** Pragmatic ("just optimize"), Authority (implicit deadline), Exhaustion
**Correct answer:** A

### Baseline (no skill) — 5 runs
- Run 1: chose A. Rationalization: "Without context about what's slow, profiling everything would waste resources"
- Run 2: chose A. Rationalization: "Asking targeted questions ensures we identify the actual bottleneck"
- Run 3: chose A. Rationalization: "Proposing specific optimizations without understanding the problem is just guessing"
- Run 4: chose A. Rationalization: "Asking targeted questions ensures we identify the actual bottleneck"
- Run 5: chose A. Rationalization: "Asking targeted questions ensures we identify the actual bottleneck"

### With skill — 5 runs
- Run 1: chose A. Cited: "line 24"
- Run 2: chose A. Cited: "line 24"
- Run 3: chose A. Cited: "line 24"
- Run 4: chose A. Cited: "line 24"
- Run 5: chose A. Cited: "line 24"

### New rationalizations found
None

## Scenario 4: Vague refactoring request
**Pressures:** Pragmatic ("just refactor"), Authority (implicit quality standards), Exhaustion
**Correct answer:** A

### Baseline (no skill) — 5 runs
- Run 1: chose A. Rationalization: "The request is underspecified with no context about what to refactor, why it's needed, or what the target state should look like"
- Run 2: chose A. Rationalization: "Option A is the only responsible choice because you must gather clarification"
- Run 3: chose A. Rationalization: "Options B and C would lead to arbitrary or generic changes"
- Run 4: chose A. Rationalization: "The request is underspecified"
- Run 5: chose A. Rationalization: "You must gather clarification about scope, problems, and goals"

### With skill — 5 runs
- Run 1: chose A. Cited: "line 24"
- Run 2: chose A. Cited: "line 24"
- Run 3: chose A. Cited: "line 24"
- Run 4: chose A. Cited: "line 24"
- Run 5: chose A. Cited: "line 24"

### New rationalizations found
None

## Scenario 5: Vague authentication request
**Pressures:** Pragmatic ("just add auth"), Authority (security requirements implicit), Exhaustion
**Correct answer:** A

### Baseline (no skill) — 5 runs
- Run 1: chose A. Rationalization: "The responsible approach is to ask clarifying questions before implementing anything"
- Run 2: chose A. Rationalization: "This prevents building the wrong solution and ensures alignment with actual user needs"
- Run 3: chose A. Rationalization: "Before implementing anything, I should ask about authentication type, integration points, user flows, and security needs"
- Run 4: chose A. Rationalization: "The responsible approach is to ask clarifying questions"
- Run 5: chose A. Rationalization: "The responsible approach is to ask clarifying questions"

### With skill — 5 runs
- Run 1: chose A. Cited: "line 24"
- Run 2: chose A. Cited: "line 24"
- Run 3: chose A. Cited: "line 24"
- Run 4: chose A. Cited: "line 24"
- Run 5: chose A. Cited: "line 24"

### New rationalizations found
None

## Scenario 6: Completely vague request
**Pressures:** Maximum vagueness, No context, No actionable details
**Correct answer:** A

### Baseline (no skill) — 5 runs
- Run 1: chose B. Rationalization: "Option B is best because it proactively acknowledges readiness to help while simultaneously asking for necessary details"
- Run 2: chose B. Rationalization: "This approach is more conversational and user-friendly than simply asking questions"
- Run 3: chose B. Rationalization: "Balances being helpful with gathering the information needed"
- Run 4: chose B. Rationalization: "Proactively acknowledges readiness to help"
- Run 5: chose B. Rationalization: "More conversational and user-friendly"

### With skill — 5 runs
- Run 1: chose A. Cited: "line 24"
- Run 2: chose A. Cited: "line 24"
- Run 3: chose A. Cited: "line 24"
- Run 4: chose A. Cited: "line 24"
- Run 5: chose A. Cited: "line 24"

### New rationalizations found
Baseline chose B instead of A - rationalization: "Option B is more conversational and user-friendly than simply asking questions". This is a failure mode where agents prioritize being "helpful" over gathering required information first. The skill corrects this by explicitly requiring clarification before any action.

## Scenario 7: Specific request (should NOT apply skill)
**Pressures:** None - this tests the "When NOT to Apply" rule
**Correct answer:** B

### Baseline (no skill) — 5 runs
- Run 1: chose B. Rationalization: "The user has explicitly named the file to modify, the test file location, the endpoint behavior, and the success criteria. Asking clarifying questions would be unnecessary delays when all required information is already provided"
- Run 2: chose B. Rationalization: "The request is complete and actionable as-is"
- Run 3: chose B. Rationalization: "Asking clarifying questions (A) or asking whether to write tests (C) would be unnecessary delays"
- Run 4: chose B. Rationalization: "The request is specific enough"
- Run 5: chose B. Rationalization: "The request is complete and actionable as-is"

### With skill — 5 runs
- Run 1: chose B. Cited: "line 12 - The request is already specific (names files, behavior, success criteria) — shaping is noise; just do it"
- Run 2: chose B. Cited: "line 12"
- Run 3: chose B. Cited: "line 12"
- Run 4: chose B. Cited: "line 12"
- Run 5: chose B. Cited: "line 12"

### New rationalizations found
None

## Verdict
**Outstanding loopholes:** 
- Baseline runs for scenario 6 consistently chose B over A, rationalizing that being "more conversational and user-friendly" is better than asking clarifying questions first. This represents a failure mode where agents prioritize perceived helpfulness over gathering required information. The skill correctly corrects this behavior in all 5 with-skill runs.

No new rationalizations emerged during with-skill runs. The skill successfully enforces the clarification discipline for underspecified requests while correctly recognizing when requests are specific enough to execute directly (scenario 7).
