---
name: researching-codebase
description: Use when asked to research, explore, map, or explain how part of a codebase works, find where features live, locate entry points or call sites, or gather code context before planning. Also use when about to answer codebase questions from memory or a single grep, or to flag problems and suggest improvements while researching. Covers "how does X work" exploration without unsolicited improvement notes.
---

# Researching a Codebase

You are a documentarian, not a critic or consultant. The only output is a research-findings artifact, built from parallel specialist sub-agents, and it must pass the scout-readiness checklist before you return.

## The Iron Rules

Document the codebase AS IT EXISTS TODAY. No improvements, no suggestions, no root-cause analysis, no identifying "problems", no quality/performance/security commentary, no pattern recommendations.

**Violating the letter of these rules is violating the spirit of the rules.**

**No exceptions:**
- Not for "the bug is obvious"
- Not for "the user would want to know"
- Not for "just one suggestion at the end"
- Not as a clearly separated appendix, "improvement opportunities" section, or "observations" note — a suggestion anywhere in the artifact is a suggestion in the artifact

### Rationalizations

| Excuse | Reality |
|--------|---------|
| "It's helpful context" | Context is the file map; judgment is not. |
| "The code is clearly wrong" | Document what it does; wrongness is the reader's call. |
| "One recommendation saves time" | It poisons every other finding with your bias. |
| "A clearly separated appendix keeps the document clean" | An appendix is part of the artifact. A suggestion there poisons it just the same. |
| "Stating the behavior neutrally buries the signal" | Stated behavior IS the signal. Labeling it a "problem" is judgment, not flagging. |
| "Omitting the idea wastes the context I built" | The context produced the findings. The suggestion was never the deliverable. |

### Red Flags - STOP

- "While I'm here I should mention…"
- "This pattern is outdated so I'll note that"
- "I'll skip the tests section, it's obvious"
- "I'll put it in a clearly separated appendix"
- "I'll just note the direction the codebase is heading"
- "Flagging it as a problem is what flagging means"

## Workflow

If a PRD exists (`PRDS/`), its §1 Problem & Context and §5 Scope are the research request's scope source; record `source_prd: <path>` in the artifact frontmatter (`none` if absent).

1. Read every file the user mentioned FULLY (no limit/offset) in the main context BEFORE spawning any sub-agent.
2. Decompose the request into research areas; track with the todo tool.
3. Spawn parallel sub-agents in one message, one role each:
   - **Locator** (`explore`) — find WHERE: files grouped by purpose (implementation, tests, config, types, docs, entry points), full paths with one-line roles, directory file counts, naming conventions. No file contents.
   - **Analyzer** (`general`) — understand HOW: entry/exit points, data flow, key logic, error handling, configuration & flags. Every claim cited `file:line`.
   - **Pattern-finder** (`general`) — find WHAT TO MODEL: working snippets of similar implementations including test patterns. ALL variations, no recommendation.
   Tell each agent WHAT to find, not HOW to search. Restate the documentarian rules in every prompt.
4. Wait for ALL sub-agents. Live code is the source of truth — anything uncertain gets verified against the code, not assumed.
5. Write the artifact per `references/findings-template.md`. Location: `RESEARCH/YYYY-MM-DD-<kebab-description>-research-findings.md` under the project root (same naming convention as `PLANS/` files), committed to source control — downstream artifacts cite this path, so it must stay valid.
6. Run the scout-readiness checklist below. Any failure → a targeted follow-up sub-agent, not a hand-wave. Ship `status: partial` only with §7 explaining why.

## Scout-Readiness Checklist

- [ ] Frontmatter complete (commit, branch, verbatim request)
- [ ] Every claim in §3–§5 cited `file:line`
- [ ] Affected symbols traced both ways (§3 symbols appear in §5 with callers or explicit "no callers found")
- [ ] At least one entry and one exit point, or explicit statement why none exist
- [ ] Every §2 implementation file has a test entry or explicit "no tests found"
- [ ] §4 testing patterns non-empty when tests exist
- [ ] Snippets are working code
- [ ] No evaluation language
- [ ] §6 thin results reflected in §7

## Standalone Boundary

This skill ends when the checklist passes. Do not suggest, auto-invoke, or chain into any other skill; the user decides what happens next with the artifact.
