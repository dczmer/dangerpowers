# Work in Progress

Mostly-completed skills, but need to review and fold back into the plugin after cleaning them up and testing them.

I successfully implemented 80% of the workflow that I had planned, but ran into some issues:

1. The writing-skills definition contains instructions that _only_ work for this project, and only for `opencode`. I wanted this to be generic so I can use it on any project, with any standardized coding agent.
2. The method I used to register the skills in this repository, so that `opencode` could see them caused issues with test contamination during evals. I manually symlinked the folders into `./opencode/{agents,skills}` - this makes them load automatically whenever I work on this project, but also makes it hard to start a subagent that does not know about the skills for clean baselines. The symlinks also confuse the agent at times. I plan to turn this into a proper 'plugin' for opencode. I know the same directory structure can work so I can later make a `claude code` plugin from the same repository. And `pi` is even easier, we can just point to this folder as an 'extension' or even provide the path to it when we start the agent from the command line.
3. The `writing-skills` skill was used to create all of the other skills in this folder, but `writing-skills` evolved over time and the previously generated skills are not consistent.

I also learned some new things about writing and testing skills and want to make sure they are incorporated from the start.
