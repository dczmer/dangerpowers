# Deterministic-vs-LLM Work Audit: The Four Testing Skills

Audit of `trigger-testing-skills`, `pressure-testing-skills`,
`shape-testing-skills`, and `retrieval-testing-skills`, looking for instances
where the LLM is doing work better suited to a deterministic script:
counting and math, complex conditional logic, writing output with strict
schema formats. `trigger-testing-skills` is the comparison baseline because
it was designed to separate these concerns as much as possible. Report
only — no changes were made.

## What the exemplar (trigger-testing-skills) actually delegates

Trigger-testing embodies the separation principle explicitly (SKILL.md
lines 15–19):

- **Scripts do:** looping, counting, splitting, scoring (Wilson-lower-bound
  in `evaluator.py`), manifest recording.
- **LLM does:** input resolution, failure categorization with cited
  evidence, description revision, report prose, go/no-go judgment.
- **Consumption rule:** exit codes + JSON only, never prose stdout.
- The score itself is never computed by the LLM; `totals.score` /
  `totals.failed` are read from JSON, and even winner selection is a
  documented one-line rule (highest score, ties → earlier iteration)
  applied over at most 3 numbers.

Residual mechanical work even in the exemplar (noted for fairness):

- **Planned-spend arithmetic** (step 5, line 44): `train_size × reps ×
  max-iterations + validate_size × reps + reps` is LLM arithmetic over two
  numbers read from JSON.
- **Sanity threshold math** (step 10, line 63): "triggered in ≥ 60% of
  non-void runs" over 3-ish reps is a small percentage calculation done by
  the LLM.
- **Report assembly**: the strict template (lines 118–138) is LLM-rendered,
  including the `(16 pass / 8 fail / 3 void)` counts.

So the exemplar's standard is: *judgment and prose to the LLM; counting,
scoring, and state to scripts — and where the LLM does touch numbers,
they're tiny and cross-checked by documented rules.*

---

## Findings

### 1. Inventory diffing is deterministic set logic, done by hand — pressure, shape, retrieval

- Pressure lines 114–116, shape lines 99–101, retrieval lines 71–76: the
  LLM rebuilds an inventory fresh, then diffs it against the persisted
  manifest with rules of the form "new → propose scenario; changed → flag
  re-test; deleted → propose pruning."
- The diff inputs are fully deterministic: fact/rule ids plus verbatim
  statement strings. String-equality diffing is exactly what a script does
  flawlessly and an LLM does sloppily (especially across a large body — a
  pressure inventory can be dozens of rules). A mis-diff silently misdrives
  the whole campaign: a "changed" rule misread as "same" never gets
  re-tested; a "deleted" misread as "changed" proposes scenarios for dead
  rules.

**Suggested fix:** add a `diff-manifest` helper (or fold it into
`evaluator.py`) that takes the fresh inventory and the old manifest and
emits `{new, changed, deleted, excluded}` JSON. The LLM still makes the
*proposals*; the *diff* becomes a script product. This is the single
highest-value mechanical extraction across the three skills — it's pure set
logic, it's repeated identically in three places, and errors are silent
rather than loud.

### 2. `scored.json` derivations are deterministic conditional logic, authored by the LLM — all three, worst in retrieval

- **Retrieval, line 253:** `ablation_flag = (control == pass)` — this is a
  derivable field, not a judgment. The LLM recomputes a boolean the script
  could set mechanically.
- **Retrieval, line 178:** "entry result = worst non-void run outcome (void
  only if every run is void)" — an ordered aggregation over a results
  array. That is complex conditional logic: filter voids, take min by a
  pass<fail<gap ordering, special-case all-void. The LLM must re-derive
  this per entry.
- **Retrieval line 253 / shape line 405:** conditional field presence
  (`missed_bullets` required non-empty for fail and gap, *absent*
  otherwise; `classification` iff result is fail; shape's `adopted_arm`
  exactly when adopted, `restraint_gate` null otherwise) — strict-schema
  JSON with presence rules written by the LLM.
- **Pressure lines 323–331:** the four verdicts are mechanically
  specifiable from evidence: red-complies → `no-failure`;
  green-passes-or-refactor-converges → `bulletproof`; 3 refactor rounds
  exhausted → `unresolved`; all red void → `void`. The LLM infers verdicts,
  then `pressure-scored-check` re-validates them post-hoc (lines 338–347)
  — evidence the verdict logic was considered mechanical enough to check,
  but it's still produced by the LLM first.

Note the pattern here: all three skills already have the validation half of
the solution (`scored-check`, `shape-scored-check`, `pressure-scored-check`).
The checks catch *inconsistent* output but not *wrong* output that happens
to be internally consistent (e.g., a wrongly-derived `ablation_flag:
false` when control passed passes every schema check).

**Suggested fix:** have each `*-scored-check`-adjacent script (or a sibling
generator) emit the deterministic skeleton — entry ids from the results
union, derived fields (`ablation_flag`, the worst-of aggregation, verdict
from arm presence + round counts), and the exact conditional key presence.
The LLM fills only judgment fields (classification, notes, counters'
content). The existing checks then become redundant backstops instead of
the primary correctness mechanism. Why: each of these is a small pure
function over JSON that is already fully specified in prose; specifying it
once in code eliminates an entire class of silent mis-scores.

### 3. Report count arithmetic is LLM counting, checked only conditionally — pressure, shape, retrieval

- Pressure report: per-arm "compliant count, cited count" per rule and
  `summary: B bulletproof / N no-failure / U unresolved / V void (<total>
  rules)` (lines 500–501).
- Shape report: per-arm marker counts and `summary: A adopted / N
  no-failure / U unresolved / V void` (line 403).
- Retrieval report: `summary: N pass / M fail / G gap / V void` (line 225).

In all three, the counts are later passed to the `*-scored-check
--bulletproof B ...` flags — but **only "when given"** (pressure line 347,
shape line 241, retrieval line 254). The LLM can omit the flags, or
transpose a digit into both the report and the flags such that the check
passes against the report while the report is wrong. Nothing currently
forces the report's numbers to equal the scored sums.

**Suggested fix:** make the counts-check unconditional given `scored.json`
(the script knows the four sums from the file it already reads), or have
the check script emit a machine-computed counts block the LLM copies
verbatim into the report. This matches the exemplar's spirit: `record`
reads the score from JSON, never from prose. Why: counting 4–40 items is
precisely where LLMs slip, and here the slip propagates into the
persistent manifest.

### 4. Cost-formula arithmetic in proposal cards — pressure, shape

- Pressure lines 163–166: `5 + 5 per failing baseline + 5×rounds per
  refactor (cap 3) + 1 meta per violating rep`, per-rule cap 25. The
  `cost:` closing line is LLM arithmetic over per-rule counts that won't be
  known exactly until mid-campaign (failing baselines are discovered, not
  known at proposal time — so the line is at best an estimate computed by
  formula).
- Shape lines 64–65 give an explicit worked example: `3×(5+15) +
  (5+15+10) = 90` — multiplication-with-parentheses LLM math, embedded in
  the skill text itself as guidance.

**Suggested fix:** a tiny cost helper (or accept as residue). The shape case
is bounded and pre-computable from the entries file, so a script could emit
the `cost:` number deterministically from `entries.json`; the pressure case
is genuinely contingent, so at minimum the formula should be rendered by
the script from actual run counts at spend-confirmation time rather than
restated by the LLM. Why: this is the same residue class the exemplar
accepted for planned spend (see exemplar residue above), but shape's
version is fully determined by inputs, so there's no excuse left.

### 5. Section-anchored id numbering is deterministic allocation — pressure, shape, retrieval

- Pressure lines 111–112, shape lines 126–127, retrieval line 221:
  rule/fact ids are `R-<section-slug>-<nn>` / `F-<section-slug>-<nn>`,
  numbered within each section.

Choosing slugs and per-section sequence numbers over a freshly-read body is
mechanical. Numbering errors (gaps, duplicates, off-by-one after an edit)
wouldn't be caught by any schema validation, and id stability across
campaigns is what makes the diff in finding 1 meaningful — a renumbered id
looks "deleted + new" instead of "same."

**Suggested fix:** fold id assignment into the inventory/diff script from
finding 1. Low-to-medium value individually, but essentially free once
finding 1 exists, and it makes the diff deterministic end-to-end. Why: id
stability is the load-bearing invariant of the whole manifest-diff design,
yet the ids are minted by the least reliable component.

### 6. Pattern-rule frequency comparison is counting + a threshold — shape

- Lines 334–336: "the winner's property frequency must **EXCEED** the
  control's — equal frequency means the rule is not binding."

`shape-evidence` already emits per-marker triage counts (lines 310–312).
Comparing two numbers with a strict-inequality test is deterministic
conditional logic sitting on top of numbers the script already computes.
The judgment part (what counts as the property being present, template
echoes vs. real hits) is rightly LLM; the comparison itself is not.

**Suggested fix:** have `shape-evidence` (or a flag on it) emit the
control-vs-variant frequency deltas so the LLM reads a computed comparison
instead of performing one over hand-counted hits. Why: a strict `>` vs `>=`
distinction decided by LLM arithmetic is a coin flip at the exact tie
boundary, and the tie boundary is the decision the rule exists for.

### 7. What was checked and deliberately *not* flagged

These are LLM work by design and consistent with the exemplar — flagging
them would be false positives:

- **Rule/fact classification and inventory building** (all three): genuine
  document judgment.
- **Choice + citation judging in pressure** ("never extracts the choice
  letter… read every answer," lines 319–321): judgment over free text;
  correctly left to the LLM with grep only as triage. Same for shape's
  convergence-by-reading and retrieval's rubric scoring.
- **Failure categorization with cited phrases in trigger** (lines 90–94):
  judgment with an evidence discipline.
- **Scenario/fixture/query/counter authoring**: creative judgment.
- **Meta-reply classification in pressure** (lines 372–380): three-way
  judgment call over free text — could theoretically be scripted, but the
  classification depends on semantics of the reply, so this is correctly
  LLM.

---

## Summary table

| # | Finding | Skill(s) | Type | Severity | Fix |
|---|---------|----------|------|----------|-----|
| 1 | Manifest diffing by hand | pressure, shape, retrieval | conditional logic | **High** | `diff-manifest` script |
| 2 | scored.json derivations (ablation_flag, worst-of, verdicts, key presence) | all three | conditional logic + strict schema | **High** | script-generated skeleton; LLM fills judgment fields only |
| 3 | Report count arithmetic, conditionally checked | pressure, shape, retrieval | counting | Medium–High | unconditional counts check / script-emitted counts |
| 4 | Cost formula math | pressure, shape | math | Medium | cost helper (shape fully scriptable; pressure at confirmation time) |
| 5 | Section-anchored id numbering | pressure, shape, retrieval | deterministic allocation | Medium | fold into finding-1 script |
| 6 | Property-frequency EXCEED comparison | shape | counting + threshold | Low–Medium | emit comparison from `shape-evidence` |
| — | Exemplar residue: planned-spend math, 60% sanity threshold, report template | trigger | math / schema | Low | acceptable as-is; note the bar |

## The one-paragraph takeaway

Against the exemplar's standard — scripts own counting, scoring, and state;
the LLM owns judgment, evidence, and prose — the three newer skills mostly
hold the line on *runtime* mechanics (suites, evidence extraction, pre-spend
gates are all scripted) but push three deterministic responsibilities back
onto the LLM: **diffing** (finding 1), **deriving scored.json fields and
verdicts** (finding 2), and **report arithmetic** (finding 3). All three
share a telling tell: each skill already ships a post-hoc `*-check` script
whose only job is to catch LLM errors in exactly these areas. The checks are
the diagnosis; the fix is to move the deterministic half *upstream* —
generate the skeleton and the counts in the script, and let the LLM supply
only the fields that require reading an answer. Findings 4–6 are the same
class at smaller scale.
