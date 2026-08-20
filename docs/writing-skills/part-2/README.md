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

## Issues Running Tests

- need to run (first) without the skill, but skill may be auto-loaded when the agent starts up
- contamination from other skill descriptions
- contamination from your global AGENTS.md
- other plugins or extensions may affect behavior or inject context (more contamination)
- triggering the real skill may cause it to start doing actual work, which can be expensive and slow and produce junk artifacts or make undesirable changes on your system
- managing campaign artifacts
    
- custom agent: system prompt and tool usage restrictions
- run from tmp directory, don't pick up repo-level skills, rules, etc
- can override XDG_RUNTIME_DIR to prevent loading global AGENTS.md (opencode)

pi is actually a pretty good option as a test harness, because you can control most of these things with command-line arguments.

- copy skill "stubs" to a tmp working space (just the descriptions, no body that will potentially start executing work)

## Custom Harness


## Integration into writing-skills


## Testing writing-skills


## Example
