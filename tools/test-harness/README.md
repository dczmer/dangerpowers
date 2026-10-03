These evaluator scripts are slop :(

I was learning while I developed each type of skill optimization campaign and the careful design I started with (trigger testing) turned into this mess through the course of adding retrieval, shape, and pressure testing campaigns.

Still, the core abstractions have served their purpose of separating concerns and encapsulating harness-specific details. The real problem is that I only modeled trigger testing flow when I designed it and didn't account for the different eval procedures and artifacts that each new test campaign required.

My point in writing these skills was that AI quickly turns complex code into slop every time you refactor something, and this is an amazing example of how fast it can happen. But this was a necessary step in learning how these things work, and the end result actually does work pretty well. It's just ugly with way to much code and a lot of cyclomatic complexity.

The other big problem is that, even though I implemented all of the deterministic operations in script, the agent is still driving. That means it has to transfer a ton of information back and forth between the scripts and the agent session, and it has to use a lot of command line arguments in very complex and exact configurations.

Since it's not broken, and it's actually useful, I'm choosing to just document my vibe-refactored mess for now. Once I get the full end-to-end execution pipeline re-implemented, I'll rewrite the entire thing, possibly using DSPy as the driver instead of a skill inside of a coding agent.
