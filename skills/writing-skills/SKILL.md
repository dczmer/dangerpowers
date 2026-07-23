---
name: writing-skills
description: Use when creating new skills, editing existing skills, or reviewing a skill before deploying it to this repo's skills/ directory.
---

# Writing Skills

## Overview

A skill is a reusable reference guide for a proven technique, pattern, or tool — not a narrative about a problem you solved once.

**Core principle:** Write guidance that addresses an observed failure, not a hypothetical one. If you haven't seen an agent get it wrong without the skill, you don't know what the skill needs to prevent. Same Iron Law as TDD: **no discipline rule without a failing baseline first.**

**Placement:** Decide where the skill file goes BEFORE writing anything:
1. If the user's prompt specifies a location, use it.
2. If this repo is a skill library (its AGENTS.md directs where skills live — e.g. this repo uses `skills/`), follow that direction.
3. Otherwise, use the `question` tool to ask whether to accept the default `.opencode/skills/` or enter a specific path (e.g. `.agents/skills/` for cross-tool portability). Do not proceed until answered.

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

## Skill Types

| Type | What it is | Example |
|------|-----------|---------|
| Technique | Concrete method with steps | condition-based-waiting |
| Pattern | Way of thinking about problems | flatten-with-flags |
| Reference | API docs, syntax, tool guides | nix flake reference |
| Discipline | A rule agents must follow under pressure | verification-before-completion |

The type determines how the skill is written and (later) tested.

## Frontmatter

Two required fields: `name` and `description`.

- `name`: lowercase letters, numbers, hyphens only. Prefer gerunds/verb-first: `writing-skills`, not `skill-writing`.
- `description`: third person, describes ONLY when to use — never what the skill does or how it works.
  - Start with "Use when..." plus concrete triggering conditions and symptoms.
  - **Never summarize the workflow.** A description that summarizes the process becomes a shortcut agents follow instead of reading the skill body. (Tested failure mode in superpowers: a description saying "code review between tasks" caused an agent to do one review when the skill required two.)
  - Include keywords an agent would search for: error messages, symptoms, synonyms, tool names.

```yaml
# Bad: summarizes workflow
description: Use when writing skills — drafts frontmatter, structures the body, runs the checklist

# Good: triggering conditions only
description: Use when creating new skills, editing existing skills, or reviewing a skill before deployment
```

## Match the Form to the Failure

Before writing guidance, classify the failure you observed. The wrong form measurably backfires.

| Observed failure | Right form | Wrong form |
|---|---|---|
| Violates a rule it knows (discipline) | Prohibition + rationalization table + red flags | Soft guidance ("prefer...", "consider...") |
| Complies but output has wrong shape | Positive recipe: state what the output IS — its parts, in order | Prohibition list ("don't restate", "never narrate") |
| Omits a required element | Structural: REQUIRED field or slot in the template | Prose reminders near the template |
| Behavior depends on a condition | Conditional on an observable predicate ("if the plan file exists, reference it") | Unconditional rule + exemption clauses |

**Rules for any form:**
- **No nuance clauses.** "Don't X unless it matters" reopens negotiation. Express a real exception as its own conditional on an observable predicate.
- **Exemption clauses don't scope.** "This limit doesn't apply to code blocks" still suppresses code blocks. Restructure so the rule can't reach the exempt content.
- **Why prohibitions backfire on shaping problems:** agents negotiate with "don't X" under a competing incentive. A recipe leaves nothing to negotiate — output matches the stated shape or it doesn't.

## Bulletproofing Discipline Skills

For skills that enforce a rule under pressure:

1. **Close every loophole explicitly.** Don't just state the rule; forbid the specific workarounds.
   ```markdown
   Committed without running tests? Fix forward, don't amend.

   **No exceptions:**
   - Not for "docs-only changes"
   - Not for "the hook was slow"
   - Not for "I'll run them right after"
   ```
2. **Cut off spirit-vs-letter arguments early:**
   ```markdown
   **Violating the letter of the rules is violating the spirit of the rules.**
   ```
3. **Rationalization table** — seed it with excuses actually observed, grow it as new ones appear:
   ```markdown
   | Excuse | Reality |
   |--------|---------|
   | "It's a one-line change" | One-line changes break builds. Run the check. |
   ```
4. **Red flags list** so agents can self-check:
   ```markdown
   ## Red Flags - STOP
   - "I'll verify after committing"
   - "This case is different because..."
   ```
5. **Add violation symptoms to the description** — triggers for when an agent is *about* to violate, not just when the rule applies.

Persuasion register: for discipline skills use authority language ("YOU MUST", "No exceptions") and commitment devices (checklists tracked as todos). Avoid hedging and avoid friendliness-as-compliance.

## Structure

```
skills/
  skill-name/
    SKILL.md              # Required. Overview + workflow.
    references/           # Heavy reference (100+ lines), loaded on demand
      some-topic.md
    scripts/              # Reusable tools
```

- Keep principles, patterns, and short code inline. Move heavy reference to `references/` and reusable tools to `scripts/`, referenced one level deep from SKILL.md.
- Keep SKILL.md concise — every token competes with conversation context. Reference `--help` instead of documenting flags; cross-reference other skills by name (`**REQUIRED SUB-SKILL:** use <name>`) instead of repeating their content.
- One excellent, complete example beats several mediocre ones. No multi-language versions, no fill-in-the-blank templates.
- Flowcharts only for non-obvious decisions or loops you might exit early. Tables for reference, numbered lists for linear steps.
- When editing an existing skill, read it fully first and match its established form and register — don't blend styles.

## Testing Discipline Skills

**The Iron Law: NO SKILL WITHOUT A FAILING TEST FIRST.**

Applies to new skills AND edits to existing rules. Before writing or changing a discipline rule, run a baseline pressure scenario without the skill and watch an agent violate it (RED). Then write the minimal counter (GREEN). Then close any new loopholes found on re-runs (REFACTOR).

**No exceptions:**
- Not for "simple additions"
- Not for "just a wording tweak"
- Not for "documentation updates"

If the skill contains no rule an agent could violate (pure reference material), pressure testing does not apply. If a discipline rule must ship untested, it must be explicitly flagged as untested in the skill — never silently.

**REQUIRED:** See `references/pressure-testing.md` for scenario design, execution protocol, meta-testing, done criteria, and the results-log format.

## Checklist

Create a todo for each item.

**Content:**
- [ ] Addresses a specific observed failure (not hypothetical)
- [ ] Correct skill type identified; form matches the failure type
- [ ] No nuance clauses; no exemption clauses that try to scope

**Frontmatter:**
- [ ] `name` is hyphens/lowercase, gerund or verb-first
- [ ] `description` starts with "Use when...", third person, triggers/symptoms only — no workflow summary
- [ ] Keywords included (error messages, symptoms, synonyms, tools)

**Body:**
- [ ] Overview states the core principle in 1-2 sentences
- [ ] Discipline rules bulletproofed: explicit loophole closures, rationalization table, red flags
- [ ] One complete example; no multi-language dilution
- [ ] Flowchart only if a decision is non-obvious
- [ ] Supporting files only for heavy reference or tools, one level deep
- [ ] Concise: no repeated content, no obvious explanations, flags deferred to `--help`

**Deployment:**
- [ ] Placement decided per the Placement rule (prompt > repo direction > `question` tool with `.opencode/skills/` default)

**Testing (discipline skills only):**
- [ ] Baseline scenarios run WITHOUT the skill; rationalizations documented verbatim (RED)
- [ ] Scenarios re-run WITH the skill; agent complies and cites the skill (GREEN)
- [ ] New loopholes closed (rule negation + rationalization row + red flag + description symptom) and re-tested (REFACTOR)
- [ ] Results log written to `test-campaigns/` in the skill's directory
- [ ] Any rule shipped untested is explicitly flagged as untested in the skill
