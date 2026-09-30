# Writing Skills Deep Dive - Part 4: Revelations

testing skills turned out to be way more important than i realized; and not just skills, but every type of prompt. i spent a lot of tokens and a lot of time trying to understand the _why_ behind how agents are inconsistent, and how to fix that. i've also been thinking a lot more about when/where to use custom harnesses or applications and writing different types of agents, outside of just using a general coding assistant.

i made some mistakes along the way to writing the eval harness, like over-training my skills on really weak local models. i started with this idea that running the evals on the local models would harden the skills so they work well on every model. that caused some of the skills to bloat with repeated or expanded sections and clauses that are completely unnecessary for the models i actually use for general work.

once i realized i had made a mistake, i decided to use an "ablation" process to empirically prune away the extra rules and facts from those bloated skills. any eval that repeatedly passes a control test on my actual target model can be removed from the skill to save tokens. of course i had to build an ablation process into my already complicated eval harness to make this possible.

i also found some tricks to help manage costs, like smoke-test reps, using the right model for the job, excessive validation before execution, and early exit logic to prevent running more reps if something goes wrong.

finally, i started looking at off-the-shelf solutions instead of building and maintaining all of this stuff myself.

## The Case Against Auto-Invoking Skills

you write a skill, the agent loads the skill description into the system prompt, if the user prompt matches the skill description then the skill will be loaded automatically. except when it doesn't load the skill. or when it loads a skill you didn't intend.

what is the cost of a skill that doesn't fire when it's needed? if the skill has a reason to exist, then it needs to fire when expected. skills enforce discipline rules, which have compliance costs of some sort, so not firing the skill has some measurable, tangible cost.

what is the cost of a skill that fires when it's not supposed to? context pollution, loss of context token overhead, potentially conflicting rules or workflow steps that compete with your actual instructions. this affects everything you do after the skill is incorrectly loaded.

you can't count on 100% accuracy, only aim for a number approaching 100%. statistically extremely likely, but not guaranteed to work as expected.

I have observed lower-end models need more tuning to actually trigger the skill, higher-end models with CoT reasoning have a tendency to rationalize needing to load a skill when it's not actually needed (or vice-versa).

my suggestion: for coding assistants, use commands for things instead. they don't put description text in the context, you can load them by name or with a slash-command (harness specific), and you can tell the agent to manually load or pass the skill file if you need to hand it to subagents. you can say "use the X skill to ..." or even just point to a file path with a saved prompt.

auto-triggering skills is still important for a couple of scenarios though:
- automated development workflows or factories: when a task is broken into smaller components and each is delegated to a subagent, the subagent should pick up the correct skills for the job automatically. in claude code or codex, you can just tell the main agent to have the subagent load the skill, but if things are automated you may need auto-invocation.
- autonomous agents (not coding assistants) that use skills to execute actions based on user prompts or some form of input from another system. this is probably where you want auto-invocation and you want to constantly test and add new eval queries to match real world prompts.

## Model Coverage

optimize your skills for the models that you intend to use, and optimize them again whenever you change models or new versions come out.

if you have a skill that you only intend to use on high-end models with very large context windows, optimize the skills for that model, even if the process is expensive.

don't over-train on a low-end model if that is not what you actually intend to use. i did this to save money but the skills got bloated with very verbose wording over time. those extra rules and facts take up more context, require more test cases, for no value if the target model doesn't actually need them.

but training a skill on a specific local model DOES increase the accuracy and people use this technique to achieve similar results to a non-optimized prompt against a leading frontier model.

## Ablation and Retirement

rules or facts in a skill that are not needed just consume more context space, artificially inflate test scores.

ablation doesn't just apply to the rules in the skill file: test evals that never fail just make testing take longer and cost more tokens.

however, since execution is not 100% deterministic, it is still useful to keep evals for ablated rules for regression coverage for important invariant rules.

since i had over-trained my skills on a local model, i am using this process to identify, remove, and regression-test rules and facts that are not needed:
- when a control run passes all reps, don't bother with the skill run. mark that skill for ablation instead.
- when a rule marked for ablation has passed with only the control 3 times, then prompt the user to delete it, optionally keeping the eval as a regression test
- when a rule has been deleted but we're still covering it for regression, keep track of how many times in a row it passes without the rule. suggest removing the rule when confident the rule is covered intrinsically by the model.

## non-deterministic application requires deterministic verification

the verification checklists at the end of a skill/prompt are a big help, but not 100% guaranteed to avoid the issue.

try thinking about how to deterministically, and automatically, verify things the AI implements.

another agent, with a fresh context, can review output and session transcripts as well. also not a 100% guarantee, but useful for things that are hared to test normally and as an additional layer of protection.

## Some Tips on Controlling Costs

smoke tests: run a single rep from the first batch and bail if there is an error. don't run any further reps if the first one doesn't launch the eval successfully.

in campaign scenarios that start by running a control group - the eval query without the skill rule/fact in place. if the controls always pass, you can skip the actual test evals. this model doesn't need it, you can flag those rules for ablation.

the other cost management suggestion is to use the right model for the job. don't try to use a small or outdated model to do something complex, and you don't always need to use the biggest, most powerful model for every task. anthropic models, for example: use sonnet by default and use opus when you need the extra reasoning and context space. if you optimize the skills against sonnet, then you can get comparable results to using opus. the current economics around token consumption makes no sense, so i expect it won't be long before everyone is concerned with min-maxing token usage instead of token-maxing.

you can do a lot with a local model now. i'm currently using qwen3.8 27B on a 16G radeon card, which is surprisingly good and fast enough to be usable, but i could only squeeze about 80K tokens of context out of it. i also have a gemma4 26B-A4B model that is really fast, but not as smart and also has a small context window. but simple or straight-forward tasks can be delegated to these local models reliably, if the skills and prompts are optimized for those models.

## Bonus Rant: Markdown is a Terrible Programming Language

i may be out of line here, but when i hear people talking about "programming languages are dead" because you can do everything with yaml and markdown now, i think that is objectively worse. yaml has always been a pain in the ass to work with, but it least it's structured and can have a schema and mechanical checks and audits. it's the worst configuration language, except for all the other ones.

on reviewing, refactoring, and debugging markdown (it sucks; no systematic consistency like you get with code; seems more prone to duplication and drift than the code base). agents like to leave little "tombstone" markers where you asked it to remove a statement: "do not do X because we don't do X in this process any longer (Issue #1105)". that is not helpful and it's really easy to miss those types of things in a 5K line markdown diff.

like all things, you can try to train your agent to be more systematic and consistent: never leave "tombstones", always use mdl to lint and format, use a subagent to do a consistency check across the whole document, etc.

## An Even Better Harness

i did the first version from within the coding agent because i wanted to target the actual agent running the skills - the exact system prompt, routing, and tool calling conventions are important and have direct impact on how the skills execute, and i didn't want to reverse engineer a fast-moving target like a harness system prompt and implementation. but i already broke that rule by using custom agents that override the system prompt already, so that ship has sailed. still, a script-driven approach could still shell-out to headless CLI instances to run the evals and use an SDK to talk to the 'judgement' llm.

my harness works surprisingly well, but it's a bit messy. it started from a really promising design that i made and fed to the AI to build. but trying to reuse the evaluator script across four different types of tests made the code around this simple process much more complicated. i can tell that there is still too much happening in the skill vs what is happening in the script - this process needs to be driven by a deterministic program that calls the AI when it needs judgment, not driven by an agent that needs to sync data in and out of a script-based system.

i have been looking at DSPy (and their GEPA module) as a way to implement a better version of this. either using GEPA or porting my own testing and scoring code to DSPy directly.

DSPy is a python library that can talk to your LLMs. it flips the typical agentic coding paradigm by driving the process with a program and calling out the LLM only when you need inference. this works well for implementing an automated program that does something specific, like an eval harness for testing skills, for example.

TODO: example of DSPy doing something and then calling an llm

DSPy can also generate prompts from python code - functions, classes, attributes, and types can be cleverly used to generate a specific, optimized query for a special situation based programmatically.

TODO: example of DSPy generating prompt from code

but DSPy can do a lot more than that (check out the docs). i'm particularly interested in using it to optimize queries and prompts. you can write python functions to "score" a response from an LLM and DSPy will use one of several optimization strategies to automatically improve the prompt. so if we were to setup one of our test scenarios, then implement scoring methods (which can call out to LLMs as needed) to verify the results, and the framework will take care of the rest.

TODO: example of the DSPy implementation and a scoring method

## Quorum

TODO: hosted platform for running your evals across multiple models and providers; reminds me of a browserstack/sauce labs for ai agent skill evals.
