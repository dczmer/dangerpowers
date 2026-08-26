# Writing Skills Deep Dive - Part 2: Trigger Testing

The skill `description` field is the primary triggering mechanism. When the agent starts up, it loads all skill front-matter into context along with instructions to read the corresponding skill file when a matching trigger phrase is encountered. (NOTE: this isn't 100% true any more - some harnesses have developed optimizations or ways to defer loading of skills to reduce context bloat).

But LLMs are non-deterministic and don't always load your skills the way you expect:
- Sometimes the wording of your description is passive or worded in a way the AI can easily rationalize away.
- Sometimes the contents of the current context window may conflict and cause the AI to decide NOT to load the skill.
- If the description paraphrases what the skill actually does, the AI may decide the description provides enough instruction and doesn't bother to load the skill.
- A vaguely written description may trigger too often, hijacking requests for other skills or invoking skills at the wrong times.

## What is Trigger Testing?

- evaluate how frequently a skill triggers for pre-defined "positive" trigger phrases
- evaluate how frequently a skill triggers for pre-defined "negative" trigger phrases (false-positives)
- run multiple tests over the same prompts to get a good measure (llms not deterministic)
- run a self-optimizing loop: examine the results, decide where problems exist, update description, re-run entire suite of tests, accept or revert, repeat.

## Conventions and Best Practices

- Don't ship skills without trigger tests
- (Or, write skills that do not auto-trigger)
- Keep it short/lean; front-matter always loaded into context (<1024 chars)
- Don't skip negative cases (when NOT to trigger)
- test both the positive and negative trigger cases
- track false-positive rates in eval suites
- test early, with minimal description and a few known trigger phrases
- 10-20 real prompts (ideally from actual user sessions)
- start small with just a "golden" rule-set and iterate
- expand incrementally when new edge cases arise
- every user-reported issue => regression eval

## Custom Harness

we need to do a bit of harness engineering. but do we need a custom harness or can we do something simpler?

concerns:
- isolate from other skills so they don't hijack requests
- avoid actually triggering skill workflows or real work
- avoid letting the agent find the skill file in the repository
- organize test artifacts

we can create a `/tmp` workspace for each test run and copy over just the yaml front-matter of the target skill, then launch an agent from that workspace directory. this isolates from the repository skills and prevents the skill from doing any actual work.

isolating from other skills could be harder, if they are installed in the user's global skills directory. `opencode --pure` will prevent loading plugins but not skills installed in your agents directory. you can try changing `$XDG_RUNTIME_DIR` but that causes other issues.

subagent orchestration:
- easy and works on every harness
- not isolated from other skills
- not isolated from source skills (repository with real skill files)
- no way to prevent doing actual work
- no way to use different models in subagent sessions (at least not in opencode)

cli agent orchestration:
- can isolate from other skills, and from project-level AGENTS.md by running from a tmp directory
- requires harness-specific commands, making it harder to support multiple harnesses
- can specify model and system prompt
- pi is a really good option here

issues with opencodesdk custom harness:
- matches opencode harness routing and system prompt
- opencode lock-in or maintain multiple implementations for each harness

issues with langchain custom harness:
- completely flexible and customizable
- does not actually match specific harness routing and system prompt
- have to reverse-engineer a moving target to try and match
- have to manage as a separate package/project

i chose cli agent orchestration. the skill implements the testing logic, we use a script to manage a workspace directory, and we use skill reference files to hold harness-specific commands.

Design changes from the skills.old version:
- The skill file drives the campaign logic
- The script is ported to python + asyncio + type hints
- The `cmd_init` can use the generic `.agents` directory instead of `.opencode`
- The script manages the test workspaces and `cmd_batch`, but does not implement the `cmd_eval`
- We have a per-harness module that implements `cmd_eval` for that harness and outputs the verdict, starting with one for opencode.

## Integration into writing-skills

TBD

## Testing writing-skills

TODO

## Example

TODO
