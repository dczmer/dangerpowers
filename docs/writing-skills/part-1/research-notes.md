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
| 14 | `disable-model-invocation: true` **replaces** `description` and so costs less context | **Incorrect (Resolved)** | See finding **F3** below |

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
| 44 | …because of sampling/temperature **plus** floating-point rounding and parallel-GPU differences | **Mostly incorrect (Resolved)** | See finding **F2** |
| 45 | Let the agent find its own way; don't prescribe step-by-step | **Half right — needs the conditional (Resolved)** | See finding **F1** |
| 46 | If it must be a rigid procedure, write a script | **Sound** | A's low-freedom example is literally a script invocation; A "Prefer scripts for deterministic operations"; B on determinism and cost |
| 47 | If the agent keeps writing the same ad-hoc script, save it as a reusable one | **Sound** | D: "If you notice the agent independently reinventing the same logic each run… that's a signal to write a tested script once and bundle it in `scripts/`"; A "Even if Claude could write a script, pre-made scripts offer advantages: more reliable, save tokens, save time, ensure consistency" |
| 48 | Reserve model reasoning for judgment and semantic understanding | **Sound** | B (code for what code does well); F "Mechanical constraints — if it's enforceable with regex/validation, automate it, save documentation for judgment calls" |

## 6. Taxonomy and process

| # | Claim | Verdict | Source |
|---|---|---|---|
| 49 | Capability vs. preference skills; preference skills are durable | **Attributed only** | J. No written source uses this split. Two adjacent taxonomies you can cite alongside it: G's "reference content" (conventions, style guides, domain knowledge) vs "task content" (step-by-step actions you invoke with `/name`), and F's four types (discipline / technique / pattern / reference) |
| 50 | Capability skills may become unnecessary as models improve | **Attributed, plausible** | J. D gives the empirical test: "if the agent already handles the entire task well without the skill, the skill may not be adding value" |
| 51 | Superpowers' "discipline" and "prohibitions" concepts | **Sound** | F, both terms used as described. Worth knowing for later: F now warns prohibitions are the *wrong* form for output-shape failures |
| 52 | Write the initial skill content yourself | **Contested (Resolved)** | See finding **F4** |
| 53 | AI-generated skills carry no-ops and session-specific junk | **Sound** | D names the failure mode: "vague, generic procedures ('handle errors appropriately,' 'follow best practices for authentication')"; A builds a review step around it: "Check that Claude A hasn't added unnecessary explanations" |
| 54 | Don't write the skill first — baseline, three scenarios, minimum instructions | **Sound** | A "Build evaluations first", and the four steps in the draft map 1:1 onto A's list (identify gaps → create three evaluations → establish baseline → write minimal instructions → iterate). F's Iron Law is the hard version: "NO SKILL WITHOUT A FAILING TEST FIRST" |
| 55 | Don't create a skill for one-offs, well-documented standard practice, project-specific conventions, or mechanically enforceable constraints | **Contested (one item) (Resolved)** | F verbatim for all four. But "project-specific" is wrong as stated — see finding **F5** |
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

### F1 — The draft contradicts itself on step-by-step instructions — **Resolved**

> **Resolution.** Reframed as calibration on task fragility rather than a prohibition on specificity.
>
> - `README.md` gained a short **Calibrating Specificity** section, placed before the determinism
>   section that it feeds into. It opens by naming this as the one two-sided rule in the post, quotes
>   A's robot-on-a-path framing (narrow bridge vs. open field), gives A's `migrate.py` example as the
>   specific case and refactoring/tests as the loose case, and closes with the per-instruction test:
>   if a step could vary without anything breaking, state the outcome; if it couldn't, spell it out.
> - The two blanket bullets in *Content* ("Focus on goals and constraints, not a step-by-step
>   process" / "don't micro-manage execution steps") were replaced by one pointer to that section.
> - The DeepMind paragraph was scoped to open-field tasks in both sentences that carried the blanket
>   claim, so the advice survives with its domain stated.
> - "If it must be rigid, write a script" became an explicit three-level scale — goals and
>   constraints → explicit ordered steps → script — closing the gap where the draft jumped from
>   level 1 to level 3 and left no room for a legitimately procedural skill that isn't scriptable.
> - `writing-skills.md`: content rules 29–30 collapsed into one fragility-calibration directive;
>   checklist items 81–82 collapsed into one item phrased as a conditional on an observable predicate
>   ("every prescribed step is justified by fragility…"), not an exemption clause — which #28/**F**
>   would otherwise have made the one unavailable fix. Line 67 narrowed to "fully deterministic
>   processes" to match level 3.
>
> Two things this also fixed, beyond what was written up below: `writing-skills.md` contradicted
> *itself* — line 70 prescribed "numbered lists for linear steps" while line 81 forbade exactly that,
> 11 lines apart — and the skill now passes its own checklist, which it previously could not.
>
> Row 46 ("if it must be a rigid procedure, write a script") is left at **Sound**. Its text was
> restructured by this fix, but the claim's verdict never changed.

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

### F2 — The non-determinism explanation is the hypothesis that got refuted — **Resolved**

> **Resolution.** The refuted causal clause was replaced with the batch-invariance mechanism, cited to **I**.
>
> - `README.md` (opening paragraph of *Determinism, Rigid Processes, and Scripts*): "partly because of many
>   little factors that affect computation, like rounding errors in precise floating-point math or
>   differences in how data is processed on parallel GPUs" is gone. It now states that even at temperature
>   zero the same prompt against the same endpoint won't reliably return the same tokens, attributes that
>   to batch-invariance — kernels return slightly different floating-point results depending on the batch
>   size they run at, and batch size tracks concurrent server traffic — and notes you don't control it.
>   Sampling/temperature is kept as the by-design source.
> - The framing claim was softened in both places it appeared: the paragraph opens "non-deterministic in
>   **practice**" rather than flatly "non-deterministic," and "LLMs are non-deterministic by nature" was cut
>   from the following paragraph (it was a restatement, and **I** shows the property is fixable with
>   batch-invariant kernels, so "by nature" is wrong).
> - **I** was added to the reference list.
>
> The conclusion the section draws — same instructions, different route each run, so move guaranteed
> sequences into a script — was load-bearing on none of this and is unchanged. Rows 43 and 46–48 keep their
> verdicts.
>
> Note on why this wasn't a wording nitpick: floating point appears in both the old and new text, but the
> causal direction was inverted. The old text implied the arithmetic is inherently jittery; the arithmetic is
> deterministic given a fixed batch, and the nondeterminism enters through the batch.

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

### F3 — `disable-model-invocation` doesn't work the way the draft says — **Resolved**

> **Resolution.** All three errors fixed in `README.md`; `writing-skills.md` never mentioned the field.
>
> - **Mechanism.** "replace the `description: ...` in the front-matter with `disable-model-invocation: true`"
>   became "add `disable-model-invocation: true` to the front-matter." That single word change is the whole
>   fix — the keys are orthogonal, so nothing needs removing. No explicit "keep the description" sentence was
>   added; "add" already implies it, and the paragraph is tighter without it.
> - **Context claim.** "does not take up as much context" deleted rather than inverted. Whether such a skill's
>   description occupies the system prompt specifically is a client implementation detail no source pins down,
>   so the draft now makes no claim either way. The real benefit — control over timing — was already the
>   paragraph's closing point.
> - **Portability.** Added, sourced to **G**: the key is a Claude Code extension, not one of the spec's six
>   fields. *Revised in a later pass* — this was promoted from footnote to frame. The paragraph now opens "How
>   you declare this depends on your agent. It isn't in the Agent Skills spec, so there's no portable way to
>   express it," and gives the Claude Code key as one agent's spelling rather than as the instruction. More
>   honest about a genuinely non-portable feature, and it's the only Claude-Code-specific fact in either file.
> - **Self-contradiction.** "never hijacks another prompt" was narrowed to "never hijacks another prompt and
>   doesn't require any trigger testing, though its description is still loaded into context and can still
>   color the agent's reasoning." The immunity is real for *invocation* only; the contamination hazard the
>   draft itself lists in *Issues* still applies, and the two passages no longer disagree.
> - **G's rationale grafted in**, replacing personal preference as the sole justification: side effects, or
>   wanting to control the timing — committing, deploying, cutting a release — "you don't want the agent
>   deciding to deploy because your code looks ready." *Revised in a later pass* — the in-prose attribution
>   ("the Claude Code docs recommend it") was dropped and the point is now made in the author's own voice, per
>   a standing preference to keep advice applicable to any coding agent. Attributing an *idea* to a source is
>   fine (the post does it for **A** at the calibration section, and for **J** and **F** throughout); framing
>   advice as one vendor's recommendation is what reads as endorsement.
> - **G added to the reference list** (`https://code.claude.com/docs/en/skills`). Kept even after the prose
>   citation was removed — it backs the `description` fallback behavior and the extension-vs-spec status. A
>   reference list is attribution, not allegiance. Clears one of the four suggested additions below.
>
> Deliberately not added: `user-invocable: false` (the model-only inverse). Real, but the post doesn't
> otherwise enumerate frontmatter keys and it isn't needed to make any claim correct.

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

### F4 — "Write the initial skill content yourself" is contested, and A contradicts it directly — **Resolved**

> **Resolution.** Reframed from "who types it" to "what the model writes from," which keeps the draft's
> original observation and drops only the remedy A contradicts. `README.md` *Start Small* is now four short
> paragraphs where it was one.
>
> - The rule is still credited to **J**, then explicitly restated rather than repeated: "the problem
>   underneath it is narrower than 'AI writing is bad.'"
> - **Two opposed failure modes, one root cause.** **D**'s under-grounding case (write it cold → generic
>   filler, "handle errors appropriately") is now paired with the draft's own over-fitting case (write it at
>   the end of a working session → rules encoding incidental details of that conversation). Both are the
>   model writing from the wrong evidence. The pairing is **not in any source** — D only has the first half —
>   and it's the strongest original idea in the section, so it should be flagged as the author's own, not
>   attributed.
> - **Remedy replaced.** "Type it yourself" → control the input material (hand-done transcript, runbook,
>   review comments, a patch), which is exactly **D**'s fix, plus read the draft back in a fresh session with
>   no memory of authoring it. That second step is **A**'s Claude A / Claude B split doing double duty: a
>   context-free reader is the only reliable detector for leaked context, since the leakage is invisible from
>   inside the conversation that produced it. A's review step ("check that Claude A hasn't added unnecessary
>   explanations") is the same move.
> - **Hand-writing kept as an option, demoted from a rule:** "one way to get there, and a fine default for a
>   short skill. It just isn't the part that matters." This is what lets the section improve on **J** without
>   reading as a correction of a source the post is citing approvingly.
> - Consequential edit: the next paragraph's "the AI will **take over** editing the skill file" became "the AI
>   will be doing most of the editing" — "take over" implied the human wrote the draft, which the rewrite no
>   longer claims.
>
> Row 53 keeps **Sound**; the draft now expands that claim into the two-failure-mode framing rather than
> weakening it. Row 54 (baseline → three scenarios → minimum instructions) is untouched and still reads
> consistently after the rewrite. is the opposite: develop the skill *with* Claude ("Claude A") and test it
with a fresh instance ("Claude B"), and explicitly, "You don't need special system prompts or a
'writing skills' skill to get Claude to help create Skills."

D locates the real failure mode more precisely, and supports your observation without supporting your
remedy: "A common pitfall in skill creation is asking an LLM to generate a skill without providing
domain-specific context — relying solely on the LLM's general training knowledge. The result is
vague, generic procedures." D's fix is to ground generation in real material (a hands-on task
transcript, runbooks, review comments, patches), not to hand-write it.

Suggested reframe: the rule isn't "type it yourself," it's "don't let the model invent content it has
no evidence for" — plus A's review step, which exists precisely because model-authored skills bloat.

### F5 — "Project-specific conventions go in AGENTS.md" is wrong as stated — **Resolved**

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

> **Resolved.** Three bullets rewritten in `writing-skills.md` — README needed no change.
>
> - `:16` "You'd reference it again across projects" → "across projects or repeatedly within one."
>   The load-bearing criterion is *recurring*, not *cross-project*; the cross-project reading was a
>   milder form of the same defect.
> - `:17` "The pattern applies broadly (not project-specific)" → "It's a procedure or workflow, not a
>   standalone fact." Substitutes G's actual distinction for the generality test.
> - `:22` "Project-specific conventions (those go in AGENTS.md)" → "Durable facts needed in every
>   session (those go in AGENTS.md)." Retargets the bullet at facts instead of at project scope, which
>   is the routing G describes. Kept the AGENTS.md spelling rather than G's CLAUDE.md, per the
>   vendor-neutrality pass — G's point holds for either file.
>
> Also closed an internal contradiction not captured in any table row: `README.md:31` defines
> preference skills as those encoding conventions and workflows "specific to your project or
> environment" and `:33` calls that category the durable one, while the skill file linked from the
> post told you not to write skills for project-specific conventions. The README was the correct side,
> so the fix landed entirely in `writing-skills.md`.
>
> Sprawl guard preserved: it was never the generality bullet, it was one-off vs. recurring, which
> survives at `:16` and `:20`. Other three items in the *Don't create for* list untouched — F verbatim
> and sound. No checklist change; nothing in the checklist tests the when-to-create criteria.

### F6 — One addition worth making, because it strengthens your central argument — **Resolved**

G documents something the draft doesn't: once a skill loads, "its content stays in context across
turns, so every line is a recurring token cost." That's a stronger justification for the <500-line
rule than "it gets loaded once," and it's the same argument the draft already makes about references.

> **Resolved.** Two additions, both in `README.md`. No table row to update — F6 is an addition, not an
> audited claim. Both new statements are sourced to G, already in the reference list.
>
> - `:76` — the <500-line justification now states the cost is per-turn, not per-invocation: the body
>   "sits in the conversation history for the rest of the session, re-sent with every turn that
>   follows." Fixes an inversion in the draft's own argument, which made the compounding case for
>   reference files at `:100` but only the one-time case for the body — backwards, since the body is
>   the part guaranteed to be there. Phrased around conversation history rather than any agent's
>   implementation, so it stays vendor-neutral.
> - `:61` — added the same mechanism for descriptions, one sentence: they live in the system prompt, so
>   they're paid from the first turn of every session whether the skill fires or not. This was the
>   unstated mechanism behind two existing *Issues* bullets (`:146` too many skills bloat context,
>   `:147` foreign descriptions contaminating reasoning).
>
> Two deliberate non-edits:
>
> - `:104` ("a reference file that is ALWAYS loaded is pointless") could carry the same recurring-cost
>   framing, but the sharpened `:76` already establishes it and repeating it would violate the draft's
>   own no-repeated-content rule.
> - `writing-skills.md:67` already gives the correct justification in directive form ("every token
>   competes with conversation context"). Adding the mechanism there would be rationale in a file whose
>   own checklist forbids commentary that isn't a goal, constraint, or end condition.

---

## In-scope guidance the draft omits — **Folded in**

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

> **Folded in.** All seven landed as bullets in *Some Established Conventions* (`README.md:159–169`).
> No new table rows — same treatment as F6's additions; these are additions, not audited claims. Each
> traces to A or D, both already in the reference list.
>
> Ordering: new bullets were interleaved rather than appended, so the section groups as
> definition/discovery → content → consistency → scripts. Concretely: *coherent units* and *gotchas*
> and *defaults, not menus* and *no time-sensitive info* after the descriptions bullet; *MCP names*
> after the terminology bullet; *no voodoo constants* after the existing scripts bullet. No existing
> bullet was reworded — only repositioned relative to the new ones.
>
> Two judgement calls worth recording:
>
> - **Test across models** is arguably testing scope, which the post defers to part 2 (`:7`). Kept it
>   because it's stated as a convention ("don't assume large-model behavior transfers") rather than a
>   procedure, and phrased by model size instead of naming Opus/Haiku, per the vendor-neutrality pass.
> - **Gotchas** is really content guidance and would sit as naturally in *Content* (`:88–94`). Put it
>   in Conventions as directed. It's the highest-value item of the seven — it's the mechanism behind
>   the durable/preference category at `:33`, so if the post ever needs a stronger argument for why
>   preference skills don't become obsolete, this bullet is where it starts.
>
> Not folded in: **row 22's** wording nit (`:57` describes skill matching as keyword dispatch; it's
> semantic matching against descriptions) and the three agentskills.io deep links. Both still open.

## Suggested reference-list additions — **Applied**

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

> **Applied.** All nine references now sit in one normalized list (`README.md:181–189`). The bare
> `https://agentskills.io` landing-page link is gone, replaced by the three deep links as recommended.
>
> Formatting normalized — the list had drifted into two styles: the three original entries used
> `- [Descriptive title](url)`, while the four later additions (including the two I added during F2/F3,
> which matched the then-current style) used `* Title: [url](url)` with the raw URL as link text. Now
> uniformly `- [Publisher - Title](url)`, sorted alphabetically by publisher (*superseded by the
> citation pass* — the list is now sorted by source key). Hyphen separators rather
> than em-dashes, matching the draft's prose style; the one em-dash I'd introduced in the Claude Code
> entry is gone.
>
> Publisher prefixes were added to the three original entries, which previously attributed
> inconsistently ("Agentskills.io spec + guide" had none, "DeepMind - …" had one). Renames:
> Agentskills.io spec + guide → three *Agent Skills* entries; DeepMind → *Google DeepMind*;
> Superpowers "writing-skills" skill → *Superpowers - "writing-skills" skill*.
>
> Every source key A–J now resolves to a listed reference. Reference-list work is closed.

---

## Inline citations — **Applied**

`README.md` now carries inline citations keyed to the same A–J letters used in this document, so a
claim in the post and its row in the tables above resolve to the same key.

Mechanism: each reference-list entry gained an HTML anchor and a visible key —
`- <a id="ref-a"></a>**[A]** [Anthropic - Skill authoring best practices](…)`. Statements cite it
either by hyperlinking a source name already present in the prose ("[Thinking Machines](#ref-i)
traced this to batch-invariance") or, where no source is named, with a trailing marker
`([A](#ref-a))`. The list is sorted by key rather than by publisher, so a reader following `[G]` back
from the prose lands on it by position; this supersedes the publisher-alphabetical ordering set by the
reference-list pass.

Placement rule: at most one marker per paragraph or bullet, attached to the sentence carrying the
borrowed claim rather than to every clause. Where several sources support one statement they share a
marker (`([A](#ref-a), [C](#ref-c))`).

Deliberately left uncited, so absence of a marker stays meaningful:

- `:102` extract-only-when-longer — original heuristic (row 41). The marker on the preceding sentence
  stops before it.
- `:41–43` the two-opposed-failure-modes framing — original (per **F4**); the two markers in that
  passage sit on D's filler examples and A's fresh-reader step, not on the framing.
- `:132–138` the three-level fragility scale — original synthesis (per **F1**).
- `:88–94` and `:106–108` summary bullet lists — recaps of claims cited where first stated.
- `:57` and `:150`/`:154` — see the open items under **P5** below.

---

## Plagiarism scan

Method: every assertion in `README.md` diffed against the verbatim source excerpts recorded in the
tables and findings above.

**Scope limit.** The comparison corpus is the ~60 quoted snippets in this document, not the live
pages. Anything a source says that was never quoted here could not be checked. A complete pass needs
A–J fetched and diffed in full; the findings below are a floor, not a ceiling.

Severity: **P1** verbatim, unquoted, uncited · **P2** near-verbatim with substitutions · **P3** quoted
but unattributed · **P4** borrowed example or enumeration, reworded.

### P1 — Verbatim, unquoted, uncited

**`README.md:68`** — "You don't want the agent deciding to deploy because your code looks ready."

G, per `:267` above: *"You don't want Claude deciding to deploy because your code looks ready."*
Thirteen words reproduced with one substitution (`Claude` → `the agent`), in the author's voice.

Compounding factor: the **F3** resolution at `:242` records that the in-prose attribution to G was
*deliberately removed* for vendor-neutrality. The neutrality goal is right; the effect was to leave a
borrowed sentence with nothing pointing at its origin. A `([G](#ref-g))` marker has been added, which
fixes attribution but not the verbatim overlap — **still open**: either reword in the author's voice
or restore G's wording as an explicit quotation.

**`README.md:161`** — "environment-specific facts that defy reasonable assumptions"

D, per `:389` above: *"The highest-value content in many skills is a list of gotchas —
environment-specific facts that defy reasonable assumptions."* Seven words verbatim, no quotation
marks. The adjacent "highest-value content in the whole file" claim is also D's, reworded. Cited to D
now; the seven-word run **still needs rewording or quoting**.

### P2 — Near-verbatim with substitutions

**`README.md:159`** — "The field gets injected into the system prompt and mixing point of view causes
discovery problems."

A, per row 16: *"The description is injected into the system prompt, and inconsistent point-of-view
can cause discovery problems."* Same clause order, three synonym swaps (`description` → `field`,
`inconsistent point-of-view` → `mixing point of view`, `can cause` → `causes`). Reads as original
prose. Cited to A now; restructuring recommended.

**`README.md:78`** — "core principals in 1-2 sentences"

F's `SKILL.md` template, per row 25: *"Core principle in 1-2 sentences."* Short and functional, so
low severity, but it is F's template line intact (the post's "principals" is a spelling slip, not a
rewrite). Cited to F.

**`README.md:162`** — "Provide defaults, not menus."

D's section title used verbatim as the bullet lead-in, per `:386`. A slogan rather than prose; the
`([A](#ref-a), [D](#ref-d))` marker is sufficient treatment.

### P3 — Quoted, unattributed

**`README.md:41`** — `"handle errors appropriately," "follow best practices"`

Both from D, per row 53 and `:305`, including D's comma-inside-quote punctuation. The quotation marks
mean nothing is passed off as original prose, but with no source attached they read as the author's
invented examples of filler rather than D's documented ones. **Resolved** by the `([D](#ref-d))`
marker on that sentence.

Contrast with the two passages that were already handled correctly: `:114` (robot-on-a-path,
attributed in prose to Anthropic) and `:116–118` (A's `migrate.py` instruction, blockquoted and
introduced as "Anthropic's own example"). Those needed only links.

### P4 — Borrowed examples and enumerations

None verbatim; each reproduces a source's specific illustrative choices. Individually minor,
cumulatively a pattern. All now carry markers; none require rewording.

| Line | Borrowed element | Source |
|---|---|---|
| `:165` | the `field` / `box` / `element` / `control` rotation example | A — row 11 already noted it was "lifted from this section" |
| `:159` | "Processes Excel files and generates reports" / "I can help you with" | A's good/avoid pair (row 16) |
| `:163` | "If you're doing this before August 2025" | A's rot example |
| `:158` | `processing-pdfs`, `analyzing-spreadsheets` | A's gerund examples (row 10) |
| `:43` | "a transcript of doing the task by hand, an existing runbook, review comments, a patch" | D's grounding list — item-for-item identical, reordered |
| `:47–51` | the baseline → three scenarios → minimum-instructions sequence | A's list; row 54 records the 1:1 mapping |
| `:167` | "If you don't know the right value, the agent has no way to work it out either." | A's *"If you don't know the right value, how will Claude determine it?"* — rhetorical question flattened to a statement |
| `:122` | "Most skills are a mix of both, and each section calibrates separately." | D's *"Most skills have a mix. Calibrate each part independently."* |

### Confirmed original

`:20` "the description is not documentation, it's the router" · `:41–43` the two-failure-mode framing
· `:102` the extract-when-longer cost test · `:132–138` the three-level fragility scale. Left
uncited, per the placement rule above.

### P5 — Statements no source supports

Not plagiarism; flagged because the citation pass had to skip them.

- `:57` — "instructions on how to detect and dispatch skills based on words or phrases." Matching is
  semantic against descriptions, not keyword dispatch (E). This is row 22, still open, and it is now
  the only uncited mechanical claim in the *Descriptions and Triggers* section.
- `:150`, `:154` — third-party descriptions as a prompt-injection vector. Row 59 stands: mechanism
  sound, exploit unsourced. No marker was added, because H merely defines prompt injection and citing
  it would overstate the support. Row 59's recommendation — lean on `allowed-tools` and `` !`command` ``
  injection, both documented in G — is the way to make this citable.

### Corrections to this document, found during the scan

- `:450` claims "every source key A–J now resolves to a listed reference." **H** (Claude Code
  security) is not in `README.md`'s reference list. Nine references, A–J minus H. Either add H or drop
  it from the key table at `:17`.
- `:398` claims all seven omitted items landed at `README.md:159–169`. Six did. **Fully-qualified MCP
  tool names** (`ServerName:tool_name`, A) is absent from *Some Established Conventions*.
- `:296–298` has a text-corruption artifact: the **F4** resolution block ends mid-sentence and
  splices into the original finding — "…still reads consistently after the rewrite. is the opposite:
  develop the skill *with* Claude…" A sentence introducing A's position was lost.
