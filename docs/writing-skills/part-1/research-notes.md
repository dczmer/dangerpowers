# Part 1 — Rule Audit and Sources

Every suggestion, rule, and convention asserted in `README.md` and `writing-skills.md`, with a
verdict and a citable source. Scope is limited to part 1 (no evals/optimization).

## Source keys

| Key | Source |
|---|---|
| **A** | [Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) (Anthropic) |
| **B** | [Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) (Anthropic Engineering) |
| **C** | [Agent Skills specification](https://agentskills.io/specification) |
| **D** | [Best practices for skill creators](https://agentskills.io/skill-creation/best-practices) |
| **E** | [Optimizing skill descriptions](https://agentskills.io/skill-creation/optimizing-descriptions) |
| **F** | [superpowers `writing-skills`](https://github.com/obra/superpowers/blob/main/skills/writing-skills/SKILL.md) |
| **G** | [Extend Claude with skills](https://code.claude.com/docs/en/skills) (Claude Code) |
| **H** | [Claude Code security](https://code.claude.com/docs/en/security) |
| **I** | [Defeating Nondeterminism in LLM Inference](https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/) (Thinking Machines) |
| **J** | [DeepMind — Don't Ship Skills Without Evals](https://youtu.be/0vphxNt4wyk) |

Verdicts: **Sound** · **Sound, with caveat** · **Contested** (sources disagree) · **Incorrect**

---

## 1. Mechanics and structure

| # | Claim | Verdict | Source |
|---|---|---|---|
| 1 | A skill is a directory containing `SKILL.md`; `scripts/` and `references/` are optional | **Sound** | C — spec directory structure. Adds a third convention, `assets/` (templates, images, data files) |
| 2 | Only `name` + `description` are pre-loaded into the system prompt at startup | **Sound** | A "At startup, only the metadata (name and description) from all Skills is pre-loaded"; B calls this "the first level of progressive disclosure"; C quantifies it at "~100 tokens" per skill |
| 3 | Everything else is read on demand | **Sound** | A "No context penalty for large files… don't consume context tokens until actually read" |
| 4 | The whole `SKILL.md` loads when the skill fires | **Sound** | C "the agent will load this entire file once it's decided to activate a skill" |
| 5 | The description is the router, not documentation | **Sound** | E "the description carries the entire burden of triggering"; A "The description is critical for skill selection… from potentially 100+ available Skills" |
| 6 | `SKILL.md` < 500 lines | **Sound** | A, C, G all state 500 lines verbatim. C adds a second ceiling: "< 5000 tokens recommended". F is far stricter — a *word* budget (<500 words, <200 for frequently-loaded skills) |
| 7 | `name`: lowercase/numbers/hyphens, 64 chars | **Sound** | C. Three constraints the draft omits: must not start or end with a hyphen, no consecutive hyphens, **must match the parent directory name** |
| 8 | `description` ≤ 1024 chars | **Sound** | C "hard limit of 1024 characters". Claude Code additionally truncates `description` + `when_to_use` at **1,536 chars** in the skill listing (G) |
| 9 | Forward slashes in paths, even on Windows | **Sound** | A, verbatim anti-pattern: "Unix-style paths work across all platforms" |
| 10 | Gerund naming (`processing-pdfs`) | **Sound** | A "Consider using gerund form (verb + -ing)". Note A treats it as a preference, not a rule — noun phrases and verb-first are "acceptable alternatives". F agrees: "Gerunds (-ing) work well for processes" |
| 11 | One term per concept; don't rotate field/box/element/control | **Sound** | A "Use consistent terminology" — the field/box/element/control example is lifted from this section |
| 12 | Scripts handle their own error cases | **Sound** | A "Solve, don't defer"; C scripts should "include helpful error messages" and "handle edge cases gracefully" |
| 13 | Move deterministic logic to scripts to save tokens and get consistency | **Sound** | A "Prefer scripts for deterministic operations"; B "sorting a list via token generation is far more expensive than simply running a sorting algorithm" and "many applications require the deterministic reliability that only code can provide" |
| 14 | `disable-model-invocation: true` **replaces** `description` and so costs less context | **Incorrect** | See finding **F3** below |

## 2. Descriptions and triggering

| # | Claim | Verdict | Source |
|---|---|---|---|
| 15 | Include what (capability) *and* when (triggers) | **Contested** | A and C both say include both. **F says the opposite**: "describes ONLY when to use (NOT what it does)". Your skill file sides with A/C while keeping F's no-workflow-summary rule — a defensible synthesis, but say so |
| 16 | Written in third person, always | **Sound** | A, in a Warning box: "The description is injected into the system prompt, and inconsistent point-of-view can cause discovery problems." Good/avoid examples in the draft are A's |
| 17 | Imperative, starts with "Use when…" | **Sound** | E "Use imperative phrasing… 'Use this skill when…' rather than 'This skill does…'"; F same. Not in conflict with #16 — the ban is on first/second person ("I can help you…"), not on imperatives |
| 18 | Never paraphrase/TLDR the skill body — the agent will skip loading it | **Sound, single-source** | F only, but with a concrete reproduction: a description summarising "code review between tasks" caused one review where the body's flowchart specified two; removing the summary fixed it. E offers an independent second cause of non-triggering: "agents typically only consult skills for tasks that require knowledge or capabilities beyond what they can handle alone" |
| 19 | Use trigger words a user would actually type | **Sound, with caveat** | E "Err on the side of being pushy"; F "Keyword Coverage". Caveat from E: "Avoid adding specific keywords from failed queries — that's overfitting. Instead, find the general category" |
| 20 | Don't hijack phrases belonging to other skills | **Sound** | E — the whole should-not-trigger / near-miss section: "an over-broad description means it triggers when it shouldn't" |
| 21 | Skills can be made explicit-only, slash-command style | **Sound** | G — `disable-model-invocation: true`; "Use this for workflows with side effects… You don't want Claude deciding to deploy because your code looks ready." G also documents the inverse, `user-invocable: false` |
| 22 | "The system prompt contains instructions on how to detect and dispatch skills based on words or phrases from your prompt" | **Wording nit** | Matching is semantic against descriptions, not keyword dispatch — E: "When a user's task matches a description". Keywords help; they aren't the mechanism |

## 3. Body content

| # | Claim | Verdict | Source |
|---|---|---|---|
| 23 | Be concise; every no-op and flowery paragraph is bloat | **Sound** | A "The context window is a public good"… "Does this paragraph justify its token cost?"; D "Would the agent get this wrong without this instruction? If the answer is no, cut it" |
| 24 | Anything obvious or that the agent can figure out is waste | **Sound** | A "Default assumption: Claude is already very smart. Only add context Claude doesn't already have"; D "Add what the agent lacks, omit what it knows" |
| 25 | Open with an overview stating the core principle in 1–2 sentences | **Sound** | F's `SKILL.md` template: "## Overview — What is this? Core principle in 1-2 sentences"; A frames SKILL.md itself as "an overview that points Claude to detailed materials" |
| 26 | Include when-to-use and when-*not*-to-use so the agent can abort early | **Sound** | F template ("Bullet list with SYMPTOMS… When NOT to use"). E supports the same idea one level up: "Add specificity about what the skill does *not* do" |
| 27 | Avoid passive phrasing ("X is preferred"); use "always use X" / "X must be used when Y" | **Sound, with caveat** | A, in the iteration loop: Claude A "might suggest… using stronger language such as 'MUST filter' instead of 'always filter'". Caveats: D "For flexible instructions, explaining *why* can be more effective than rigid directives"; F's form-to-failure table shows prohibitions measurably backfire when the failure is wrong-shaped output rather than rule-skipping |
| 28 | State constraints directly — no "unless X" / "except when Y" | **Sound, single-source but evidenced** | F: "appending a single nuance clause to a winning recipe degraded it from consistent to noisy"; "Exemption clauses don't scope. 'This limit doesn't apply to code blocks' still suppresses code blocks." Consistent with A's conditional-workflow pattern (express the exception as a conditional on an observable predicate, not an exemption) |
| 29 | One complete example; don't duplicate across languages | **Sound, with caveat** | F "One excellent example beats many mediocre ones" / "Multi-Language Dilution" anti-pattern. Caveat: A's Examples pattern uses **three** short input/output pairs for a commit-message skill — when you're teaching output *style*, several compact pairs beat one long example |
| 30 | End with a checklist or verification procedure | **Sound** | A "provide a checklist that Claude can copy into its response and check off"; D "Checklists for multi-step workflows"; both also document the stronger version, a validation loop (run validator → fix → repeat) |
| 31 | Create a todo for each checklist item | **Sound** | F: "IMPORTANT: Create a todo for EACH checklist item below" |
| 32 | Flowcharts for non-obvious decisions, tables for reference data, numbered lists for linear steps | **Sound** | F, verbatim: "Use flowcharts ONLY for: non-obvious decision points… Never use flowcharts for: reference material → tables, lists; linear instructions → numbered lists" |
| 33 | Reference `--help` instead of documenting flags | **Sound** | F "Move details to tool help" |
| 34 | Cross-reference other skills by name, not by `@`-link | **Sound** | F: "`@` syntax force-loads files immediately, consuming 200k+ context before you need them" |
| 35 | Read an existing skill fully before editing it | **Sound, unsourced** | No source states it; A's iteration loop assumes it ("Share the current SKILL.md"). Obvious enough to keep uncited |
| 36 | No fill-in-the-blank templates | **Contested** | F says don't ("Create fill-in-the-blank templates" is an anti-pattern) — but F means *code examples*. A ("Template pattern") and D ("Templates for output format") both actively recommend fill-in-the-blank templates for output shape: "agents pattern-match well against concrete structures". Scope the rule to code examples |

## 4. Progressive disclosure

| # | Claim | Verdict | Source |
|---|---|---|---|
| 37 | Skills are a standardized implementation of progressive disclosure | **Sound** | B names three levels explicitly: metadata → `SKILL.md` → bundled files; C repeats them with token budgets |
| 38 | Move corner cases to `references/`, load on condition | **Sound** | A Pattern 3 "Conditional details". D adds the critical operational detail: "The key is telling the agent *when* to load each file. 'Read `references/api-errors.md` if the API returns a non-200 status code' is more useful than a generic 'see references/ for details'" |
| 39 | Heavy reference = 100+ lines | **Sound** | F "Heavy reference (100+ lines)"; A uses the same threshold for a different rule: files over 100 lines should carry a table of contents, because Claude may preview them with `head -100` |
| 40 | An always-loaded reference file is pointless | **Sound, inferred** | Follows directly from D #38 and B's advice to split out content that is "mutually exclusive or rarely used". No source says it in these words; the reasoning is airtight |
| 41 | Extract only when the extracted text is longer than the conditional-load instruction replacing it | **Sound, unsourced** | Nobody states this cost/benefit test. It's a good original contribution — flag it as your own heuristic |
| 42 | References one level deep (skill file only) | **Sound** | A, with the mechanism: "Claude may partially read files when they're referenced from other referenced files… might use commands like `head -100`… resulting in incomplete information." C repeats: "Avoid deeply nested reference chains" |

## 5. Determinism and rigid process

| # | Claim | Verdict | Source |
|---|---|---|---|
| 43 | LLMs are non-deterministic | **Sound** | E "Model behavior is nondeterministic — the same query might trigger the skill on one run but not the next" |
| 44 | …because of sampling/temperature **plus** floating-point rounding and parallel-GPU differences | **Mostly incorrect** | See finding **F2** |
| 45 | Let the agent find its own way; don't prescribe step-by-step | **Half right — needs the conditional** | See finding **F1** |
| 46 | If it must be a rigid procedure, write a script | **Sound** | A's low-freedom example is literally a script invocation; A "Prefer scripts for deterministic operations"; B on determinism and cost |
| 47 | If the agent keeps writing the same ad-hoc script, save it as a reusable one | **Sound** | D: "If you notice the agent independently reinventing the same logic each run… that's a signal to write a tested script once and bundle it in `scripts/`"; A "Even if Claude could write a script, pre-made scripts offer advantages: more reliable, save tokens, save time, ensure consistency" |
| 48 | Reserve model reasoning for judgment and semantic understanding | **Sound** | B (code for what code does well); F "Mechanical constraints — if it's enforceable with regex/validation, automate it, save documentation for judgment calls" |

## 6. Taxonomy and process

| # | Claim | Verdict | Source |
|---|---|---|---|
| 49 | Capability vs. preference skills; preference skills are durable | **Attributed only** | J. No written source uses this split. Two adjacent taxonomies you can cite alongside it: G's "reference content" (conventions, style guides, domain knowledge) vs "task content" (step-by-step actions you invoke with `/name`), and F's four types (discipline / technique / pattern / reference) |
| 50 | Capability skills may become unnecessary as models improve | **Attributed, plausible** | J. D gives the empirical test: "if the agent already handles the entire task well without the skill, the skill may not be adding value" |
| 51 | Superpowers' "discipline" and "prohibitions" concepts | **Sound** | F, both terms used as described. Worth knowing for later: F now warns prohibitions are the *wrong* form for output-shape failures |
| 52 | Write the initial skill content yourself | **Contested** | See finding **F4** |
| 53 | AI-generated skills carry no-ops and session-specific junk | **Sound** | D names the failure mode: "vague, generic procedures ('handle errors appropriately,' 'follow best practices for authentication')"; A builds a review step around it: "Check that Claude A hasn't added unnecessary explanations" |
| 54 | Don't write the skill first — baseline, three scenarios, minimum instructions | **Sound** | A "Build evaluations first", and the four steps in the draft map 1:1 onto A's list (identify gaps → create three evaluations → establish baseline → write minimal instructions → iterate). F's Iron Law is the hard version: "NO SKILL WITHOUT A FAILING TEST FIRST" |
| 55 | Don't create a skill for one-offs, well-documented standard practice, project-specific conventions, or mechanically enforceable constraints | **Contested (one item)** | F verbatim for all four. But "project-specific" is wrong as stated — see finding **F5** |
| 56 | A skill is a reference guide for a proven technique, not a narrative | **Sound** | F "Skills are NOT: Narratives about how you solved a problem once"; anti-pattern "Narrative Example" |

## 7. Issues section

| # | Claim | Verdict | Source |
|---|---|---|---|
| 57 | Too many skills bloat the context window | **Sound, quantifiable** | C ~100 tokens of metadata per skill; A "context window is a public good… Other Skills' metadata"; G caps the listing text at 1,536 chars per skill to "reduce context usage" |
| 58 | Other skills' descriptions contaminate reasoning | **Sound** | E's near-miss/false-trigger analysis; D warns that over-narrow skills force several to load at once, "risking overhead and conflicting instructions" |
| 59 | Skills that never fire, or fire too broadly | **Sound** | E, first paragraph |
| 60 | The agent skips a skill whose description already summarizes it | **Sound** | = #18, F |
| 61 | Third-party skill descriptions are a prompt-injection vector | **Mechanism sound, exploit unsourced** | No source documents this attack. What *is* documented and makes the point better: descriptions are "injected into the system prompt" (A); a project skill's `allowed-tools` applies "including in a `-p` run in a folder you've never trusted… review the `allowed-tools` of skills checked into a repository before you run Claude Code there" (G); and a skill body's `` !`command` `` lines "never prompt for permission" (G). H defines prompt injection and lists untrusted-content practices. Recommend leaning on `allowed-tools` and `!`-injection rather than descriptions |

---

## Findings that need an edit

### F1 — The draft contradicts itself on step-by-step instructions

Line 24 states the correct rule ("Match how specific your instructions are to how easy the task is
to get wrong"), then line 87, line 113, and two checklist items in `writing-skills.md` state a
blanket prohibition: "Does not describe a rigid step-by-step process."

Both A and D frame this as a *calibration*, not a prohibition, and both give worked low-freedom
examples that are exactly the thing the blanket rule forbids:

- A: "Match the level of specificity to the task's fragility and variability." Low freedom is
  correct when "operations are fragile and error-prone, consistency is critical, or a specific
  sequence must be followed" — its example is `Run exactly this script: python scripts/migrate.py
  --verify --backup. Do not modify the command or add additional flags.`
- A: "Use workflows for complex tasks. Break complex operations into clear, sequential steps."
- D: "Most skills have a mix. Calibrate each part independently." D's *recommended* example of a
  reusable method is a four-step numbered procedure.

A's robot-on-a-path analogy is the best framing available and worth quoting: a narrow bridge with
cliffs gets exact instructions; an open field gets general direction. Suggested fix: keep the
DeepMind "let it find its own way" advice as the default for open-field work, and replace the
absolute checklist items with a fragility test. As written, the skill file would fail its own
checklist on any deploy or migration skill.

### F2 — The non-determinism explanation is the hypothesis that got refuted

The draft attributes non-determinism to "sampling and temperature" plus "rounding errors in precise
floating-point math or differences in how data is processed on parallel GPUs." **I** names that
second half specifically — "the 'concurrency + floating point' hypothesis" — and shows it's
incomplete: an identical matmul repeated a thousand times on the same GPU returns bitwise identical
results, and "the forward pass of an LLM involves no operations that require atomic adds."

The actual driver: kernels are not batch-invariant, and "the primary reason nearly all LLM inference
endpoints are nondeterministic is that the load (and thus batch-size) nondeterministically varies."
Same request, different concurrent traffic, different reduction order, different rounding. With
batch-invariant kernels, "all of our 1000 completions are identical."

Two consequences for the paragraph: temperature/sampling is a real source of variation and can stay;
and the framing "LLMs are non-deterministic by nature" should soften to *inference endpoints are
non-deterministic in practice*, since I demonstrates the property is fixable. The conclusion you draw
from it — write a script when you need a guaranteed sequence — is unaffected.

### F3 — `disable-model-invocation` doesn't work the way the draft says

The draft says to "replace the `description: ...` in the front-matter with
`disable-model-invocation: true`," and that such a skill "does not take up as much context."

- C makes `description` **required** (1–1024 chars, non-empty). A skill with no description is not
  spec-compliant.
- G makes it optional but recommended, and falls back: "If omitted, uses the first paragraph of
  markdown content." So dropping it doesn't remove the skill from the listing — it just replaces
  your routing text with whatever your first paragraph happens to say.
- The two fields are orthogonal. `disable-model-invocation: true` stops automatic invocation; you
  keep the description for the `/` menu and drop nothing from context.
- G also flags a portability cost worth one sentence: `disable-model-invocation` is a Claude Code
  extension, not one of the spec's six fields, and non-spec keys can trip validation on the
  claude.ai and API paths.

The rest of the paragraph holds up well — G endorses the pattern for exactly your reason: "Use this
for workflows with side effects or that you want to control timing, like `/commit`, `/deploy`…
You don't want Claude deciding to deploy because your code looks ready."

### F4 — "Write the initial skill content yourself" is contested, and A contradicts it directly

A's recommended process is the opposite: develop the skill *with* Claude ("Claude A") and test it
with a fresh instance ("Claude B"), and explicitly, "You don't need special system prompts or a
'writing skills' skill to get Claude to help create Skills."

D locates the real failure mode more precisely, and supports your observation without supporting your
remedy: "A common pitfall in skill creation is asking an LLM to generate a skill without providing
domain-specific context — relying solely on the LLM's general training knowledge. The result is
vague, generic procedures." D's fix is to ground generation in real material (a hands-on task
transcript, runbooks, review comments, patches), not to hand-write it.

Suggested reframe: the rule isn't "type it yourself," it's "don't let the model invent content it has
no evidence for" — plus A's review step, which exists precisely because model-authored skills bloat.

### F5 — "Project-specific conventions go in AGENTS.md" is wrong as stated

`writing-skills.md` inherits this from F ("put in your instructions file"), but G contradicts it:
"Create a skill when you keep pasting the same instructions, checklist, or multi-step procedure into
chat, **or when a section of CLAUDE.md has grown into a procedure rather than a fact**. Unlike
CLAUDE.md content, a skill's body loads only when it's used."

D goes further — project specificity is what makes a skill *worth having*: "A data-pipeline skill
synthesized from your team's actual incident reports and runbooks will outperform one synthesized
from a generic 'data engineering best practices' article."

The real line is facts vs. procedures, not project vs. general: durable facts belong in CLAUDE.md
(always loaded), procedures belong in a skill (loaded on demand). Note this cuts against the "applies
broadly (not project-specific)" bullet too.

### F6 — One addition worth making, because it strengthens your central argument

G documents something the draft doesn't: once a skill loads, "its content stays in context across
turns, so every line is a recurring token cost." That's a stronger justification for the <500-line
rule than "it gets loaded once," and it's the same argument the draft already makes about references.

---

## In-scope guidance the draft omits

Not an argument to expand the post — just flagging basics from A and D that fall inside part 1's
scope, in case any earn a line:

- **Avoid time-sensitive information** (A) — "If you're doing this before August 2025…" rots; use a
  collapsed "old patterns" section instead.
- **Provide defaults, not menus** (A "Avoid offering too many options", D "Provide defaults, not
  menus") — pick one library, mention the escape hatch.
- **Gotchas sections** (D) — "The highest-value content in many skills is a list of gotchas —
  environment-specific facts that defy reasonable assumptions." This is the strongest single
  argument for preference/durable skills in any of the sources.
- **Design coherent units** (D) — scope a skill like a function; too narrow forces several to load at
  once, too broad can't be activated precisely.
- **No voodoo constants in scripts** (A) — justify `TIMEOUT = 30`; "If you don't know the right
  value, how will Claude determine it?"
- **Fully-qualified MCP tool names** (A) — `ServerName:tool_name`.
- **Test across models** (A) — "What works perfectly for Opus might need more detail for Haiku."

## Suggested reference-list additions

```
- Agent Skills specification: https://agentskills.io/specification
- Best practices for skill creators: https://agentskills.io/skill-creation/best-practices
- Optimizing skill descriptions: https://agentskills.io/skill-creation/optimizing-descriptions
- Claude Code — Extend Claude with skills: https://code.claude.com/docs/en/skills
- Thinking Machines — Defeating Nondeterminism in LLM Inference:
  https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/
```

The existing bare `https://agentskills.io` link is worth replacing with the three deep links — most
of the description and calibration rules in the post trace to specific pages, not the landing page.
