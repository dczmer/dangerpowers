---
name: prompt-shaping
description: Use when a user asks for help turning a vague or under-specified idea, request, or task into a detailed prompt with concrete requirements and scope. Covers interviewing the user one question at a time and emitting a copyable spec and prompt text.
disable-model-invocation: true
metadata.opencode/slash: true
metadata.opencode/autoinvoke: false
---

# Prompt Shaping

Turn an under-specified idea into a copyable prompt through a one-question-at-a-time interview. State the interpretation BEFORE drafting, so misalignment costs a sentence instead of a wrong prompt.

The deliverable is the prompt artifact itself: a filled Spec block plus the complete prompt text. Do not execute the task the prompt describes.

## When NOT to Apply

- The request is already specific (names files, behavior, success criteria) — shaping is noise; draft the prompt directly.
- The request is purely informational ("what does X do?") — there is nothing to scope.
- The user already corrected a previous interpretation — apply the correction, don't re-interview.

## Process

0. **Ground in context** — Before asking anything, scan the environment for existing patterns that inform reasonable defaults, what the prompt must integrate with, and constraints the user didn't state but likely expects. Never ask a question the codebase already answers.
1. **Restate in natural language** — Articulate what you understand the user wants, making assumptions explicit.
2. **Interview one question at a time** — Ask a single focused question per turn until every Spec field below is answered. Ask clarifying questions rather than writing a plan document; shaping is about aligning with the user, not deferring work. Elicit each field explicitly:
   - **Goal** — what should the prompt make the model do?
   - **In scope** — what must the output cover?
   - **Out of scope** — what must the output avoid or ignore?
   - **Assumptions** — what are you taking for granted that the user should confirm?
   - **Success criteria** — what observable property of the output proves the prompt worked?
   - **Output format** — structure, length, style; ask for or propose a worked example of ideal output.
   - **Audience** — who or what consumes the output?
   - **Grounding context** — which documents, facts, or definitions must the prompt include or reference?
   - **Failure cases** — what would a bad response look like?
3. **Emit the Spec block for sign-off** — Present the filled Spec block and ask the user to confirm or correct it. The interview converges on user sign-off, not on your confidence.
4. **Emit the prompt** — On confirmation, write the complete prompt text in a single code fence, encoding every Spec field. Keep it model-agnostic: omit few-shot exemplars, chain-of-thought scaffolding, and role personas. Add a prompting technique when the user explicitly requests it.

## Spec Block

```markdown
## Spec
- **Goal:** ...
- **In scope:** ...
- **Out of scope:** ...
- **Assumptions:** ...
- **Success criteria:** ...
- **Output format:** ...
- **Audience:** ...
- **Grounding context:** ...
- **Failure cases:** ...
```

## Example

> **User**: "help me write a prompt for adding some kind of caching"
>
> **Agent**: "It sounds like you want a prompt that instructs a coding agent to reduce redundant computation or network calls by storing results temporarily. I'm assuming in-memory, not distributed. One question at a time: which layer should the cache cover — the API client, the database layer, or something else?"
>
> *(interview continues, one question per turn)*
>
> **Agent**:
> ```markdown
> ## Spec
> - **Goal:** Add caching to the API client layer to eliminate repeated network calls.
> - **In scope:** In-memory LRU cache wrapper around the API client; invalidation on write; a test asserting repeated calls hit the cache.
> - **Out of scope:** Distributed caching, database-layer caching, cache persistence.
> - **Assumptions:** Single-process service; cache size of 1000 entries is acceptable.
> - **Success criteria:** Test asserting a repeated identical call produces exactly one network request passes.
> - **Output format:** New module `cache.py` plus a test file; concise comments.
> - **Audience:** The coding agent executing the prompt; maintainers reading the diff.
> - **Grounding context:** Existing `api_client.py` patterns; project test conventions.
> - **Failure cases:** Cache without invalidation; caching added to the wrong layer; no test.
> ```
>
> "Confirm or correct this spec, and I'll emit the prompt."
>
> **User**: "looks right"
>
> **Agent**:
> ```markdown
> Add an in-memory LRU cache (1000 entries) around the API client in `api_client.py`, as a new module `cache.py` following the existing patterns in that file. Invalidate cache entries on write operations. Do not add distributed caching, database-layer caching, or persistence. Write a test asserting that a repeated identical call produces exactly one network request, following the project's test conventions. Keep comments concise.
> ```

## Gotchas

- Announcing what you are about to build instead of asking is the primary failure mode — state an interpretation and ask, never draft first and ask later.
- Batching all nine questions into one message reads as a form, not an interview; users half-answer. One question per turn.
- A confirmed spec with no emitted prompt is a failed run — always close with the code-fenced prompt after sign-off.
- Skip a field only when the user explicitly waives it; silently dropped fields produce silently wrong prompts.

## Checklist

- [ ] Scanned the environment before asking any question
- [ ] Asked one question per turn; no batched question lists
- [ ] Every Spec block field explicitly elicited or explicitly waived
- [ ] Spec block confirmed by the user before drafting
- [ ] Prompt emitted in a single code fence, encoding all confirmed fields
- [ ] No task execution; no plan document substituted for questions
- [ ] Prompt contains no exemplars, CoT scaffolding, or personas beyond what the user explicitly requested
