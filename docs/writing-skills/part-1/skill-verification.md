# `writing-skills.md` vs. the final draft — verification report

Written 2026-08-25 against `README.md` and `writing-skills.md`; refreshed 2026-08-25 after the
`README.md` prose rewrite. The rewrite changed wording and line numbers but not structure or content,
so every finding below stands — only the references and quotes have been re-resolved. Re-check them
before acting if either file has moved on.

**Fixes applied so far:** C1, C2, and C4; C3 reviewed and accepted with no change (see the work queue
at the bottom for what remains).

Companion document: `research-notes.md` holds the source audit, citation pass, and plagiarism scan for
`README.md`. This file covers only the blog-to-skill correspondence.

**Verdict:** the skill is well-built and self-consistent on its core rules, but it is **not** what
`README.md:274` claims it is. That line says the skill contains "everything we've covered in this
document, and nothing we haven't covered yet." Both halves fail: roughly a dozen blog rules are absent,
and roughly a dozen skill rules appear nowhere in the blog. The apparent conflict on description voice
turned out to be a wording slip in the post rather than a real disagreement (C1, since fixed), and the
skill violates two of its own rules — one of them in its own `description` field.

---

## 1. Direct conflicts

**C1 — Description voice: third person vs. imperative. Resolved 2026-08-25.** `README.md:264` said
descriptions get written "in third person, **always**," with the good/bad pair "Processes Excel files and
generates reports" / "I can help you with", while `writing-skills.md:40` mandated "`description`:
imperative ("Use when...")". On their face the two picked opposite forms.

It was not a source conflict. `research-notes.md:49–50` had already adjudicated the pair: A puts third
person in a warning box about point-of-view consistency ("inconsistent point-of-view can cause discovery
problems"), and E — which `:264` cited *in support of* third person — is itself the source of the
imperative rule ("Use imperative phrasing… 'Use this skill when…' rather than 'This skill does…'"). The
ban both sources describe is on first and second person ("I can help you…"), not on imperatives. The
post's error was using "third person" to mean "not first person" and then attaching "always" to it, which
over-read both citations.

Applied: `README.md:264` now states the rule as third person *about* the skill, and `:270` says
explicitly that an imperative trigger clause ("Use when the user asks to...") is still third person;
`writing-skills.md:40` states the person rule directly and keeps "Use when…" as the opening clause;
`writing-skills.md:87` changed `imperative` → `third person` to match — a third site for the same rule
that this report originally missed.

The skill's own `:3` is not a violation of the resolved rule — "the user" is third person. Its remaining
defects are the ones under S1.

**C2 — Templates: endorsed vs. prohibited. Resolved 2026-08-25.** `README.md:134` recommends including
"templates or snippets that illustrate what you want the AI to do." `writing-skills.md:68` said "no
fill-in-the-blank templates." On their face the two sentences contradicted, and the skill never drew
the distinction.

It was a vocabulary collision, not a real disagreement. The blog's "templates or snippets" means a
filled-in, concrete example of a desired output — the very next sentence prescribes one complete
example with no multi-language dilution. The skill's prohibition targets blank forms with placeholders,
which force the agent to instantiate the example and reintroduce the judgment it was meant to remove.

Applied: `writing-skills.md:68` now reads "no fill-in-the-blank templates — show one complete, filled-in
example instead," naming the actual failure mode and pointing at the endorsed alternative. The blog
needed no edit; its wording already sits inside a sentence about concrete examples. One-line edit, so no
line reference in this report has shifted.

**C3 — Frontmatter field set. Accepted 2026-08-25 — no change.** `writing-skills.md:37` opens "Two
required fields: `name` and `description`" and never mentions another key. `README.md:95` documents
`disable-model-invocation: true` as an authoring decision with real consequences.

Decision: accept. `:37` claims only that two fields are *required*, not that the list is exhaustive, so
there is no inaccuracy to fix. The manual-invocation mechanism is agent-specific (absent from the Agent
Skills spec, per `README.md:95`), and the skill's audience — an agent authoring or editing skills —
does not need it to produce correct frontmatter. Documenting an optional, non-portable key would cost
every reader a line for a decision that rarely applies.

**C4 — Extraction threshold (soft conflict). Resolved 2026-08-25.** `README.md:165` gave a comparative
test — extract to `references/` when the extracted text is longer than the conditional-load instruction
replacing it — while `writing-skills.md:60` gave an absolute one: "Heavy reference (100+ lines)". Not
contradictory (a 100+ line extract virtually always passes the comparative test), but different
heuristics, and `100+` appeared nowhere in the post.

Applied: `README.md:165` now adds the threshold as a rule of thumb: "As a rough rule of thumb, anything
over about 100 lines belongs in a reference file regardless." The comparative test stays as the
principle; the skill's number is now grounded in the post. The skill needed no edit. One-line edit, so
no line reference in this report has shifted.

---

## 2. Blog rules missing from the skill

**The big cluster: 9 of the 10 "Established Conventions" bullets (`README.md:253–262`) are absent, and
the tenth is only half-covered.** Gerund naming made it in (`:39`, `:86`); the 64-character limit in the
same bullet did not. Missing:

| Blog | Rule |
|---|---|
| `:253` | 64-character name limit |
| `:254` | Scope a skill like a function — one coherent unit of work; too narrow vs. too broad |
| `:255` | Include a "gotchas" section — the blog calls this "often the highest-value content in the whole file" |
| `:256` | Provide defaults, not menus |
| `:257` | No time-sensitive information |
| `:258` | Forward slashes in paths |
| `:259` | One term per concept |
| `:260` | Scripts handle their own error cases |
| `:261` | No magic constants in scripts |
| `:262` | Don't assume a large-model skill works on a small model |

The gotchas omission is the one to fix first — the post gives it the strongest superlative of any rule
in the document, and the skill's checklist has no item for it.

**Other gaps:**

- **`README.md:105` — "when to use / when not to use" sections inside the skill body.** The skill's
  "When to Create a Skill" (`:12–23`) answers a different question (*should this be a skill at all*),
  and the Body checklist (`:90–96`) has no item for early-abort sections. The blog's stated rationale —
  giving the agent a chance to bail after triggering — is absent.
- **`README.md:39–50` — grounding and cold review.** Give the model real material (transcript, runbook,
  review comments, a patch) rather than asking it to imagine the process; read the draft back in a fresh
  session with no memory of writing it. Nothing in the skill addresses where content comes from or how
  to review it. Partial mitigation: "write it yourself" is human-facing advice, but "ground it in real
  material" and "review cold" are both expressible as directives.
- **`README.md:223` — promote repeated ad-hoc scripts** into saved reusable scripts.
- **`README.md:225` — reserve LLM evaluation** for work that genuinely needs reasoning or semantic
  understanding. Implied by `writing-skills.md:66` but not stated.
- **`README.md:72`, `:235` — don't write descriptions that hijack phrases belonging to other skills.**
  The skill covers the *no-TLDR* failure mode well (`:43`) but not the over-broad-trigger one.
- **`README.md:169` — keep the main file to the happy path.** `writing-skills.md:65` gets close but
  never says it.

**Correctly excluded** (consistent with the post's stated scope at `:7` and `:280`): eval-first
authoring (`:26`, `:54–60`), trigger and pressure testing (`:91`, `:128`), and discipline/prohibition
rules (`:35`, `:215`). These are deferred to later installments by name, so their absence is a feature,
not a gap.

---

## 3. Skill rules that appear nowhere in the blog

This is the half of `:274` that fails more clearly, because several of these are the skill's *best*
rules:

- **`:32` and `:77` — "No nuance or exemption clauses that scope a directive ('unless X', 'except when
  Y')."** Sharp, unusual, and completely unmentioned in the post. The most conspicuous reverse gap.
- **`:12–23` — the entire "When to Create a Skill" section.** The blog never discusses whether to create
  a skill: not the "wasn't intuitively obvious" test, not one-off solutions, not standard practices
  documented elsewhere.
- **`:22` — durable facts belong in AGENTS.md.** AGENTS.md is never mentioned in the post.
- **`:23` — automate mechanical constraints; reserve documentation for judgment calls.** Adjacent to the
  blog's scripts material but a distinct criterion.
- **`:67` — reference `--help` instead of documenting flags**; and **cross-reference other skills by
  name** with the `**REQUIRED SUB-SKILL:**` convention.
- **`:69`, `:93` — flowcharts for non-obvious decisions, tables for reference data, numbered lists for
  linear steps.**
- **`:70` — read an existing skill fully before editing it.**
- **`:65`, `:94` — supporting files referenced "one level deep."**
- **`:42` — state what the skill produces**; **`:44` — move exhaustive anti-pattern enumerations into the
  body**; **`:88` — no `Keywords:`-style label.**
- **`:74` — "Create a todo for each item."**

---

## 4. Where the skill breaks its own rules

**S1 — The `description` violates three of the skill's own description rules.** `writing-skills.md:3`:

> `Use when the user asks to "write a new skill", "create skill", "edit skill", "update skill", or "review skill".`

- `:88` requires "Trigger terms woven into prose; no `Keywords:`-style label." This is a bare list of
  five quoted trigger phrases — functionally the keyword label the rule prohibits, just without the
  label.
- `:42` requires stating what the skill produces. It doesn't.
- `:41` requires "concrete triggering conditions and symptoms." There are no symptoms, only phrasings.

The skill's own *Good* example at `:51` satisfies all three and is a materially better description than
the one the file actually ships with. This is also the rule most likely to matter in practice, since
`README.md:20` calls the description "the thing that decides whether your skill ever gets used at all."

**S2 — Passive phrasing at `:39`.** "**Prefer** gerunds/verb-first" is precisely the soft form `:31`
bans ("never passive phrasing"), and `:82` puts "free of passively-phrased wording" on the checklist.
`:68` ("One excellent, complete example beats several mediocre ones") is declarative rather than
directive — borderline by the same rule.

**S3 — Checklist items with no corresponding body directive.** `:83` (never-always-loaded reference
files) and `:88` (no `Keywords:` label) appear only in the checklist. The Structure and Frontmatter
sections don't state either rule, so the checklist is carrying content the body should establish.

**S4 — No complete example.** `:92` requires "One complete example." The file has a directory tree
(`:56–63`) and a description bad/good pair (`:46–52`) — two partial snippets, no complete SKILL.md.

**Rules it does satisfy:** 96 lines (well under 500) · gerund name, lowercase-hyphen · one-sentence
Overview stating a core principle · ends with a checklist · no exemption clauses · no `references/`
files loaded unconditionally · directives throughout except S2.

---

## 5. What matches well

Genuinely tight correspondence on: the <500-line limit (`README.md:103` → `:28`, `:79`);
specificity-matched-to-fragility, including the per-step test (`:205` → `:29`, `:80`); no-op elimination
(`:151` → `:30`, `:81`); active phrasing as a rule (`:132` → `:31`); the no-TLDR/no-workflow-summary
description rule, which the skill states more forcefully than the post does (`:73` → `:43`); pointless
always-loaded reference files (`:167` → `:83`); one example, no multi-language dilution (`:134` → `:68`,
`:92`); scripts for deterministic processes (`:221` → `:66`); and terminal checklist (`:136` → `:33`,
`:96`).

---

## 6. On the `:274` claim

As written, `README.md:274` is an accuracy problem in the post, independent of the skill's quality.
Three ways out, in rough order of effort:

1. **Weaken the claim** — "based largely on the superpowers version, covering the rules from this post
   that apply at authoring time" — and drop the "nothing we haven't covered" half. Cheapest, and honest.
2. **Close the conventions gap** — fold the nine missing bullets into the skill, most of which are one
   line each. The gotchas section, function-scoped skills, and defaults-not-menus are the highest value.
3. **Reconcile the reverse gap** — the skill's nuance-clause prohibition and when-to-create criteria are
   strong enough to deserve a paragraph in the post rather than removal from the skill.

C1 (description voice) has been resolved independently of `:274`, since it was a wording defect in the
post rather than a scope question.

---

## Work queue for the follow-up session

Nothing below has been decided or applied.

- [x] **C1** — no decision needed; the sources agree and the post's wording was the bug. Fixed at
      `README.md:264`/`:270`, `writing-skills.md:40`, and `:87`. The skill's `:3` is voice-clean; left to S1
- [x] **C2** — vocabulary collision, not a real disagreement; the blog's "templates" are worked examples.
      Fixed at `writing-skills.md:68` by pointing the prohibition at the endorsed alternative
- [x] **C3** — accepted, no change. `:37` lists required fields only, not an exhaustive set; the
      mechanism is agent-specific and out of scope for the skill
- [x] **C4** — blog adopted the 100-line rule as a rule of thumb alongside the comparative test, at
      `README.md:165`; the skill keeps its threshold and is now grounded in the post
- [ ] **§2** — fold in the nine missing conventions (gotchas first), plus when-to-use/when-not-to-use,
      grounding + cold review, script promotion, LLM-for-reasoning, and anti-hijacking
- [ ] **§3** — decide per item: add to the post, or drop from the skill
- [ ] **S1** — rewrite the skill's `description` to satisfy `:41`, `:42`, and `:88`
- [ ] **S2** — "Prefer gerunds/verb-first" → directive form
- [ ] **S3** — give `:83` and `:88` body directives, or drop them from the checklist
- [ ] **S4** — decide whether the skill needs one complete SKILL.md example
- [ ] **§6** — fix or weaken the `README.md:274` claim once the scope above settles
