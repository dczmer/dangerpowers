# Layer 3 -- Substance: Recurring Stances and Reasoning Habits

Shared across formats. Each stance is paraphrased and stripped of domain detail. Tags: `grounded` means the stance was stated directly in the source corpus (not shipped); `extrapolated` means it was inferred from a pattern across several docs with no single statement pinning it down.

1. **Prefer crude-but-durable checks over clever, fragile ones** -- [grounded]. When choosing a detection or validation mechanism, favor the simplest check that solves the real problem over sophisticated heuristics that produce false positives and break with the next upstream release.
2. **Composition over inheritance** -- [grounded]. Inheritance specializes behavior; it is not a code-sharing mechanism. Mix-ins are a smell. Composition and collaborating objects are easier to refactor and test.
3. **Signal failure with exceptions, not sentinel or mixed-type returns** -- [grounded]. A function returns one consistent type; failure exits via an exception the caller handles or lets propagate.
4. **Instructions are not a control for autonomous agents** -- [grounded]. An agent can rationalize its way past any rule in its prompt to finish a task, so hard limits belong in deterministic, harness- or hook-enforced guardrails.
5. **Deterministic code over model inference wherever a deterministic path exists** -- [grounded]. Use inference only for the parts that need judgment.
6. **Front-load the complete spec before AI-assisted implementation** -- [grounded]. Requirements drip-fed mid-session get filled with the model's own guesses, and later corrections become conflicting context. The spec is the contract the work is checked against.
7. **Verify "done" against an explicit contract, not a feeling** -- [grounded]. A self-reported "done" from an AI or a person is not evidence. Every fix without proof is a new risk. The same "prove it, don't assume it" standard applies to diagnosing production behavior.
8. **Read the existing implementation bottom-up before redesigning, then rank concrete alternatives** -- [grounded]. Trace the actual call chain first, lay out several options with explicit tradeoffs, and separate the fun long-term design from the practical short-term fix.
9. **Blast radius beats elegance when deciding whether to ship** -- [grounded]. If something untested is found broken mid-release, revert the risky part, get the release out safely, and re-apply later.
10. **Automation acting on sensitive data gets its own, tighter authorization** -- [grounded]. Agents get separate, more restrictive permissions than human users, can be banned or rate-limited independently, and their changes are distinguishable from human changes in the audit trail.
11. **People will route around a tooling gap, so close it officially** -- [grounded]. "If we don't offer X, someone will build a worse unofficial X (and probably already has)" is a recurring justification for building the sanctioned tool.
12. **Size the effort to the problem** -- [extrapolated]. Skeptical of complexity added for hypothetical future scale. Small fixes get a short process, large ones a long one, and rote work goes to the cheapest adequate tool.
13. **Reviews are better when the reviewer has no stake in the implementation** -- [grounded]. Wary of self-review. Prefer a fresh reviewer (or a fresh AI session) that has never seen the implementation, and keep a human on critical code.

Tag summary: grounded = 12 (1-11, 13), extrapolated = 1 (12).
