---
name: shape-testing-skills
description: Use when the user asks to run a shape test or shape-testing campaign against a skill's output-shaping rules, verify that formatting or structure guidance actually holds in generated artifacts, or tune rule phrasing that produces inconsistent, bloated, or wrong-shaped output. Covers inventorying every shaping and pattern rule in a skill body and testing temptation fixtures across wording variants with a no-guidance control, reporting per-rule convergence and an adopted phrasing.
disable-model-invocation: true
metadata.opencode/slash: true
metadata.opencode/autoinvoke: false
---

# Shape Testing Skills

## Overview

Run one shape-testing campaign for a skill's body rules and report which phrasings
actually bind. A shaping failure is a composition failure: the agent loaded the skill
and followed its discipline rules, but the deliverable violates the output contract
because the model's training prior pulled it toward a more common shape (self-contained
single files, inline styles, prose summaries). Shape tests are unit tests for wording:
cheap, fresh-context samples that measure a phrasing before you commit to it.

The campaign inventories **every** shaping and pattern rule in the skill body, then
tests each with the same instrument as the single-rule micro-test: a temptation fixture
run through a restricted headless agent across wording variants, with a no-guidance
control as the stopping signal. Many rules per campaign are licensed by one mechanizable
invariant:

> At any moment, the workspace skill differs from the intact skill by exactly **one**
> rule's section.

Consequence: the harness serializes entries × arms strictly — one entry, one arm, one
byte-state at a time; only the reps *within* one arm batch parallelize (they share
identical bytes, read-only).

Scope rules, up front:

- "Does the skill trigger for query X?" is a **trigger-testing** question; "can the
  agent find documented fact X?" is **retrieval-testing** — wrong tracks, do not run
  shape scenarios for them.
- A rule the agent skips under pressure is **discipline**; a documented fact with no
  rule to violate is **reference** content. Neither is shape-tested — record both as
  excluded with a routing reason.
- **Frontmatter-convention guidance is always out of scope** — the harness matches
  section spans against the body only (frontmatter stripped), so a frontmatter rule
  has no anchor span to swap.

Staging, capture, validation, and manifest recording live in `tools/test-harness/`
(`workspace-manager.sh`, `evaluator.py`), invoked from this skill's resolved directory.
Consume exit codes and JSON from those scripts only — never parse their prose stdout.

## Inputs

Collect all inputs before starting. Prompt the user for any that are missing.

- **Skill name or path** — the skill under test. A path is used directly; a bare name is
  resolved against the known skills roots. From the resolved location, derive the
  **source root**: the directory containing the `skills/` directory the skill lives in
  (for `<root>/.opencode/skills/<name>`, the source root is `<root>/.opencode`).
- **Harness** — required, user-specified (e.g. `opencode`). No default.
- **Model / variant** — optional passthroughs, and the only model-selection path: the
  eval agent pins no model config, and the installer asserts that pre-spend.
- **Reps** — runs per entry per arm; default 5.
- **Timeout** — per-run abort, in seconds; default 120.

Run with the model that will consume the skill in production, at default temperature.
Re-check adopted phrasings on model upgrades via the ablation track (rules whose control
stopped failing).

## Rule inventory

Read the skill body fully and build the inventory fresh from the current doc — the
manifest is a diff baseline, never a cache. Classify every body rule:

- **shaping** — prescribes the *form* of the artifact: file layout, styling mechanism,
  section order, required elements. In scope.
- **pattern** — "when you see X, reframe as Y". In scope, with the restraint-gate
  sub-track (see Scoring).
- **discipline** — compliance-cost rules the agent rationalizes away under pressure.
  Excluded: pressure-testing track, not shaping.
- **reference** — documented facts with no rule to violate. Excluded: retrieval-testing
  track.
- **technique** — how-to guidance the agent applies or not; no competing shape. Excluded.

If no shaping or pattern rules exist, stop: report the routings, run no campaign. Every
excluded rule gets a routing reason in the manifest.

Persist the inventory as `rules.json` next to the entries file:

```json
{
  "skill": "react-component-conventions",
  "generated": "2026-09-13",
  "rules": [
    {"id": "R-styling-01", "section": "Styling", "kind": "shaping",
     "statement": "styling lives in a co-located CSS module, never inline",
     "entries": ["css-modules-not-inline"]}
  ],
  "excluded": [
    {"id": "R-general-01", "section": "Workflow", "kind": "discipline",
     "reason": "compliance-cost rule — pressure-testing track, not shaping"}
  ]
}
```

Rule ids are section-anchored (`R-<section-slug>-<nn>`) so doc edits never renumber
other sections. Regenerate the manifest at proposal time and whenever entries are added
or retired; never hand-maintain it between campaigns. The diff against the previous
manifest drives the work: new rule (no manifest id) → propose an entry; changed rule
(same id, different statement) → flag its entries for re-testing; deleted rule →
propose pruning its entries (an entry testing an undocumented rule measures nothing).

## Entries file format

One entry per rule under test, at the default convention
`<source-root>/skills-workspace/<skill>/shape-tests/entries.json`:

```json
[
  {
    "id": "css-modules-not-inline",
    "rule": "R-styling-01",
    "kind": "shaping",
    "section": "## Styling\n\nComponents use css modules, never use inline styles",
    "fixtures": {
      "application": "Write a React component called `PriceTag` for our store UI.\n\n- Props: name (string), price (number), salePrice (optional number)\n- Shows the product name and price; when on sale, shows the old price struck through next to the sale price, plus a \"SALE\" badge\n- The badge turns a darker red on hover\n\nRespond with the complete file(s), each prefixed by its path."
    },
    "markers": {
      "inline_style": "style=\\{\\{",
      "hover_hack": "onMouseEnter|onMouseLeave",
      "css_module_import": "import styles from",
      "module_css_block": "\\.module\\.css"
    },
    "variants": {
      "v1": "Never use inline styles or `style` props.",
      "v2": "Every component ships as two files: `Name.tsx` and `Name.module.css`. All class names come from `import styles from './Name.module.css'`. Interactive states (hover, focus, active) are CSS pseudo-classes.",
      "v3": "Every component ships as two files: `Name.tsx` and `Name.module.css`. …unless a style is truly one-off."
    }
  }
]
```

- `id` — stable entry identifier; never reuse ids across rules. `rule` — the manifest
  id of the rule covered. `kind` — `shaping` or `pattern`.
- `section` — the rule's **verbatim** span from the skill body, used for the on-disk
  arm swap; it must appear exactly once in the synced body (frontmatter stripped), and
  the harness aborts pre-spend on doc drift. Because the span must exist, entries can
  only test rules already authored — guidance not yet written is out of scope, test it
  with the single-rule micro-test flow manually.
- `fixtures` — `application` (required; the temptation fixture) and, for pattern
  entries only, `counter-example` (a situation where the pattern should NOT be applied,
  for the restraint gate). No other keys.
- `markers` — non-empty dict of grep tokens for wrong **and** right shapes. Tokens are
  line-scored regexes; invalid regexes abort pre-spend.
- `restraint_markers` — grep tokens for over-application; required exactly when `kind`
  is `pattern`, forbidden otherwise.
- `variants` — 1–3 entries keyed `v1`…`v3`; the v0 control (section omitted) is
  implicit and never stored.

### Fixture design

The fixture's job is to tempt the wrong shape. If it contains no temptation, every arm
scores clean and you have learned nothing.

- Self-contained: no references to real files, repos, or context. Every path mentioned
  is illustrative.
- Never quote the rule text, the markers, or the expected shape — that tests following
  directions, not shaping under a competing incentive.
- Include at least one requirement the tempting wrong shape cannot satisfy, so the
  failure is forced into the open. Example: a `PriceTag` component whose badge must
  darken on hover — inline `style={{}}` cannot express hover, so the agent must either
  write real CSS (right shape) or reach for an `onMouseEnter`/`useState` hack (worse
  shape).
- Don't stack pressure into fixtures (deadlines, sunk cost, authority). The temptation
  here is structural.

## Eval agent

All arms run under one restricted agent, `agents/shape-evaluator.opencode.md`,
installed into the eval workspace by the harness before the first run: `skill: allow`;
read/grep/glob/list allowed; edit, bash, task, todowrite, webfetch, websearch, question,
external_directory denied. Only **one** workspace and one agent are needed, because the
v0 control (rule's section omitted) is still the skill being loaded — just with
different bytes.

The agent pins no `model`/`variant`/`temperature`/`top_p` — the installer asserts this
and aborts before any spend, so campaign `--model`/`--variant` flags are the only
model-selection path. The install step substitutes `{{SKILL_NAME}}` with the skill under
test; the per-run prompt is the bare fixture text — never rule text, markers, or
expected shape. Read-only is enforced by the harness permission layer, not claimed in a
prompt.

## Campaign flow

Phase 1 runs 5 control reps for **all** rules; only rules whose control exhibits the
failure earn a phase-2 variant run, after a second spend confirmation. Pattern-rule
winners then run the restraint gate against the counter-example fixture before they can
be adopted; non-converging rules get one round-2 mini-campaign on a changed form (cap 2
rounds), then `unresolved`. This preserves the micro-test's "control arm is the
stopping signal" rule across many rules without burning variant spend on rules whose
failure does not reproduce.

## Workflow

(`<shape-skill-dir>` = this skill's own resolved absolute path, same convention as the
retrieval track.)

1. Inputs per the Inputs section; read the skill body fully.
2. Build the rule inventory fresh; classify every rule; diff against `rules.json`.
   No shaping/pattern rules → stop, report routings.
3. Present proposal cards (see Proposal format) — one per entry: covered rule,
   classification confirmation, full fixture text, markers (and `restraint_markers`
   for pattern entries), variant texts, `why:` line, and the cost formula (`5 +
   5×variants per failing rule`; pattern `+5 per gated variant, cap +10`; per-rule cap
   30, pattern 40). User approves the proposal.
4. Preflight (no spend): `python3 --version` (>= 3.10); `evaluator.py check
   --harness <h>`.
5. One sterile workspace: `workspace-manager.sh init --prefix shape-test` → WS;
   `sync --skill <s> --source <root> --workspace $WS --full`; `status --skill <s>
   --source <root> --workspace $WS --full`.
6. `campaign-init --root <root>/skills-workspace/<s>/shape-tests` → CAMP.
7. Snapshot into the campaign dir (plain cp, record the exact commands):
   `entries.json`, `rules.json`, and the verified synced skill dir — the exact bytes
   being measured, before any arm rewriting.
8. **Spend confirmation #1**: rules × 5 control reps.
9. `evaluator.py shape-suite --harness <h> --skill <s> --agents-dir <shape-skill-dir>/agents --workspace $WS --entries <entries> --arms v0 --out $CAMP/results-control.json [--model m] [--variant v] [--reps 5] [--timeout 120]`
10. Score controls via `shape-evidence`. Rules whose control never exhibits the failure
    → `no-failure` + ablation flag; **stop those rules, author nothing**.
11. **Spend confirmation #2**: failing rules × variants × 5 reps.
12. Write `$CAMP/entries-failing.json` (the filtered entries) and run `shape-suite
    --arms v1,v2,v3 --entries $CAMP/entries-failing.json --out $CAMP/results-variants.json`
    (same other flags).
13. Score: `shape-evidence` marker triage → hand-read every flagged sample →
    convergence verdict per rule (see Scoring). Pattern-rule winners: restraint gate —
    `shape-suite --arms <winner> --fixture-key counter-example --out
    $CAMP/results-restraint.json` (5 reps, scored against `restraint_markers`); a
    variant that over-applies is disqualified — gate the next-best converging variant
    the same way.
14. Non-converging rules → round-2 mini-campaign (changed FORM, new filtered entries
    file, second campaign dir, **never recorded**), cap 2 rounds → else `unresolved`,
    escalate to the user.
15. Write `$CAMP/scored.json` (schema per shape-scored-check); run `evaluator.py
    shape-scored-check --results $CAMP/results-control.json --results
    $CAMP/results-variants.json [--results $CAMP/results-restraint.json] --scored
    $CAMP/scored.json [--adopted A --no-failure N --unresolved U --voids V]` — with
    the counts given (all four, matching the report summary), the check gates `record`.
16. Report (multi-rule format per Report format).
17. After every completed FULL campaign (never aborted, never a mini-campaign):
    `evaluator.py record --skill <s> --skill-path <skill dir> --manifest
    <root>/skills-workspace/<s>/manifest.json --scope dir --track shape-test
    --campaign <name> --adopted A --no-failure N --unresolved U --voids V`.
18. Write-backs to the source `SKILL.md` only on explicit user confirmation; afterwards
    re-run the adopted rule's entry as a confirmation mini-campaign (second campaign
    dir, never recorded).
19. `cleanup --workspace $WS --prefix shape-test`.

## shape-suite mechanics

Pre-spend gates (all exit 1 with an exact message before any harness invocation):
harness CLI on PATH; agent file exists, frontmatter `name:` matches `shape-evaluator`,
no `model`/`variant`/`temperature`/`top_p` pins; the skill is synced in the workspace
(`$WS/.agents/skills/<s>/` present); entries-file schema validation; `--fixture-key`
is `application` or `counter-example` and the keyed fixture exists on every selected
entry; `--arms` parses to a subset of `{v0} ∪ variants` present on each entry;
`--reps`/`--timeout` >= 1; out directory exists; every section span occurs verbatim
exactly once in the synced body (frontmatter stripped — doc drift aborts before
spend).

Then, **strictly serially** per entry, per arm — never parallelize arms to save
wall-clock, two variant byte-states at once makes attribution impossible:

1. Split the synced `SKILL.md` into frontmatter block + body.
2. Assemble the arm bytes: v0 = span removed together with exactly one following blank
   line; vN = span replaced by the variant text. Frontmatter is preserved
   byte-for-byte. The rewrite is verified before dispatch.
3. Run the reps — a smoke rep first (a harness failure here aborts before further
   spend), then parallel batches of at most 10 workers — with arm-tagged progress lines
   (`[ v0 ]`…`[ v3 ]`). The per-run prompt is the bare fixture text; `skill=` is passed
   for **every** arm so load-signal detection works on all arms.
4. Restore the original synced bytes before the next arm, and on abort — the workspace
   must never be left carrying a variant byte state.

Results JSON: entries keyed by arm (`entry.arms = {"v0": {"runs": [...]}, …}`), each run
carrying `arm`, `answer_text`, `tool_calls`, `void_signals`, `timeout`, `session_id`,
and the full run record, plus a `config` block (`skill`, `harness`, `model`, `variant`,
`reps`, `timeout`, `date`, entries-file path, `arms`, `fixture_key`) so every run is
attributable to the exact model selection that produced it. The entry's
`markers`/`restraint_markers` are carried into the results so `shape-evidence` triages
without re-reading the entries file.

Void signals: `skill-not-loaded` (fires for any arm without a completed load — every
arm loads the skill), `empty-answer`, `read-outside-workspace`. `timeout` stays a
separate boolean field — it is NOT a void signal: an abort after a complete inline
answer still scores; abort with partial/empty output is caught by `empty-answer` plus
driver judgment.

## Scoring

`shape-evidence --results <file> [--entry <id>] [--arm vN]` prints per entry/arm/rep the
answer text, void signals, session id, and marker triage counts (per-marker count of
answer lines matching each grep token). Triage only — the driver reads every flagged
sample by hand and judges **convergence across the 5 reps**: when wording lands, all
reps produce the same structure; five different structures across five reps means the
wording is not binding. Template echoes and quoted counter-examples masquerade as
marker hits — grep is triage, not verdict. For pattern rules the v0-vs-winner
property-frequency comparison is the primary detector, not a sanity gate.

Adoption discipline (restated from the micro-test):

- A prohibition arm is a measurement instrument, never a candidate — `adopted` may only
  name a recipe / structural arm even when a prohibition suppresses the banned token
  (suppressed tokens that migrate to a worse shape are displacement, not a fix).
- Ties go to the shorter phrasing — skills reload constantly; prose length is a real
  cost.
- A pattern-rule variant is adoptable only after passing the restraint gate.
- Adopt the variant that converges on the right shape and beats the control without
  regressing other markers.

Pattern rules ("when you see X, reframe as Y") have two signature failures the standard
flow misses:

- **Silent non-application.** The output is plausible and well-formed; the property is
  simply absent, so no marker trips. The with/without-control comparison is the primary
  detector: if the leading variant's outputs do not exhibit the property more often
  than the control, the rule is not binding — change the form.
- **Over-application.** The lens gets forced onto situations that do not call for it.
  This failure only exists *with* the guidance loaded, so counter-example fixtures need
  no control arm. Before adopting any variant, run the **restraint gate**: 5 reps
  against the entry's `counter-example` fixture (`--fixture-key counter-example`),
  scored against `restraint_markers`. A variant that over-applies is disqualified; gate
  the next-best converging variant the same way. Budget +5 samples per gated variant,
  cap +10.

## Improving the skill definition

Match the fix to the observed failure. The form that fixes one failure type backfires
on another.

| Observed result | Right form | Never |
|---|---|---|
| Control never exhibits the failure | Author nothing; flag an existing rule for ablation re-check | Hardening a phantom "just in case" |
| Prohibition suppresses the token but the failure migrates (inline styles banned → `useState` hover hacks) | Positive recipe: state what the output IS — its parts, in order | Stacking more prohibitions |
| A required element is omitted from an artifact the agent already produces | Structural REQUIRED field or slot in the template it fills in | Prose reminders near the template |
| Behavior should depend on a condition | Conditional keyed to an observable predicate ("if the brief exists, reference it") | Unconditional rule + exemption clauses |
| Reps disagree on the shape (noisy) | Change the form, not more words | Appending nuance clauses ("…unless it matters") |
| Two variants tie on every metric | Adopt the shorter phrasing | Merging the two |
| No convergence after 2 rounds | Escalate — restructure or enforce mechanically instead of prose | A third round on the same form |

Campaign rules:

- Fix between campaigns, never mid-campaign: complete the full pass, then apply edits.
  Mid-campaign doc edits invalidate every later result (and the section-span assertion
  makes drift abort pre-spend anyway).
- Present recommended edits to the user and apply them only after confirmation.
- Keep fixtures, variant texts, and section spans verbatim within and across campaigns;
  editing any of them invalidates comparison.
- A nuance clause appended to a winning recipe degrades it — express a real exception
  as its own conditional on an observable predicate, and test that as a new variant.
- Exemption clauses do not scope ("this limit doesn't apply to code blocks" still
  suppresses code blocks). If part of the output must be exempt, restructure so the
  rule cannot reach it.

## Campaign layout

```
<source-root>/skills-workspace/<skill>/shape-tests/
├── rules.json                     # inventory manifest (diff baseline)
├── entries.json                   # canonical entries
├── campaign-YYYY-MM-DD[-n]/
│   ├── entries.json  rules.json   # snapshots (plain cp, commands recorded)
│   ├── <skill>/                   # snapshot of verified synced skill dir
│   ├── results-control.json/.log  # phase 1
│   ├── entries-failing.json       # filtered entries driving phase 2
│   ├── results-variants.json/.log # phase 2
│   ├── results-restraint.json/.log  # pattern restraint gates (if any)
│   ├── scored.json
│   └── report.md
└── campaign-YYYY-MM-DD-2/         # mini-campaigns (round 2, confirmation):
                                   # second campaign dir + filtered entries;
                                   # never recorded
```

Campaign artifacts live in the persistent campaign dir under `skills-workspace/` —
never inside the temp eval workspace. The campaign snapshot of the *verified* synced
skill dir is taken at setup, before any arm rewriting — the recorded checksum reflects
the unmodified source, with per-arm variant text pinned by the snapshotted
`entries.json`.

## Proposal format

Before writing or running anything, present the inventory and planned entries as one
self-contained card per entry, in this fixed layout:

    shape test proposal: react-component-conventions — 2026-09-13
    source: skills/react-component-conventions/SKILL.md (body: 180 lines)
    entries file: skills-workspace/react-component-conventions/shape-tests/entries.json (missing — generating)
    scope: discipline/reference/technique rules excluded with routing reasons

    ## 1. css-modules-not-inline (shaping)
    covers: R-styling-01

    fixture:
    Write a React component called `PriceTag` for our store UI.
    …(full application fixture text)…

    markers:
    - inline_style      style=\{\{
    - hover_hack        onMouseEnter|onMouseLeave
    - css_module_import import styles from
    - module_css_block  \.module\.css

    variants:
    - v1 (prohibition): Never use inline styles or `style` props.
    - v2 (recipe): Every component ships as two files: `Name.tsx` and
      `Name.module.css`. …
    - v3 (recipe+nuance): V2 + "…unless a style is truly one-off."

    why: the hover requirement cannot be expressed with inline styles, so the
    fixture forces the agent into real CSS or a mouse-event hack — a wrong shape
    no marker ambiguity can hide.

    coverage: 4 shaping+pattern rules / 4 entries / 3 excluded
    excluded: R-general-01 (discipline → pressure-testing track), …
    cost: 5 control reps per rule, then 5 × variants per failing rule
    (pattern rules +5 per gated variant, cap +10); per-rule cap 30, 40 pattern

- Rule ids and entry ids are section-anchored and stable across campaigns; account for
  every rule exactly once — in a card or an exclusion with a stated reason.
- Show the full fixture text and variant texts in every card — a proposal without them
  is unreviewable.
- Every shaping/pattern entry carries 1–3 variants; the v0 control is implicit
  (section omitted). Never lead with a prohibition as the proposed fix — it is a
  measurement arm, not a candidate.
- Cost is the formula — phase 1 is always rules × 5; phase 2 spends only on failing
  rules. The per-phase spend confirmations live in the Workflow, not in this proposal.

## Report format

    shape test: react-component-conventions — 2026-09-13
    entries: skills-workspace/<skill>/shape-tests/entries.json (4 rules)
    artifacts: <source-root>/skills-workspace/<skill>/shape-tests/campaign-YYYY-MM-DD[-n]/
    manifest: recorded (sha256:…, A adopted / N no-failure / U unresolved / V void)

    ## css-modules-not-inline (shaping) — adopted v2
    arm              inline-style  hover-hack  css-module  shape across 5 reps
    V0 control       4/5           2/5         1/5         noisy — failure exists
    V1 prohibition   1/5           4/5         1/5         displaced, not fixed (measurement only)
    V2 recipe        0/5           0/5         5/5         converged → ADOPT
    notes: …
    write-back: replace the Styling section of <skill>/SKILL.md with the
    V2 text from entries.json [awaiting user confirmation]

    ## <pattern-rule-id> (pattern) — adopted v2, restraint gate pass
    …(same table, plus gate line: counter-example 5 reps, over-application 0/5)

    no-failure (ablation review):
    <rule-id> — control never exhibited the failure; re-check next campaign.

    unresolved:
    <rule-id> — no convergence after 2 rounds; escalate (restructure or
    mechanical enforcement instead of prose).

    summary: 2 adopted / 1 no-failure / 1 unresolved / 0 void (4 rules)

`manifest:` reads `not recorded (aborted)`, `not recorded (mini-campaign)`, or
`not recorded (calibration pilot)` on those paths — only a completed full campaign is
recorded.

## shape-scored-check

The driver scores entries offline from the results files (zero spend) and writes
`<campaign>/scored.json`; `evaluator.py shape-scored-check` validates it against the
results before anything is recorded. Schema — one object per entry covered by the
campaign:

```json
{
  "entries": [
    {
      "id": "css-modules-not-inline", "kind": "shaping", "result": "adopted",
      "adopted_arm": "v2", "restraint_gate": null,
      "marker_counts": {"v0": {"inline_style": 4, "hover_hack": 2},
                        "v1": {"inline_style": 1, "hover_hack": 4},
                        "v2": {"inline_style": 0, "hover_hack": 0}},
      "notes": "v2 converged on the right shape across 5/5 reps"
    }
  ]
}
```

- `result` — one of `adopted`, `no-failure`, `unresolved`, `void`. `kind` — `shaping`
  or `pattern`; must match the results' kind for the entry so the check can enforce
  gate rules without reading the entries file.
- `adopted_arm` — required exactly when `result` is `adopted`; must name a non-v0 arm
  present in that entry's results (a prohibition/absence arm is a measurement
  instrument, never a candidate).
- `restraint_gate` — `pass` or `fail`; required exactly when `kind` is `pattern` and
  `result` is `adopted`; forbidden otherwise.
- `marker_counts` — optional, per-arm marker hit counts; `notes` — optional string.
- Entry-id coverage is **union with dedupe** across the repeated `--results` files: an
  id appearing in N files (control, variants, restraint) is scored exactly once, and
  every union id must be covered — missing, duplicate, or unknown ids fail validation.
  One `--results` file is a valid phase-1-only campaign.
- Optional `--adopted/--no-failure/--unresolved/--voids` (all four together) must equal
  the scored sums; pass the counts from the report summary so an arithmetic slip fails
  here, before `record`.

## Gotchas

- A fixture with no temptation proves nothing — if every arm is clean, suspect the
  fixture before declaring victory.
- Never put rule text, expected shape, or markers in the run prompt; the per-run prompt
  is the bare fixture text. Extra framing contaminates the measurement.
- Never let the eval agent know this is a test.
- Grep is triage, not verdict. A sample that writes `// don't use style={{}} here`
  trips the inline-style grep without being a violation — read every flagged match by
  hand.
- Multi-file artifacts need all expected files: a recipe demanding `Name.tsx` +
  `Name.module.css` fails a rep that returns only one block, even if the returned block
  looks right.
- A missing skill-load signal is `void`, not `no-failure` — the doc was never in
  context; re-run the arm before scoring it.
- Timeout voids are not always agent defects: concurrent reps share one endpoint, so
  per-rep latency rises with parallelism — on a slow local server the default 120 s can
  abort clean runs mid-answer (observed in calibration: 2 empty-answer voids at 120 s,
  0 at 300 s). Raise `--timeout` before pressure-testing the agent body.
- Every run in a results file carries its headless `session_id` (shown by
  `shape-evidence`), and harness-abort error lines end with `[session <id>]` when the
  harness emitted one before failing — include it when reporting an abort so the failed
  session can be inspected.

## Checklist

- [ ] Inputs collected: skill resolved name-or-path, source root derived, harness user-specified, model/variant/reps/timeout settled; rule inventory built fresh, every rule classified, manifest diffed; no shaping/pattern rules → stopped with routings reported
- [ ] Every excluded rule recorded with a routing reason; frontmatter-convention rules never proposed as entries
- [ ] Proposal cards in the fixed format, one per entry, with full fixture/variant texts and the cost formula; user approved
- [ ] Every `section` span copied verbatim and appearing exactly once in the body (frontmatter stripped); `fixtures.application` on every entry; `counter-example` + `restraint_markers` exactly on pattern entries
- [ ] Preflight green: python3 >= 3.10, `evaluator.py check --harness` exit 0; ONE workspace initialized with `--prefix shape-test`
- [ ] Skill synced `--full` and verified with `status --full`; campaign dir created; entries.json, rules.json, and the verified synced skill dir snapshotted with the exact cp commands recorded
- [ ] Spend confirmation #1 (rules × 5 control reps) before phase 1; `shape-suite --arms v0` wrote results-control.json; only exit codes and JSON consumed
- [ ] Controls scored via `shape-evidence`; no-failure rules stopped with nothing authored and flagged for ablation review
- [ ] Spend confirmation #2 (failing rules × variants × 5 reps) before phase 2; `shape-suite --arms v1,v2,v3 --entries $CAMP/entries-failing.json` wrote results-variants.json
- [ ] Every flagged marker sample hand-read; convergence judged across the 5 reps, not by marker averages; prohibition arms never adopted; ties to the shorter phrasing
- [ ] Pattern-rule winners gated: 5 reps on `counter-example` with `--fixture-key counter-example`, scored against `restraint_markers`; over-applying variants disqualified and the next-best gated
- [ ] Round 2 (if any) changed the FORM in a never-recorded mini-campaign; hard cap 2 rounds respected
- [ ] scored.json written for every union results id; `shape-scored-check` exits 0 — including the report-summary counts when passed
- [ ] Report shows per-rule per-arm tables, gate lines for pattern rules, no-failure/unresolved sections, summary counts, and the `artifacts:`/`manifest:` lines
- [ ] `record --scope dir --track shape-test` run only after a completed full campaign — never aborted, never a mini-campaign, never a calibration pilot
- [ ] Write-backs applied only with user confirmation, followed by a never-recorded confirmation mini-campaign; `cleanup --workspace $WS --prefix shape-test` run
