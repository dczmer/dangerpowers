---
name: writing-skills
description: Use when the user asks to "write a new skill", "create skill", "edit skill", "update skill", or "review skill" — including reviewing one before deployment. Produces a validated SKILL.md with correct frontmatter, a directive body, and a closing checklist.
---

# Writing Skills

## Overview

A skill is a reusable reference guide for a proven technique, pattern, or tool — not a narrative about a problem you solved once.

**Placement:** Decide where the skill file goes BEFORE writing anything:
1. If the user's prompt specifies a location, use it.
2. If the current project's AGENTS.md directs where skills live (e.g. a `skills/` directory convention), follow that direction.
3. Otherwise, use the `question` tool to ask whether to accept the default `.opencode/skills/` or enter a specific path (e.g. `.agents/skills/` for cross-tool portability). Do not proceed until answered.

## Pre-flight Checks

This skill requires that `agentskills` is available in the current `PATH` in order to validate the final results. Check with `command -v agentskills` before beginning work. If it is not found, then abort and inform the user.

## When to Create a Skill

**Create when:**
- The technique wasn't intuitively obvious
- You'd reference it again across projects
- The pattern applies broadly (not project-specific)

**Don't create for:**
- One-off solutions
- Standard practices well-documented elsewhere
- Project-specific conventions (those go in AGENTS.md)
- Mechanical constraints enforceable with code or validation — automate those; save documentation for judgment calls

## Content

- Written as directives, not essays.
- Lean and short (`SKILL.md` should be <500 lines).
- Describes goals, constraints and end conditions, not rigid step-by-step instructions.
- Describes the required outcome, rather than enforcing a procedural path.
- Does not contain no-op statements or commentary that is not relevant to the goals, constraints, or end conditions.
- Use explicit instructions ("Always use X"), never passive phrasing ("X is recommended").
- State constraints directly. No nuance or exemption clauses that scope a directive ("unless X", "except when Y") — fold the condition into the directive or leave it out.
- Ends with a checklist or verification procedure so the agent can verify its work.

## Frontmatter

Two required fields: `name` and `description`.

- `name`: lowercase letters, numbers, hyphens only. Prefer gerunds/verb-first: `writing-skills`, not `skill-writing`.
- `description`: imperative ("Use when..."), describes WHAT the skill does AND WHEN to use it — a few sentences to a short paragraph, ≤1024 chars.
  - Start with "Use when..." plus concrete triggering conditions and symptoms.
  - State what the skill produces (one clause) so the agent can match user intent, not just internal mechanics.
  - **Never summarize the workflow.** A description that summarizes the process becomes a shortcut agents follow instead of reading the skill body.
   - Keep it concise. Move exhaustive anti-pattern enumerations into the body; keep only the most discriminating trigger or symptom in the description.
  - Weave trigger terms (error messages, symptoms, synonyms, tool names) into the prose. Never append a `Keywords:` or `Trigger phrases:` label — see Description YAML safety below.
  - **Err on the side of being pushy.** List contexts where the skill applies, including situations where the user doesn't name the domain — the description is the primary trigger mechanism, and under-triggering makes the skill invisible.
  - **Front-load boundaries; never trail them.** A "Do NOT use for..." clause at the end of a description is weak — readers treat the positive trigger framing as dominant and rationalize past trailing negations. If a boundary matters, make it the opening condition ("Use ONLY when X and NOT when Y").
  - **Match speech acts, not request properties.** The router can only match what's visible in the prompt's surface — frame triggers as what the user says or does ("user says 'not sure', hedges with 'some kind of X'"), never as judgments about the request ("request is vague / underspecified").
  - **Anchor with quoted micro-phrases.** Short quoted signals give the router literal handles to match against; they outperform abstract category names ("expresses uncertainty").
  - **Name negative classes by verb category.** When excluding a class of requests, list the action verbs that define it (write, fix, add, run) rather than describing the class abstractly ("direct imperatives").

```yaml
# Bad: summarizes workflow
description: Use when writing skills — drafts frontmatter, structures the body, runs the checklist

# Good: what + when, keywords woven
description: Use when creating new skills, editing existing skills, or reviewing a skill before deployment. Covers frontmatter and body structure for skill files.
```

### Description YAML safety

The `description` is a YAML scalar. Two pitfalls that break parsing (`agentskills validate` fails and the skill will not load):

- **Colon-in-scalar:** a plain scalar cannot contain `key: value` (a colon followed by a space). Appending `Keywords: ...` or `Trigger phrases: ...` inside a one-line plain-scalar description causes parsing failures. Weave keywords into prose instead.
- **Length:** long descriptions bloat every agent run since all descriptions load at startup. Keep to a short paragraph (limit in Frontmatter above).

## Structure

```
skills/
  skill-name/
    SKILL.md              # Required. Overview + workflow.
    references/           # Heavy reference (100+ lines); load on demand
      some-topic.md
    scripts/              # Reusable tools
```

- Keep principles, patterns, and short code inline. Move heavy reference to `references/` and reusable tools to `scripts/`, referenced one level deep from SKILL.md.
- Use scripts for deterministic or rigid step-by-step processes.
- Keep SKILL.md concise — every token competes with conversation context. Reference `--help` instead of documenting flags; cross-reference other skills by name (`**REQUIRED SUB-SKILL:** use <name>`) instead of repeating their content.
- One excellent, complete example beats several mediocre ones. No multi-language versions, no fill-in-the-blank templates.
- Use flowcharts for non-obvious decisions or loops with early exits, tables for reference data, numbered lists for linear steps.
- When editing an existing skill, read it fully first and match its established form and register — don't blend styles.

## Checklist

Create a todo for each item.

**Preflight**
- [ ] `agentskills` is available in the current PATH.

**Content:**
- [ ] No nuance clauses; no exemption clauses that try to scope
- [ ] Instructions written as directives
- [ ] `SKILL.md` is <500 lines.
- [ ] Does not describe a rigid step-by-step process.
- [ ] Describes a desired outcome and constraints, rather than a procedural path.
- [ ] Is free of no-op statements.
- [ ] Is free of passively-phrased wording.
- [ ] No reference files that are _always_ loaded by the main skill body - that does nothing to keep the skill lean.

**Frontmatter:**
- [ ] `name` is hyphens/lowercase, gerund or verb-first
- [ ] `description` starts with "Use when...", imperative, states WHAT + WHEN — no workflow summary
- [ ] Trigger terms woven into prose; no `Keywords:`-style label; ≤1024 chars
- [ ] `agentskills validate <resolved-skill-dir>` (the skill's base directory) prints `Valid skill`

**Body:**
- [ ] Overview states the core principle in 1-2 sentences
- [ ] One complete example; no multi-language dilution
- [ ] Flowchart only if a decision is non-obvious
- [ ] Supporting files only for heavy reference or tools, one level deep
- [ ] Concise: no repeated content, no obvious explanations, flags deferred to `--help`
- [ ] Ends with a checklist or verification procedure

**Deployment:**
- [ ] Placement decided per the Placement rule (prompt > repo direction > `question` tool with `.opencode/skills/` default)
