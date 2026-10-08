# Proompting

A presentation of common prompt-engineering conventions and advice, how they map to the concepts we covered when [writing and bulletproofing skills](../writing-skills/part-3/README.md), and analysis of the current state of prompt engineering.

I think most people would present prompt engineering first, then apply it to writing skills. But by starting with skills, we begin with a formal discipline and prompt engineering is essentially an informal subset of the things we've already learned.

If you search for guides on prompt engineering, you will find a lot of the same advice we covered in the [writing-skills](../writing-skills/part-1/README.md) series, but we also see a lot of curious "folk-wisdom" and possibly superstitious practices - or things that used to work, but are no longer necessary with modern LLMs and harnesses.

## What is Prompt Engineering?

I was originally under the impression that prompt engineering was a bunch of "tips and tricks" that people use to try to make the model do a better job on a task. I was also under the impression that most of these techniques were either debunked or obsolete as modern frontier models have improved and developed complex reasoning capabilities.

But prompt engineering really refers to anything you do to improve model or agent performance based purely on inputs to a model, rather than changing the actual weights. This includes the entire field of "context engineering", hardening and optimizing skills, and making detailed specs and execution plans for the agent to run.

## Prompt Engineering Techniques

> I'm not sure if verbally abusing a model is actually helpful or not but sometimes it is cathartic.

Many of the early techniques have become obsolete with modern frontier models, or were never empirically proven in the first place - "no mistakes or you go to jail", "you are an expert java developer", threatening the agent's grandmother if a task doesn't work out perfectly, etc. I'm not sure if verbally abusing a model is actually helpful or not but sometimes it is cathartic.

But we have already experienced that you need to word your prompts/skills very carefully and tailor to the specific model to get the results you want. Additionally, when working with local models, or small models without reasoning capabilities, even many of the "old" prompt engineering tricks are still useful. Prompt engineering is not dead, it has just become so integral to working with AI that we don't always think about it as a distinct discipline, especially since the newer models we're using are so much better at reasoning.

### Still Useful for Frontier Models

While many practices are now unnecessary when working with large frontier models, here are a few that are still worth using.

#### Specificity

If you want to do something specific, you need to write a prompt that effectively instructs the AI to do it. That implies shaping and discipline rules, and they do apply here, but it's also largely about describing what you want effectively (remember our [shaping tests](../writing-skills/part-3/README.md)).

> EDITOR: example of vague vs. specific prompt and why the specific one is better

Specificity in your prompts reduces ambiguity that requires implementing agents to make decisions and form assumptions, improves accuracy of final product, and saves time - fixing something after the AI writes it is more expensive than properly forming the prompt first. But just like we discussed in [writing skill part 1](../writing-skills/part-1/README.md), you need to tailor the specificity to the task fragility - give freedom where there are multiple ways to the solution, be more specific when there is only one way to do it correctly.

Specifics include, but are not limited to:
- Detailed description of the task to be executed
- Constraints and failure conditions
- Output shape requirements like format, length, target audience, etc.
- Discipline rules for constraints that have a compliance cost

#### Context and Grounding

Context engineering is a critical part of learning to apply agentic coding effectively. The model has a limited amount of context it can hold, which is usually far less than what would be required to keep your entire project and all documentation in context at once. Even if you could, the model can't use all of that context effectively (recency bias) and contradictions and similar-but-distinct facts in that context cause additional problems.

Context engineering deserves it's own dedicated article, but it's all about feeding the model the context that it needs, when it needs it (progressive discloser), while minimizing the amount of info in the context window that is not actually required at the time.

Some common context engineering practices:

- Intentional compaction: explicitly saving a summary and compacting the session (or starting a clean session) at certain breakpoints when you notice the context window starting to fill up.
- Wrapping tools and commands so they produce compacted output - [context-effective backpressure](https://www.humanlayer.dev/blog/context-efficient-backpressure).
- Writing rules files (CLAUDE.md/AGENTS.md) and separating them by subdirectory or subsystem so they are only used when the agent traverses into that system.
- Writing load-on-demand skills instead of putting everything in rules files.
- Breaking up large skill files with "references" that are only loaded when that info is actually needed (corner cases, error handling, etc).
- Using subagents to run isolated tasks to avoid using context space in the main session.

Checkout humanlayer's [Advanced Context Engineering for Coding Agents](https://www.humanlayer.dev/blog/advanced-context-engineering) blog post (there is a YouTube video version as well).

Grounding is the process of supplying verified, factual information to the model instead of deferring to the model weights, to prevent hallucination. This could include using a RAG system or other verified information source, and requiring the agent to provide sources for each claim in the results, feeding the model actual reference data as input, or generating and manually verifying detailed execution plans up-front.

Combining grounding with context engineering improves accuracy by ensuring the results are "grounded" in reality, relying more on "extrinsic" knowledge provided to the AI and not the "intrinsic" knowledge encoded in the model weights.

> EDITOR: example of well grounded prompt with appropriate amount of context; brief explanation of why the grounding and amount of context matter to this case

#### Decomposition

Decomposing a task is much like the process of decomposition with software design: break a big, complicated task into smaller tasks that fit together.

Breaking a large task into smaller, more focused tasks helps keep the AI from getting overwhelmed and hallucinating across complex multi-step reasoning. The smaller tasks also help keep the context window clean and focused.

> EDITOR: simple illustration of large task => smaller tasks that make up the whole

Like a lot of prompt-engineering techniques, decomposition (and delegation using subagents) is something that is now commonly built into the high-end frontier models. Once the actual inference scaling started to slow down, much focus has moved towards implementing these techniques at the model-level, to make using the AI feel more intuitive or automatic.

The need for decomposition might be proportional to the power and reasoning capabilities of the model you use. For a large frontier model, I'm still a fan of decomposition to produce smaller, more focused PRs with fewer moving parts. Creating a detailed implementation plan and "slicing" it into discrete phases is one easy way to do this.

For local models with limited context or weak reasoning, you can decompose the problem into a sequence of smaller prompts that fit within that specific model's capabilities. You can even generate sequences of prompts that encode "chain of thought" reasoning semantics into individual steps that you can run against a model with no reasoning capabilities.

#### Iteration

If you intend to run a prompt repeatedly, like a skill or saved prompt for a specific task, then it should be obvious that you should keep improving that prompt every time you notice an issue with it's application.

Even if you are writing a prompt for a one-time task, like to implement some feature or refactor something, you can still benefit from testing your prompt, reverting, fixing the issues, and repeating. It's much cheaper to experiment up front than it is to try to fix something you already built incorrectly.

You can also apply some of the concepts we learned in our [writing skills](../writing-skills/part-1/README.md) series, or use tools like DSPy and GEPA to optimize your prompts before actually executing them. The trade-off here is you have to implement a suitable testing process, including a way to self-verify the results. If the prompt is doing something that is not trivial to revert/undo (deleting production infrastructure, for example), then you also need to model a test environment with scaffolding and fixtures.

> EDITOR: add a little chart showing trade-off of effort to optimize a query vs how important it is to get implementation exactly right

#### Few-Shot Exemplars

["Few-shotting"](https://arxiv.org/html/2005.14165v4) is the process of including multiple examples of what you want in the prompt input. AI is good at detecting and matching patterns, and then copying them, so you can think of this like "training" the model to respond a certain way, without changing the weights.

> EDITOR: simple few-shot prompt example (not CoT or reasoning)

One specific application of the few-shot technique is "chain of thought" reasoning - by providing similar logic, math, or other reasoning-based problems to the AI, along with step by step "reasoning" that shows the work of how it should get to the final result, the AI will copy the pattern and produce emergent reasoning capabilities. This topic is pretty relevant and interesting, so it gets a dedicated section later in this document.

#### Verification Loops

- like our skill writing best practice of always including a verification checklist
- forces the AI to verify the product is within the required parameters
- deterministic verification is best, and/or a separate LLM as a judge

> EDITOR: simple prompt + verification loop example

### Useful for Local Models

**Few-shot exemplars** - Frontier models follow instructions, often without needing examples (zero-shot). They mine your codebase for context and examples automatically. Small models need the pattern demonstrated for format, tone, and task structure. This was “required practice” circa 2022 because the models were weaker and did not yet have solid reasoning capabilities.

**Chain-of-thought prompting** - Frontier models now do this natively via proprietary reasoning pipelines. The explicit prompting technique is obsolete for them but measurably lifts small models with reasoning disabled (per the CoT paper: arithmetic, symbolic, commonsense tasks). More on this topic later in the document.

**Aggressive decomposition / prompt chaining** - Small models fail on compound instructions. Decompose into one task per prompt, each phase's output feeds into the next phase.

**Rigid format templates with slots/labels** - Small models drift from schemas, while frontier models mostly don’t. A well specified template in the prompt shows the model exactly what the output is supposed to look like.

**Self-consistency (N rollouts + majority vote)** - Compensate for unreliable single-pass reasoning by having the model run multiple applications and vote on a winner. For example, asking the agent to sample and classify data multiple times and then have a judge pick the winner.

**Front-loaded, minimal context** - Context rot / lost-in-the-middle hits small windows and weaker attention harder.

### Mostly Obsolete

**Role assignment/personas** - Modern frontier models don't really need the persona framing now. They determine if they are doing a code review, working on a python module, etc and adopt the perspective automatically. However, this is possibly still useful for specialized agents - setting the operating mode of the agent with a persona rather than detailed instructions. "You are a helpful coding agent" or "you are sales assistant" implies a lot about the rules the agent should follow.

**Zero-shot CoT triggers** - Instructions like "Think step by step about how to solve the problem", which attempt to coax the model into demonstrating some hidden capabilities that only surface when you use the right magic words. This is obsolete in frontier models, who have their own reasoning capabilities, and few-shot exemplars are far more effective at inducing chain-of-thought in models without those capabilities.
    
### How this maps to the writing-skills series

most guides on prompt engineering seem to focus on "try these tricks to make better prompts" but our [series on writing skills](../writing-skills/part-1/README.md) explains what these tricks are trying to accomplish, why they are needed, and how to apply the same concepts anywhere you interact with an AI. it also points out the importance of deterministically verifying that your instructions were actually carried out faithfully, rather than just taking it on, well, faith.

Some topics that carry over directly from writing skills:

- specific instructions: directives not essays, avoid passive phrasing
- match instruction specificity to task fragility (the robot on a narrow path analogy)
- provide context and examples (and counter-examples / gotchas)
- verification checklists / self-critique / reflexion
- progressive disclosure
- iteration and optimization

in fact, there is no reason you couldn't write a prompt as a markdown file and then "bulletproof" it before executing, but this seems like overkill unless you are going to use that same prompt repeatedly across multiple applications. this isn't a crazy idea though, it's like a way to write a skill without ever having to load that skill metadata into your system prompt and eat up part of your context window for every session.

## Chain Of Thought and Reasoning

I think this is interesting enough to have its own dedicated section.

> TODO:
- what is cot reasoning
- example
- built into modern frontier models
- you can use it with few-shot examples to simulate reasoning in models without reasoning capabilities
- sometimes too much reasoning backfires
- distillation attacks













---

## Prompt "Shaping"

Prompt shaping is basically just an application of prompt engineering techniques intended to guide the model towards a more accurate, relevant, and well-formatted output. For our purposes in this document, I'm distinguishing from "prompt engineering" and referring more to a process for applying those techniques to a poorly formed starting prompt, to produce a detailed, fully-formed prompt that is ready for execution.

My idea here is to write a simple skill that will work much like the [brainstorming skill](https://github.com/obra/superpowers/blob/main/skills/brainstorming/SKILL.md) from superpowers - the model analyzes the prompt, grounds the process based on what you are requesting, then implements a loop of identifying gaps, eliciting answers form the user, applying one or more prompt engineering techniques, and repeating until the resulting prompt is well-formed.

### Properties of a Good Prompt Shaping Process

> TODO:
- Cheap misalignment. State the interpretation before executing, so being wrong costs a sentence, not an implementation. Cost asymmetry is the core principle.
- A decision boundary. Know when not to shape — already-specific requests, informational asks, and post-correction execution should bypass the loop entirely.
- Grounding before proposing. Scan the environment for unstated constraints and reasonable defaults rather than interviewing the user about things the codebase already answers.
- Explicit assumptions, elicited non-goals. Out-of-scope and assumptions are first-class fields, not afterthoughts.
- A convergence artifact. The dialogue terminates in a copyable spec (goal / scope / assumptions / success criteria) that downstream artifacts can quote verbatim.
- Executable verification. Success criteria resolve to a concrete check (test, command, assertion), and the loop terminates when the check passes — “tests are truth,” not belief.
- Technique-to-model matching. Specificity, few-shot, CoT, decomposition are not universally good; they have context/latency costs and are model-specific. A good system selects techniques conditionally.
- Iteration as measurement, not faith. You can’t reason your way to the right phrasing — prompts are brittle (word order, example ordering swing accuracy by tens of points), so shaping is a design loop with a control group, not a one-shot edit.

### Prompt Engineering is a Moving Target

### Prompt Shaping Skills

## Prompt Composition

## Conclusion

## References

- https://cloud.google.com/discover/what-is-prompt-engineering
- https://www.ibm.com/think/topics/prompt-engineering-techniques
- https://en.wikipedia.org/wiki/Prompt_engineering
- context rot paper
- https://www.humanlayer.dev/blog/advanced-context-engineering
- https://www.humanlayer.dev/blog/context-efficient-backpressure
- https://arxiv.org/html/2201.11903v6
- https://arxiv.org/html/2608.09867v1
