# The 7 Habits of Highly Effective Agents

**Author:** Dave Czmer
**Last Modified:** Monday, August 03, 2026

---

## Introduction

AI _is_ very powerful and useful for engineering. It's also messy, non-deterministic, and unpredictable.

AI development works best when a project is well structured, has well maintained rules files, clear architectural patterns and conventions to "copy" from. But using AI for development, ironically, degrades those qualities of a project repository over time.

How do we avoid losing control of the project architecture and devolving into "slop" as we hurl more and more machine-generated PRs at it with an ever-increasing pace?

I wan't to outline the issues and challenges that I think are important. I won't dive deep into any one topic right now, just an overview with enough detail to start a discussion. I'm also not going to talk about how to "solve" any of these issues in this document. I would like to continue this with a series of very short, focused documents that target a specific issue or "habit."

---

## The 7 Habits

[Humanlayer](https://www.humanlayer.dev/blog) wrote a blog titled "12 Factor Agents" as a homage to "[12 Factor Apps](https://12factor.net/)." Every technical writer who has ever written a blog has riffed on Dijkstra's "[Considered Harmful](https://en.wikipedia.org/wiki/Considered_harmful)."

As I started thinking about all of the various layers, or "levels," of issues, skills, techniques we employ to apply AI-driven development, these "levels" started to remind me of the structure of "The 7 Habits of Highly Effective People," which grouped it's 7 habits into 4 levels:

- **"Private Victory"** - How you see the world around you, and your place within it.
- **"Public Victory"** - Learning to get what you want through your own actions and influence.
- **"Sharpening the Saw"** - Continuous growth and self-improvement. The "Upwards Spiral."
- **"Inside Out Again"** - Real change comes from "the inside out."

I think the challenges I've seen can be grouped into a similar structure:

- **"Personal Efficacy"** - How well you know and use your tools, your fundamentals. What is your mental model regarding how this technology _actually_ works, and how does that influence how you use it? How to be an individual contributor.
- **"Own the Quality"** - Working on larger changes and features, crossing domains, and major refactoring without losing the design and creating duplication and structural issues. How to minimize drift, clutter, duplication that make it harder for everyone else to work on the project.
- **"Own the Architecture"** - Using the AI to do well scoped tasks, within the boundaries and conditions that _YOU_ design. Keeping a strong structural foundation over the long-term.
- **"Sharpening the Saw"** - Keeping current, practicing, reading, experimenting, incorporating new techniques and tools into your workflow.

---

## Personal Efficacy

Learn how to use your tools. Sharpen your mental models. Foundational engineering knowledge matters more than ever.

### Habit 1: Master your tools.

You are a professional engineer. You use these tools every day. You should know how to use them effectively and when to use the right tool for the job. You should understand how they work and their strengths and limitations.

- How do AI and agentic coding assistants work? What are the strengths and limitations? Where does it typically fall short?
- Understand and leverage the features of the tools you use. From Claude Code hooks and subagents, to LSPs and linters, and how to use the command line effectively.

### Habit 2: Remember the fundamentals.

Everything you would have needed to know about engineering _without_ AI.

- You still have to know what the AI is doing so you can verify it yourself.
- You still have to know the product and what types of changes and practices will cause issues over time, how it will be deployed, how your changes affect quality and cost of ownership.
- You still have to know the details of your programming language, libraries, the OS your application runs on, and how to spot subtle issues before they cause problems later.
- You still have to know how to manage quality, testability, extensibility, and security.
- You should still be planning for safe roll-out, ability to triage issues in production, and limiting blast-radius of your changes.

### Habit 3: Manage context carefully.

Context and managing your context window are the most impactful thing you can do to achieve better results.

- Context engineering (VERY important and A LOT to cover):
  - Compaction, summarization, progressive disclosure, context hygiene, context rot, too much context, bad context ("distractors"), avoiding the "_dumb zone_," …
- Keeping the agent focused:
  - "Thrashing" to try to figure out an action by trial-and-error, doing things you didn't ask it to do, brittle, complex, and unnecessary modifications, duplicating instead of reusing existing code, …
  - Planning, specifications, and verification instructions.

---

## Own the Quality

AI is fantastic at analyzing, summarizing, and auditing code and documents. But the code it generates typically fail a careful quality review, unless you take very intentional steps to prevent it.

AI can generate a PR so fast, and it looks so convincingly "good" that it's very easy to miss important issues. These seemingly harmless little issues happen when you develop without AI as well, but now it's happing 50x faster.

I think a big reason for these issues is because of the way AI has to use very narrowly targeted analysis and implementation. It can't fit the entire project, plus all documentation, plus all review comments ever, etc. into it's working context. Either you have to tell it EVERYTHING it might need, or else it has to systematically search for just the information it needs while trying to minimize how much data it sends to the model. It takes a myopic purview of the current task, and it frequently misses references or important details in areas that it didn't think to check.

### Habit 4: Manage Scope and Orthogonal Changes

It's easy to be a 10x engineer when every change uses 10x the lines of code it should require. Try to identify and avoid:

- Scope creep.
- Undesired and orthogonal changes and improvements.
- Fixing the "symptom" instead of the cause.

### Habit 5: The Details ARE Important

When PRs are merging faster than you can actually review them properly, small issues accumulate and compound quickly. Beware of the following:

- Brittleness: coupling and cohesion, over-testing, over-mocking, hard-coding, duplication.
- Useless abstraction, one-line functions that add nothing.
- Unnecessary complexity.

---

## Own the Architecture

Now to address the long-term effects of AI-driven development on a project, and how to keep control of the design so that the AI is not the one making the decisions.

This is my biggest concern with the direction of software engineering in the "AI era."

A lot of the issues here are caused by gradual accumulation of "almost right" changes that compound over time.

### Habit 6: Don't Out-Source Thinking

You are the engineer, Claude is your intern. You frame the structure, Claude fills in the implementation details. Avoid these pitfalls:

- Letting "Claude take the wheel": Why did the AI implement things this way? Is it what we want? It's not enough that it seems to work and the tests all pass. You should tell it exactly what to do and how to do it.
- Trusting the tests to prove quality and regressions. Tests only catch things you are explicitly testing for already. AI has a habit of changing the tests instead of fixing the root cause, and a habit of making things fail silently when they should raise.
- Cognitive debt: The changes happen so fast, and the volume of changing code is so large, that you lose track of how things actually work.

### Habit 7: Own the Architecture

"Losing the architecture" basically means, after many isolated changes to a codebase over time, little changes made by the AI along the way become load-bearing parts of the architecture. If you can no longer reason about the architecture of the project, without asking the AI to do it, you are going to have a bad time.

- Important architectural structures bifurcate and responsibilities become unclear.
- Small duplications and changes, that were applied to make one feature work, get reused and copied and become part of the architecture unintentionally.
- Exponentially increasing cost of analysis, refactoring operations as the architecture sprawls and duplication and brittleness sprawls. Soon you have 15 work-trees with swarms of agents running 24/7 doing pointless refactoring.
- Consistency drift: references to things that no longer exist, outdated instructions or comments, hard-coded lists in multiple places that are not in sync, duplication with subtle differences.

---

## Sharpening the Saw

Seek out advice, resources, and training materials. Keeping on top of new trends (and knowing when to avoid the "fads"). Learning to learn effectively and how to approach and accomplish difficult things - not just once, but repeatedly.

Actually practicing and getting hours of hands-on experience in different environments. Start a project from scratch and do it 100% AI-driven, note the point where you lose control of the architecture and are unable to make changes by hand any more. Pick up a large open-source project and start using the AI to learn how to work in that codebase, and training the AI to work effectively for you.

If you only do training "on the job" while at work, then you only learn how to do that specific job. If you intentionally train on various topics and find a place to practice and experiment, then you can work on any job.
