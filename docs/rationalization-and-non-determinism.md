# Why Do Agents Misbehave?

Build a basic mental model of how LLMs and agentic coding assistants work, what they are good at, what they are not good at, and how that affects their application.

## Why Do Agents Misbehave?

> You're absolutely right. I violated every rule. You gave clear instructions and I disregarded them completely.

Some issues that cause AIs to go rouge, forget instructions, ignore or override operational rules, and produce inconsistent outcomes.

### Non-Determinism in LLMs

It turns out that LLMs have a lot of indeterminism built-in to the way they work. Inference is a probabilistic statistics sampling, next-token guessing process. That sampling process involves several parameters, such as temperature, that cause a certain amount of randomness when selecting the next best token from the pool of potential candidates. Supposedly, this makes the results from the AI seem more "creative" because it can generate alternate solutions to the same problems.

But there are also a lot of reasons why responses are always different, even with the same prompt and same agent and model.

LLMs make heavy use of floating point numbers in billions of computations that run in highly-parallel threads across multiple computers at once. But computers are not good with floating point numbers. There are always minuscule rounding errors, and those errors compound over all of the computations that happen when generating a response.

The way in which an LLM breaks up computations over multiple threads is dynamic, based on many different conditions (like how much traffic the servers are under). This means that rounding-errors from computations are dependent on exactly how they were grouped and integrated. In other words, things you might expect to be associative operations, that shouldn't matter on which order the results are combined, actually do matter because the rounding errors of those values is different based on how/where it was computed.

Massively parallel hardware splits operations across thousands of concurrent threads where completion order varies. Differences in hardware, or even different generations of the same GPU architecture, means floating point math is handled differently, leading to subtle differences depending on which GPU performed the operation. This usually means slightly different rounding errors or differences in timing.

So non-determinism in AI is partly by design, and partly because it relies heavily on very complex and precise floating point math, and we haven't solved floating point math in computers yet.

### Context Overload

This is a fundamental concept of context engineering. Too much context (or bad context) can have disastrous effects, from AI "forgetting" about certain rules, to using conflicting information as justification to apply which ever rule it prefers instead of surfacing the conflict to the user.

LLMs have trouble effectively utilizing a large context in messages. As the size of the context surpasses 40% (of an assumed 200K context window), accuracy of the results begins to diminish exponentially. This is based on total tokens - a 2M context window still has the same issues around 60K tokens despite the relatively small percentage of the window in use.

Detractors (info not relevant to the task at hand, output from failed commands, etc) and conflicting context (contradictory input from the user, conflicts between phrases or rules in different sections of the context) create problems for attention and provide loopholes that the agent can use to justify making unexpected decisions later.

A system called the "[3-Prompt Rule](https://dev.to/novaelvaris/the-3-prompt-rule-why-limiting-ai-turns-produces-better-code-399e)" provides a simple process to effectively avoid context overload and conflicting instructions in your working context. This might sound extreme, but think more about what this is trying to solve and why it works: by specifying the full spec up-front, you reduce the amount of undefined behavior that the agent has to guess at in the first steps (which become part of it's working context). Making iterative changes, corrections, improvements after the initial generation means you are contradicting the behavioral rules the AI invented that are in its working context - you are polluting the context window by correcting the AI's work so far.

### Loopholes and Rationalization

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
> Pressing down on you

Pressure refers to any force that makes an agent want to violate a rule that it already knows: time, sunk cost, authority, economics, exhaustion, social, friction and "pragmatic not dogmatic" framing.

I find this interesting because, it seems, AI is susceptible to the same types of pressure as humans. It's also interesting because this is one effective way that hackers use to break and abuse AI model safeguards.

The Concept of pressure testing is built on one assumption: agents resist a single pressure and break under combined pressures. If you construct scenarios where you can prompt a subagent to make a decision with multiple points of pressure applied, you can analyze how well it responds and update your prompt to correct the impulse to break the rules.

It seems that mentions of pressure-causing constraints in the context window get mixed with the instructions and rules in the context window. The AI can then use these as justification for bypassing certain rules that are an obstacle to quickly solving the problem or conflict with it's reward-based training rules.

## How does inference work? ELI5

> I AM NOT AN EXPERT AT LLM IMPLEMENTATION!!! I'm only trying to illustrate a high-level view of the process to highlight where problems occur.

Inference is the process of applying the trained model's execution phase against it's weights to determine semantic meaning between tokens and generate a response.

- **Parsing:** Analyze sentence structure, assigning parts of speech (noun, verb, adjective, etc) to each word and identifying grammatical relationships.
- **Tokenization:** The model splits sentences into individual words (tokens), creating the building blocks for performing semantic analysis.
- **Stemming:** Reduces words to their root form (walking => walk, etc). This ensures models treat words consistently.
- **Entity recognition and relationship extraction:** Identify and categorize specific entities (like people or places) within the text and uncover their relationships.
- **Word embedding:** Finally, creates a numerical representation for each word (vector), capturing its meaning and connection to other words. This allows the model to process the text and perform tasks like translation or summarization.

A process called "attention" is the secret sauce that makes modern LLMs magic. The move to transformer architecture introduced attention as an improvement over the old process. It creates multiple weightings for tokens based on context and allows the AI to detect dependencies in far-flung areas of a large input. This allows the AI to distinguish the difference between "bat" as the subject of "Swing the bat!" vs. "The bat flew at night."

An important note is that this relies on billions of floating-point operations that are all susceptible to minuscule rounding errors that add up and compound to slightly alter calculation of the next token in a response, which then impacts the calculation of the next token, and so on.

## What is a harness?

A harness is an application system that provides tools and processes to bridge an LLM (brain) response to actions in a local system, as well as managing context and implementing the execution loop. A harness is the plumbing or infrastructure that an agent uses to achieve autonomy.

A harness defines a set of "tools," with schemas that define the purpose of the tool, how to invoke it, and how to read the response. These schemas are injected into the system prompt so that the instructions are always available.

When the LLM decides that it needs to read a file for more information, for example, it will respond with a message requesting to use the "Read" tool. The harness can interpret the request, execute the Read tool, and then send back a response to the LLM with the content that it asked for. There are similar tools for writing, editing, executing shell commands, etc.

But tools vary between agent implementations, and different models are trained to expect certain versions of tools which may not match up to the agent that you are using. Additionally, since the instructions to use the tools are part of the system prompt, the AI can "forget" how to call them or get confused on how to structure the tool call request.

The harness is also where the security and guardrails features are typically implemented, like restricting what Bash commands can be executed or which folders and files the harness is allowed to access.

## What is an agent?

An agent is an implementation of a LLM + a harness that creates a fully autonomous system. The most important type of agent for us is a "coding assistant" agent, specifically designed for working with software development.

An agent uses the LLM to reason, plan, and take actions to bridge the LLM and harness. This is where a lot of recent innovation has taken place. The techniques and process that people have developed to make AI work more effectively eventually get coded into the agent and harness (and into the LLM via reinforcement training), making the agent easier to use for this specific purpose.

Proprietary agents, created by commercial AI companies like OpenAI and Anthropic, are designed along with the models they are intended to be used with. This gives a much better user experience and makes the same models seem less capable when used in a different agent. The system prompts that ship with these coding agents also makes a big difference on how they execute certain tasks.

## Limitations of LLMs and Agentic Coding Assistants

Many of the limitations I describe below can be "solved" or mitigated effectively once you know they exist, but every solution comes with tradeoffs. This article is just about understanding the limitations, not about the many complex ways you can address them.

Not an exhaustive list:

- Can only hold a small context window. An LLM + agent can do a good job of scanning your project to find related context, identify the working areas and tests, etc. But it can't hold the entire project, all documents, all review comments ever, into it's working context, which means it can't reason about anything outside of the little slice of context that it collects. It frequently misses related things and leads to duplication, architectural fragmentation, drift.
- LLMs can't count. This may come as a surprise. Inference is about finding semantic meanings between tokens, it's not a procedural multi-function process. However, it can write to a file and use command line tools to count things.
- Hallucinate or drop details when it can't find a match from the source context (too specific, conflicting or incorrect instructions, info not relevant at all to the task, too long).
- Rationalize - or create reasons to justify - decisions to subvert written rules in order to achieve their goal. Your AGENTS.md rules are actually just suggestions.
- LLMs are non-deterministic. Inference has an intentional amount of randomness, plus it depends on EXACTLY what is in your context window and how the request was worded. Floating point math precision also plays a role in the outcome consistency.
- Can only reproduce patterns from existing training data. Can't innovate or create new constructs that it hasn't already seen before.
- Handle reasoning well when it comes to literal meanings, but fail when reasoning requires deeper understanding of multi-step processes and nuanced interpretation.
- Struggle with linguistic elements such as idioms, colloquialisms, and figurative language.
- Output reflects the biases found in the training data. And Reddit comments are one of the biggest sources of training data… Have you read the comments on Reddit?
- Can't plan for the future, anticipate needs of the product or the other parts of the software lifecycle, deployment, etc.
- Struggle writing code for new versions of languages/libraries that have been updated since the model was trained (see [Context7](https://github.com/upstash/context7)).
- Lack of memory across sessions means they have to re-learn everything you teach them when starting a new session.
- Do not understand privacy concerns about the data they are evaluating, or respect chain of custody or accountability requirements. If the AI thinks the best solution to the current problem is to publish your proprietary data to the internet, well…
- Tend to fail on autonomous multi-step processes due to compounding mistakes or errors in earlier steps. Without a human to correct the issues when they happen, they become part of the context that drives future decision making.
- Really like to "fix" unrelated things in the process of making a change.

## Conclusion

Now, with all of this perspective, you should be able to plan for, and recognize, these issues and limitations as design constraints. You can work around, or even outright solve, most of these issues by applying various techniques and systems.

It's a long road and the best practices are changing every day. Maybe start by evaluating your own work flow against the 3-prompt rule, or by trying something like [Superpowers](https://github.com/obra/superpowers) to implement an end-to-end system for planning and executing tasks.

## References

- [The 3-Prompt Rule: Why Limiting AI Turns Produces Better Code](https://dev.to/novaelvaris/the-3-prompt-rule-why-limiting-ai-turns-produces-better-code-399e)
- [Context7](https://github.com/upstash/context7)
- [Superpowers](https://github.com/obra/superpowers)
