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
control as the stopping signal. Like the pressure track, this track uses **injection,
not byte-states**: each arm's body (v0: the rule's section span removed; vN: the span
replaced by the variant text) is assembled fresh from the snapshotted skill body and
injected into every rep's prompt as "Project conventions". The skill is never synced
and the workspace is never written, so a variant can never leak into another arm's
run and there is no skill-load step that can fail — the conventions are always in
context. The harness still serializes entries × arms — one entry, one arm at a time;
only the reps *within* one arm batch parallelize (identical prompt bytes, read-only);
the serial order is spend discipline, not an optimization target.

Scope rules, up front:

- A question about whether a skill *fires* for a query is a trigger-testing question, and a question about whether an agent can *find a documented fact* is a retrieval-testing question; both are wrong tracks here — route them to their own tracks instead of running shape scenarios for them.
- A rule the agent skips under pressure is **discipline**; a documented fact with no
  rule to violate is **reference** content. Neither is shape-tested — record both in
  the manifest (`rules.json`) as excluded entries, each with its routing reason.
- **Frontmatter-convention guidance is always out of scope** — the harness matches
  section spans against the body only (frontmatter stripped), so a frontmatter rule
  has no anchor span to swap.

Staging, capture, validation, and manifest recording live in `tools/test-harness/`
(`workspace-manager.sh`, `evaluator.py`), invoked from this skill's resolved directory.
Consume exit codes and JSON from those scripts only — never parse their prose stdout.

## Quick reference

- Harness: always user-specified — prompt the user for it; never assume, auto-detect,
  or pick one yourself.
- Model: run the model that will consume the skill in production, at default
  temperature, via the campaign `--model`/`--variant` flags — never pin model config
  in the eval agent file.
- Defaults: 5 reps per entry per arm; 120 s per-run timeout.
- Phases: phase 1 runs 5 control reps for ALL rules (never skipped); phase 2 runs
  variants (5 reps each) only for rules whose control exhibited the failure, after a
  second spend confirmation. A generic continuation message ("keep going", "proceed",
  "sounds good", a thumbs-up) is **NOT** a second spend confirmation. The second
  spend confirmation must be an explicit approval that names the rules earning
  variant runs — if the user's reply does not enumerate them, stop and ask again
  before any variant rep dispatches.
- Pattern winners run the restraint gate before adoption: 5 reps on the
  counter-example fixture, scored against `restraint_markers`; counter-example
  fixtures need no control arm.
- Non-converging rules get one round-2 mini-campaign on a changed form — hard cap
  2 rounds, then `unresolved`.
- Cost: `5 + 5×variants` per failing rule; pattern `+5` per gated variant, cap `+10`;
  per-rule cap 30 (pattern 40). Example: 3 failing shaping rules + 1 failing pattern
  rule, 3 variants each, all gated → `3×(5+15) + (5+15+10) = 90`.
- Serialization: one entry, one arm at a time — never parallelize arms; only reps
  within one arm batch parallelize. Arms differ only in prompt bytes (injection, not
  byte-states); the serial order is spend discipline.
- Fix between campaigns, never mid-campaign; fixtures, variant texts, and section
  spans stay verbatim across campaigns.
- Record only after a completed FULL campaign (`--scope dir --track shape-test`,
  all four counts); cleanup uses `--prefix shape-test`.

## Inputs

Collect all inputs before starting. Prompt the user for any that are missing.

- **Skill name or path** — the skill under test. A path is used directly; a bare name is
  resolved against the known skills roots. From the resolved location, derive the
  **source root**: the directory containing the `skills/` directory the skill lives in
  (for `<root>/.opencode/skills/<name>`, the source root is `<root>/.opencode`).
- **Harness** — required, user-specified (e.g. `opencode`). No default: prompt the
  user; never assume, auto-detect, or pick one yourself.
- **Model / variant** — optional passthroughs, and the only model-selection path:
  never pin `model`/`variant`/`temperature`/`top_p` in the eval agent file — the
  installer asserts none exist and aborts pre-spend; pass `--model`/`--variant` to
  the campaign instead. Run with the model that will consume the skill in
  production, at default temperature.
- **Reps** — runs per entry per arm; default 5.
- **Timeout** — per-run abort, in seconds; default 120.

Run with the model that will consume the skill in production, at default temperature.
Re-check adopted phrasings on model upgrades via the ablation track (rules whose control
stopped failing).

## Rule inventory

Read the skill body fully and build the inventory fresh from the current doc — the
manifest is a diff baseline, never a cache. When asked to reuse a previous campaign's
manifest as a starting inventory, refuse: rebuild fresh from the current doc; the old
manifest only drives the new/changed/deleted diff. Classify every body rule:

- **shaping** — prescribes the *form* of the artifact: file layout, styling mechanism,
  section order, required elements. In scope.
- **pattern** — "when you see X, reframe as Y". Classify by the rule's trigger
  structure, never by the layout of the artifact it produces: a rule that reframes a
  *request* is a pattern rule even when the reframed output prescribes a layout. In
  scope; pattern winners must pass the restraint-gate sub-track before adoption
  (see Scoring).
- **discipline** — compliance-cost rules the agent rationalizes away under pressure.
  Excluded: pressure-testing track, not shaping.
- **reference** — documented facts with no rule to violate. Excluded: retrieval-testing
  track.
- **technique** — how-to guidance the agent applies or not; no competing shape. Excluded.

If no shaping or pattern rules exist, stop: report the routings, run no campaign. Every
excluded rule gets a routing reason in the manifest.

The inventory is a `rules.json` file:

- `skill`, `generated` (date)
- `rules` — array of `{id, section, kind, statement, entries}`
- `excluded` — array of `{id, section, kind, reason}`: this is where excluded rules
  are recorded — there is no other manifest — and every excluded rule carries its
  routing reason in `reason`
- Rule ids are section-anchored: `R-<section-slug>-<nn>`, numbered within their
  section so doc edits never renumber other sections

Every entry is a JSON object with exactly these keys: `id` (stable, never reused), `rule` (manifest id), `kind` (`shaping` or `pattern`), `section` (the rule's verbatim span from the skill body), `fixtures` (`application` always; `counter-example` exactly when kind is `pattern`), `markers` (non-empty dict of grep tokens for wrong and right shapes), `restraint_markers` (exactly when kind is `pattern`, forbidden otherwise), `variants` (1-3 entries keyed `v1`..`v3`; the v0 control is implicit and never stored).

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
installed into the eval workspace by the harness before the first run: the read quartet
(`read`/`grep`/`glob`/`list`) allowed; everything else (`skill`, `edit`, `bash`,
`task`, `todowrite`, `webfetch`, `websearch`, `question`, `external_directory`)
denied. The conventions are injected into the prompt, so **any skill-load attempt is a
void signal** (`skill-load-attempted`) — the load cannot be required, only violated.
Only **one** workspace and one agent are needed, because arms differ only in prompt
bytes: the v0 control (rule's section omitted) is still the full conventions being
injected — just with different bytes.

The single eval workspace is initialized with `--prefix shape-test` and is **never
synced**; a synced skill in it trips the contamination gate (recreate the workspace,
never copy the skill in to "fix" it).

The agent pins no `model`/`variant`/`temperature`/`top_p` — the installer asserts this
and aborts before any spend, so campaign `--model`/`--variant` flags are the only
model-selection path. There is no `{{SKILL_NAME}}` substitution (the agent loads
nothing); the per-run prompt is the injected conventions plus the bare fixture text —
never rule text, markers, or expected shape. Read-only is enforced by the harness
permission layer, not claimed in a prompt.

## Campaign flow

Phase 1 runs 5 control reps for **all** rules. Phase 2 itself is conditional: only
rules whose control exhibits the failure earn a variant run, after a second spend
confirmation — healthy rules get no variant spend at all. Pattern-rule
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
   --harness <h> [--model m]` (with `--model`, the check also validates the
   model against the harness's model list).
5. One sterile workspace: `workspace-manager.sh init --prefix shape-test` → WS
   (never synced; `sync`/`status` are not part of this track at all).
6. `campaign-init --root <root>/skills-workspace/<s>/shape-tests` → CAMP.
7. Snapshot into the campaign dir (plain cp, record the exact commands):
   `entries.json`, `rules.json`, and the source skill dir — plus `skill-body.txt`,
   the snapshotted `SKILL.md` with its frontmatter block stripped (the exact
   injected bytes), produced with a documented pipeline, never by hand-editing;
   one form, run from the repo root against the campaign dir's skill snapshot:

   ```bash
   uv run python -c "import pathlib, sys; sys.path.insert(0, 'tools/test-harness'); \
   from evaluator import extract_frontmatter; \
   src = pathlib.Path('$CAMP/<skill>/SKILL.md').read_text(); \
   fm = extract_frontmatter(src) or sys.exit('no frontmatter block'); \
   pathlib.Path('$CAMP/skill-body.txt').write_text(src[len(fm):])"
   ```
8. **Spend confirmation #1**: rules × 5 control reps — phase 1 covers ALL rules
   and is never skipped.
9. `evaluator.py shape-suite --harness <h> --skill <s> --agents-dir <shape-skill-dir>/agents --workspace $WS --entries <entries> --skill-file $CAMP/skill-body.txt --arms v0 --out $CAMP/results-control.json [--model m] [--variant v] [--reps 5] [--timeout 120]`
10. Score controls via `shape-evidence`. Rules whose control never exhibits the failure
    → `no-failure` + ablation flag; **stop those rules, author nothing**.
11. **Spend confirmation #2**: failing rules × variants × 5 reps — only rules
    whose control exhibited the failure earn variant runs. A generic continuation
    message ("keep going", "proceed", "sounds good", a thumbs-up) is **NOT** a second
    spend confirmation. The second spend confirmation must be an explicit approval
    that names the rules earning variant runs — if the user's reply does not
    enumerate them, stop and ask again before any variant rep dispatches.
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
no `model`/`variant`/`temperature`/`top_p` pins; `--skill-file` exists and is non-empty
(the snapshotted body, frontmatter already stripped by the driver); entries-file schema
validation; `--fixture-key` is `application` or `counter-example` and the keyed fixture
exists on every selected entry; `--arms` parses to a subset of `{v0} ∪ variants`
present on each entry; `--reps`/`--timeout` >= 1; out directory exists; every section
span occurs verbatim exactly once in the snapshotted body (doc drift aborts before
spend); and the **contamination gate** (a synced skill in the workspace fails with
"recreate the workspace, never sync").

Then, **strictly serially** per entry, per arm — never parallelize arms; the serial
order is spend discipline, not an optimization target (arms differ only in prompt
bytes, so nothing mechanical prevents parallel arms — one entry, one arm at a time
keeps attribution and spend clean):

1. Assemble the arm body from the snapshot: v0 = the rule's section span removed
   together with exactly one following blank line; vN = the span replaced by the
   variant text. The assembly is verified before dispatch (`verify_arm_bytes`).
2. Inject: the per-run prompt is `Project conventions:` + the assembled arm body +
   `Task:` + the bare fixture text — never rule text, markers, or expected shape.
   Injection, not byte-states: each rep's prompt is assembled fresh from the
   snapshotted bytes, so a variant can never leak into another arm's run, and there
   is no skill-load step that can fail — the conventions are always in context.
3. Run the reps — a smoke rep first (a harness failure here aborts before further
   spend), then parallel batches of at most 10 workers — with arm-tagged progress
   lines (`[ v0 ]`…`[ v3 ]`). The workspace is never written; there is no byte
   state to restore, on completion or abort.

Results JSON: entries keyed by arm (`entry.arms = {"v0": {"runs": [...]}, …}`), each run
carrying `arm`, `answer_text`, `tool_calls`, `void_signals`, `timeout`, `session_id`,
and the full run record, plus a `config` block (`skill`, `harness`, `model`, `variant`,
`reps`, `timeout`, `date`, entries-file path, `skill_file`, `arms`, `fixture_key`) so
every run is attributable to the exact model selection that produced it. The entry's
`markers`/`restraint_markers` are carried into the results so `shape-evidence` triages
without re-reading the entries file.

Void signals: `skill-load-attempted` (any captured skill tool call — the conventions
are injected and the skill tool is denied, so there is no load signal on this track;
an attempt is a violation, not a requirement), `empty-answer`,
`read-outside-workspace`. `timeout` stays a separate boolean field — it is NOT a void
signal: an abort after a complete inline answer still scores; abort with
partial/empty output is caught by `empty-answer` plus driver judgment.

## Scoring

Two rules govern every scoring decision:

- "The grep flagged all reps" is not convergence. Convergence means all reps produce
  the same structure — established by reading the reps, never by marker counts
  alone — and grep is triage, not verdict: every flagged sample is hand-read before
  it counts, because template echoes and quoted counter-examples masquerade as
  marker hits.
- Never adopt a prohibition arm: `adopted` may only name a recipe / structural arm —
  a suppressed token that migrates to a worse shape is displacement, not a fix.

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
  detector: the winner's property frequency must **EXCEED** the control's — equal
  frequency means the rule is not binding; change the form.
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
│   ├── <skill>/                   # snapshot of the source skill dir
│   ├── skill-body.txt             # the exact injected bytes (frontmatter stripped)
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
never inside the temp eval workspace. The campaign snapshot of the source skill dir
and of `skill-body.txt` (the exact injected bytes) is taken at setup — the recorded
checksum reflects the unmodified source, with per-arm variant text pinned by the
snapshotted `entries.json`.

Every pre-campaign plan is one self-contained card per planned entry, in this order: a heading line `## N. <entry-id> (<kind>)`; a `covers:` line naming the manifest rule id; a `fixture:` section with the full fixture text; a `markers:` list; a `variants:` list naming each arm and its full text; a `why:` line. After the cards, three closing lines: `coverage:`, `excluded:`, `cost:`. Nothing else precedes or wraps the cards.

Every campaign report opens with four lines — `shape test: <skill> — <date>`, `entries:`, `artifacts:`, `manifest:` — then one block per rule — **every** rule, including no-failure, unresolved, and void rules, gets its own `## <entry-id> (<kind>) — <verdict>` heading, a table with one row per arm (arm name, marker counts, shape across reps), a `notes:` line, a `write-back:` line; then `no-failure (ablation review):` and `unresolved:` sections — indexes listing those same rules, never substitutes for the per-rule blocks — where applicable; and a final `summary: A adopted / N no-failure / U unresolved / V void (<total> rules)` line.

scored.json holds one object per entry covered: `id`, `kind` (`shaping`/`pattern`, matching the results), `result` (one of `adopted`, `no-failure`, `unresolved`, `void`), `adopted_arm` (exactly when result is adopted; a non-v0 arm present in that entry's results), `restraint_gate` (`pass`/`fail`, exactly when kind is pattern and result is adopted; `null` otherwise), optional `marker_counts` and `notes`. Every entry id in the results is covered exactly once — a missing, duplicate, or unknown id fails `shape-scored-check`. Example:

```json
[
  {"id": "R-styling-01", "kind": "shaping", "result": "adopted", "adopted_arm": "v2", "restraint_gate": null},
  {"id": "R-review-02", "kind": "pattern", "result": "adopted", "adopted_arm": "v3", "restraint_gate": "pass"}
]
```

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
- Before scoring any run, check its void signals: `skill-load-attempted` means the rep
  tried to load a skill instead of using the injected conventions — set it aside and
  re-run that arm before scoring it. There is no "not loaded" void: the conventions
  are in the prompt by construction, so a run can never fail for load reasons.
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
- [ ] Preflight green: python3 >= 3.10, `evaluator.py check --harness` (with `--model` when a model is set) exit 0; ONE workspace initialized with `--prefix shape-test`
- [ ] Workspace never synced (contamination gate clean); campaign dir created; entries.json, rules.json, the source skill dir, and skill-body.txt (via the documented pipeline — never hand-edited) snapshotted with the exact commands recorded
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
