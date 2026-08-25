---
name: writing-skills
description: Use when the user asks to "write a new skill", "create skill", "edit skill", "update skill", or "review skill".
---

# Writing Skills

## Overview

A skill is a reusable reference guide for a proven technique, pattern, or tool — not a narrative about a problem you solved once.

## When to Create a Skill

**Create when:**
- The technique wasn't intuitively obvious
- You'd reference it again, across projects or repeatedly within one
- It's a procedure or workflow, not a standalone fact

**Don't create for:**
- One-off solutions
- Standard practices well-documented elsewhere
- Durable facts needed in every session (those go in AGENTS.md)
- Mechanical constraints enforceable with code or validation — automate those; save documentation for judgment calls

## Content

- Written as directives, not essays.
- Lean and short (`SKILL.md` should be <500 lines).
- Instruction specificity matches task fragility. Prescribe exact steps where the operation is irreversible, order-dependent, or has one correct form. State goals, constraints and end conditions everywhere else.
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

```yaml
# Bad: summarizes workflow
description: Use when writing skills — drafts frontmatter, structures the body, runs the checklist

# Good: what + when, keywords woven
description: Use when creating new skills, editing existing skills, or reviewing a skill before deployment. Covers frontmatter and body structure for skill files.
```

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
- Use scripts for fully deterministic processes.
- Keep SKILL.md concise — every token competes with conversation context. Reference `--help` instead of documenting flags; cross-reference other skills by name (`**REQUIRED SUB-SKILL:** use <name>`) instead of repeating their content.
- One excellent, complete example beats several mediocre ones. No multi-language versions, no fill-in-the-blank templates.
- Use flowcharts for non-obvious decisions or loops with early exits, tables for reference data, numbered lists for linear steps.
- When editing an existing skill, read it fully first.

## Checklist

Create a todo for each item.

**Content:**
- [ ] No nuance clauses; no exemption clauses that try to scope
- [ ] Instructions written as directives
- [ ] `SKILL.md` is <500 lines.
- [ ] Every prescribed step is justified by fragility (irreversible, order-dependent, one correct form); steps that could vary harmlessly are stated as outcomes instead.
- [ ] Is free of no-op statements.
- [ ] Is free of passively-phrased wording.
- [ ] No reference files that are _always_ loaded by the main skill body - that does nothing to keep the skill lean.

**Frontmatter:**
- [ ] `name` is hyphens/lowercase, gerund or verb-first
- [ ] `description` starts with "Use when...", imperative, states WHAT + WHEN — no workflow summary
- [ ] Trigger terms woven into prose; no `Keywords:`-style label; ≤1024 chars

**Body:**
- [ ] Overview states the core principle in 1-2 sentences
- [ ] One complete example; no multi-language dilution
- [ ] Flowchart only if a decision is non-obvious
- [ ] Supporting files only for heavy reference or tools, one level deep
- [ ] Concise: no repeated content, no obvious explanations, flags deferred to `--help`
- [ ] Ends with a checklist or verification procedure
