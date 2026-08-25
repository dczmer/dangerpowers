# Writing Skills Deep Dive - Part 1: Basics

Have you ever tried to write a skill, but the AI couldn't figure out how to execute certain steps or, even worse, completely disregard important rules from your instructions? Maybe the skill doesn't fire when you expect it to, or fires too frequently and runs when you don't want it? Then you add more and more rules, change wording to further emphasize rules that should not be broken? Did you end up with a 3K line markdown file that you were not satisfied with?

I was inspired by how well `superpowers` skills fire and how well they stick to the rules, so I did some research on their [`writing-skills` meta-skill](#ref-f). I also researched the [`agentskills.io` spec](#ref-c) and their advice for writing and testing skills ([D](#ref-d), [E](#ref-e)). Finally, I watched a [presentation by someone from Google DeepMind team](#ref-j) that pulls everything together and gives a kind of recipe for writing and managing skills. (All references are linked at the bottom of the document, and cited inline by their `[A]`-`[J]` key).

This entry will just explore the basics and not go into testing or optimization. The follow-up to this post will cover trigger and pressure testing and we'll build our own "eval" harness to carry out the tests.

## Basics

Skills are a mechanism for extending AI agent capabilities or enforcing conventions or preferences. Skills provide instructions or context on-demand - skills are a formalized implementation of progressive disclosure ([B](#ref-b), [C](#ref-c)).

```
my-skill/
├── SKILL.md           # skill definition/instructions
├── scripts/           # helper scripts (optional)
├── references/        # reference docs (optional)
```

A skill is a directory with a `SKILL.md` in it ([C](#ref-c)). The frontmatter has a `name` and a `description`, and those two fields are the only part that gets pre-loaded into the system prompt at startup. Everything else is read on demand ([A](#ref-a)). So the description is not documentation, it's the router ([E](#ref-e)). If it's vague, the skill never fires and you spend an afternoon debugging a prompt when the actual bug is one line of yaml.

The rest of it comes down to four things ([A](#ref-a)):
* Be concise, because the context window is shared with everything else the agent needs to know.
* Match how specific your instructions are to how easy the task is to get wrong.
* Split content out into files that only get read when they're needed.
* Build the evals first, before you write the doc.

The [Google DeepMind presentation](#ref-j) classifies skills into two broad categories:

1. Capability: teaches the agent something it doesn't know how to do today.
2. Preferences: encodes preferences, conventions, workflows that are specific to your project or environment.

Capability skills may become unnecessary as models evolve and become more capable. Preference skills are custom rules that are unlikely to ever be integrated into the models - they are "durable."

[Superpowers](#ref-f) breaks things down into 4 types of skills but I prefer the capability/preference explanation. However, superpowers calls out the concept of "discipline" - rules you add to steer or correct agent behavior while executing a skill. Discipline rules that are intended to prevent the agent from doing something wrong are called "prohibitions."

## Start Small

The [DeepMind presentation's](#ref-j) first rule is to **write the initial skill content yourself**. I'd put it slightly differently, because the problem underneath it is narrower than "AI writing is bad."

Ask an agent to write a skill cold and you get filler - "handle errors appropriately," "follow best practices" - because it has nothing concrete to work from ([D](#ref-d)). Ask it to write one at the end of a long working session and you get the opposite problem: rules that encode incidental details of that conversation. A path that only existed on your branch. An error you hit once. A decision that was right that afternoon and is noise forever after. Both failure modes come from the same place - the model wrote from the wrong evidence - and the second is harder to catch, because every one of those rules looked justified at the time.

So the rule isn't "type it yourself." It's: control what the model writes from, and never ship a skill you haven't read back cold. Give it real material - a transcript of doing the task by hand, an existing runbook, review comments, a patch - instead of asking it to imagine the process ([D](#ref-d)). Then open the draft in a fresh session that has no memory of writing it ([A](#ref-a)). Leaked context is obvious from there and nearly invisible from inside; anything you can't justify without that history is what to cut.

When we get to testing and optimization, the AI will be doing most of the editing, but it will do so under very specific instructions. You just need to make sure it stays concise and free of no-ops or contradictory instructions.

In fact, the common advice is actually to NOT write a skill right away, but to build one up with a TDD-like approach ([A](#ref-a)) (basically the opposite of how everyone writes skills):
1. Run the agent on real representative tasks with no skill at all. Write down where it failed.
2. Build three scenarios that test those specific failures.
3. Measure the baseline without the skill.
4. Write the minimum instructions that fix the observed gaps.

The point is that you build-up the skill by solving actual real-world problems instead of ones you just predicted/imagined. But since we are only talking about "what is a skill" and not covering evals yet, this advice must be deferred to later installments.

## Descriptions and Triggers

Skills are activated using the `skill` tool in your coding agent. The `description` of each skill is loaded into the context window, and the agent picks a skill by matching your request against those descriptions ([E](#ref-e)). That match is semantic, not a keyword lookup - the phrasing you use in a description still matters, but it works by shaping meaning rather than by registering literal trigger words.

A good description should have the following properties:
- Include what (capability) and when (triggers) ([A](#ref-a), [C](#ref-c))
- Should be short (< 1024 characters) ([C](#ref-c)) because every skill description takes space in your context window. Descriptions live in the system prompt, so you pay for them from the first turn of every session, whether the skill ever fires or not ([A](#ref-a), [G](#ref-g)).
- Triggers the skill based on phrases you intend to active ([E](#ref-e)).
- Does not "hijack" phrases that should load other skills, or not load a skill at all ([E](#ref-e)).
- Does not paraphrase the contents of the skill - AI will cheat and not load the skill if the description already has a TLDR of what it does ([F](#ref-f)).

How do you write skill descriptions that trigger when you want them to, and not when you do not want them to? With a process called "trigger testing," which we will be doing later, after covering the basics of skill files first.

You can also define skills that do not auto-trigger, and invoke them explicitly, like slash-commands. I like this because I'm used to working in command mode, either in my terminal or in my text editor. It's also the right shape for anything with side effects, or where you want to control the timing - committing, deploying, cutting a release. As the Claude Code docs put it, "You don't want Claude deciding to deploy because your code looks ready" ([G](#ref-g)). A skill defined like this never hijacks another prompt and doesn't require any trigger testing or optimization, though its description is still loaded into context and can still color the agent's reasoning. The trade-off is that it becomes something you do explicitly, rather than implicitly based on an LLM interpreting your prompt.

How you declare this depends on your agent. It isn't in the Agent Skills spec ([C](#ref-c)), so there's no portable way to express it - in Claude Code it's `disable-model-invocation: true` in the front-matter ([G](#ref-g)). Check whether your agent supports it before relying on it.

## Content

The body of your `SKILL.md` file contains the instructions or context that the agent should follow to accomplish a task.

Skill files should be short: <500 lines ([A](#ref-a), [C](#ref-c)). When a skill is invoked, the entire contents of the skill file are loaded into the context window - and it stays there. This isn't a one-time cost paid at invocation; the skill body sits in the conversation history for the rest of the session, re-sent with every turn that follows ([G](#ref-g)). Fifty lines of preamble in a skill you trigger early is fifty lines you keep paying for while you do everything else. So every no-op statement, every paragraph of flowery prose that could be concise directives, becomes bloat that wastes context space. Anything that is obvious, or that the agent can easily figure out on it's own is also waste (we'll see how to detect that with eval tests later).

A skill should start with a brief overview - a sentence or two on the principle the skill is built around ([F](#ref-f)). It should contain a section that describes when to use the skill, and when not to use the skill. These sections give the AI a chance to abort early, after triggering the skill, if it's not actually applicable to the current problem context.

One frustration I have encountered is how often the AI will forget or ignore an instruction by rationalizing a reason to circumvent a rule that is making it hard to accomplish its task. A process called "pressure testing" can be used to ensure your skill's rules are consistently followed. We'll cover pressure testing in the next installment.

One way to make your rules more effective, and less likely to be ignored, is to avoid the use of passive phrasing. Don't say "X is preferred" because that gives the AI room to decide that the rule isn't necessary. Instead, use strongly worded phrases like "always use X" or "X must be used when Y happens" ([A](#ref-a)).

Where possible, include an example of important outputs, like templates or snippets that illustrate what you want the AI to do. Focus on one complete example and do not dilute the skill definition by duplicating examples in multiple languages - the AI can map the example to the target language ([F](#ref-f)).

Including a checklist or verification procedure at the end allows the AI to self-check its work ([A](#ref-a), [D](#ref-d)). I find that this frequently surfaces issues that the AI skipped over, or that were introduced while it was refactoring. Having a verification procedure ensures that the AI is forced to check each item in the list before claiming a task is completed.

Some suggested best practices:
- Write concise directives, not essays.
- Keep free of no-ops, commentary, or unnecessary rules.
- Match instruction specificity to task fragility (see below).
- Include examples to illustrate what you want.
- Avoid passive phrasing when describing rules.
- Include a checklist or verification process.

## Progressive Disclosure

Probably, you are already familiar with the concept of "progressive disclosure" - loading targeted chunks of information into context, when they are needed, leaving more operating overhead for the agent to work when they are not needed. But it's worth pointing out that skills are just a standardized implementation for progressive disclosure that follow specific conventions and file/folder layout ([B](#ref-b), [C](#ref-c)).

The concept of progressive disclosure also applies to the skills themselves. If you write a skill that is 200K lines long, then you fill up your context window as soon as the skill is loaded. Even if your skill is much shorter than that, any lines which are not actually used in your session - rules about corner-cases or errors that never happen, for example - are just taking up space in your context window.

You can extract these corner-cases from the `SKILL.md` file and move them to their own files under the `references` directory, then link them into the main file with instructions to read the reference when a certain condition is met ([A](#ref-a), [D](#ref-d)). This is worth doing when the instructions to be extracted are longer than the instructions they would be replaced with (evaluate a condition and load the reference file).

However, a reference file that is ALWAYS loaded whenever you use the skill is pointless. It's no different than just keeping it inline because it still fills up your context window.

- Keep the main skill file short and only cover the "happy path."
- Move corner-cases and error handling instructions to reference files and only load them when they are actually needed.
- Reference files that are always loaded are pointless (they do not help managing context bloat).

## Calibrating Specificity

Most of the rules in this post are one-sided - concise beats verbose, always. This one isn't, so it gets its own section.

How specific your instructions should be depends on how easy the task is to get wrong. [Anthropic's skill-authoring guide](#ref-a) frames it as a robot following a path: a narrow bridge with cliffs on both sides gets exact step-by-step instructions, while an open field gets a direction and a destination. Neither answer is correct in general.

Be specific when the operation is irreversible, order-dependent, or has exactly one correct form - migrations, deploys, release cutting, anything that touches production. Getting the sequence wrong costs more than the tokens you spend pinning it down. [Anthropic's own example](#ref-a) is about as rigid as instructions get:

> Run exactly this script: `python scripts/migrate.py --verify --backup`. Do not modify the command or add additional flags.

Be loose when many routes reach the same outcome - refactoring, writing tests, exploring an unfamiliar codebase. State the goal, the constraints, and how to verify the result, then let the agent route itself.

A single skill usually needs both, so calibrate section by section rather than settling on one setting for the whole file ([D](#ref-d)). The test to apply per instruction: if a step could vary without anything breaking, state the outcome instead. If it couldn't, spell it out.

## Determinism, Rigid Processes, and Scripts

LLMs are non-deterministic in practice. Some of that is by design - sampling and temperature. But even at temperature zero, the same prompt against the same endpoint won't reliably give you the same tokens. [Thinking Machines](#ref-i) traced this to batch-invariance: the kernels serving your request produce slightly different floating-point results depending on the batch size they run at, and batch size depends on how much other traffic the server is handling at that moment. You don't control that. Either way, you can give an agent the same instructions many times and it will take a slightly different route to get there each time (or maybe VERY different routes).

A rule from the [DeepMind presentation](#ref-j) that surprised me: on open-field tasks, let the agent find it's own way to the solution. They are designed to reason and figure out a solution with iteration. The AI will find its way to the solution but will always take a different approach each time.

You may see it doing things that obviously won't work, but eventually figure it out. My initial instinct was to lock that down with tighter rules, so it never tries to execute commands that will not work, or to tell it exactly what to do at each step. When the task had many valid routes, that backfired - the rigid execution steps caused more problems than the wandering did. Only when you see it do something bad, or consistently struggle to figure out the next step, should you add discipline rules to correct it.

So there are three levels available, and the fragility of the task picks which one you use:

1. **Goals and constraints.** The agent routes itself. The default for open-field work.
2. **Explicit ordered steps.** For when the sequence matters but each step still needs judgment, or drives a system a script shouldn't touch unattended.
3. **A script.** For when the process is fully deterministic.

The third one is the one people reach for least and should reach for most. You can ask the LLM to write the script, or if you see the agent frequently writing an ad-hoc script for the same step each time, ask it to save it as a reusable script ([D](#ref-d)). Any time you can move deterministic logic to a script instead of having an LLM interpret it each time, that will save token costs and ensure more consistent application ([A](#ref-a), [B](#ref-b)).

Keep the LLM evaluation for places where you _need_ reasoning or semantic understanding ([B](#ref-b), [F](#ref-f)).

## Issues

Some issues I've observed (not counting issues with testing processes):

- Too many skills bloat your context window. Try to disable plugins or skills that you don't need for the current session ([C](#ref-c), [G](#ref-g)).
- Descriptions from other skills influencing LLM reasoning, contaminating the context window ([E](#ref-e)).
- Skills that never seem to fire automatically, or skills that fire too broadly and hijack prompts they shouldn't receive ([E](#ref-e)).
- LLM deciding NOT to execute a skill that should have triggered, because the skill description had a TLDR of the process it encapsulates. "I don't need to read the skill, I already know what to do from the description." ([F](#ref-f))
- Prompt injection and over-broad tool grants from third-party skills - a description sits in your context whether the skill ever fires or not, and a skill checked into a repo carries its own `allowed-tools` ([G](#ref-g)).

It mostly comes down to context window management, triggering, and contaminating your context with instructions you don't always want.

I should also point out that installing a third-party skill means trusting more than its instructions. The `description` is loaded into your context whether or not the skill ever fires, and workspace trust doesn't gate `allowed-tools` - Claude Code applies a project skill's grant even in a `-p` run in a folder you've never trusted, which is why the docs tell you to review the `allowed-tools` of any skills checked into a repository before you run an agent there ([G](#ref-g)). Injected `` !`command` `` lines never prompt for permission either, though they fail closed - a command that isn't already allowed aborts the invocation rather than asking you - so the real exposure is a broad grant and an injected command in the same skill. This will also become clear when you start doing trigger and pressure testing campaigns, as descriptions from other skills will frequently cause your agent to exhibit undesired behavior for the test scenario.

## Some Established Conventions

* Naming: Gerund form (`processing-pdfs`, `analyzing-spreadsheets`). Lowercase, numbers, hyphens, 64 chars. ([A](#ref-a), [C](#ref-c))
* Descriptions get written in third person, always. "Processes Excel files and generates reports", not "I can help you with". All of these descriptions land in the same system prompt, and one that breaks pattern is harder to trigger. Include both what it does and when to use it, with the trigger words a user would actually type. ([A](#ref-a), [E](#ref-e))
* Scope a skill like a function - one coherent unit of work. Too narrow and you need three of them loaded at once to get anything done; too broad and no description can trigger it precisely. ([D](#ref-d))
* Include a "gotchas" section - the things about your setup that a sensible guess gets wrong. This is often the highest-value content in the whole file, because it's exactly what the model can't derive on its own. ([D](#ref-d))
* Provide defaults, not menus. Pick one library, one approach, and name it. Mention the escape hatch if there is one, but don't hand the agent a decision it has no basis for making. ([A](#ref-a), [D](#ref-d))
* No time-sensitive information. "If you're doing this before August 2025" rots. If an older approach still needs documenting, put it in a clearly labeled section for legacy patterns. ([A](#ref-a))
* Forward slashes in paths, even on Windows. ([A](#ref-a))
* Pick one term per concept and use it everywhere. Don't rotate between field, box, element, and control. ([A](#ref-a))
* Scripts should handle their own error cases instead of failing and leaving the agent to figure it out. ([A](#ref-a), [C](#ref-c))
* No magic constants in scripts. If a script sets `TIMEOUT = 30`, say why it's 30. A number you can't justify is a number the agent can't either. ([A](#ref-a))
* Don't assume a skill that works on a large model works on a small one. Instructions a frontier model follows fine may need to be spelled out for a smaller, faster one. ([A](#ref-a))

## Example

Here is our own `writing-skills` skill, based largely on the [`superpowers`](#ref-f) version, containing everything we've covered in this document, and nothing we haven't covered yet (testing and optimization rules).

[writing-skills (without testing)](./writing-skills.md)

You can use this to write a new skill, iterate on a skill, or clean-up an existing skill. Whenever we run a test campaign and optimization loop, a skill like this will be loaded into context to ensure the AI follows these rules when modifying the skill.

In the following installments, we'll augment this skill to focus on writing optimal descriptions, writing discipline rules, and testing skills.

## References

- <a id="ref-a"></a>**[A]** [Anthropic - Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
- <a id="ref-b"></a>**[B]** [Anthropic - Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- <a id="ref-c"></a>**[C]** [Agent Skills - Specification](https://agentskills.io/specification)
- <a id="ref-d"></a>**[D]** [Agent Skills - Best practices for skill creators](https://agentskills.io/skill-creation/best-practices)
- <a id="ref-e"></a>**[E]** [Agent Skills - Optimizing skill descriptions](https://agentskills.io/skill-creation/optimizing-descriptions)
- <a id="ref-f"></a>**[F]** [Superpowers - "writing-skills" skill](https://github.com/obra/superpowers/blob/main/skills/writing-skills/SKILL.md)
- <a id="ref-g"></a>**[G]** [Claude Code - Extend Claude with skills](https://code.claude.com/docs/en/skills)
- <a id="ref-i"></a>**[I]** [Thinking Machines - Defeating Nondeterminism in LLM Inference](https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/)
- <a id="ref-j"></a>**[J]** [Google DeepMind - Don't Ship Skills Without Evals](https://youtu.be/0vphxNt4wyk?si=j9E5D7a-scWELD6_)
