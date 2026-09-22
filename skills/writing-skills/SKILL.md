---
name: writing-skills
description: Use when authoring, editing, or reviewing the definition file of a skill — creating a new skill, updating an existing one, or checking one against conventions before deployment. Covers frontmatter conventions and body structure for skill files. Trigger only when the request asks to change or review a skill's definition content; a request that operates on a skill without changing its definition — running or testing it, loading or invoking one by name, discovering which skills exist, picking a skill for a task, or asking what a skill does — is not for this skill.
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
- Lean and short: the whole skill — `SKILL.md` plus every file the body loads — must stay under 500 lines total. This is a hard limit, not a guideline.
- Moving content into `references/` (or any companion file) to get under the limit is a violation, not a way to comply: any content a reader must open to use the skill counts toward the limit. No exceptions — a reviewer calling the file "dense, not bloated" does not raise the limit, and a release deadline does not suspend it.
- Instruction specificity matches task fragility. Prescribe exact steps where the operation is irreversible, order-dependent, or has one correct form. State goals, constraints and end conditions everywhere else.
- Does not contain no-op statements or commentary that is not relevant to the goals, constraints, or end conditions.
- Use explicit instructions ("Always use X"), never passive phrasing ("X is recommended").
- State constraints directly. No nuance or exemption clauses that scope a directive ("unless X", "except when Y") — fold the condition into the directive or leave it out.
- Provide defaults, not menus. Name the one approach unconditionally. Give alternatives only as condition-scoped switches — each gated on the concrete condition that disqualifies the default ("use setuptools when the build compiles C extensions"). Never frame the choice as open: no neutral comparisons, no "pick whichever fits."
- Pick one term per concept and use it everywhere.
- No time-sensitive information. Put legacy approaches in a clearly labeled legacy section.
- Every skill includes a `## Gotchas` section listing the setup details a sensible guess gets wrong: surprising defaults, silent failure modes, ordering traps.
- Ends with a checklist or verification procedure so the agent can verify its work.
- When a request asks for something the skill forbids: (1) name the forbidden part and state that you are not producing it, in one sentence; (2) produce the compliant artifact in full. Both parts, always.

## Frontmatter

- Open every SKILL.md with a YAML frontmatter block delimited by `---`, carrying the two required fields `name` and `description`, before any body content.

- Name the skill with a gerund or verb-first slug, all lowercase hyphens: `profiling-slow-sql-queries`, not `sql-query-profiler`.
- `description`: third person about the skill, never first or second person ("I can help you..."). Exactly two parts, in order, ≤1024 chars:
  1. An imperative trigger clause — "Use when..." plus the concrete triggering conditions and symptoms. Weave trigger terms into prose; never a `Keywords:`-style label or a bare list of quoted phrases.
  2. One coverage clause naming the domain or technique the skill covers.
  No procedure steps: a sequence of things the workflow does is not a coverage clause. The body owns the HOW; the description exists only so the agent can match user intent.
  Keep it concise. Move exhaustive anti-pattern enumerations into the body; keep only the most discriminating trigger or symptom in the description.

```yaml
# Bad: summarizes workflow
description: Use when writing skills — drafts frontmatter, structures the body, runs the checklist

# Good: what + when, keywords woven
description: Use when creating new skills, editing existing skills, or reviewing a skill before deployment. Covers frontmatter and body structure for skill files.
```

## Discovery

A skill is used only if a future agent can find it. Optimize for the retrieval flow from the searching agent's side:

1. Encounters a problem ("tests are flaky")
2. Searches skills (greps descriptions)
3. Matches a description
4. Scans the overview (is this relevant?)
5. Reads patterns (quick reference table)
6. Loads the example (only when implementing)

Consequences:

- Description and overview must use the vocabulary an agent reaches for mid-task: error messages, symptoms, tool names, and synonyms ("flaky", "hang", "race condition") — not the skill's internal conceptual name.
- Put searchable terms early and often; the overview has seconds to answer "is this relevant?".
- Diagnose non-use by step: never found is a step 2–3 failure (description, keywords); found but dismissed is step 4 (overview); read but not applied is step 5–6 (patterns, example).

## Structure

```
skills/
  skill-name/
    SKILL.md              # Required. Overview + workflow.
    references/           # Heavy reference (100+ lines); load on demand
      some-topic.md
    scripts/              # Reusable tools
```

- SKILL.md carries the workflow and one short illustrative snippet. Bulk reference data (matrices, catalogs, long lists) lives in `references/<topic>.md`, linked once from SKILL.md. Small tables may stay inline.
- Use scripts for fully deterministic processes. Scripts handle their own error cases instead of failing back to the agent. No magic constants — justify every number in the script.
- Keep SKILL.md concise — every token competes with conversation context. Reference `--help` instead of documenting flags; cross-reference other skills by name (`**REQUIRED SUB-SKILL:** use <name>`) instead of repeating their content.
- Show one complete, filled-in example, not several mediocre ones. No multi-language versions, no fill-in-the-blank templates.
- A procedure with branches or early exits MUST be a ```mermaid flowchart TD block: one node per step, one diamond per branch, one terminal node per early exit. Reference data MUST be a markdown table. Numbered lists are only for strictly linear steps.
- When editing an existing skill, read it fully first.
- Don't assume a skill that works on a large model works on a small one; spell out instructions a frontier model could follow implicitly.

## Gotchas

- A description that summarizes the workflow stops the skill from loading — the agent decides it
  already knows the process and skips the body. State WHAT + WHEN, never HOW.
- Description triggering is testable, not a matter of taste: a description that fires too often or
  not at all is a bug. Run trigger-testing-skills against it and confirm agents load the body and
  follow it, rather than executing the description's summary.
- Extracting to `references/` saves nothing if the file loads on every invocation — that is inline
  content with extra steps. Load a reference only under a condition.

## Checklist

Create a todo for each item.

**Content:**
- [ ] No nuance clauses; no exemption clauses that try to scope
- [ ] Includes a "Gotchas" section for setup details a sensible guess gets wrong
- [ ] Provides defaults, not menus of options
- [ ] Instructions written as directives
- [ ] `SKILL.md` is <500 lines.
- [ ] Every prescribed step is justified by fragility (irreversible, order-dependent, one correct form); steps that could vary harmlessly are stated as outcomes instead.
- [ ] Is free of no-op statements.
- [ ] Is free of passively-phrased wording.
- [ ] No reference files that are _always_ loaded by the main skill body - that does nothing to keep the skill lean.

**Frontmatter:**
- [ ] `name` is hyphens/lowercase, ≤64 chars, gerund or verb-first
- [ ] `description` has both slots: "Use when..." trigger clause + one coverage clause; no procedure steps; third person; ≤1024 chars
- [ ] Trigger terms woven into prose; no `Keywords:`-style label
- [ ] Triggering behavior verified with trigger-testing-skills, not assumed

**Body:**
- [ ] Overview states the core principle in 1-2 sentences
- [ ] One complete example; no multi-language dilution
- [ ] Flowchart only if a decision is non-obvious
- [ ] Supporting files only for heavy reference or tools, one level deep
- [ ] Concise: no repeated content, no obvious explanations, flags deferred to `--help`
- [ ] Ends with a checklist or verification procedure
