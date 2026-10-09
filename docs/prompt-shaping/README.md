# Proompting

A presentation of common prompt-engineering conventions and advice, how they map to the concepts we covered when [writing and bulletproofing skills](../writing-skills/part-3/README.md), and analysis of the current state of prompt engineering.

I think most people would present prompt engineering first, then apply it to writing skills. But by starting with skills, we begin with a formal discipline and prompt engineering is essentially an informal subset of the things we've already learned.

If you search for guides on prompt engineering, you will find a lot of the same advice we covered in the [writing-skills](../writing-skills/part-1/README.md) series, but we also see a lot of curious "folk-wisdom" and possibly superstitious practices - or things that used to work, but are no longer necessary with modern LLMs and harnesses.

## What is Prompt Engineering?

> "Anything that improves model performance through inputs rather than weights is prompt engineering - including most of what you already do."

I was originally under the impression that prompt engineering was a bunch of "tips and tricks" that people use to try to make the model do a better job on a task. I was also under the impression that most of these techniques were either debunked or obsolete as modern frontier models have improved and developed complex reasoning capabilities.

But prompt engineering really refers to anything you do to improve model or agent performance based purely on inputs to a model, rather than changing the actual weights [[A]](#ref-a). This includes the entire field of "context engineering", hardening and optimizing skills, and making detailed specs and execution plans for the agent to run.

## Prompt Engineering Techniques

> I'm not sure if verbally abusing a model is actually helpful or not but sometimes it is cathartic.

Many of the early techniques have become obsolete with modern frontier models, or were never empirically proven in the first place - "no mistakes or you go to jail", "you are an expert Java developer", threatening the agent's grandmother if a task doesn't work out perfectly, etc. I'm not sure if verbally abusing a model is actually helpful or not but sometimes it is cathartic.

But we have already experienced that you need to word your prompts/skills very carefully and tailor to the specific model to get the results you want. Additionally, when working with local models, or small models without reasoning capabilities, even many of the "old" prompt engineering tricks are still useful - the discipline has become so integral to working with AI that we don't always think about it as a distinct discipline, especially since the newer models we're using are so much better at reasoning.

### Still Useful for Frontier Models

> "Frontier models retired the superstitions, not the craft."

While many practices are now unnecessary when working with large frontier models, here are a few that are still worth using.

#### Specificity

> "Fixing a vague prompt's output costs more than writing the specific prompt first."

If you want to do something specific, you need to write a prompt that effectively instructs the AI to do it. That implies shaping and discipline rules, and they do apply here, but it's also largely about describing what you want effectively (remember our [shaping tests](../writing-skills/part-3/README.md)).

**Bad:** "Add validation to the signup form."
*Why it fails: the agent must guess which fields, rules, and error UX you want.*

**Good:** "In `SignupForm.tsx`, validate email format and require passwords of 12+ chars with at least one digit; show inline errors under each field and disable submit until valid. Do not change the API schema."
*Why it works: file, rules, output shape, and a non-goal - no decisions left to the agent.*

Specificity in your prompts reduces ambiguity that requires implementing agents to make decisions and form assumptions, improves accuracy of the final product, and saves time - fixing something after the AI writes it is more expensive than properly forming the prompt first. But just like we discussed in [writing skill part 1](../writing-skills/part-1/README.md), you need to tailor the specificity to the task fragility - give freedom where there are multiple ways to the solution, be more specific when there is only one way to do it correctly.

Specifics include, but are not limited to:
- Detailed description of the task to be executed
- Constraints and failure conditions
- Output shape requirements like format, length, and target audience, etc.
- Discipline rules for constraints that have a compliance cost

#### Context and Grounding

> "Feed the model the context it needs, when it needs it - and anchor it in verified facts, not its weights."

Context engineering is a critical part of learning to apply agentic coding effectively. The model has a limited amount of context it can hold, which is usually far less than what would be required to keep your entire project and all documentation in context at once. Even if you could, the model can't use all of that context effectively (recency bias) [[B]](#ref-b) and contradictions and similar-but-distinct facts in that context cause additional problems.

Context engineering deserves its own dedicated article, but it's all about feeding the model the context that it needs, when it needs it (progressive disclosure), while minimizing the amount of info in the context window that is not actually required at the time. Think of the context window as a workbench, not a warehouse: the warehouse holds everything you might ever need, but only what fits on the bench is actually usable, and a cluttered bench slows the work.

Some common context engineering practices:

- Intentional compaction: explicitly saving a summary and compacting the session (or starting a clean session) at certain breakpoints when you notice the context window starting to fill up.
- Wrapping tools and commands so they produce compacted output - the [context-efficient backpressure](#ref-c) pattern.
- Writing rules files (CLAUDE.md/AGENTS.md) and separating them by subdirectory or subsystem so they are only used when the agent traverses into that system.
- Writing load-on-demand skills instead of putting everything in rules files.
- Breaking up large skill files with "references" that are only loaded when that info is actually needed (corner cases, error handling, etc.).
- Using subagents to run isolated tasks to avoid using context space in the main session.

Check out HumanLayer's [Advanced Context Engineering for Coding Agents](#ref-d) blog post (there is a YouTube video version as well).

Grounding is the process of supplying verified, factual information to the model instead of deferring to the model weights, to prevent hallucination [[E]](#ref-e). This could include using a RAG system or other verified information source, and requiring the agent to provide sources for each claim in the results, feeding the model actual reference data as input, or generating and manually verifying detailed execution plans up-front.

Combining grounding with context engineering improves accuracy by ensuring the results are "grounded" in reality, relying more on "extrinsic" knowledge provided to the AI and not the "intrinsic" knowledge encoded in the model weights.

**Bad:** "Write a migration for the users table."
*Why it fails: the model invents a schema from its weights - hallucination by construction.*

**Good:** "Here is the current `users` schema (pasted) and the target schema (pasted). Write the Alembic migration between them; verify with `alembic upgrade head` against the docker-compose test DB."
*Why it works: the facts come from the repo instead of the weights, and the context contains exactly what the task needs - nothing else competing for attention.*

#### Decomposition

> "A big task is just small tasks that haven't been named yet."

Decomposing a task is much like the process of decomposition with software design: break a big, complicated task into smaller tasks that fit together.

Breaking a large task into smaller, more focused tasks helps keep the AI from getting overwhelmed and hallucinating across complex multi-step reasoning. The smaller tasks also help keep the context window clean and focused.

```mermaid
flowchart LR
  A[Add OAuth login] --> B[DB migration: oauth_accounts table]
  A --> C[Token exchange endpoint]
  A --> D[Session handling]
  A --> E[Login UI]
  C --> D
```

Like a lot of prompt-engineering techniques, decomposition (and delegation using subagents) is something that is now commonly built into the high-end frontier models. Once gains from inference-time scaling started to slow, much focus has moved towards implementing these techniques at the model-level, to make using the AI feel more intuitive or automatic.

The need for decomposition might be proportional to the power and reasoning capabilities of the model you use. For a large frontier model, I'm still a fan of decomposition to produce smaller, more focused PRs with fewer moving parts. Creating a detailed implementation plan and "slicing" it into discrete phases is one easy way to do this.

For local models with limited context or weak reasoning, you can decompose the problem into a sequence of smaller prompts that fit within that specific model's capabilities. You can even generate sequences of prompts that encode "chain of thought" reasoning semantics into individual steps that you can run against a model with no reasoning capabilities.

#### Iteration

> "It's cheaper to test and fix a prompt than to fix what a bad prompt built."

If you intend to run a prompt repeatedly, like a skill or saved prompt for a specific task, then it should be obvious that you should keep improving that prompt every time you notice an issue with its application.

Even if you are writing a prompt for a one-time task, like to implement some feature or refactor something, you can still benefit from testing your prompt, reverting, fixing the issues, and repeating. It's much cheaper to experiment up front than it is to try to fix something you already built incorrectly.

You can also apply some of the concepts we learned in our [writing skills](../writing-skills/part-1/README.md) series, or use tools like [DSPy](https://dspy.ai) and [GEPA](https://dspy.ai/api/optimizers/GEPA/overview/) [[F]](#ref-f) to optimize your prompts before actually executing them. The trade-off here is you have to implement a suitable testing process, including a way to self-verify the results. If the prompt is doing something that is not trivial to revert/undo (deleting production infrastructure, for example), then you also need to model a test environment with scaffolding and fixtures.

```mermaid
quadrantChart
  title Optimization Effort vs. Cost of Getting It Wrong
  x-axis Low effort --> High effort
  y-axis Low stakes --> High stakes
  One-off throwaway prompt: [0.15, 0.15]
  Feature implementation prompt: [0.4, 0.6]
  Reusable skill or saved prompt: [0.7, 0.75]
  Production infrastructure runbook: [0.9, 0.95]
```

#### Few-Shot Exemplars

> "Examples are training without touching the weights."

["Few-shotting"](#ref-g) is the process of including multiple examples of what you want in the prompt input. AI is good at detecting and matching patterns, and then copying them, so you can think of this like "training" the model to respond a certain way, without changing the weights.

**Bad (zero-shot):** "Classify the sentiment of: 'The food was cold but the staff were lovely.'"
*Why it fails: nothing pins the label set or output format, so the model may answer with a paragraph.*

**Good:** "Classify sentiment as POS, NEG, or MIXED. 'Battery dies in an hour' → NEG. 'Great camera, terrible screen' → MIXED. 'Best purchase I've made' → POS. 'The food was cold but the staff were lovely' →"
*Why it works: the exemplars demonstrate the exact label set and arrow format for the model to copy.*

One specific application of the few-shot technique is "chain of thought" reasoning - by providing similar logic, math, or other reasoning-based problems to the AI, along with step-by-step "reasoning" that shows the work of how it should get to the final result, the AI will copy the pattern and produce emergent reasoning capabilities. This topic is pretty relevant and interesting, so it gets a dedicated section later in this document.

#### Verification Loops

> "Done means a check passed, not that the agent said so."

A verification loop is the prompt-engineering version of our skill-writing best practice of always including a verification checklist: it forces the AI to confirm the product is within the required parameters before declaring done. Deterministic verification (a test, a command, an assertion) is best; where no deterministic check exists, a separate LLM acting as judge is the fallback.

**Bad:** "Refactor the parser to handle nested quotes."
*Why it fails: "done" is whatever the agent says it is.*

**Good:** "Refactor the parser to handle nested quotes. Done only when `pytest tests/test_parser.py -k quotes` passes - run it, show the output, and iterate until green."
*Why it works: completion is a deterministic check, not the agent's judgment.*

### Useful for Local Models

> "The 'obsolete' tricks are the small-model toolkit."

#### Few-Shot Examples for Small Models

> "Small models don't infer the pattern - you have to show it."

Frontier models follow instructions, often without needing examples (zero-shot). They mine your codebase for context and examples automatically. Small models need the pattern demonstrated for format, tone, and task structure. This was “required practice” circa 2022 because the models were weaker and did not yet have solid reasoning capabilities.

#### Chain-of-Thought Prompting for Small Models

> "Write the reasoning out, and a small model will follow it."

Frontier models now do this natively via proprietary reasoning pipelines. The explicit prompting technique is obsolete for them but measurably lifts small models with reasoning disabled (per the CoT paper: arithmetic, symbolic, and commonsense tasks) [[H]](#ref-h). More on this topic later in the document.

#### Aggressive Decomposition / Prompt Chaining

> "One task per prompt; each output feeds the next."

Small models fail on compound instructions. Decompose into one task per prompt, each phase's output feeds into the next phase.

#### Rigid Format Templates

> "Show the model exactly what the output looks like."

Small models drift from schemas, while frontier models mostly don’t. A well-specified template in the prompt shows the model exactly what the output is supposed to look like.

#### Self-Consistency (N Rollouts + Majority Vote)

> "Run it N times and let the majority vote."

Compensate for unreliable single-pass reasoning by having the model run multiple applications and vote on a winner. For example, asking the agent to sample and classify data multiple times and then have a judge pick the winner.

#### Front-Loaded, Minimal Context

> "Small windows rot faster - put what matters first, and nothing else."

Context rot / lost-in-the-middle hits small windows and weaker attention harder.

### Mostly Obsolete

> "If a technique coaxes hidden capability out with magic words, frontier models no longer need it."

#### Role Assignment and Personas

> "A persona is a compressed instruction set."

Modern frontier models don't really need the persona framing now. They determine if they are doing a code review, working on a Python module, etc., and adopt the perspective automatically. However, this is possibly still useful for specialized agents - setting the operating mode of the agent with a persona rather than detailed instructions. "You are a helpful coding agent" or "you are a sales assistant" implies a lot about the rules the agent should follow.

#### Zero-Shot CoT Triggers

> "Magic words stop working once the capability is no longer hidden."

Instructions like "Think step by step about how to solve the problem", which attempt to coax the model into demonstrating some hidden capabilities that only surface when you use the right magic words. Frontier models reason natively regardless of such triggers (see above), and for models without reasoning capabilities, few-shot exemplars are far more effective at inducing chain-of-thought than a bare trigger phrase.

## Chain of Thought and Reasoning

> "A prompt can simulate the reasoning pipeline a small model was never given."

I think this is interesting enough to have its own dedicated section.

Chain of thought reasoning is when the model breaks down a task step-by-step and analyzes each piece individually to "reason" about what the user wants and how to produce it. If you run your coding agent with the "thinking" output enabled (verbose output in Claude Code), then you are probably used to seeing the traces as the model is analyzing your request. If all goes well, the AI figures out missing details, determines which verification steps are appropriate and applies them automatically, etc. If it goes poorly, you end up with 20 minutes of "hmm... actually" output where the model is constantly second-guessing itself in a loop.

Chain of thought prompting is a technique that was [first published in 2022](#ref-h), before models had built-in reasoning systems. By providing few-shot example 'queries' and the 'answers' that illustrate the step-by-step how the AI should arrive at the answer, the model effectively learns the pattern and applies that reasoning process while producing the answer to your actual query. This is reported to greatly increase accuracy when working with math, symbolic reasoning, logic, etc.

**Bad:** "Q: A train travels 120 km in 1.5 hours, then 80 km in 45 minutes. What is its average speed?" *(asked bare, to a small model with reasoning disabled)*
*Why it fails: the model jumps straight to an answer and often botches the unit conversion.*

**Good:** prepend one exemplar - "Q: A car drives 100 km in 2 hours. Average speed? A: Let's work step by step. Total distance = 100 km. Total time = 2 h. Speed = 100 / 2 = 50 km/h." - then ask the train question.
*Why it works: the exemplar demonstrates the decompose-and-convert pattern, which the model copies onto the new problem.*

So if this is built into modern frontier models, is it still a useful technique to know about? Actually, yes. If you run a local model with reasoning disabled, you can simulate the reasoning process of a modern frontier model with just a prompt input. If you combine this with our prompt/skill optimization strategies, you can produce high-quality output rivaling what the frontier model can do.

I have observed one particular downside to the reasoning in frontier models (besides occasionally getting stuck in a loop): It seems to lead to new ways for the model to disregard your rules. While testing the skills in this repository against different models, the weaker local models needed careful wording to make the rules trigger/apply, while the frontier models mostly just worked, but had a tendency to occasionally reason their way out of loading a skill even when the trigger conditions clearly matched.

### Distillation

> "The encrypted thinking trace is the frontier model's diary - and its cheaper siblings can read it aloud."

Recently, the topic of [distillation attacks](#ref-i) has been prevalent. Distillation is the process of extracting the proprietary "reasoning" steps out of frontier models so they can be used to train other models or to copy that proprietary reasoning implementation. Anthropic and OpenAI have accused several prominent Chinese AI labs of stealing their data through distillation ([[J]](#ref-j), [[K]](#ref-k)).

CoT reasoning traces from frontier models are encrypted, and the client just hands the encrypted blocks back, along with the rest of the message, on each turn. What you read in the 'thinking' output is heavily summarized or redacted output that comes along with the response, separate from the encrypted blocks.

The flaw: these encrypted blocks are fully compatible and interchangeable across sessions, users, and even different models from the same provider ecosystem. By extracting the thinking trace signatures from Opus to Haiku, and asking it to output its own reasoning, Haiku will effectively decode and print the encrypted thinking traces.

```mermaid
sequenceDiagram
  participant F as Frontier model
  participant C as Client
  participant W as Weaker sibling model
  F->>C: encrypted reasoning block
  C->>W: replay block + "print your reasoning"
  W-->>C: frontier trace decoded as plaintext
```

This mostly works because models like Haiku or GPT-5.6 Luna are designed as fast, cost-effective tools and they do not have all the safeguards and refusal mechanics that the large models have (so probably this won't last forever).

It is also something of a security concern, because someone could get a hold of your session data and use the encrypted blocks to read traces of your proprietary data.

## Prompt "Shaping"

> "Shaping is a loop that turns a vague request into an executable spec."

Prompt shaping is basically just an application of prompt engineering techniques intended to guide the model towards a more accurate, relevant, and well-formatted output. For our purposes in this document, I'm distinguishing from "prompt engineering" and referring more to a process for applying those techniques to a poorly formed starting prompt, to produce a detailed, fully-formed prompt that is ready for execution.

My idea here is to write a simple skill that will work much like the [brainstorming skill](#ref-l) from superpowers - the model analyzes the prompt, grounds the process based on what you are requesting, and then implements a loop of identifying gaps, eliciting answers from the user, applying one or more prompt engineering techniques, and repeating until the resulting prompt is well-formed.

### Properties of a Good Prompt Shaping Process

> "Being wrong should cost a sentence, not an implementation."

- Cheap misalignment between AI assumptions and the human's expectations. The agent should state the interpretation before executing, so being wrong costs a sentence, not an implementation. Cost asymmetry is the core principle.
- A decision boundary. Know when not to shape - already-specific requests, informational asks, and post-correction execution should bypass the loop entirely.
- Grounding before proposing. Scan the environment for unstated constraints and reasonable defaults rather than interviewing the user about things the codebase already answers.
- Explicit assumptions, elicited non-goals. Out-of-scope and assumptions are first-class fields, not afterthoughts.
- A convergence artifact. The dialogue terminates in a copyable spec (goal / scope / assumptions / success criteria) that downstream artifacts can quote verbatim, or a markdown file on disk that can be read in a new session.
- Executable verification. Success criteria resolve to a concrete check (test, command, or assertion), and the loop terminates when the check passes.
- Technique-to-model matching. Specificity, few-shot, CoT, decomposition are not universally good; they have context/latency costs and are model-specific. A good system selects techniques conditionally.
- Iteration as measurement, not faith. You can’t reason your way to the right phrasing - prompts are brittle (word order, example ordering swing accuracy by tens of points) [[M]](#ref-m), so shaping is a design loop with a control group, not a one-shot edit.

I decided to implement two specific versions of this:

1. For clarifying and forming prompts for frontier models, [shaping-prompts](../../skills/shaping-prompts/SKILL.md) scans your environment for context up-front, interviews the user one question at a time until every prompt structure requirement is met.
2. A separate version, specifically for small local models with limited to no reasoning capabilities ([shaping-small-model-prompts](../../skills/shaping-small-model-prompts/SKILL.md)). An extended version of the first skill that tries to target model based on capabilities, context size, etc. Creates CoT exemplars when the problem includes math/logic/symbolism, breaks large tasks into chains of prompts, etc.

## Prompt Composition and Prompt Generation

> "Your repeated prompt clauses are a library waiting to be built."

When first starting to use AI, it doesn't take long before you start seeing patterns or clauses that you frequently repeat in your prompts: "do not make assumptions or design decisions yourself surface all blocking questions to the user", "write a detailed plan with code blocks for new code, diffs for things that change, and mermaid diagrams for complex relationships and flows", "no mistakes!", etc. It is convenient to be able to save and quickly apply those prompt fragments to whatever prompt you are working on.

There are also a lot of patterns and conventions for generalizing or optimizing prompts using tools or other software. These tools help you build or generate quality prompts or provide high-level interfaces for running some kind of optimization loop.

I'm not going to mention any prompt generator tools here, because the point of this series is learning how to do this stuff "the hard way", but once you get to that point, then it might make sense to leverage a tool that can make your daily work easier or more efficient.

One prompt generation tool I do want to mention is [DSPy](https://dspy.ai). It lets you write your prompts as Python code. Classes, variables, functions, etc., all carry some kind of metadata - from type, to the way things are named, to how they are composed, etc. That can all be leveraged to generate very precise queries, and the prompts produced are designed to be very effective across a wide variety of models and capabilities. But you don't have to just go with the default prompts it produces, it has built-in optimization processes you can use to test and fine-tune your prompt. It even has a module to implement optimization using [GEPA](https://dspy.ai/api/optimizers/GEPA/overview/).

The idea of a "prompt composer" is also interesting, as it sits somewhere between hand-written prompts and a full prompt generator tool. Select individual parts or clauses to construct a complex prompt from multiple fragments. I see there are quite a few tools out there: [Vapi](#ref-n), [SnapLogic](#ref-o), etc. But the general idea is so simple and straightforward, you can easily make your own tool and then start collecting prompt fragments that you repeatedly use.

As an example, here is my hand-rolled "prompt fragments" extension for pi. One of the things I love about the pi coding agent is just how easy it is to extend and modify. This is not some revolutionary extension, it's just an example of a simple hack to make my life a little easier.

1. Start with your basic prompt
![a basic prompt](./images/prompt-fragments-1.png)
2. Launch the composer dialog with a keybinding
![prompt composer](./images/prompt-fragments-2.png)
3. Select the fragments you wish to append/prepend to your prompt
![composed prompt](./images/prompt-fragments-3.png)

## Conclusion

> "The only durable prompt-engineering skill is the habit of testing every model yourself."

Prompt engineering is a complex, moving target. What was true today probably won't be true in 6 months. The only way to know what is effective is to experiment and test with every model you intend to use, and to do it all over again when those models release brand new versions. If we're lucky, that means we'll be able to do less prompt engineering.

Carefully crafting and optimizing prompts (and skills) to specifically target a local or small open-weight model is a cost-effective way to get consistent, quality results from a model that may seem useless to people who haven't gone down this rabbit hole.

Look for ways to compose, generate, and optimize your prompts. Composition and generation can save a lot of time for day-to-day work, and optimization helps keep consistent and accurate results.

## References

- <a id="ref-a"></a>**[A]** [Google Cloud - What Is Prompt Engineering?](https://cloud.google.com/discover/what-is-prompt-engineering)
- <a id="ref-b"></a>**[B]** [Chroma - Context Rot: How Increasing Input Tokens Impacts LLM Performance](https://research.trychroma.com/context-rot)
- <a id="ref-c"></a>**[C]** [HumanLayer - Context-Efficient Backpressure for Coding Agents](https://www.humanlayer.dev/blog/context-efficient-backpressure)
- <a id="ref-d"></a>**[D]** [HumanLayer - Advanced Context Engineering for Coding Agents](https://www.humanlayer.dev/blog/advanced-context-engineering)
- <a id="ref-e"></a>**[E]** [IBM - Prompt Engineering Techniques](https://www.ibm.com/think/topics/prompt-engineering-techniques)
- <a id="ref-f"></a>**[F]** [DSPy - dspy.GEPA: Reflective Prompt Optimizer](https://dspy.ai/api/optimizers/GEPA/overview/)
- <a id="ref-g"></a>**[G]** [Brown et al. - Language Models Are Few-Shot Learners](https://arxiv.org/html/2005.14165v4)
- <a id="ref-h"></a>**[H]** [Wei et al. - Chain-of-Thought Prompting Elicits Reasoning in Large Language Models](https://arxiv.org/html/2201.11903v6)
- <a id="ref-i"></a>**[I]** [Stealing Reasoning Traces from Proprietary LLM APIs](https://arxiv.org/html/2608.09867v1)
- <a id="ref-j"></a>**[J]** [Anthropic - Detecting and Preventing Distillation Attacks](https://www.anthropic.com/news/detecting-and-preventing-distillation-attacks)
- <a id="ref-k"></a>**[K]** [Reuters - OpenAI Says China's DeepSeek Trained Its AI by Distilling US Models](https://www.reuters.com/world/china/openai-accuses-deepseek-distilling-us-models-gain-advantage-bloomberg-news-2026-02-12/)
- <a id="ref-l"></a>**[L]** [obra/superpowers - Brainstorming Skill](https://github.com/obra/superpowers/blob/main/skills/brainstorming/SKILL.md)
- <a id="ref-m"></a>**[M]** [Lu et al. - Fantastically Ordered Prompts and Where to Find Them](https://arxiv.org/abs/2104.08786)
- <a id="ref-n"></a>**[N]** [Vapi - AI Prompt Composer](https://vapi.ai/blog/vapi-ai-prompt-composer)
- <a id="ref-o"></a>**[O]** [SnapLogic - Prompt Composer](https://docs.snaplogic.com/agentcreator/prompt-composer/agentcreator-promptcomposer-about.html)
