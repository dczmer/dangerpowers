# dangerpowers

> Actually, my name is Dave Powers. Danger is my middle name.

Dissecting popular frameworks like superpowers and building my own - to learn and to implement a process tailored to my own preferences.

---

## Motivation

When I first installed (superpowers)[https://github.com/obra/superpowers], I was amazed by how consistently the skills fired, and how well they enforced the operational rules without the AI rationalizing or working around the constraints and rules.

The skills I had written before would not fire consistently (especially across models), and the AI would frequently chose to work around the operational policy rules and prohibitions. This resulted in adding more and more instructions and corner-cases until the SKILL.md files started to grow out of control. Not only did this make my custom skills way more complex than they needed to be, it also did not solve the core problems of firing and following the process exactly.

But `superpowers` seems to be able to do this with relatively simple, concise skill definitions and metadata. So I started reading how their skills were organized, what important sections they contained, etc. Eventually, I came across their `writing-skills` skill, which had most of the skill design wisdom baked-in. This is where I learned about concepts like "pressure", "rationalization", "goal obsession", and "prompt interpretation" issues.

By adding `superpowers` to my agent, I suddenly had a solid, structured process that the AI naturally followed. An end-to-end system for planning, executing, and iterating on tasks, backed by actual research and best practices.

What do I like about `superpowers`?
- Systematic processes for writing specs, making plans, executing plans - consistently.
- Skills trigger when you need them and they stick to the rules.
- Writing-skills skill implements a 'bulletproof' approach to testing and optimizing skills you write.
- Systematic-debugging takes over and follows a systematic process to debug issues instead of just making assumptions and changing things without evidence.
- Skills that drive subagent delegation and use of git worktrees.
- I like the TDD approach, in concept.

What do I dislike about `superpowers`?
- The skills are a little too "sticky" - sometimes they kick in when I really didn't want them.
- A meta-skill, `using-superpowers`, is injected into the system prompt so you lose control over some of your context and when/how these skills might trigger.
- Ideological differences on exactly what/how the spec-ing, planing, execution should be designed.
- Preference for vertically slicing plans vs. unit-based TDD implementation.
- Little details that I like to control, like where/how artifacts are stored and organized.

But, mostly, I wanted to take these skills apart and put them back together myself, so I can learn how and why they work, and any interesting concepts or idioms that I had not heard of.

Some other projects of inspiration:
- Bulletproof
- Humanlayer
- Pi-subagents
- Claude Code planning mode

---

## Skills and Workflows


