# Writing Skills Deep Dive - Part 1: Basics

Have you ever tried to write a skill, but the AI couldn't figure out how to execute certain steps or, even worse, completely disregard important rules from your instructions? Maybe the skill doesn't fire when you expect it to, or fires too frequently and runs when you don't want it? Then you add more and more rules, change wording to further emphasize rules that should not be broken? Did you end up with a 3K line markdown file that you were not satisfied with?

I spent some time experimenting with `superpowers` and was impressed by how well the skills triggered and how they implemented a full end-to-end development system. I was particularly impressed at how well the skills would stick to the rules, even in long-running sessions.

[agentskills.io](agentskills.io) has a skills guide, and the official skills spec, and a `python` package, called `agentskills`, that can verify and validate your skill file and front-matter. They also described processes for testing and optimizing triggering and testing the product of what the skill can produce.

I also watched a presentation about how Google DeepMind team writes skills, which covers much of the same stuff but adds more specific advice and a sort of recipe for writing and developing skills.

This entry will just explore the basics and not go into testing or optimization. The follow-up to this post will cover trigger and pressure testing and we'll build our own "eval" harness to carry out the tests.

## Basics

Skills are a mechanism for extending AI agent capabilities or enforcing conventions or preferences. Skills provide instructions or context on-demand - skills are a formalized implementation of progressive disclosure.

> TODO: ascii art skill file/folder layout

The DeepMind presentation classifies skills into two categories:

1. Capability: teaches the agent something it doesn't know how to do today.
2. Preferences: encodes preferences, conventions, workflows that are specific to your project or environment.

Capability skills may become unnecessary as models evolve and become more capable. Preference skills are custom rules that are unlikely to ever be integrated into the models - they are "durable."

Superpowers breaks things down into 4 types of skills but I prefer the capability/preference explanation. However, superpowers calls out the concept of "discipline" - rules you add to steer or correct agent behavior while executing a skill. Discipline rules that are intended to prevent the agent from doing something wrong are called "prohibitions."

## Human vs. AI

The first rule from the DeepMind presentation was to write the initial skill content yourself. AI-generated skill definitions tend to contain a lot of unnecessary statements, no-ops, or rules based on something that happened in the context when the skill was written but make no sense when the skill is executed in a different session.

When we get to testing and optimization, the AI will take over editing the skill file, but it will do so under very specific instructions. You just need to make sure it stays concise and free of no-ops or contradictory instructions.

One of the first big skills I tried to write ended up with a lot of unnecessary text prohibiting the execution of certain instructions that existed in previous drafts of the skill file. I would decide to completely remove a rule or a piece of information from the skill file and ask the AI to do it. Instead of simply removing it, it would replace the text with a statement explaining that the specific rule is not applicable, until the skill body was littered with "tombstone" comments about rules that didn't exist.

## Descriptions and Triggers

Skills are activated using the `skill` tool in your coding agent. The system prompt managed by your coding agent contains instructions on how to detect and dispatch skills based on words or phrases from your prompt. The `description` of each skill is loaded into the context window and that is what is used to match against your prompt.

A good description should have the following properties:
- Include what (capability) and when (triggers)
- Should be short (< 1024 characters) because every skill description takes space in your context window.
- Triggers the skill based on phrases you intend to active.
- Does not "hijack" phrases that should load other skills, or not load a skill at all.
- Does not paraphrase the contents of the skill - AI will cheat and not load the skill if the description already has a TLDR of what it does.

How do you write skill descriptions that trigger when you want them to, and not when you do not want them to? With a process called "trigger testing," which we will be doing later, after covering the basics of skill files first.

You can also define skills that do not auto-trigger, and use them explicitly like slash-commands. I like this because I'm used to working in command mode, either in my terminal or in my text editor. A skill defined like this does not take up as much context, never hijacks another prompt, doesn't require any trigger testing or optimization. The trade-off is that it becomes something you do explicitly, rather than implicitly based on an LLM interpreting your prompt.

To make a skill that does not auto-trigger, replace the `description: ...` in the front-matter with `disable-model-invocation: true`.

## Content

The body of your `SKILL.md` file contains the instructions or context that the agent should follow to accomplish a task.

Skill files should be short: <500 lines. When a skill is invoked, the entire contents of the skill file will be loaded into the context window. This means that every no-op statement, every paragraph of flowery prose that could be concise directives, become bloat that wastes context space. Anything that is obvious, or that the agent can easily figure out on it's own is also waste (we'll see how to detect that with eval tests later).

A skill should start with an overview that states it's core principals in 1-2 sentences. It should contain a section that describes when to use the skill, and when not to use the skill. These sections give the AI a chance to abort early, after triggering the skill, if it's not actually applicable to the current problem context.

One frustration I have encountered is how often the AI will forget or ignore an instruction by rationalizing a reason to circumvent a rule that is making it hard to accomplish its task. A process called "pressure testing" can be used to ensure your skill's rules are consistently followed. We'll cover pressure testing in the next installment.

One way to make your rules more effective, and less likely to be ignored, is to avoid the use of passive phrasing. Don't say "X is preferred" because that gives the AI room to decide that the rule isn't necessary. Instead, use strongly worded phrases like "always use X" or "X must be used when Y happens".

Where possible, include an example of important outputs, like templates or snippets that illustrate what you want the AI to do. Focus on one complete example and do not dilute the skill definition by duplicating examples in multiple languages - the AI can map the example to the target language.

Including a checklist or verification procedure at the end allows the AI to self-check its work. I find that this frequently surfaces issues that the AI skipped over, or that were introduced while it was refactoring. Having a verification procedure ensures that the AI is forced to check each item in the list before claiming a task is completed.

Some suggested best practices:
- Write concise directives, not essays.
- Keep free of no-ops, commentary, or unnecessary rules.
- Focus on goals and constraints, not a step-by-step process or rigid execution path.
- Include examples to illustrate what you want.
- Avoid passive phrasing when describing rules.
- Include a checklist or verification process.
- Give the agent freedom to complete the task (don't micro-manage execution steps or exact commands).

## Progressive Disclosure

Probably, you are already familiar with the concept of "progressive disclosure" - loading targeted chunks of information into context, when they are needed, leaving more operating overhead for the agent to work when they are not needed. But it's worth pointing out that skills are just a standardized implementation for progressive disclosure that follow specific conventions and file/folder layout.

The concept of progressive disclosure also applies to the skills themselves. If you write a skill that is 200K lines long, then you fill up your context window as soon as the skill is loaded. Even if your skill is much shorter than that, any lines which are not actually used in your session - rules about corner-cases or errors that never happen, for example - are just taking up space in your context window.

You can extract these corner-cases from the `SKILL.md` file and move them to their own files under the `references` directory, then link them into the main file with instructions to read the reference when a certain condition is met. This is worth doing when the instructions to be extracted are longer than the instructions they would be replaced with (evaluate a condition and load the reference file).

However, a reference file that is ALWAYS loaded whenever you use the skill is pointless. It's no different than just keeping it inline because it still fills up your context window.

- Keep the main skill file short and only cover the "happy path."
- Move corner-cases and error handling instructions to reference files and only load them when they are actually needed.
- Reference files that are always loaded are pointless (they do not help managing context bloat).

## Determinism, Rigid Processes, and Scripts

LLMs are non-deterministic. Partly by design (sampling and temperature), and partly because of many little factors that affect computation, like rounding errors in precise floating-point math or differences in how data is processed on parallel GPUs. This means that you can give an agent the same instructions many times, and it will take slightly different route to get there each time (or maybe VERY different routes).

A rule from the DeepMind presentation that surprised me: let the agent find it's own way to the solution. Don't try to prescribe exact step-by-step instructions. LLMs are non-deterministic by nature, but they are designed to reason and figure out a solution with iteration. The AI will find its way to the solution but will always take a different approach each time.

You may see it doing things that obviously won't work, but eventually figure it out. My initial instinct was to lock that down with tighter rules, so it never tries to execute commands that will not work, or to tell it exactly what to do at each step. But these rigid execution steps seem to cause even more problems. Instead, just focus on goals and constraints and give the AI freedom to find it's own way. Only when you see it do something bad, or consistently struggle to figure out the next step, should you add discipline rules to correct it.

If something needs to be a rigid step-by-step process or precise execution procedure, write a script instead. You can ask the LLM to write the script, or if you see the agent frequently writing an ad-hoc script for the same step each time, ask it to save it as a reusable script. In fact, any time you can move deterministic logic to a script instead of having an LLM interpret it each time, that will save token costs and ensure more consistent application.

Keep the LLM evaluation for places where you _need_ reasoning or semantic understanding.

## Issues

Some issues I've observed (not counting issues with testing processes):

- Too many skills bloat your context window. Try to disable plugins or skills that you don't need for the current session.
- Descriptions from other skills influencing LLM reasoning, contaminating the context window.
- Skills that never seem to fire automatically, or skills that fire too broadly and hijack prompts they shouldn't receive.
- LLM deciding NOT to execute a skill that should have triggered, because the skill description had a TLDR of the process it encapsulates. "I don't need to read the skill, I already know what to do from the description."
- Prompt-injection attacks from the `description` field of third-party skills.

It mostly comes down to context window management, triggering, and contaminating your context with instructions you don't always want.

I should also point out that descriptions from third-party skills you install are a prime vector for prompt injection attacks. This will become clear when you start doing trigger and pressure testing campaigns, as descriptions from other skills will frequently cause your agent to exhibit undesired behavior for the test scenario.

## Example

Here is our own `writing-skills` skill, based largely on the `superpowers` version, containing everything we've covered in this document, and nothing we haven't covered yet (testing and optimization rules).

[writing-skills (without testing)](./writing-skills.md)

You can use this to write a new skill, iterate on a skill, or clean-up an existing skill. Whenever we run a test campaign and optimization loop, a skill like this will be loaded into context to ensure the AI follows these rules when modifying the skill.

In the following installments, we'll augment this skill to focus on writing optimal descriptions, writing discipline rules, and testing skills.

## References

- [Agentskills.io spec + guide](https://agentskills.io)
- [Superpowers "writing-skills" skill](https://github.com/obra/superpowers/blob/main/skills/writing-skills/SKILL.md)
- [DeepMind - Don't Ship Skills Without Evals](https://youtu.be/0vphxNt4wyk?si=j9E5D7a-scWELD6_)
