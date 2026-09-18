# Docs Index

## Writing Skills Deep Dive

Skills are the primary mechanism for extending a model's capabilities. But agents frequently break the rules - try running some evals, you might be surprised how unreliable it can be. This is especially important if you intend to deploy agents to production systems, it is critical that they work as consistently as possible. 

How do you write an effective skill? How do you harden skills so the agents don't break the rules? Why do they break the rules in the first place? Answering these questions gives insight into how LLMs and agents work. That insight translates to updated mental models and changes how you think about applying AI - where it makes sense, and where it's not always the best solution.

### Part 1: Basics

[part-1/README.md](./writing-skills/part-1/README.md) — **Writing Skills Deep Dive, Part 1**. Covers the basics of how skills work, crafting descriptions and triggers, keeping content concise, progressive disclosure via reference files, calibrating instruction specificity to task fragility, when to use scripts vs. goals vs. explicit steps, common issues (context bloat, hijacking, prompt injection), and established conventions.

Supplementary:
* [rationalization-and-non-determinism.md](./writing-skills/part-1/rationalization-and-non-determinism.md) — Notes on how LLMs and agentic coding assistants actually work: why inference is non-deterministic (sampling, floating-point math, batch-invariance), why large/conflicting context degrades performance and enables rationalization, how pressure causes agents to bypass rules, and ELI5 explanations of inference, harnesses, and agents.
* [part-1/writing-skills.md](./writing-skills/part-1/writing-skills.md) — The simplified example `writing-skills` skill from Part 1.

### Part 2: Trigger Testing

[part-2/README.md](./writing-skills/part-2/README.md) — **Writing Skills Deep Dive, Part 2**. Covers trigger testing: running eval campaigns to measure how reliably a skill's description causes it to load (or not load), optimizing descriptions iteratively without overfitting, designing realistic test queries, failure categories and how to address them.

Supplementary
* [part-2/developing-a-better-harness.md](./writing-skills/part-2/developing-a-better-harness.md) — **Writing Skills Deep Dive, Part 2.5**. A companion post to Part 2 covering the implementation of a custom trigger-testing harness for this repository: isolating test runs in a temp workspace, using skill frontmatter "stubs" to prevent runaway workflows, a restricted custom agent definition, scripting the eval loop and math, strategy-pattern CLI mapping, train/validate partitioning, Wilson intervals, overfit sanity checks, iteration caps, and per-skill artifact management.
* [part-2/confidence-intervals-eli5.md](./writing-skills/part-2/confidence-intervals-eli5.md) — An AI-generated, ELI5 explanation of Wilson score confidence intervals using cookie-tasting analogies; explains why small sample pass rates are misleading and how the "+4 rule" keeps scores honest. Useful because our evals use relatively small sample sizes.
* [part-2/example/skills/trigger-testing-skills/SKILL.md](./writing-skills/part-2/example/skills/trigger-testing-skills/SKILL.md) — The example `trigger-testing-skills` skill from Part 2: runs one round of parallel subagent trigger evals for a single query, classifies results as pass/fail/void, and reports transcript reasoning for failures.
