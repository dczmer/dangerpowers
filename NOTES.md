# Notes

Raw notes for humans only. Just organizing my thoughts before starting the project.

Learning and experimenting with context and harness engineering by building my own 'superpowers'-like library and custom subagents.

- Start with skills that can reproduce the work I normally do when setting up or working on a project.
- Then start orchestrating workflows with skills and subagents.

## things what belong in my own global AGENTS.md

(current system, rules for ALL projects, etc)

- user preferences for all workflows
- machine-specific rules (on nix system, never `find /nix/store`); things that always need correction on your system
- operational rules (karpathy's rules)

- examples:
    * don't ever make a git commit without user consent
    * stop when you cant find an expected command in PATH instead of thrashing
    * don't ever try to install dependencies on your own; prompt the user
    * global rules of operation (like karpathy's rules)

## things what belong in a project AGENTS.md (or subfolder rules file)

- project-specific rules
- a high-level overview of the project and where to find things
- stack, available tools
- commands for development and testing
- workflow and verification procedures
- anything that the agent always/frequently gets wrong when working on this project

WARNING: both the global and project level files should be as minimal as possible. too much context is bad. incorrect or conflicting context is bad. the agents can figure out a lot on their own these days. start with an empty file and watch what the agent does - add things to the appropriate file as needed.

## things what belong in the system prompt

things at the beginning of the message seem to be honored more consistently where things in the middle of the message can get ignored.

normally, don't touch it unless you are making a custom agent or some kind of plugin where you need to alter/override the "you are a helpful coding agent" persona.

## things what belong in skills

## things what need custom subagents

- when you want control over model and effort levels for the task
- when you want to restrict what tools the agent can use
- when you want to control system prompt so you are not always "a helpful coding agent"
- when you want the convenience of using a custom primary agent in opencode

a custom subagent lets you set the model to use so you can use a high or low model, high or low effort, etc. based on the needs of the task.

you can use restrict what tools the subagent can use, effectively sandboxing agents to only the tools that it really needs.

you can control the system prompt. the default system prompt instructs the model to act as a helpful coding assistant, but that might conflict with specific instructions you want to give a special purpose subagent.

in opencode, you can define 'primary' subagents that let you toggle 'modes' with the tab key. by default it has 'build' and 'plan' modes but when you add a new primary agent type it becomes a new 'mode' and you can prompt it directly.

# 1. starting a new project + working with nix

language-specific stuff (later)

- using lua?:
    * dependencies: lua, stylua, luacheck, lua-language-server
    * create config files for the checkers
- using node?:
    * dependencies: nodejs
    * init package.json and setup 'test' and 'build' scripts
    * add node_modules to .gitignore
- using python?:
    * dependencies: uv
    * run uv init

# opencode primary agent that knows the workflow, how to use subagents, skills
