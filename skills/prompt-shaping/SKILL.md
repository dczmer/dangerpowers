---
name: prompt-shaping
description: Use when a user's request is vague, underspecified, or incomplete — the request names a goal without naming the scope, target, or boundaries (even if those words aren't used). Use this skill to avoid building the wrong thing by clarifying intent before execution. Does not apply when the request already names specific files, libraries, or exact implementation details.
---

# Prompt Shaping

Rapid prototyping of user intent through structured proposals. State the interpretation BEFORE executing, so misalignment costs a sentence instead of a wrong implementation.

## When NOT to Apply

- The request is already specific (names files, behavior, success criteria) — shaping is noise; just do it.
- The request is purely informational ("what does X do?") — there is nothing to scope.
- The user already corrected a previous interpretation — execute the correction, don't re-shape.

## Process

0. **Context grounding** — Before proposing, scan the environment: existing patterns that inform reasonable defaults, what the proposal must integrate with, constraints the user didn't state but likely expects.
1. **Restate in natural language** — Articulate what you understand the user wants, making assumptions explicit.
2. **Bullet the structure** — Break the restatement into scannable components.
3. **Propose an iterative grounding loop** — Define how completion will be verified.
4. **State the next action** — Commit to a concrete step if the interpretation is correct.

**Clarification step:** When the request is underspecified (doesn't name scope, target, or boundaries), **ask clarifying questions** rather than writing a plan document. Shaping is about aligning with the user, not deferring work.

## Grounding Loop (Iterative Verification)

- **Define success criteria** — What observable outcome proves the request is fulfilled?
- **Propose a verification method** — A concrete executable check (test, command, assertion).
- **Commit to iteration** — Run the verification repeatedly until it passes.

The loop terminates when verification passes, not when you believe the work is done.

## Spec Block

When shaping converges, emit the agreed intent as a copyable block so downstream artifacts can quote it verbatim as their `request:`:

```markdown
## Spec
- **Goal:** ...
- **In scope:** ...
- **Out of scope:** ...
- **Assumptions:** ...
- **Success criteria:** ...
```

If the work will span multiple skills or sessions, offer to save it to `RESEARCH/YYYY-MM-DD-<kebab-description>-spec.md` under the project root (committed to source control).

Example proposals:
> "I'll add the API endpoint, then write a test that calls it and asserts the expected response. I'll iterate until the test passes."

> "I'll fix the bug by first writing a failing test that reproduces it, then modifying the code until the test passes."

## Example

> **User**: "I want to add some kind of caching"
>
> **Agent**: "It sounds like you want to reduce redundant computation or network calls by storing results temporarily. I'm assuming:
> - In-memory cache (not distributed)
> - Cache invalidation on write
> - For the API layer, not the database layer
>
> If this is correct, I'll start by adding a simple LRU cache wrapper around the API client, with a test asserting repeated calls hit the cache."
