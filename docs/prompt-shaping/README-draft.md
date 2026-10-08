Properties of a good prompt shaping system:
- Cheap misalignment. State the interpretation before executing, so being wrong costs a sentence, not an implementation. Cost asymmetry is the core principle.
- A decision boundary. Know when not to shape — already-specific requests, informational asks, and post-correction execution should bypass the loop entirely.
- Grounding before proposing. Scan the environment for unstated constraints and reasonable defaults rather than interviewing the user about things the codebase already answers.
- Explicit assumptions, elicited non-goals. Out-of-scope and assumptions are first-class fields, not afterthoughts.
- A convergence artifact. The dialogue terminates in a copyable spec (goal / scope / assumptions / success criteria) that downstream artifacts can quote verbatim.
- Executable verification. Success criteria resolve to a concrete check (test, command, assertion), and the loop terminates when the check passes — “tests are truth,” not belief.
- Technique-to-model matching. Specificity, few-shot, CoT, decomposition are not universally good; they have context/latency costs and are model-specific. A good system selects techniques conditionally.
- Iteration as measurement, not faith. You can’t reason your way to the right phrasing — prompts are brittle (word order, example ordering swing accuracy by tens of points), so shaping is a design loop with a control group, not a one-shot edit.

--

CoT and distilling:

https://arxiv.org/html/2608.09867v1

cot reasoning traces from frontier models are encrypted, and the client just hands the encrypted blocks back, along with the rest of the message, on each turn. what you read in the 'thinking' output is heavily summarized or redacted output that comes along with the response, separate from the encrypted blocks.

the flaw: these encrypted blocks are fully compatible and interchangeable across sessions, users, and even different models from the same provider ecosystem. by extracting the thinking trace signatures from opus to haiku, and asking it to output it's own reasoning, haiku will effectively decode and print the encrypted thinking traces.

this mostly works because models like haiku or gpt-5.6 luna are designed as fast, cost-effective tools and they do not have all the safeguards and refusal mechanics that the large models have (so probably this won't last forever).

it also means that someone could get a hold of your session data and use the encrypted blocks to read your proprietary information from the traces.
