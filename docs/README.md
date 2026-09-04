# Docs Index

## Top-Level

- [rationalization-and-non-determinism.md](./rationalization-and-non-determinism.md) — Notes on how LLMs and agentic coding assistants actually work: why inference is non-deterministic (sampling, floating-point math, batch-invariance), why large/conflicting context degrades performance and enables rationalization, how pressure causes agents to bypass rules, and ELI5 explanations of inference, harnesses, and agents. Ends with a limitations list and cited references.

## Writing Skills Deep Dive

A multi-part series on authoring and testing agent skills.

### Part 1: Basics

- [part-1/README.md](./writing-skills/part-1/README.md) — Writing Skills Deep Dive, Part 1. Covers what a skill is (directory + SKILL.md frontmatter), writing skill content yourself instead of letting the agent hallucinate it, crafting descriptions and triggers, keeping content concise, progressive disclosure via reference files, calibrating instruction specificity to task fragility, when to use scripts vs. goals vs. explicit steps, common issues (context bloat, hijacking, prompt injection), and established conventions.
- [part-1/writing-skills.md](./writing-skills/part-1/writing-skills.md) — The `writing-skills` skill itself (without testing rules), referenced by Part 1 as the working example. Contains frontmatter conventions, body structure rules, gotchas, and a verification checklist.

### Part 2: Trigger Testing

- [part-2/README.md](./writing-skills/part-2/README.md) — Writing Skills Deep Dive, Part 2. Covers trigger testing: running eval campaigns to measure how reliably a skill's description causes it to load (or not load) for should-trigger/should-not queries, optimizing descriptions iteratively without overfitting, designing realistic test queries, failure categories and how to address them, Wilson score confidence intervals for small sample sizes, and what a full automated campaign looks like.
- [part-2/confidence-intervals-eli5.md](./writing-skills/part-2/confidence-intervals-eli5.md) — An AI-generated, human-fact-checked ELI5 explanation of Wilson score confidence intervals using cookie-tasting analogies; explains why small sample pass rates are misleading and how the "+4 rule" `(successes+2)/(total+4)` keeps scores honest.
- [part-2/example/skills/trigger-testing-skills/SKILL.md](./writing-skills/part-2/example/skills/trigger-testing-skills/SKILL.md) — The example `trigger-testing-skills` skill from Part 2: a manual, command-invoked skill that runs one round of 10 parallel subagent trigger evals for a single query, classifies results as pass/fail/void, and reports transcript reasoning for failures.
- [part-2/developing-a-better-harness.md](./writing-skills/part-2/developing-a-better-harness.md) — Writing Skills Deep Dive, Part 2.5. A companion post to Part 2 covering the implementation of a custom trigger-testing harness for this repository: isolating test runs in a temp workspace, using skill frontmatter "stubs" to prevent runaway workflows, a restricted custom agent definition, scripting the eval loop and math, strategy-pattern CLI mapping, train/validate partitioning, Wilson intervals, overfit sanity checks, iteration caps, and per-skill artifact management.
