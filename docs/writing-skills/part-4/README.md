---
author: dczmer
date:   2026-10-04
---

# Writing Skills Deep Dive - Part 4: Revelations

Closing thoughts on the Writing Skills Deep Dive series. This is mostly opinions and advice but also a quick peek at DSPy and the potential for writing a much better test harness.

This is part 4 of "Writing Skills Deep Dive", continuing from [Writing Skills Deep Dive - Part 3: Bulletproofing](../part-3/README.md).

Testing skills turned out to be way more important than I realized - and not just skills, but every type of prompt you feed to a model. I spent a lot of tokens and a lot of time trying to understand the _why_ behind how agents are inconsistent, and how to fix that. I've also been thinking a lot more about when/where to use custom harnesses or applications, and when to write different types of agents, outside of just using a general coding assistant.

I also observed that the mechanism for auto-invoking skills is probably not the best model for applying context on demand. The user experience of the agent understanding what you want and applying it automatically sounds great, but it introduces the risk that it just won't get it right. But if you explicitly load skills, or use "slash" commands, then you can eliminate that risk.

I made some mistakes along the way to writing the eval harness - most notably over-training my skills on really weak local models (more on that in the Model Coverage section). Once I realized I had made a mistake, I decided to use an "ablation" process to empirically prune away the extra rules and facts from those bloated skills. Any fact/rule that repeatedly passes a control test on my actual target model can be removed from the skill to save tokens. Of course, I had to build an ablation process into my already complicated eval harness to make this possible.

I also found some tricks to help manage costs, like smoke-test reps, using the right model for the job, excessive validation before execution, and early exit logic to prevent running more reps if something goes wrong.

Finally, I started looking at off-the-shelf solutions instead of building and maintaining all of this stuff myself, as well as frameworks and tools like LangChain and DSPy to invert the model so deterministic programs are the driver and we only call the LLM where we actually need it.

## The Case Against Auto-Invoking Skills

> "You can't count on 100% accuracy — you can only aim for a number approaching it."

You write a skill, the agent loads the skill description into the system prompt. If a user prompt matches the skill description then the skill will be loaded automatically. Except when it doesn't load the skill. Or when it loads a skill you didn't intend.

What is the cost of a skill that doesn't fire when it's needed? If the skill has a reason to exist, then it needs to fire when expected. Skills enforce discipline rules, which have compliance costs of some sort, so not firing the skill has some measurable, tangible cost.

What is the cost of a skill that fires when it's not supposed to? Context pollution, loss of context token overhead, and potentially conflicting rules or workflow steps that compete with your actual instructions. This affects everything you do after the skill is incorrectly loaded.

You can't count on 100% accuracy, only aim for a number approaching 100%. Statistically, it's extremely likely but not guaranteed to work as expected.

I have observed my smaller local models need more tuning to actually trigger the skill, and the higher-end models with CoT reasoning have a tendency to rationalize needing to load a skill when it's not actually needed (or vice-versa).

My suggestion: for coding assistants, use "commands" or disable auto-invocation. They don't put description text in the context, you can load them by name or with a slash-command (harness specific), and you can tell the agent to manually load or pass the skill file if you need to hand it to subagents. You can say "use the X skill to ..." or even just point to a file path with a saved prompt.

Auto-triggering skills is still important for a couple of scenarios though:

- Automated development workflows or factories: when a task is broken into smaller components and each is delegated to a subagent, the subagent should pick up the correct skills for the job automatically. A human driving Claude Code or Codex can just tell the main agent to have the subagent load the skill, but if things are more automated, you may need auto-invocation.
- Autonomous agents (not coding assistants) that use skills to execute actions based on user prompts or some form of input from another system. This is probably where you want auto-invocation and you want to constantly test and add new eval queries to match real-world prompts.

## Non-Deterministic Application Requires Deterministic Verification

> "A prompt is not a program."

If there is a 99.9% chance that a skill will fire, or that the agent will stick to every rule and instruction in your prompts, what do you do about that 0.1% chance? Do you just accept it? In some cases you can totally accept it. In other cases, you know that you will eventually hit that 0.1% and it will have some cost, and you've probably built more things on top of this that will lead to cascading failures across a system.

The verification checklists at the end of a skill/prompt are a big help, but not 100% guaranteed to avoid the issue. Forcing the agent to work through the verification list means it has to address every item directly, but it still has a tendency to lie about some of the items - or maybe they were verified at some point but then the agent made more changes and broke something that was already verified.

Having another agent session review the implementation against the plan document and verify each checklist item helps a lot, at the cost of even more token spend. Maybe it goes from 0.1% failure to 0.01%. That's pretty close to the odds of having a catastrophic network or hardware failure even with code that is 100% deterministic.

But to build reliable products and services, try thinking about how to deterministically and automatically verify things the AI implements. Unit tests and audits are a good start, but tests can only prove the presence of a bug, never the absence of bugs. The process we used to "shape test" and "pressure test" skill bodies is an interesting approach: catalog each rule/requirement (or quality metric) and generate a small script or regex to score your results automatically.

Another way to improve reliability and determinism is to write programs that only call the LLM when inference is needed, and everything else is scripted. If it feels like I'm repeating this point, there is a reason: a prompt is not a program. LLMs are great at one-shotting something impressive, but bad at following a complex chain of actions and conditional execution, and bad at counting and math. Make things easy and set the model up for success by letting it do the things it's good at, and letting actual code handle everything else.

## Model Coverage

> "Don't over-train on a weaker model if that is not what you actually intend to use."

Optimize your skills for the models that you intend to use, and optimize them again whenever you change models or new versions come out. If you have a skill that you only intend to use on high-end models with very large context windows, optimize the skills for that model, even if the process is expensive.

Don't over-train on a weaker/local model if that is not what you actually intend to use. I did this to save money but the skills got bloated with very verbose wording over time. Those extra rules and facts take up more context and require more test cases for no real value if the target model doesn't actually need them.

But training a skill on a specific local model DOES increase accuracy - people use this technique to match, on a local model, what a non-optimized prompt gets from a leading frontier model. I'm personally having a lot of fun with a local Qwen3.8 27B (as of 2026-09-30) on a 16G graphics card - tuning skills against that model is free and it really does improve performance. Just beware that it tends to bloat the skill bodies as rules have to be expanded, repeated, and emphasized to make the model obey more consistently.

## Ablation and Retirement

> "Rules that are not needed just consume more context space and artificially inflate test scores."

As described by the "Don't Ship Skills Without Evals" presentation ([A](#ref-a)), newer models gain new capabilities with every version. Rules written to add new capabilities or correct undesirable behavior may become obsolete when the models learn how to do those things better intrinsically. Meanwhile, skills that encode preferences or proprietary processes or workflows will probably _never_ be handled by the model alone - these are durable skills, but individual rules may still become obsolete. ([A](#ref-a))

Ablation is the process of removing unnecessary rules or facts because the model doesn't need them. Rules that are not needed just consume more context space and artificially inflate test scores. We can do this by running "control" groups - the eval with the rule under test removed from the skill. If the control always passes, the rule is potentially eligible for ablation. 

Ablation doesn't just apply to the rules in the skill file: test evals that never fail just make testing take longer and cost more tokens. You may want to keep evals around after a rule has been deleted for regression coverage, but if it really never fails, you might as well drop it.

When every rule and fact in a skill can be removed via ablation, then you can retire the skill.

Since I had over-trained my skills on a local model, I am using this process to identify, remove, and regression-test rules and facts that are not needed:

- When a control run passes all reps, don't bother with the skill run. Mark that skill for ablation instead.
- When a rule marked for ablation has passed with only the control 3 times, then prompt the user to delete it, optionally keeping the eval as a regression test.
- When a rule has been deleted but we're still covering it for regression, count consecutive control passes, and suggest dropping the eval once you're confident the model handles that case intrinsically.

## Some Tips on Controlling Costs

> "The current economics around token consumption makes no sense, so expect everyone to start min-maxing token usage instead of token-maxing."

Smoke tests: run a single rep from the first batch and bail if there is an error. Don't run any further reps if the first one doesn't launch the eval successfully. This catches problems with the harness invocation, connection to the model server, or tests with bad prompts that always time out.

Control groups: if your campaign starts with control runs (see Ablation and Retirement) and the controls always pass, don't spend tokens on the test evals for those rules.

The other cost management suggestion is to use the right model for the job. Don't try to use a small or outdated model to do something complex, and you don't always need to use the biggest, most powerful model for every task. Anthropic models, for example: I use Sonnet by default, and reach for Opus or Fable only when I need the extra reasoning and context space. If you optimize skills against Sonnet, you can get results comparable to using Opus.

You can do a lot with a local model now. I'm currently using Qwen3.8 27B on a 16G Radeon card. The model is surprisingly good and fast enough to be usable, but I could only squeeze about 80K tokens of context out of it. I also have a Gemma4 26B-A4B model that is really fast, but not as smart and also has a small context window. But simple or straightforward tasks can be delegated to these local models reliably, if the skills and prompts are optimized for those models.

## Bonus Rant: Markdown is a Terrible Programming Language

> "Reviewing, refactoring, and debugging Markdown sucks."

I may be out of line here, but when I hear people talking about "programming languages are dead" because you can do everything with YAML and Markdown now, I think that is objectively worse. YAML has always been a pain in the ass to work with, but at least it's structured and can have a schema and mechanical checks and audits. It's the worst configuration language, except for all the other ones.

An LLM can "see" and understand the entire context at once. Thanks to attention, AI doesn't get confused when a document starts talking about complex details relating to something that isn't even defined until the very end of the document. A human trying to read a document like this will be completely lost. When AI is writing and updating the Markdown autonomously, it doesn't bother to keep it optimized for human readers.

Reviewing, refactoring, and debugging Markdown sucks. There is no systematic consistency validation like you get when compiling or interpreting code, and it seems more prone to duplication and drift than code. For example, agents like to leave little "tombstone" markers where you asked them to remove a statement: "do not do X because we don't do X in this process any longer (Issue #1105)". That is not helpful, and it's really easy to miss those types of things in a 5K-line Markdown diff. Correcting the way AI does code comments and documentation is on my short-list of must-have solutions.

Like all things, you can try to train your agent to be more systematic and consistent: never leave "tombstones", always use mdl to lint and format, and use a subagent to do a consistency check across the whole document, etc. But this is just one tiny aspect in one specific domain. If you have to fine-tune and correct everything the AI does, then you run into hard context management problems and it becomes less clear whether AI is actually improving your process or making things easier.

## An Even Better Harness

> "It didn't solve the separation of deterministic code from inference; it just moved the non-deterministic aspects to another location."

I did the first version from within the coding agent because I wanted to target the actual agent running the skills - the exact system prompt, routing, and tool calling conventions are important and have direct impact on how the skills execute, and I didn't want to reverse engineer a fast-moving target like a harness system prompt and implementation. But I already broke that rule by using custom agents that override the system prompt, so that ship has sailed. Still, a script-driven approach could shell out to headless CLI instances to run the evals, and use an SDK to talk to the 'judgement' LLM.

My harness works surprisingly well, but it's a bit messy. It started from a really promising design that I made and fed to the AI to build. But trying to reuse the evaluator script across four different types of tests made the code around this simple process much more complicated. I can tell that there is still too much happening in the skill vs what is happening in the script - the script is doing the deterministic parts but the agent is driving so it has to transfer a ton of information back and forth to the script and make calls with really complicated arguments to bridge that info back into the deterministic part. It didn't solve the separation of deterministic code from inference; it just moved the non-deterministic aspects to another location.

My opinion is that processes like these test campaigns should be driven by a script and call out to an LLM for judgment, not the other way around. So I have been looking at DSPy (and its GEPA module) as a way to implement a better version of this - either using GEPA, or porting my own testing and scoring code to DSPy directly. There are a ton of tools and SDKs I could use to do this, but DSPy seems interesting to me.

DSPy is a Python library that can talk to your LLMs. It flips the typical agentic coding paradigm by driving the process with a program and calling out to the LLM only when you need inference. ([B](#ref-b)) This works well for implementing an automated program that does something specific, like an eval harness for testing skills, for example.

A minimal DSPy program that calls an LLM only for the inference step:

```python
import dspy

# Point DSPy at a local, OpenAI-compatible server (e.g. vLLM, llama.cpp).
lm = dspy.LM("lamma.cpp/qwen3.8-27b", api_base="http://localhost:8000/v1")
dspy.configure(lm=lm)

class TriggerCheck(dspy.Signature):
    """Decide whether the user's request should load the named skill."""
    request: str = dspy.InputField()
    skill_name: str = dspy.InputField()
    should_load: bool = dspy.OutputField()

judge = dspy.ChainOfThought(TriggerCheck)

# Deterministic Python drives the loop; the LLM is called only for inference.
for query in load_queries("skills-workspace/trigger-tests/queries.json"):
    prediction = judge(request=query.text, skill_name=query.skill)
    if prediction.should_load != query.expected:
        log_mismatch(query, prediction)
```

DSPy can also generate prompts from Python code - functions, classes, attributes, and types can be used to programmatically generate a specific, optimized query for a special situation.

A class-based signature: the class name, docstring, field types, and field descriptions are what DSPy turns into the rendered prompt:

```python
from typing import Literal
import dspy

class TriggerVerdict(dspy.Signature):
    """Classify whether a user request should load a specific skill."""
    request: str = dspy.InputField(desc="the raw user prompt")
    skill: str = dspy.InputField(desc="the candidate skill's name")
    verdict: Literal["load", "skip"] = dspy.OutputField()
    rationale: str = dspy.OutputField()

classify = dspy.Predict(TriggerVerdict)
result = classify(
    request="review docs/writing-skills/part-4/README.md",
    skill="reviewing-blog-posts",
)
print(result.verdict)  # "load" or "skip"
```

But DSPy can do a lot more than that ([check out the docs](https://dspy.ai/current/getting-started/program-dont-prompt/)). I'm particularly interested in using it to optimize queries and prompts. You can write Python functions to "score" a response from an LLM, and DSPy will use one of several optimization strategies to automatically improve the prompt. So if we set up one of our test scenarios and implement scoring methods (which can call out to LLMs as needed) to verify the results, the framework will take care of the rest.

A scoring method for a trigger test, as a plain Python function that DSPy can optimize against:

```python
import dspy

def trigger_metric(example, prediction) -> float:
    """Score a trigger-test prediction against its expected verdict."""
    if prediction.verdict == example.expected_verdict:
        return 1.0
    return 0.0

evalset = [
    dspy.Example(
        request="just fix the typos in this post",
        expected_verdict="skip",
    ).with_inputs("request"),
    dspy.Example(
        request="review docs/writing-skills/part-4/README.md",
        expected_verdict="load",
    ).with_inputs("request"),
]

evaluate = dspy.Evaluate(devset=evalset, metric=trigger_metric)
score = evaluate(classify)
```

## Off-the-Shelf Solutions

I found a lot of interesting tools and frameworks for optimizing AI systems, but most were specific to optimizing agents or full-stack AI applications, not about testing and verifying skills. I did find a few interesting things to consider, but they fall into the category of skill generators or optimizers, where our implementation is more of a verifier.

The three testing skills we created in this series (pressure, retrieval, and shape) decompose a skill into individual rules and facts, classify each one by type, and run a purpose-built campaign per rule. We use control arms to verify the rule is actually needed, run each test in a fresh context, execute them with a restricted headless agent, and score them against explicit expectations. Fixes are disciplined, not free-form: the edit has to match the observed failure category (a rationalization table for pressure failures, a positive recipe for shape failures, and doc edits for retrieval failures). And the whole thing exists to produce _verdicts_ - bulletproof, no-failure, flag-for-ablation - not just a better skill.

### GEPA (or DSPy + GEPA)

> "The Pareto frontier keeps those alternative lineages alive so the search doesn't get painted into a corner by the first strong candidate."

GEPA (Genetic-Pareto) is a generalized reflective prompt optimizer - an evolutionary optimizer for any text component of an AI system, whether that's a prompt, a skill, a code file, or a config. You give it a candidate text and a scoring metric, it runs the system, reads the full execution traces (tool calls, reasoning, and error messages), and uses a judge LLM to reflect on _why_ the candidate failed and propose targeted mutations. Repeat until the budget is exhausted. ([C](#ref-c))

The "Pareto" part is the clever bit: instead of only keeping the single best-scoring candidate, GEPA keeps a pool of the top-performing mutations across different task instances. A prompt that emerges early as the best candidate may have a limited performance ceiling, and a greedy optimizer keeps polishing that one form instead of stepping back and trying a different approach entirely. The Pareto frontier keeps those alternative lineages alive so the search doesn't get painted into a corner by the first strong candidate.

The paper reports beating reinforcement learning (GRPO) by 6% on average (and by up to 20%) while using up to 35x fewer rollouts - and beating the previous best prompt optimizer, MIPROv2, by over 10%. ([C](#ref-c)) Since you can optimize against cheap or local models, the whole process is supposedly much cheaper than fine-tuning. It's available as a standalone library, as a DSPy module (write scoring functions - which can call a judge LLM or verify things deterministically - and it auto-optimizes your prompt), and is even packaged as an agent skill you can use to optimize anything. ([C](#ref-c), [D](#ref-d))

Compared to our approach, the reflection loop is essentially what we do manually: read the transcript, diagnose the failure, edit the skill, and re-run. The metric plays the role of our expectation rubrics.

GEPA optimizes the whole skill (or prompt or other artifact) against end-task success. Its mutations are free-form rewrites, while our fixes are constrained to match the failure category - and that constraint is load-bearing, because we know from testing that the wrong form of fix backfires (prohibitions cause failure migration, nuance clauses add noise).

GEPA has no equivalent of our control arms and ablation flags: it will happily keep optimizing a rule that never mattered, because it has no concept of "this rule is unnecessary, delete it." GEPA is an optimizer that produces a mutated artifact, while our harness is a test suite that produces verdicts. Those are different outputs.

Verdict: the most promising of the three as a foundation for a better harness, mainly because the architecture is exactly the inversion I argued for above - a deterministic program driving the loop, calling the LLM only for judgment and mutation. I could see GEPA automating the REFACTOR loop of a pressure campaign or the variant search of a shape campaign. But the campaign design - rule classification, control arms, per-rule verdicts, and ablation - would still be ours to build on top.

### Microsoft SkillOpt

> "SkillOpt is a skill training framework, not a testing framework — if the goal is 'prove which rules actually bind,' it doesn't answer that question at all."

SkillOpt is Microsoft's take on the same idea. A target model executes tasks in a "forward" pass, a separate _optimizer model_ reflects on the resulting trajectories in a "backward" pass and proposes edits to the skill, then a validation gate decides whether to keep the candidate. It borrows the whole ML training discipline - epochs, batch sizes, learning rates, and strict train/validation splits - and applies it to a markdown document instead of weights. The output is a deployable `best_skill.md`. ([E](#ref-e))

Of the three, this one is closest in spirit to our approach: it optimizes skill documents specifically (not arbitrary prompts), and the train/validate split mirrors what we did in the trigger-testing skill (though we never applied that discipline to the other test tracks). But the core differences are the same as GEPA's. SkillOpt optimizes end-task success of the whole skill, while we test rule by rule. And while our process applies a fixed mitigation matched to the failure category - a rationalization table for a pressure failure, a positive recipe for a shape failure - SkillOpt's optimizer model invents its own edits from whatever it observes in the trajectory. It would probably converge on something like a rationalization table after seeing rationalization in a trace, but as an emergent edit, not as a disciplined response with a known reason behind it.

Verdict: SkillOpt is a skill _training_ framework, not a testing framework - it assumes you already have tasks and a metric, and you just want the skill to get better at them. If the goal is "make the agent better at X," it's a strong option. If the goal is "prove which rules in this skill actually bind, and which can be deleted," it doesn't answer that question at all.

### Trace2Skill

> "It's a generator, not a verifier."

Trace2Skill, from the Qwen team, goes in a different direction: it _authors_ skills from execution traces. You point it at a pool of agent trajectories - and optionally an existing skill definition - and multiple analyst agents process the traces in parallel, proposing patches that a consolidation step merges into a unified, conflict-free skill directory. It supports two modes: "deepening" an existing human-written skill with lessons distilled from real runs, and creating entirely new skills from scratch. ([F](#ref-f))

It consumes the same raw material our harness produces - transcripts of agents succeeding and failing - but runs the pipeline in the opposite direction. We start from a hand-authored skill and measure whether its rules bind, while Trace2Skill starts from observed behavior and induces what the rules should have been. There are no control groups, no per-rule verdicts, no pressure scenarios, because it isn't measuring compliance at all - it's mining experience for content.

Verdict: Authoring and maintaining skill content is the step _before_ our harness becomes relevant, and distilling production traces into skill updates is a genuinely useful capability - especially for the autonomous-agent scenario where you want skills to keep pace with real-world usage. I could imagine using Trace2Skill to draft or enrich a skill, then running our campaigns to verify the result. But it's a generator, not a verifier, and it's not a foundation for a better test harness.

## Conclusion

> "Testing tells you which rules bind; ablation tells you which rules never did."

Four parts in, the arc of this series went from writing a skill, to testing whether it fires, to testing whether its rules bind, to deciding what to delete. If there's one takeaway from the whole exercise, it's that a skill is never finished - it just gets better-tested.

## References

- <a id="ref-a"></a>**[A]** [Google DeepMind (Philipp Schmid) - Don't Ship Skills Without Evals](https://youtu.be/0vphxNt4wyk?si=j9E5D7a-scWELD6_)
- <a id="ref-b"></a>**[B]** [DSPy - Program, Don't Prompt](https://dspy.ai/current/getting-started/program-dont-prompt/)
- <a id="ref-c"></a>**[C]** [GEPA - Reflective Prompt Evolution Can Outperform Reinforcement Learning](https://arxiv.org/abs/2507.19457)
- <a id="ref-d"></a>**[D]** [gepa-ai/gepa](https://github.com/gepa-ai/gepa)
- <a id="ref-e"></a>**[E]** [Microsoft Research - SkillOpt: Agent Skills as Trainable Parameters](https://www.microsoft.com/en-us/research/blog/skillopt-agent-skills-as-trainable-parameters/)
- <a id="ref-f"></a>**[F]** [Qwen-Applications/Trace2Skill](https://github.com/Qwen-Applications/Trace2Skill)
