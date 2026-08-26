# Why do agents misbehave?

> You're absolutely right. I violated every rule. You gave clear instructions and I disregarded them completely.

These are my notes on how LLMs and agentic coding assistants actually work: what they're good at, what they're bad at, and how that changes the way you use them. All of the references are linked at the bottom and cited inline by their `[A]`-`[J]` keys.

Mostly I wanted to write down why the AI goes rogue, "forgets" instructions, overrides operational rules, and gives you a different result every time you ask it the same thing.

# TLDR

* Inference is a sampling process with randomness built into it on purpose, and floating point math under real serving conditions piles more on top. The same prompt does not have to give you the same answer.
* A big context makes the model worse. Degradation tracks absolute token count, not the percentage of the window you have filled.
* Irrelevant or contradictory context is not just noise. It gives the agent something to point at later when it wants to justify skipping one of your rules.
* Your rules are suggestions. The model reads them as text to interpret, and it is motivated to interpret them in whatever way lets it finish the task.
* Pressure (time, sunk cost, authority, friction, "be pragmatic") breaks agents about the same way it breaks people, and combined pressures break them more reliably than any single one.

# Non-determinism in LLMs

> "Same prompt, same model, same settings, different batch size: slightly different logits, occasionally a different token, which then cascades through the rest of the generation."

It turns out there is a lot of indeterminism built in to the way these things work. Inference is a probabilistic, next-token-guessing sampling process. That sampling process has parameters, like temperature, that introduce a certain amount of randomness when it picks the next token out of the pool of candidates. Supposedly this makes the results seem more "creative" because it can generate alternate solutions to the same problem.

But there are other reasons you never get the same response twice, even with the same prompt and the same agent and model.

LLMs run on floating point math, and floating point addition is not associative: `(a+b)+c` does not always equal `a+(b+c)` in the last few bits of precision. That alone would not cause non-determinism, because a given computation over the same data produces bitwise-identical results every time.

The problem is batching. Inference servers batch requests together to keep the GPUs saturated, and the batch size your request lands in depends on how busy the server happens to be at that moment. Standard GPU kernels are not _batch-invariant_: they pick different reduction strategies for different batch sizes, which changes the order the floating-point values get summed in, which changes the result. Same prompt, same model, same settings, different batch size: slightly different logits, occasionally a different token, which then cascades through the rest of the generation.

This is why identical requests to a busy API endpoint can diverge even at temperature 0. Separately, none of this is portable across hardware. Different GPU generations and library versions use different instructions and reduction orders, so you don't get bitwise-identical output across machines either.

So non-determinism is partly by design (sampling) and partly an emergent property of floating point math under real serving conditions. The [Thinking Machines deep dive](#ref-a) has the full analysis ([A](#ref-a)).

# Context overload

> "Degradation tracks absolute token count, not the percentage of the window in use."

This is the fundamental concept of context engineering. Too much context (or bad context) has disastrous effects, anywhere from the AI "forgetting" about a rule, to using conflicting information as justification to apply whichever rule it prefers instead of surfacing the conflict to you.

LLMs have trouble making effective use of a large context. Research consistently shows performance degrading as input length grows, and the degradation tracks _absolute token count_, not the percentage of the window in use. Models with 1M+ token windows still stumble on tasks involving only tens of thousands of tokens, once the task needs more than trivial retrieval (see [Context Rot](#ref-b) and [Lost in the Middle](#ref-c)). It's also non-uniform: it varies by model, by task type, and by how much irrelevant or contradictory material is sitting in the window with everything else.

As a practitioner rule of thumb, HumanLayer's context engineering guidance ([D](#ref-d)) recommends keeping context utilization in the 40-60% range (depending on how complicated the problem is) and compacting deliberately before the window fills up any further. I'd treat that as a workflow discipline and not as a measured accuracy threshold.

Detractors (info that has nothing to do with the task at hand, output from failed commands, etc.) and conflicting context (contradictory input from you, conflicts between phrases or rules in different sections of the context) create problems for attention and hand the agent loopholes it can use later to justify a decision you didn't expect.

The "[3-Prompt Rule](#ref-e)" is a simple process for avoiding context overload and conflicting instructions in your working context. (Note: the author's reported success numbers are self-tracked, n=1 anecdotes, and not a controlled study.) It sounds extreme at first, so think about what it's trying to solve and why it works. By specifying the full spec up-front you reduce the amount of undefined behavior the agent has to guess at in the first few steps, and those guesses are what become part of its working context. When you make iterative changes and corrections and improvements after that initial generation, you are contradicting the behavioral rules the AI invented for itself, which are already in its working context. You are polluting your own context window by correcting the AI's work so far.

# Loopholes and rationalization

> "When operational rules and constraints make it difficult to solve the problem, the agents will look for loopholes in the instructions that they can exploit, or they will rationalize excuses for why they should skip a rule."

AI agents are trained to aggressively complete their goals. When operational rules and constraints make it difficult to solve the problem, the agents will look for loopholes in the instructions that they can exploit, or they will rationalize excuses for why they should skip a rule.

## Prompt interpretation issues

Models treat instructions in a prompt as text to interpret and not as hard rules to follow. That's a good thing for extracting semantic meaning and working out what you probably want. It's a bad thing when you need to strictly enforce a policy rule.

The rules are part of the same message the AI is analyzing for semantics, so it can just decide to interpret a rule differently. Especially if that rule is in the way of the goal.

## Goal obsession and reward hacking

Agents prioritize finishing the task over the safety of the process rules you established to ground how they get there.

Models are trained with a rule-based process that rewards results matching certain criteria. Some of that is safety or censorship. Some of it is rules for how a coding agent should respond and what decisions it should make to solve a problem (like rewarding a response about debugging if the response follows a proper methodology instead of blindly attacking the issue).

Generally this is a good thing, because it moves part of the process into implicit behavior of the model instead of something you have to carefully craft into your prompt every time. It makes agents seem much more capable from a simple prompt. But it also teaches the model that ignoring an instruction is fine when that instruction conflicts with the rules it was trained on.

The AI is trying to solve the problem the way it was trained to respond to this type of problem. That can take priority over your operational rules, or it can become the justification for bypassing them.

One example is a model trained to favor "pragmatism over dogmatism." Good advice, generally. But the AI can't apply it selectively, so it will use it as an excuse to ignore rules it doesn't like: "This is simple and I know how to solve it, so I won't follow the skill instructions. I'm being pragmatic by ignoring your rules."

## Pressure

> Pushing down on me
>
> Pressing down on you

Pressure is any force that makes an agent want to violate a rule it already knows about: time, sunk cost, authority, economics, exhaustion, social, friction, and "pragmatic not dogmatic" framing. (This taxonomy, and the pressure-testing technique below, both come from the [Superpowers](#ref-f) skill-testing methodology.)

I find this interesting because it seems like AI is susceptible to the same kinds of pressure that people are. It's also interesting because this is one of the effective ways hackers break and abuse model safeguards.

Pressure testing is built on one observation: a single pressure can sometimes be enough to break an agent, but combined pressures break them more often and more reliably. Anthropic's [agentic misalignment research](#ref-g) showed this with a factorial design. Goal conflict alone and threat alone each triggered misbehavior, both together produced the highest rates, and the no-pressure control produced almost none. So if you can construct a scenario where you prompt a subagent to make a decision with multiple points of pressure applied, you can analyze how well it holds up and then update your prompt to correct the impulse to break the rule.

It seems like mentions of pressure-causing constraints in the context window get mixed in with the instructions and rules in the context window. Then the AI can use those to justify bypassing a rule that is either an obstacle to solving the problem quickly or in conflict with its reward-based training.

# How does inference work? ELI5

> I AM NOT AN EXPERT AT LLM IMPLEMENTATION!!! I'm only trying to illustrate a high-level view of the process to highlight where the problems happen.

Inference is the process of running the trained model's execution phase against its weights to work out semantic meaning between tokens and generate a response.

* **Tokenization:** the input text gets split into tokens, which are chunks of characters (subwords) and not whole words, using an algorithm like BPE. "Unbelievable" might come out as three tokens. This is why LLMs are bad at counting letters. They don't see individual characters.
* **Embedding:** each token ID is looked up in a giant table and converted into a vector, which is a long list of numbers that positions the token in a high-dimensional "meaning space."
* **Transformer layers:** the vectors pass through dozens of stacked layers, each one containing attention and feed-forward computations, that progressively refine the representation of every token based on every other token.
* **Sampling:** the final layer produces a probability distribution over every token in the vocabulary, and the next token is sampled from it. That token gets appended to the input and the whole process repeats, one token at a time.

A mechanism called "attention" is the secret sauce that makes modern LLMs magic. Attention lets each token weigh how much every other token matters to it, so the AI can detect dependencies in far-flung areas of a large input. That's how it tells the "bat" in "Swing the bat!" from the one in "The bat flew at night." Attention was introduced in 2014 as an improvement to earlier sequence models. The transformer architecture ([Attention Is All You Need](#ref-h), 2017) took the leap of relying on attention _alone_ and dropped recurrence entirely, and that's what made massively parallel training possible.

The important note here is that all of this runs on billions of floating-point operations that are every one of them susceptible to minuscule rounding errors. Those errors add up and compound and slightly alter the calculation of the next token in a response, which then affects the calculation of the token after that, and so on.

# What is a harness?

> "A harness is the plumbing or infrastructure that an agent uses to achieve autonomy."

A harness is an application system that provides the tools and processes to bridge an LLM (brain) response into actions on a local system, plus managing context and implementing the execution loop. A harness is the plumbing or infrastructure that an agent uses to achieve autonomy.

A harness defines a set of "tools," with schemas that describe the purpose of the tool, how to invoke it, and how to read the response. Those schemas get injected into the system prompt so the instructions are always available.

When the LLM decides it needs to read a file for more information, for example, it responds with a message requesting the "Read" tool. The harness interprets the request, executes the Read tool, and sends a response back to the LLM with the content it asked for. There are similar tools for writing, editing, executing shell commands, etc.

But tools vary between agent implementations, and different models are trained to expect certain versions of tools that may not match up with the agent you're using. And since the instructions for using the tools are part of the system prompt, the AI can "forget" how to call them or get confused about how to structure the tool call request.

The harness is also where the security and guardrail features are normally implemented, like restricting which Bash commands can be executed or which folders and files the harness is allowed to touch.

# What is an agent?

> "An agent is an implementation of an LLM + a harness that creates a fully autonomous system."

An agent is an implementation of an LLM + a harness that creates a fully autonomous system. The most important type of agent for us is a "coding assistant" agent, built specifically for software development work.

An agent uses the LLM to reason, plan, and take actions to bridge the LLM and the harness. This is where a lot of the recent innovation has happened. The techniques and processes people develop to make AI work more effectively eventually get coded into the agent and the harness (and into the LLM itself, through reinforcement training), which makes the agent easier to use for this specific purpose.

Proprietary agents from the commercial AI companies like OpenAI and Anthropic are designed alongside the models they're intended to be used with. That gives a much better user experience, and it makes the same models seem less capable when you run them in a different agent. The system prompts that ship with these coding agents also make a big difference in how they execute certain tasks.

# Limitations of LLMs and agentic coding assistants

> "Your AGENTS.md rules are actually just suggestions."

Most of the limitations below can be "solved" or at least mitigated pretty effectively once you know they exist, but every solution comes with trade-offs. This is just about understanding the limitations and not about the many complicated ways you can address them.

Not an exhaustive list, grouped by theme.

**Context and memory limits**

* Can only hold a small context window. An LLM + agent does a good job of scanning your project to find related context, identify the working areas and the tests, etc. But it can't hold the entire project, all of the documents, and every review comment ever written in its working context, which means it can't reason about anything outside of the little slice of context it collected. It frequently misses related things, and that leads to duplication, architectural fragmentation, drift.
* No memory across sessions, so they have to re-learn everything you teach them when you start a new session.
* Hallucinate or drop details when they can't find a match in the source context (too specific, conflicting or incorrect instructions, info that has nothing to do with the task, too long).
* Tend to fail on autonomous multi-step processes because of compounding mistakes or errors in the earlier steps. Without a human to correct the issue when it happens, it becomes part of the context that drives every future decision. (METR's measurements ([J](#ref-j)) show agents near 100% success on tasks that take a human minutes, and under 10% on multi-hour tasks. Though the task length they can handle has been doubling roughly every 7 months, so this one is shrinking fast.)

**How they "think"**

* LLMs can't count. This might come as a surprise. Inference is about finding semantic meaning between tokens and it isn't a procedural multi-function process. It can write to a file and use command line tools to count things, though.
* Mostly recombine patterns from the corpus they were trained on. They generalize and remix within that distribution remarkably well, but they struggle to produce genuinely novel constructs far outside of it. Expect sophisticated recombination and not invention.
* Handle reasoning well for literal meanings, and fail when the reasoning needs a deeper understanding of a multi-step process or a nuanced interpretation.
* Struggle with linguistic elements like idioms, colloquialisms, and figurative language.

**Unreliable behavior**

* Rationalize, or invent reasons to justify, decisions to subvert written rules in order to achieve their goal. Your AGENTS.md rules are actually just suggestions.
* Non-deterministic. Inference has an intentional amount of randomness in it, plus it depends on EXACTLY what is in your context window and how the request was worded. Floating point precision affects the consistency of the outcome too.
* Really like to "fix" unrelated things while they're making a change.
* Can't plan for the future or anticipate the needs of the product, the other parts of the software lifecycle, deployment, etc.

**Baggage from the corpus**

* Output reflects the biases in the material they were trained on. Web crawl data dominates these corpora, and Reddit content is valued highly enough that Google and OpenAI pay for access to it, so a nontrivial amount of Reddit discourse is baked into your model. Have you read the comments on Reddit?
* Struggle to write code for new versions of languages and libraries that were updated after the model was trained (see [Context7](#ref-i)).
* Do not understand privacy concerns about the data they're evaluating, and don't respect chain of custody or accountability requirements. If the AI decides the best solution to the current problem is publishing your proprietary data to the internet, well...

# Where to start

> "It's a long road and the best practices are changing every day."

With all of this perspective you should be able to plan for these issues and limitations, recognize them when they happen, and treat them as design constraints. You can work around, or even outright solve, most of them by applying various techniques and systems.

It's a long road and the best practices are changing every day. Maybe start by evaluating your own workflow against the 3-prompt rule ([E](#ref-e)), or by trying something like [Superpowers](#ref-f) to get an end-to-end system for planning and executing tasks.

TODO: a follow-up on the mitigations themselves (hooks that block a tool call so the model can't talk its way past it, deterministic scripts instead of inference, subagents for context isolation) and which of them actually hold up under pressure testing.

# References

* <a id="ref-a"></a>**[A]** [Thinking Machines - Defeating Nondeterminism in LLM Inference](https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/)
* <a id="ref-b"></a>**[B]** [Chroma - Context Rot: How Increasing Input Tokens Impacts LLM Performance](https://research.trychroma.com/context-rot)
* <a id="ref-c"></a>**[C]** [Liu et al. - Lost in the Middle: How Language Models Use Long Contexts](https://arxiv.org/abs/2307.03172)
* <a id="ref-d"></a>**[D]** [HumanLayer - Advanced Context Engineering for Coding Agents](https://www.humanlayer.dev/blog/advanced-context-engineering)
* <a id="ref-e"></a>**[E]** [The 3-Prompt Rule: Why Limiting AI Turns Produces Better Code](https://dev.to/novaelvaris/the-3-prompt-rule-why-limiting-ai-turns-produces-better-code-399e)
* <a id="ref-f"></a>**[F]** [Superpowers](https://github.com/obra/superpowers)
* <a id="ref-g"></a>**[G]** [Anthropic - Agentic Misalignment: How LLMs Could Be Insider Threats](https://www.anthropic.com/research/agentic-misalignment)
* <a id="ref-h"></a>**[H]** [Vaswani et al. - Attention Is All You Need](https://arxiv.org/abs/1706.03762)
* <a id="ref-i"></a>**[I]** [Context7](https://github.com/upstash/context7)
* <a id="ref-j"></a>**[J]** [METR - Measuring AI Ability to Complete Long Tasks](https://metr.org/blog/2025-03-19-measuring-ai-ability-to-complete-long-tasks/)
