./README.md is a blog post describing how to test skill bodies. we've already done retrieval and shaping tests, now we need to design a skill to implement a full pressure-testing campaign.

./examples/skills/pressure-testing-skills/SKILL.md is a simple, illustrative skill that implements a pressure test against a single rule from a target skill. it does not implement a full campaign, only illustrates the core concept.

../../../skills/ contains trigger-testing-skills, shape-testing-skills, and retrieval-testing-skills full campaign implementations. our new pressure-testing-skills skill should follow similar conventions.

~/tmp/dangerpowers-tmp/skills.old/writing-skills/references/pressure-testing.md is a previous implementation of the same process, written before the conventions in the current skills in this project were established, but should be a useful reference.

analyze the sources and provide a high-level design document that lists the process, important concerns and conventions, all systems or components involved. include a mermaid diagram of the full campaign flow.

do not make decisions or assumptions yourself - all blocking questions should be surfaced to the user for clarification before proceeding.

do not make any changes, only present the design summary.
