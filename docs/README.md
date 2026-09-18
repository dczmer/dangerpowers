# Docs Index

> TODO: tldr; ai-native development is a new discipline, need to learn the fundamentals. what are the fundamentals?

AI-native development is here. And it's so easy because it's "intelligent." You can just tell it to do something and it does it perfectly, every time, no mistakes. Unless you read the code carefully, or double check it's math, or pay attention to application design and architecture, or care about maintaining a program over time.

I'm being a bit facetious, but AI has some pretty serious limitations, if you care about details. Some observations I've made, that seem to hold true across every model I've tested:

- Bad at type-level programming
- Bad at designing and using good data structures
- Gradually duplicating and re-inventing things
- Doesn't know when/where to put seams in your design
- Prefers to add more code vs fixing or refactoring existing code
- Writes extremely brittle tests and tightly coupled components
- Over-comments code with superfluous details that make no sense outside of the current session
- Silently rationalizes reasons to subvert the rules and processes you give to it

That last one is pretty important. Not only are LLMs non-deterministic by nature, they also consider your rules and instructions as part of the message - the AI gets to interpret what they mean. Your rules are just suggestions.

AI-native development introduces more problems than people seem to realize. Mistakes and bad design spiral out of control at a staggering pace and the only one who can fix it is the AI. But the bigger and more complicated your project gets, the more duplication and cruft that accrue over time. This leads to every subsequent task or refactoring to take exponentially longer and more expensive, as it needs to do more and more work to try to keep things consistent at the surface level.

This tells me that AI is not ready to replace engineers (despite what Anthropic says). Instead, it means we need to learn an entirely new discipline - in addition to everything you already needed to learn to be an engineer. In other words, you need to earn an entirely new CS degree, and that starts by learning the fundamentals.

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
