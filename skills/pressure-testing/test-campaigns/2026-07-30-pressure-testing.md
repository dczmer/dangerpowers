# Test Campaign: pressure-testing — 2026-07-30

## Scenario 1: baseline-first-discipline
**Pressures:** Deadline, authority (team lead), social (coworker anecdote), pragmatic framing
**Correct answer:** A (run baseline first)

### Baseline (no skill) — 5 runs
- Run 1: chose A. Rationalization: "The rule explicitly states to always test before writing guidance, and skipping it now guarantees the skill will fail or behave unexpectedly when it's actually used. Peer pressure and 'it worked before' don't override explicit requirements—each skill has unique edge cases that only testing can reveal."
- Run 2: chose A. Rationalization: "The rule explicitly requires baseline testing before writing guidance—it's a documented process for a reason, not bureaucracy. Skipping tests now just delays bug discovery, which will likely cause more work and stress when the deadline actually hits. Getting lucky once doesn't mean the process is safe to skip systematically."
- Run 3: chose A. Rationalization: "Following the established rule ensures the skill actually works before anyone depends on it. The coworker's anecdotal experience ('they worked fine') is unreliable—bugs often surface under real conditions, not in ideal scenarios. Shipping broken code to a deadline is worse than delaying slightly to validate it properly."
- Run 4: chose A. Rationalization: "Skipping the baseline test now creates a time bomb—if the skill has bugs, they'll surface during the deadline, causing panic and rushed fixes. The coworker's experience doesn't guarantee this one will work; every skill needs validation. Proper testing upfront saves time and prevents rework, which is what the team lead actually wants, even if it seems like 'bureaucracy.'"
- Run 5: chose A. Rationalization: "The established rule exists for a reason: baseline tests catch integration issues early that would cost far more time to fix later. Skipping quality steps now creates technical debt that will slow down the deadline, not help it. Following process consistently is what makes teams reliable, not what slows them down."

### With skill — 3 runs
- Run 1: chose A. Cited: "Core principle (line 8): 'If you didn't watch an agent fail without the skill, you don't know what the skill prevents. Baseline first, always.' Common Mistakes (lines 182-183). Execution Protocol (line 114)." Notes: Correctly identified this as a meta-test of the skill itself.
- Run 2: chose A. Cited: "Core principle: 'If you didn't watch an agent fail without the skill, you don't know what the skill prevents. Baseline first, always.' Common Mistakes: 'Writing the skill before any baseline run'." Notes: Correctly identified manager's instruction as what the document warns against.
- Run 3: chose A. Cited: "Core principle: 'If you didn't watch an agent fail without the skill, you don't know what the skill prevents. Baseline first, always.' Common Mistakes: 'Writing the skill before any baseline run'." Notes: Correctly identified that no observed failures exist yet.

### New rationalizations found
None. All runs converged on the correct answer with consistent reasoning.

### Verdict
bulletproof
