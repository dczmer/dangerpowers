# The Case Against Skills

## The Case Against Auto-Invocation (and the Case for Commands)

not really against 'skills', but against auto-invocation mechanism (prefer commands)

skills are the standard way to extend the capabilities of a model by providing on-demand context related to a specific topic or process.

part of the idea, as explained at agentskills.io, is that you would decompose a big task into many specialized subagents to execute different parts. so if you had to make a new page on a typical webapp framework, you might have subagents for implementing the backend changes, changing the database, writing the react (bleh) components, etc. these subagents would pick up skills automatically based on the prompts that they are given and then each one would have the context needed to do its job, but would not be polluted with context from skills that it doesn't need.

but what is the value of a skill that doesn't fire when you need it? what is the cost of a skill that fires when you don't need it?

if the skill has a reason to exist, it's because it helps the agent do something it normally can't do (well). if it doesn't fire when its needed, the agent will do _something_ to achieve the goal without it. that includes breaking all of your discipline rules, which are (presumably) there for a good reason. you may not even notice that your changes break the rules because ai-generated PRs tend to be pretty large. for something like a security skill, this could be disastrous.

but a skill that fires too often might be even worse: it pollutes your context window and helps contribute to loss of accuracy from sources like attention mechanism dilution, context overload, and potentially introduces conflicting rules or 'distractors' that have a compounding effect on quality and accuracy after that.

one thing that became apparent from trigger-testing campaigns is that the process of auto-invoking skills is never 100% accurate. even if your trigger rate is 99% then that still leaves a 1/100 chance it will not work, which means you can't fully trust it. you can write very specific prompts, so they always match the trigger phrases in the description exactly, but when an agent tells another agent to do a thing, it might not always use the exact phrasing you need. with some tuning and by following some conventions, and by using a high-reasoning model, you can virtually eliminate this concern, but never completely avoid it.

but the really surprising thing to me, and the reason i am taking this stance now, is seeing how often high-reasoning frontier models auto-invoke a skill when it is NOT actually needed. reasoning is great for letting an agent autonomously find it's way to a goal, but it can backfire when the agent reasons itself into a bad state, like deciding a certain skill has something to do with the problem scenario or your current context info.

so to paraphrase, if you want to deterministically apply invariant conditions that an agent will always follow:
1. step 1, write a skill that enforces those conditions
2. step 2, spend hours trigger testing and refining the description
3. step 3, spend hours pressure testing and refining the discipline rules
4. step 3, roll a die to see if it will even use the skill when you need it
5. step 4, hope it doesn't load at the wrong time and negatively effect something

now keep in mind that i'm talking specifically about a human-in-the-loop approach to develop code where the agent is my assistant.

auto-invocation of skills (in this scenario) just introduces needless non-deterministic behavior for the sake of an automated interface. but the actions you do everyday should become muscle-memory over time. this is why people still use the command line and modal text editors like vim: you gain speed, flexibility, accuracy but it costs you the time and effort it takes to memorize things. but with the commands and actions you do frequently, the memorization part happens automatically with use.

my preference is to use 'commands' instead of skills for most things. when i need a skill that a subagent will dynamically pick up, i disable auto-invocation and have the agent instruct the subagents to load the skill by name or by file path. besides never having to worry about whether or not a command fires, you don't have to do expensive trigger/pressure testing.

i'm still writing 'skills', just calling them commands and not putting them in the system prompt at all.

if you are working with autonomous agents or running long-horizon goals, where no human is actually directing the workflow, then you might need to rely on the skill loading mechanism, but you should consider some way of deterministically verifying that it is following the rules, either in a commit hook or somehow BEFORE it makes an irreversible action (agent hooks perhaps).

an autonomous agent running in a loop, like openclaw or any other personal automation agent, frequently have to do tasks like responding to email or managing resources - things that are dangerous and/or irreversible. you really want to be sure the agent is following the rules!

this begs the question: even when the skill/command loads, how can i be sure that my discipline rules are always being followed? you can't! it's statistically very likely to work, but no guarantees. the best you can do is strategically design the skill to make the discipline rules important and to pre-answer the questions you have already seen that cause the agent to rationalize. adding a checklist at the end of the skill forces the agent to verify its work before calling a task complete, which helps _a lot_, but only after potentially dangerous or irreversible actions have been taken.

## Good ol' Prompt Engineering (and Prompt Composition)

a skill is basically a complicated prompt in a file. all the rules and advice we've covered for writing skills apply to any prompt:
- use imperative phrasing to present a rule as a _command_, not a suggestion to rationalize away
- use examples of what you want to produce
- give the right amount of freedom based on the task
- give the agent a way to verify its work
- reinforce discipline rules with things like a list of red flags, anti-patterns, etc. that try to course-correct or pre-answer a question to keep the agent on the right track

prompt engineering

prompt shaping

prompt composition
