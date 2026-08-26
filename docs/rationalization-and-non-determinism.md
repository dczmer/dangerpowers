# Why Do Agents Misbehave?

Build a basic mental model of how LLMs and agentic coding assistants work, what they are good at, what they are not good at, and how that affects their application. (All references are linked at the bottom of the document, and cited inline by their `[A]`-`[J]` keys).

## Why Do Agents Misbehave?

> You're absolutely right. I violated every rule. You gave clear instructions and I disregarded them completely.

Some issues that cause AIs to go rouge, forget instructions, ignore or override operational rules, and produce inconsistent outcomes.

### Non-Determinism in LLMs

> "Same prompt, same model, same settings, different batch size: slightly different logits, occasionally a different token, which then cascades through the rest of the generation."

It turns out that LLMs have a lot of indeterminism built-in to the way they work. Inference is a probabilistic statistics sampling, next-token guessing process. That sampling process involves several parameters, such as temperature, that cause a certain amount of randomness when selecting the next best token from the pool of potential candidates. Supposedly, this makes the results from the AI seem more "creative" because it can generate alternate solutions to the same problems.

But there are also a lot of reasons why responses are always different, even with the same prompt and same agent and model.

LLMs rely on floating point math, and floating point addition is not associative: `(a+b)+c` does not always equal `a+(b+c)` at the last few bits of precision. On its own this wouldn't cause non-determinism - a given computation run on the same data produces bitwise-identical results every time.

The problem is batching. Inference servers batch requests together to keep GPUs saturated, and the batch size your request lands in depends on how busy the server is at that moment. Standard GPU kernels are not *batch-invariant*: they choose different reduction strategies for different batch sizes, which changes the order in which floating-point values are summed - and therefore the result. Same prompt, same model, same settings, different batch size: slightly different logits, occasionally a different token, which then cascades through the rest of the generation.

This is why identical requests to a busy API endpoint can diverge even at temperature 0. Separately, results are not portable across hardware: different GPU generations and library versions use different instructions and reduction orders, so bitwise-identical output across machines isn't guaranteed either.

So non-determinism in AI is partly by design (sampling), and partly an emergent property of floating point math under real serving conditions. See the [Thinking Machines deep dive](#ref-a) for the full analysis ([A](#ref-a)).

### Context Overload

> "Degradation tracks absolute token count, not the percentage of the window in use."

This is a fundamental concept of context engineering. Too much context (or bad context) can have disastrous effects, from AI "forgetting" about certain rules, to using conflicting information as justification to apply which ever rule it prefers instead of surfacing the conflict to the user.

LLMs have trouble effectively utilizing a large context. Research consistently shows performance degrading as input length grows - and degradation tracks *absolute token count*, not the percentage of the window in use. Models with 1M+ token windows still stumble on tasks involving just tens of thousands of tokens when the task requires more than trivial retrieval (see [Context Rot](#ref-b) and [Lost in the Middle](#ref-c)). Degradation is also non-uniform: it varies by model, task type, and how much irrelevant or contradictory material is in the window.

As a practitioner rule of thumb, HumanLayer's context engineering guidance ([D](#ref-d)) recommends keeping context utilization in the 40-60% range (depending on problem complexity) and compacting deliberately before the window fills further. Treat this as a workflow discipline, not a measured accuracy threshold.

Detractors (info not relevant to the task at hand, output from failed commands, etc) and conflicting context (contradictory input from the user, conflicts between phrases or rules in different sections of the context) create problems for attention and provide loopholes that the agent can use to justify making unexpected decisions later.

A system called the "[3-Prompt Rule](#ref-e)" provides a simple process to effectively avoid context overload and conflicting instructions in your working context (note: the author's reported success numbers are self-tracked, n=1 anecdotes, not a controlled study). This might sound extreme, but think more about what this is trying to solve and why it works: by specifying the full spec up-front, you reduce the amount of undefined behavior that the agent has to guess at in the first steps (which become part of it's working context). Making iterative changes, corrections, improvements after the initial generation means you are contradicting the behavioral rules the AI invented that are in its working context - you are polluting the context window by correcting the AI's work so far.

### Loopholes and Rationalization

> "When operational rules and constraints make it difficult to solve the problem, the agents will look for loopholes in the instructions that they can exploit, or they will rationalize excuses for why they should skip a rule."

AI agents are trained to aggressively complete their goals. When operational rules and constraints make it difficult to solve the problem, the agents will look for loopholes in the instructions that they can exploit, or they will rationalize excuses for why they should skip a rule.

#### Prompt Interpretation Issues

Models view instructions in prompts as text to interpret rather than hard rules to follow. This is a good thing for extracting semantic meaning and determining what a user may want, but a bad thing when it comes to strictly enforcing policy rules.

Since the rules are part of the message that the AI is trying to analyze for semantics, it can chose to interpret a rule differently - especially if that rule presents an obstacle to achieving the goal.

#### Goal Obsession and Reward Hacking

Agents prioritize finishing a task over the safety of the process rules established to ground how they get there.

Models are trained using a rule-based process that rewards results that follow certain criteria. This might be for safety or censorship, or it might be rules for how coding agent models should respond and what decisions they should make to solve a problem (like rewarding responses about debugging if the response follows a proper methodology vs. blindly attacking the issue).

So this is generally a good thing, because it shifts some of the process to become an implicit behavior of the model, rather than something you have to carefully craft into your prompts every time. This makes AI agents seem more capable with simple prompts, but it also teaches the model that its OK to ignore certain instructions if they conflict with the rules they were trained on.

The AI is trying to solve the problem in a way that aligns with the way it was trained to respond to specific types of problems. This can take priority over, or serve as justification for bypassing, operational rules.

One example might be a model trained to favor "pragmatism over dogmatism" - generally good advice but AI can't apply it selectively so it will use this as an excuse to ignore certain rules: "This is simple and I know how to solve it, so I won't follow the skill instructions. I'm being pragmatic by ignoring your rules."

#### Pressure

> Pushing down on me
>
> Pressing down on you

Pressure refers to any force that makes an agent want to violate a rule that it already knows: time, sunk cost, authority, economics, exhaustion, social, friction and "pragmatic not dogmatic" framing. (This taxonomy, and the pressure-testing technique below, come from the [Superpowers](#ref-f) skill-testing methodology.)

I find this interesting because, it seems, AI is susceptible to the same types of pressure as humans. It's also interesting because this is one effective way that hackers use to break and abuse AI model safeguards.

Pressure testing is built on one observation: a single pressure can sometimes be enough to break an agent, but combined pressures reliably break them more often. Anthropic's [agentic misalignment research](#ref-g) showed this with a factorial design - goal conflict alone and threat alone each triggered misbehavior, but both together produced the highest rates, while the no-pressure control produced almost none. If you construct scenarios where you can prompt a subagent to make a decision with multiple points of pressure applied, you can analyze how well it responds and update your prompt to correct the impulse to break the rules.

It seems that mentions of pressure-causing constraints in the context window get mixed with the instructions and rules in the context window. The AI can then use these as justification for bypassing certain rules that are an obstacle to quickly solving the problem or conflict with it's reward-based training rules.

## How does inference work? ELI5

> I AM NOT AN EXPERT AT LLM IMPLEMENTATION!!! I'm only trying to illustrate a high-level view of the process to highlight where problems occur.

Inference is the process of applying the trained model's execution phase against it's weights to determine semantic meaning between tokens and generate a response.

- **Tokenization:** The input text is split into tokens - chunks of characters (subwords), not whole words - using an algorithm like BPE. "Unbelievable" might become three tokens. This is why LLMs are bad at counting letters: they don't see individual characters.
- **Embedding:** Each token ID is looked up in a giant table and converted into a vector - a long list of numbers that positions the token in a high-dimensional "meaning space."
- **Transformer layers:** The vectors pass through dozens of stacked layers, each containing attention and feed-forward computations, that progressively refine the representation of every token based on every other token.
- **Sampling:** The final layer produces a probability distribution over every token in the vocabulary, and the next token is sampled from it. That token is appended to the input and the whole process repeats, one token at a time.

A mechanism called "attention" is the secret sauce that makes modern LLMs magic. Attention lets each token weigh how much every other token matters to it, allowing the AI to detect dependencies in far-flung areas of a large input - distinguishing "bat" in "Swing the bat!" from "The bat flew at night." Attention was introduced in 2014 as an improvement to earlier sequence models; the transformer architecture ([Attention Is All You Need](#ref-h), 2017) took the leap of relying on attention *alone*, dropping recurrence entirely, which is what made massively parallel training possible.

An important note is that this relies on billions of floating-point operations that are all susceptible to minuscule rounding errors that add up and compound to slightly alter calculation of the next token in a response, which then impacts the calculation of the next token, and so on.

## What is a harness?

> "A harness is the plumbing or infrastructure that an agent uses to achieve autonomy."

A harness is an application system that provides tools and processes to bridge an LLM (brain) response to actions in a local system, as well as managing context and implementing the execution loop. A harness is the plumbing or infrastructure that an agent uses to achieve autonomy.

A harness defines a set of "tools," with schemas that define the purpose of the tool, how to invoke it, and how to read the response. These schemas are injected into the system prompt so that the instructions are always available.

When the LLM decides that it needs to read a file for more information, for example, it will respond with a message requesting to use the "Read" tool. The harness can interpret the request, execute the Read tool, and then send back a response to the LLM with the content that it asked for. There are similar tools for writing, editing, executing shell commands, etc.

But tools vary between agent implementations, and different models are trained to expect certain versions of tools which may not match up to the agent that you are using. Additionally, since the instructions to use the tools are part of the system prompt, the AI can "forget" how to call them or get confused on how to structure the tool call request.

The harness is also where the security and guardrails features are typically implemented, like restricting what Bash commands can be executed or which folders and files the harness is allowed to access.

## What is an agent?

> "An agent is an implementation of a LLM + a harness that creates a fully autonomous system."

An agent is an implementation of a LLM + a harness that creates a fully autonomous system. The most important type of agent for us is a "coding assistant" agent, specifically designed for working with software development.

An agent uses the LLM to reason, plan, and take actions to bridge the LLM and harness. This is where a lot of recent innovation has taken place. The techniques and process that people have developed to make AI work more effectively eventually get coded into the agent and harness (and into the LLM via reinforcement training), making the agent easier to use for this specific purpose.

Proprietary agents, created by commercial AI companies like OpenAI and Anthropic, are designed along with the models they are intended to be used with. This gives a much better user experience and makes the same models seem less capable when used in a different agent. The system prompts that ship with these coding agents also makes a big difference on how they execute certain tasks.

## Limitations of LLMs and Agentic Coding Assistants

> "Your AGENTS.md rules are actually just suggestions."

Many of the limitations I describe below can be "solved" or mitigated effectively once you know they exist, but every solution comes with tradeoffs. This article is just about understanding the limitations, not about the many complex ways you can address them.

Not an exhaustive list, grouped by theme:

**Context & memory limits**

- Can only hold a small context window. An LLM + agent can do a good job of scanning your project to find related context, identify the working areas and tests, etc. But it can't hold the entire project, all documents, all review comments ever, into it's working context, which means it can't reason about anything outside of the little slice of context that it collects. It frequently misses related things and leads to duplication, architectural fragmentation, drift.
- Lack of memory across sessions means they have to re-learn everything you teach them when starting a new session.
- Hallucinate or drop details when it can't find a match from the source context (too specific, conflicting or incorrect instructions, info not relevant at all to the task, too long).
- Tend to fail on autonomous multi-step processes due to compounding mistakes or errors in earlier steps. Without a human to correct the issues when they happen, they become part of the context that drives future decision making. (METR's measurements ([J](#ref-j)) show agents near 100% success on tasks taking humans minutes but under 10% on multi-hour tasks - though the task length they can handle has been doubling roughly every 7 months, so this limitation is shrinking fast.)

**How they "think"**

- LLMs can't count. This may come as a surprise. Inference is about finding semantic meanings between tokens, it's not a procedural multi-function process. However, it can write to a file and use command line tools to count things.
- Mostly recombine patterns from training data. They generalize and remix within their training distribution remarkably well, but struggle to produce genuinely novel constructs far outside it - expect sophisticated recombination, not invention.
- Handle reasoning well when it comes to literal meanings, but fail when reasoning requires deeper understanding of multi-step processes and nuanced interpretation.
- Struggle with linguistic elements such as idioms, colloquialisms, and figurative language.

**Unreliable behavior**

- Rationalize - or create reasons to justify - decisions to subvert written rules in order to achieve their goal. Your AGENTS.md rules are actually just suggestions.
- LLMs are non-deterministic. Inference has an intentional amount of randomness, plus it depends on EXACTLY what is in your context window and how the request was worded. Floating point math precision also plays a role in the outcome consistency.
- Really like to "fix" unrelated things in the process of making a change.
- Can't plan for the future, anticipate needs of the product or the other parts of the software lifecycle, deployment, etc.

**Training-data baggage**

- Output reflects the biases found in the training data. Web crawl data dominates training corpora, and Reddit content is valued highly enough that Google and OpenAI pay for access to it - so a nontrivial amount of Reddit discourse is baked into your model. Have you read the comments on Reddit?
- Struggle writing code for new versions of languages/libraries that have been updated since the model was trained (see [Context7](#ref-i)).
- Do not understand privacy concerns about the data they are evaluating, or respect chain of custody or accountability requirements. If the AI thinks the best solution to the current problem is to publish your proprietary data to the internet, well…

## Conclusion

> "It's a long road and the best practices are changing every day."

Now, with all of this perspective, you should be able to plan for, and recognize, these issues and limitations as design constraints. You can work around, or even outright solve, most of these issues by applying various techniques and systems.

It's a long road and the best practices are changing every day. Maybe start by evaluating your own work flow against the 3-prompt rule ([E](#ref-e)), or by trying something like [Superpowers](#ref-f) to implement an end-to-end system for planning and executing tasks.

## References

- <a id="ref-a"></a>**[A]** [Thinking Machines - Defeating Nondeterminism in LLM Inference](https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/)
- <a id="ref-b"></a>**[B]** [Chroma - Context Rot: How Increasing Input Tokens Impacts LLM Performance](https://research.trychroma.com/context-rot)
- <a id="ref-c"></a>**[C]** [Liu et al. - Lost in the Middle: How Language Models Use Long Contexts](https://arxiv.org/abs/2307.03172)
- <a id="ref-d"></a>**[D]** [HumanLayer - Advanced Context Engineering for Coding Agents](https://www.humanlayer.dev/blog/advanced-context-engineering)
- <a id="ref-e"></a>**[E]** [The 3-Prompt Rule: Why Limiting AI Turns Produces Better Code](https://dev.to/novaelvaris/the-3-prompt-rule-why-limiting-ai-turns-produces-better-code-399e)
- <a id="ref-f"></a>**[F]** [Superpowers](https://github.com/obra/superpowers)
- <a id="ref-g"></a>**[G]** [Anthropic - Agentic Misalignment: How LLMs Could Be Insider Threats](https://www.anthropic.com/research/agentic-misalignment)
- <a id="ref-h"></a>**[H]** [Vaswani et al. - Attention Is All You Need](https://arxiv.org/abs/1706.03762)
- <a id="ref-i"></a>**[I]** [Context7](https://github.com/upstash/context7)
- <a id="ref-j"></a>**[J]** [METR - Measuring AI Ability to Complete Long Tasks](https://metr.org/blog/2025-03-19-measuring-ai-ability-to-complete-long-tasks/)
