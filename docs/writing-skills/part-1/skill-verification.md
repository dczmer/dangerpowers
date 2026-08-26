# `writing-skills.md` vs. the final draft — verification report

Written 2026-08-25 against `README.md` and `writing-skills.md`; refreshed 2026-08-25 after the
`README.md` prose rewrite. The rewrite changed wording and line numbers but not structure or content,
so every finding below stands — only the references and quotes have been re-resolved. Re-check them
before acting if either file has moved on. `writing-skills.md` has since gained the §2 conventions
cluster and its own short `## Gotchas` section (96 → 110 lines); all references to it below reflect
that post-fix numbering.

**Fixes applied so far:** C1, C2, C4, the §2 conventions cluster, and §3; C3 reviewed and accepted with
no change (see the work queue at the bottom for what remains).

Companion document: `research-notes.md` holds the source audit, citation pass, and plagiarism scan for
`README.md`. This file covers only the blog-to-skill correspondence.

**Verdict:** the skill is well-built and self-consistent on its core rules, but it is **not** what
`README.md:279` claims it is. That line says the skill contains "everything we've covered in this
document, and nothing we haven't covered yet." Both halves fail: roughly a dozen blog rules were absent
(the conventions cluster — the largest block — has since been folded in; see §2), and roughly a dozen
skill rules appeared nowhere in the blog (six have since been added to the post, four deliberately kept
skill-only; see §3). The apparent conflict on description voice
turned out to be a wording slip in the post rather than a real disagreement (C1, since fixed), and the
skill violates two of its own rules — one of them in its own `description` field.

---

## 1. Direct conflicts

**C1 — Description voice: third person vs. imperative. Resolved 2026-08-25.** `README.md:269` said
descriptions get written "in third person, **always**," with the good/bad pair "Processes Excel files and
generates reports" / "I can help you with", while `writing-skills.md:44` mandated "`description`:
imperative ("Use when...")". On their face the two picked opposite forms.

It was not a source conflict. `research-notes.md:49–50` had already adjudicated the pair: A puts third
person in a warning box about point-of-view consistency ("inconsistent point-of-view can cause discovery
problems"), and E — which `:269` cited *in support of* third person — is itself the source of the
imperative rule ("Use imperative phrasing… 'Use this skill when…' rather than 'This skill does…'"). The
ban both sources describe is on first and second person ("I can help you…"), not on imperatives. The
post's error was using "third person" to mean "not first person" and then attaching "always" to it, which
over-read both citations.

Applied: `README.md:269` now states the rule as third person *about* the skill, and `:275` says
explicitly that an imperative trigger clause ("Use when the user asks to...") is still third person;
`writing-skills.md:44` states the person rule directly and keeps "Use when…" as the opening clause;
`writing-skills.md:101` changed `imperative` → `third person` to match — a third site for the same rule
that this report originally missed.

The skill's own `:3` is not a violation of the resolved rule — "the user" is third person. Its remaining
defects are the ones under S1.

**C2 — Templates: endorsed vs. prohibited. Resolved 2026-08-25.** `README.md:135` recommends including
"templates or snippets that illustrate what you want the AI to do." `writing-skills.md:72` said "no
fill-in-the-blank templates." On their face the two sentences contradicted, and the skill never drew
the distinction.

It was a vocabulary collision, not a real disagreement. The blog's "templates or snippets" means a
filled-in, concrete example of a desired output — the very next sentence prescribes one complete
example with no multi-language dilution. The skill's prohibition targets blank forms with placeholders,
which force the agent to instantiate the example and reintroduce the judgment it was meant to remove.

Applied: `writing-skills.md:72` now reads "no fill-in-the-blank templates — show one complete, filled-in
example instead," naming the actual failure mode and pointing at the endorsed alternative. The blog
needed no edit; its wording already sits inside a sentence about concrete examples. One-line edit, so no
line reference in this report has shifted.

**C3 — Frontmatter field set. Accepted 2026-08-25 — no change.** `writing-skills.md:41` opens "Two
required fields: `name` and `description`" and never mentions another key. `README.md:96` documents
`disable-model-invocation: true` as an authoring decision with real consequences.

Decision: accept. `:41` claims only that two fields are *required*, not that the list is exhaustive, so
there is no inaccuracy to fix. The manual-invocation mechanism is agent-specific (absent from the Agent
Skills spec, per `README.md:96`), and the skill's audience — an agent authoring or editing skills —
does not need it to produce correct frontmatter. Documenting an optional, non-portable key would cost
every reader a line for a decision that rarely applies.

**C4 — Extraction threshold (soft conflict). Resolved 2026-08-25.** `README.md:166` gave a comparative
test — extract to `references/` when the extracted text is longer than the conditional-load instruction
replacing it — while `writing-skills.md:64` gave an absolute one: "Heavy reference (100+ lines)". Not
contradictory (a 100+ line extract virtually always passes the comparative test), but different
heuristics, and `100+` appeared nowhere in the post.

Applied: `README.md:166` now adds the threshold as a rule of thumb: "As a rough rule of thumb, anything
over about 100 lines belongs in a reference file regardless." The comparative test stays as the
principle; the skill's number is now grounded in the post. The skill needed no edit. One-line edit, so
no line reference in this report has shifted.

---

## 2. Blog rules missing from the skill

**The big cluster — resolved with exclusions 2026-08-25.** Nine of the 10 "Established Conventions"
bullets (`README.md:254–263`) were absent, and the tenth only half-covered (gerund naming made it in at
`:43`/`:100`; the 64-character limit did not). Applied to `writing-skills.md`: the 64-char limit joined
the `name` bullet (`:43`) and its checklist item (`:100`); defaults-not-menus, one-term-per-concept,
no-time-sensitive-information, and the gotchas section joined the Content directives (`:33–36`), with
gotchas and defaults also added to the checklist (`:90–91`); script error handling and no-magic-
constants folded into the scripts bullet (`:70`); and the small-model caveat added as `:75`. A short
`## Gotchas` section (before the checklist) covers the two traps the post demonstrates with real
behavior — workflow-summarizing descriptions and always-loaded references — satisfying the skill's own
new checklist item. Two bullets
were deliberately excluded: the function-scoping rule (`README.md:255`) and forward-slashes-in-paths
(`:259`). The additions shifted the skill's line numbers (96 → 110 lines); every `writing-skills.md`
reference in this report reflects the post-fix numbering.

**Other gaps:**

- **`README.md:106` — "when to use / when not to use" sections inside the skill body.** The skill's
  "When to Create a Skill" (`:12–23`) answers a different question (*should this be a skill at all*),
  and the Body checklist (`:104–110`) has no item for early-abort sections. The blog's stated rationale —
  giving the agent a chance to bail after triggering — is absent.
- **`README.md:39–50` — grounding and cold review.** Give the model real material (transcript, runbook,
  review comments, a patch) rather than asking it to imagine the process; read the draft back in a fresh
  session with no memory of writing it. Nothing in the skill addresses where content comes from or how
  to review it. Partial mitigation: "write it yourself" is human-facing advice, but "ground it in real
  material" and "review cold" are both expressible as directives.
- **`README.md:224` — promote repeated ad-hoc scripts** into saved reusable scripts.
- **`README.md:226` — reserve LLM evaluation** for work that genuinely needs reasoning or semantic
  understanding. Implied by `writing-skills.md:70` but not stated.
- **`README.md:72`, `:236` — don't write descriptions that hijack phrases belonging to other skills.**
  The skill covers the *no-TLDR* failure mode well (`:47`) but not the over-broad-trigger one.
- **`README.md:170` — keep the main file to the happy path.** `writing-skills.md:69` gets close but
  never says it.

**Correctly excluded** (consistent with the post's stated scope at `:7` and `:285`): eval-first
authoring (`:26`, `:54–60`), trigger and pressure testing (`:92`, `:129`), and discipline/prohibition
rules (`:35`, `:216`). These are deferred to later installments by name, so their absence is a feature,
not a gap.

---

## 3. Skill rules that appear nowhere in the blog — resolved with omissions 2026-08-25

This was the half of `:279` that failed more clearly, because several of these are the skill's *best*
rules. Six of the ten reverse-gap items are now in the post; four were deliberately kept skill-only.

**Added to `README.md`:**

- Reference `--help` instead of documenting flags, and cross-reference other skills by name → `:265`
- Flowcharts for non-obvious decisions, tables for reference data, numbered lists for linear steps →
  `:266`
- Read an existing skill fully before editing it → `:267`
- Supporting files referenced one level deep → `:173`
- State what the skill produces; anti-pattern enumerations move to the body; no `Keywords:`-style label
  → `:74`
- A to-do per checklist item → `:137` (folded into the checklist paragraph)

**Kept skill-only (decision: the post stays scoped to authoring content, not skill-selection policy):**

- No nuance or exemption clauses that scope a directive (`writing-skills.md:36`, `:89`)
- The entire "When to Create a Skill" section (`:12–23`), including durable facts belonging in
  AGENTS.md (`:22`) and automating mechanical constraints (`:23`)

The additions shifted `README.md`'s line numbers (+1 after the old `:73`, +1 after the old `:171`, +3
after the old `:262`); every `README.md` reference in this report reflects the post-fix numbering.

---

## 4. Where the skill breaks its own rules

**S1 — The `description` violates three of the skill's own description rules.** `writing-skills.md:3`:

> `Use when the user asks to "write a new skill", "create skill", "edit skill", "update skill", or "review skill".`

- `:102` requires "Trigger terms woven into prose; no `Keywords:`-style label." This is a bare list of
  five quoted trigger phrases — functionally the keyword label the rule prohibits, just without the
  label.
- `:46` requires stating what the skill produces. It doesn't.
- `:45` requires "concrete triggering conditions and symptoms." There are no symptoms, only phrasings.

The skill's own *Good* example at `:55` satisfies all three and is a materially better description than
the one the file actually ships with. This is also the rule most likely to matter in practice, since
`README.md:20` calls the description "the thing that decides whether your skill ever gets used at all."

**S2 — Passive phrasing at `:43`.** "**Prefer** gerunds/verb-first" is precisely the soft form `:31`
bans ("never passive phrasing"), and `:96` puts "free of passively-phrased wording" on the checklist.
`:72` ("One excellent, complete example beats several mediocre ones") is declarative rather than
directive — borderline by the same rule.

**S3 — Checklist items with no corresponding body directive.** `:97` (never-always-loaded reference
files) and `:102` (no `Keywords:` label) appear only in the checklist. The Structure and Frontmatter
sections don't state either rule, so the checklist is carrying content the body should establish.

**S4 — No complete example.** `:106` requires "One complete example." The file has a directory tree
(`:60–67`) and a description bad/good pair (`:50–56`) — two partial snippets, no complete SKILL.md.

**Rules it does satisfy:** 110 lines (well under 500) · gerund name, lowercase-hyphen · one-sentence
Overview stating a core principle · ends with a checklist · no exemption clauses · no `references/`
files loaded unconditionally · directives throughout except S2.

---

## 5. What matches well

Genuinely tight correspondence on: the <500-line limit (`README.md:104` → `:28`, `:93`);
specificity-matched-to-fragility, including the per-step test (`:206` → `:29`, `:94`); no-op elimination
(`:152` → `:30`, `:95`); active phrasing as a rule (`:133` → `:31`); the no-TLDR/no-workflow-summary
description rule, which the skill states more forcefully than the post does (`:73` → `:47`); pointless
always-loaded reference files (`:168` → `:97`); one example, no multi-language dilution (`:135` → `:72`,
`:106`); scripts for deterministic processes (`:222` → `:70`); and terminal checklist (`:137` → `:37`,
`:110`).

---

## 6. On the `:279` claim

As written, `README.md:279` is an accuracy problem in the post, independent of the skill's quality.
Three ways out, in rough order of effort:

1. **Weaken the claim** — "based largely on the superpowers version, covering the rules from this post
   that apply at authoring time" — and drop the "nothing we haven't covered" half. Cheapest, and honest.
2. **Close the conventions gap** — *done with exclusions, see §2.* Eight of the ten bullets are now in
   the skill; function-scoping and forward-slashes stay blog-only.
3. **Reconcile the reverse gap** — *done with omissions, see §3.* Six of the ten skill-only rules are
   now in the post; nuance clauses and the when-to-create material stay skill-only by decision.

C1 (description voice) has been resolved independently of `:279`, since it was a wording defect in the
post rather than a scope question.

---

## Work queue for the follow-up session

Nothing below has been decided or applied.

- [x] **C1** — no decision needed; the sources agree and the post's wording was the bug. Fixed at
      `README.md:269`/`:275`, `writing-skills.md:44`, and `:101`. The skill's `:3` is voice-clean; left to S1
- [x] **C2** — vocabulary collision, not a real disagreement; the blog's "templates" are worked examples.
      Fixed at `writing-skills.md:72` by pointing the prohibition at the endorsed alternative
- [x] **C3** — accepted, no change. `:41` lists required fields only, not an exhaustive set; the
      mechanism is agent-specific and out of scope for the skill
- [x] **C4** — blog adopted the 100-line rule as a rule of thumb alongside the comparative test, at
      `README.md:166`; the skill keeps its threshold and is now grounded in the post
- [x] **§2 conventions cluster** — folded in eight of ten bullets (gotchas and defaults also on the
      checklist); function-scoping (`README.md:255`) and forward-slashes (`:259`) deliberately excluded
- [ ] **§2 remaining gaps** — when-to-use/when-not-to-use, grounding + cold review, script promotion,
      LLM-for-reasoning, and anti-hijacking
- [x] **§3** — six reverse-gap rules added to the post (`README.md:74`, `:137`, `:173`, `:265–267`);
      nuance clauses and the when-to-create material deliberately kept skill-only
- [ ] **S1** — rewrite the skill's `description` to satisfy `:45`, `:46`, and `:102`
- [ ] **S2** — "Prefer gerunds/verb-first" → directive form
- [ ] **S3** — give `:97` and `:102` body directives, or drop them from the checklist
- [ ] **S4** — decide whether the skill needs one complete SKILL.md example
- [ ] **§6** — fix or weaken the `README.md:279` claim once the scope above settles
