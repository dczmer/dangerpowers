# Writing Skills Deep Dive - Part 1: Basics

Have you ever tried to write a skill, but the AI couldn't figure out how to execute certain steps or, even worse, completely disregard important rules from your instructions? Maybe the skill doesn't fire when you expect it to, or fires too frequently and runs when you don't want it? Then you add more and more rules, change wording to further emphasize rules that should not be broken? Did you end up with a 3K line markdown file that you were not satisfied with?

I was inspired by how well `superpowers` skills fire and how well they stick to the rules, so I did some research on their `writing-skills` meta-skill. I also researched the `agentskills.io` spec and their advice for writing and testing skills. Finally, I watched a presentation by someone from Google DeepMind team that pulls everything together and gives a kind of recipe for writing and managing skills. (All references are linked at the bottom of the document).

This entry will just explore the basics and not go into testing or optimization. The follow-up to this post will cover trigger and pressure testing and we'll build our own "eval" harness to carry out the tests.

## Basics

Skills are a mechanism for extending AI agent capabilities or enforcing conventions or preferences. Skills provide instructions or context on-demand - skills are a formalized implementation of progressive disclosure.

```
my-skill/
├── SKILL.md           # skill definition/instructions
├── scripts/           # helper scripts (optional)
├── references/        # reference docs (optional)
```

A skill is a directory with a SKILL.md in it. The frontmatter has a `name` and a `description`, and those two fields are the only part that gets pre-loaded into the system prompt at startup. Everything else is read on demand. So the description is not documentation, it's the router. If it's vague, the skill never fires and you spend an afternoon debugging a prompt when the actual bug is one line of yaml.

The rest of it comes down to four things:
* Be concise, because the context window is shared with everything else the agent needs to know.
* Match how specific your instructions are to how easy the task is to get wrong.
* Split content out into files that only get read when they're needed.
* Build the evals first, before you write the doc.

The Google DeepMind presentation classifies skills into two broad categories:

1. Capability: teaches the agent something it doesn't know how to do today.
2. Preferences: encodes preferences, conventions, workflows that are specific to your project or environment.

Capability skills may become unnecessary as models evolve and become more capable. Preference skills are custom rules that are unlikely to ever be integrated into the models - they are "durable."

Superpowers breaks things down into 4 types of skills but I prefer the capability/preference explanation. However, superpowers calls out the concept of "discipline" - rules you add to steer or correct agent behavior while executing a skill. Discipline rules that are intended to prevent the agent from doing something wrong are called "prohibitions."

## Start Small

The first rule from the DeepMind presentation was to **write the initial skill content yourself**. AI-generated skill definitions tend to contain a lot of unnecessary statements, no-ops, or rules based on something that happened in the context when the skill was written but make no sense when the skill is executed in a different session.

When we get to testing and optimization, the AI will take over editing the skill file, but it will do so under very specific instructions. You just need to make sure it stays concise and free of no-ops or contradictory instructions.

In fact, the common advice is actually to NOT write a skill right away, but to build one up with a TDD-like approach (basically the opposite of how everyone writes skills):
1. Run the agent on real representative tasks with no skill at all. Write down where it failed.
2. Build three scenarios that test those specific failures.
3. Measure the baseline without the skill.
4. Write the minimum instructions that fix the observed gaps.

The point is that you build-up the skill by solving actual real-world problems instead of ones you just predicted/imagined. But since we are only talking about "what is a skill" and not covering evals yet, this advice must be deferred to later installments.

## Descriptions and Triggers

Skills are activated using the `skill` tool in your coding agent. The system prompt managed by your coding agent contains instructions on how to detect and dispatch skills based on words or phrases from your prompt. The `description` of each skill is loaded into the context window and that is what is used to match against your prompt.

A good description should have the following properties:
- Include what (capability) and when (triggers)
- Should be short (< 1024 characters) because every skill description takes space in your context window.
- Triggers the skill based on phrases you intend to active.
- Does not "hijack" phrases that should load other skills, or not load a skill at all.
- Does not paraphrase the contents of the skill - AI will cheat and not load the skill if the description already has a TLDR of what it does.

How do you write skill descriptions that trigger when you want them to, and not when you do not want them to? With a process called "trigger testing," which we will be doing later, after covering the basics of skill files first.

You can also define skills that do not auto-trigger, and use them explicitly like slash-commands. I like this because I'm used to working in command mode, either in my terminal or in my text editor. The Claude Code docs recommend it for anything with side effects, or where you want to control the timing - `/commit`, `/deploy` - because you don't want the agent deciding to deploy just because your code looks ready. A skill defined like this never hijacks another prompt and doesn't require any trigger testing or optimization, though its description is still loaded into context and can still color the agent's reasoning. The trade-off is that it becomes something you do explicitly, rather than implicitly based on an LLM interpreting your prompt.

To make a skill that does not auto-trigger, add `disable-model-invocation: true` to the front-matter. One caveat: this key is a Claude Code extension rather than part of the Agent Skills spec, so a skill that uses it may not validate everywhere.

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
- Match instruction specificity to task fragility (see below).
- Include examples to illustrate what you want.
- Avoid passive phrasing when describing rules.
- Include a checklist or verification process.

## Progressive Disclosure

Probably, you are already familiar with the concept of "progressive disclosure" - loading targeted chunks of information into context, when they are needed, leaving more operating overhead for the agent to work when they are not needed. But it's worth pointing out that skills are just a standardized implementation for progressive disclosure that follow specific conventions and file/folder layout.

The concept of progressive disclosure also applies to the skills themselves. If you write a skill that is 200K lines long, then you fill up your context window as soon as the skill is loaded. Even if your skill is much shorter than that, any lines which are not actually used in your session - rules about corner-cases or errors that never happen, for example - are just taking up space in your context window.

You can extract these corner-cases from the `SKILL.md` file and move them to their own files under the `references` directory, then link them into the main file with instructions to read the reference when a certain condition is met. This is worth doing when the instructions to be extracted are longer than the instructions they would be replaced with (evaluate a condition and load the reference file).

However, a reference file that is ALWAYS loaded whenever you use the skill is pointless. It's no different than just keeping it inline because it still fills up your context window.

- Keep the main skill file short and only cover the "happy path."
- Move corner-cases and error handling instructions to reference files and only load them when they are actually needed.
- Reference files that are always loaded are pointless (they do not help managing context bloat).

## Calibrating Specificity

Most of the rules in this post are one-sided - concise beats verbose, always. This one isn't, so it gets its own section.

How specific your instructions should be depends on how easy the task is to get wrong. Anthropic's skill-authoring guide frames it as a robot following a path: a narrow bridge with cliffs on both sides gets exact step-by-step instructions, while an open field gets a direction and a destination. Neither answer is correct in general.

Be specific when the operation is irreversible, order-dependent, or has exactly one correct form - migrations, deploys, release cutting, anything that touches production. Getting the sequence wrong costs more than the tokens you spend pinning it down. Anthropic's own example is about as rigid as instructions get:

> Run exactly this script: `python scripts/migrate.py --verify --backup`. Do not modify the command or add additional flags.

Be loose when many routes reach the same outcome - refactoring, writing tests, exploring an unfamiliar codebase. State the goal, the constraints, and how to verify the result, then let the agent route itself.

Most skills are a mix of both, and each section calibrates separately. The test to apply per instruction: if a step could vary without anything breaking, state the outcome instead. If it couldn't, spell it out.

## Determinism, Rigid Processes, and Scripts

LLMs are non-deterministic in practice. Some of that is by design - sampling and temperature. But even at temperature zero, the same prompt against the same endpoint won't reliably give you the same tokens. Thinking Machines traced this to batch-invariance: the kernels serving your request produce slightly different floating-point results depending on the batch size they run at, and batch size depends on how much other traffic the server is handling at that moment. You don't control that. Either way, you can give an agent the same instructions many times and it will take a slightly different route to get there each time (or maybe VERY different routes).

A rule from the DeepMind presentation that surprised me: on open-field tasks, let the agent find it's own way to the solution. They are designed to reason and figure out a solution with iteration. The AI will find its way to the solution but will always take a different approach each time.

You may see it doing things that obviously won't work, but eventually figure it out. My initial instinct was to lock that down with tighter rules, so it never tries to execute commands that will not work, or to tell it exactly what to do at each step. When the task had many valid routes, that backfired - the rigid execution steps caused more problems than the wandering did. Only when you see it do something bad, or consistently struggle to figure out the next step, should you add discipline rules to correct it.

So there are three levels available, and the fragility of the task picks which one you use:

1. **Goals and constraints.** The agent routes itself. The default for open-field work.
2. **Explicit ordered steps.** For when the sequence matters but each step still needs judgment, or drives a system a script shouldn't touch unattended.
3. **A script.** For when the process is fully deterministic.

The third one is the one people reach for least and should reach for most. You can ask the LLM to write the script, or if you see the agent frequently writing an ad-hoc script for the same step each time, ask it to save it as a reusable script. Any time you can move deterministic logic to a script instead of having an LLM interpret it each time, that will save token costs and ensure more consistent application.

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

## Some Established Conventions

* Naming: Gerund form (`processing-pdfs`, `analyzing-spreadsheets`). Lowercase, numbers, hyphens, 64 chars.
* Descriptions get written in third person, always. "Processes Excel files and generates reports", not "I can help you with". The field gets injected into the system prompt and mixing point of view causes discovery problems. Include both what it does and when to use it, with the trigger words a user would actually type.
* Forward slashes in paths, even on Windows.
* Pick one term per concept and use it everywhere. Don't rotate between field, box, element, and control.
* Scripts should handle their own error cases instead of failing and leaving the agent to figure it out.

## Example

Here is our own `writing-skills` skill, based largely on the `superpowers` version, containing everything we've covered in this document, and nothing we haven't covered yet (testing and optimization rules).

[writing-skills (without testing)](./writing-skills.md)

You can use this to write a new skill, iterate on a skill, or clean-up an existing skill. Whenever we run a test campaign and optimization loop, a skill like this will be loaded into context to ensure the AI follows these rules when modifying the skill.

In the following installments, we'll augment this skill to focus on writing optimal descriptions, writing discipline rules, and testing skills.

## References

- [Agentskills.io spec + guide](https://agentskills.io)
- [Superpowers "writing-skills" skill](https://github.com/obra/superpowers/blob/main/skills/writing-skills/SKILL.md)
- [DeepMind - Don't Ship Skills Without Evals](https://youtu.be/0vphxNt4wyk?si=j9E5D7a-scWELD6_)
* Skill authoring best practices: [https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
* Equipping agents for the real world with Agent Skills: [https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
* Defeating Nondeterminism in LLM Inference: [https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/](https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/)
* Claude Code — Extend Claude with skills: [https://code.claude.com/docs/en/skills](https://code.claude.com/docs/en/skills)
