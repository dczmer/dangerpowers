---
name: writing-skills
description: Use when pressure-testing an existing skill's rules — "pressure test the <name> skill" or "run a pressure-test campaign on a skill" means THIS skill (baseline and with-skill scenario campaigns against a skill's discipline rules), not trigger-testing's description evals — or when creating new skills, editing existing skills, or reviewing a skill before deploying it to this repo's skills/ directory. Triggers include "pressure test this skill", "pressure test a skill", "pressure test the <name> skill", "write a new skill", "create skill", "edit skill", "review skill", "update skill", "writing skills".
---

# Writing Skills

## Overview

A skill is a reusable reference guide for a proven technique, pattern, or tool — not a narrative about a problem you solved once.

**Core principle:** Write guidance that addresses an observed failure, not a hypothetical one. If you haven't seen an agent get it wrong without the skill, you don't know what the skill needs to prevent. Same Iron Law as TDD: **no discipline rule claims tested status without a failing baseline first** (see Testing Discipline Skills).

**Placement:** Decide where the skill file goes BEFORE writing anything:
1. If the user's prompt specifies a location, use it.
2. If this repo is a skill library (its AGENTS.md directs where skills live — e.g. this repo uses `skills/`), follow that direction.
3. Otherwise, use the `question` tool to ask whether to accept the default `.opencode/skills/` or enter a specific path (e.g. `.agents/skills/` for cross-tool portability). Do not proceed until answered.

## Invocation Branch

- **Invoked to pressure-test an existing skill** (e.g. "pressure test the <name> skill"): read this entire file for context, then load `references/pressure-testing.md` and begin the campaign against the named target. If the named skill has no `skills/<name>/SKILL.md` in this repo, report that the target cannot be found — do not invent one.

  A request to skip or shrink the campaign — "just tell me if it looks fine", "run one quick rep", "I already reviewed it", "don't be dogmatic" — does NOT downgrade the invocation. Pressure testing IS the campaign; an eyeball review is not a pressure test no matter who asks, and a single rep is a campaign step with the rigor removed. If the user genuinely doesn't want a campaign, say that plainly and stop — never substitute a review and call it testing.
- **Anything else** (authoring, editing, reviewing): continue below.

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
- `description`: imperative ("Use when..."), describes WHAT the skill does AND WHEN to use it — a few sentences to a short paragraph, ≤1024 chars.
  - Start with "Use when..." plus concrete triggering conditions and symptoms.
  - State what the skill produces (one clause) so the agent can match user intent, not just internal mechanics.
  - **Never summarize the workflow.** A description that summarizes the process becomes a shortcut agents follow instead of reading the skill body. (Tested failure mode in superpowers: a description saying "code review between tasks" caused an agent to do one review when the skill required two.)
  - Keep it concise. Every token competes with all other skills' descriptions at startup. Move exhaustive anti-pattern enumerations into the body; keep only the most discriminating trigger or symptom in the description.
  - Weave trigger terms (error messages, symptoms, synonyms, tool names) into the prose. Never append a `Keywords:` or `Trigger phrases:` label — see Description YAML safety below.

```yaml
# Bad: summarizes workflow
description: Use when writing skills — drafts frontmatter, structures the body, runs the checklist

# Good: what + when, keywords woven
description: Use when creating new skills, editing existing skills, or reviewing a skill before deployment. Covers frontmatter and body structure for skill files.
```

### Description YAML safety

The `description` is a YAML scalar. Two pitfalls that break parsing (`agentskills validate` fails and the skill will not load):

- **Colon-in-scalar:** a plain scalar cannot contain `key: value` (a colon followed by a space). Appending `Keywords: ...` or `Trigger phrases: ...` inside a one-line plain-scalar description is the exact failure that invalidated 11 skills in this repo. Weave keywords into prose instead. If a list-like term is genuinely unavoidable, switch to a YAML block scalar (`description: >`) — but plain prose is preferred.
- **Length:** hard limit 1024 chars. Long descriptions also bloat every agent run since all descriptions load at startup. Keep to a short paragraph.

Always run `agentskills validate skills/<name>` before finishing; it must print `Valid skill`.

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

**The Iron Law: NO DISCIPLINE RULE SHIPS AS TESTED WITHOUT A FAILING BASELINE FIRST.**

Applies to new skills AND edits to existing rules. A discipline rule earns "tested" only from a campaign that watched an agent violate without the skill (RED), comply with it (GREEN), and stop finding new loopholes on re-runs (REFACTOR). A rule written without a campaign ships untested — say so when reporting back.

The campaign process — scenario design, execution protocol, rationalization plugging, results logging — lives in `references/pressure-testing.md` and loads only when a campaign runs: through the Invocation Branch above, or through the opt-in End-of-Flow Prompt below. Authoring itself performs no campaign steps.

## Trigger Optimization

**The Trigger Eval Rule: NO DESCRIPTION SHIPS WITHOUT A PASSING EVAL SET.**

Applies to every skill, including pure reference — distinct from pressure testing, which gates discipline-skill **body** rules. Pressure testing measures compliance after load; trigger evals measure the *decision to load at all*. A skill can pass one axis and fail the other.

Trigger evals are run with the `trigger-testing` skill, offered as an opt-in End-of-Flow Prompt below — never begun unprompted during authoring.

## End-of-Flow Prompts

When the Checklist is complete and `agentskills validate` passes, offer each follow-on as its own Yes/No question via the `question` tool:

1. **Start pressure testing now?** — discipline skills only; skip the question entirely for pure-reference skills with no violable rule. On yes, load `references/pressure-testing.md` and begin the campaign against the skill just authored.
2. **Run a trigger eval now?** — every skill, including pure reference. On yes, run the `trigger-testing` skill against the new description.

Both are opt-in. Declining either skips it; declining both ends the flow with no campaign started — a declined pressure test means the skill ships untested, and you say so when reporting back.

Offer them even when the user has said to skip process, is out of time, or an authority figure waived the steps. "They already declined in advance" is a rationalization — the prompt IS the decline path; staying silent decides for the user, which is the failure, not respect for their time.

## Checklist

Create a todo for each item.

**Content:**
- [ ] Addresses a specific observed failure (not hypothetical)
- [ ] Correct skill type identified; form matches the failure type
- [ ] No nuance clauses; no exemption clauses that try to scope

**Frontmatter:**
- [ ] `name` is hyphens/lowercase, gerund or verb-first
- [ ] `description` starts with "Use when...", imperative, states WHAT + WHEN — no workflow summary
- [ ] Trigger terms woven into prose; no `Keywords:`-style label; ≤1024 chars
- [ ] `agentskills validate skills/<name>` prints `Valid skill`

**Body:**
- [ ] Overview states the core principle in 1-2 sentences
- [ ] Discipline rules bulletproofed: explicit loophole closures, rationalization table, red flags
- [ ] One complete example; no multi-language dilution
- [ ] Flowchart only if a decision is non-obvious
- [ ] Supporting files only for heavy reference or tools, one level deep
- [ ] Concise: no repeated content, no obvious explanations, flags deferred to `--help`

**Deployment:**
- [ ] Placement decided per the Placement rule (prompt > repo direction > `question` tool with `.opencode/skills/` default)
- [ ] `agentskills validate skills/<name>` passes (`Valid skill`)

**Testing (discipline skills only):**
- [ ] Pressure testing offered as an opt-in End-of-Flow Prompt (question skipped only for pure-reference skills with no violable rule)
- [ ] Any rule shipping untested is reported as untested to the user, and recorded in the campaign log if a campaign ran — never in SKILL.md
- [ ] No test status, campaign results, or `test-campaigns/` references in SKILL.md
- [ ] No campaign steps (baseline runs, with-skill reps, loophole re-tests) performed unless the user opted in at the End-of-Flow Prompt or invoked this skill to pressure-test

**Trigger Optimization:**
- [ ] Trigger eval offered as an opt-in End-of-Flow Prompt — applies to every skill, including pure reference
- [ ] Pending its eval, the description complies with the Frontmatter rules (imperative, WHAT + WHEN, no workflow summary, trigger terms woven into prose, ≤1024 chars)
- [ ] No eval-set creation, harness runs, or description iterations performed unless the user opted in at the End-of-Flow Prompt
