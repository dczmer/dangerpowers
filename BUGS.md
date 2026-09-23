## Shape Test Bugs

B1. inventory-mint gap — load_inventory requires id on excluded entries even in drafts, but mint only assigns ids to items; excluded ids must be hand-assigned, contradicting "ids are minted by the script".
B2. evidence --compare can't see v0 — suite writes control/variants to separate files, so compare prints "no v0 control arm; comparison skipped"; I merged a union file by hand to get the EXCEEDS verdicts.
B3. 120s timeout is uncalibrated for this endpoint — 53/70 empty-answer voids at 120s, 0/70 at 300s (kept as results-control-timeout120.json for the record).
B4. Marker gaps in entries.json (documented in report): decline_explicit misses "I am not producing…" phrasing; name_gerund misses verb-first names; inline_matrix_row undercounts backticked rows; template_blanks false-positives on --no-<name>/usage notation.
B5. Driver error (mine, disclosed in report): I dispatched the restraint gate and round-2 concurrently against the shared llama.cpp endpoint — 4/5 gate reps timed out; re-run serially, 5/5 clean.
B6. Made two campaign log directories for the same run: 2026-09-22 and 2026-09-22-2. (Superseded by B6 — no duplicate logs were made; the skill's layout section misuses the -2 suffix, and the mini-campaign dir should live inside the full-campaign dir.)
B7. No pre-spend way to check section-span drift at proposal time — the suite gate checks span uniqueness only after the campaign is built; add `suite --dry-run` or a `check` mode taking --entries/--skill-file. (Gap S1.)
B8. Campaign-file generation is driver-side — entries-failing/entries-restraint/round-2 contents are hand-built each campaign; add a `select`-style filtering subcommand (precedent: `split`). (Gap S6.)
B9. No end-of-campaign verification command — snapshot byte-identity, manifest↔entries wiring, span uniqueness, scored↔record consistency are hand-scripted; add `verify`/`doctor` complementing scored-check. (Gap S8.)

## Test script gaps

Ad-hoc driver-side Python required during the writing-skills shape campaign
2026-09-22 because the harness has no subcommands for these tasks:

S1. **Span-drift check** — verify every entry's `section` span occurs verbatim
   exactly once in the current skill body *before* committing to reuse a
   previous campaign's fixtures. Today only the pre-spend suite gate checks
   this, after you've already built the campaign.
S2. **Inventory construction/repair** — drafting the id-less inventory,
   restoring verbatim `statement` fields by id so `inventory-diff` goes
   silent, and repairing excluded-entry id→kind/reason mappings after
   renumbering. `inventory-mint` only assigns ids; it doesn't help fix
   them. (Partially addressed by B1: mint assigning excluded ids and
   skipping numbers used by either list removes the hand-assignment and
   collision-repair work. Drafting, verbatim statements, and semantic
   renumber detection remain driver work by design — B1 leaves those
   with the driver and inventory-diff.)
S3. **Results aggregation** — runs don't store marker counts (evidence
   computes them on the fly), so per-arm pooled triage, void/timeout
   summaries, and cross-arm comparison all need custom parsing of
   results-control/results-variants. (Mostly addressed: cross-arm
   comparison by B2's multi-file --compare; per-arm/per-rep triage by
   B4's proposed evidence --matrix, which per the B4 update below also
   carries per-arm void-signal and timeout counts. No residual once
   B2/B4 land.)
S4. (ADDRESSED WITH B2) **Compare-union merge** — `evidence --compare` requires the v0 control arm
   in the same results file, but `suite` writes control and variants to
   separate files; the driver must merge a union JSON to get EXCEEDS
   verdicts. (Filed as B2 below; this gap closes when B2 is fixed.)
S5. **Hand-read assists** — extracting the flagged samples for reading
   (table rows, frontmatter heads, second-file detection, blank-token
   extraction, mermaid blocks) rather than dumping whole answers.
   (By design, not a pending gap: hand-reading is the skill's scoring
   judgment — "grep is triage, not verdict." B4 fixes A/B reduce the
   volume of reading; no harness plan should eliminate the reading
   itself. Permanent driver responsibility.)
S6. **Campaign file generation** — `suite` consumes but never produces
   entries files: entries-failing.json, entries-restraint.json, and
   round-2 mini-campaign dirs (changed-form variants + snapshot copies)
   are all driver-built.
S7. **scored.json judgment filling** — the skeleton pre-fills
   marker_counts and nulls; mapping hand-read verdicts into
   result/adopted_arm/restraint_gate/notes is manual. (By design, not
   a pending gap: filling judgments IS the driver's scoring act. The
   skeleton already pre-fills everything mechanical. Permanent driver
   responsibility.)
S8. **End-of-campaign verification** — byte-identity of snapshots vs
   canonical files, manifest↔entries rule-id wiring, span uniqueness vs
   skill-body.txt, scored↔manifest-record consistency.

The pattern: the harness covers staging, gating, and recording (check,
suite, scored-check, record), but the whole middle — fixture viability,
triage aggregation, cross-file comparison, verdict filling, and final
consistency proof — has no subcommands, so the driver carries it with
throwaway scripts.

## B1. (RESOLVED) Inventory-mint gap

Investigated 2026-09-23 against current harness code and skill docs
(legacy .tmp artifacts disregarded as pre-date the current process).

Root cause — two functions in `tools/test-harness/evaluator.py` disagree
about what a valid draft looks like:

- `load_inventory` (line 536) requires every `excluded` entry to carry an
  `id` unconditionally, even with `allow_idless=True`. Only items get the
  idless exemption (line 573); excluded validation (line 584) has no escape
  hatch.
- `cmd_inventory_mint` (line 668) only assigns ids to items. It builds its
  per-section used-number set from items only (lines 681-687) and never
  looks at `excluded`.

So the documented workflow — "draft the inventory id-less, then run
inventory-mint" (stated in the shape, pressure, and retrieval skill docs)
— fails on any draft with excluded entries, which is every real draft.

Worse than rejection: mint can silently corrupt. Because it ignores
excluded ids when numbering, it can mint an item id that duplicates an
existing excluded id in the same section. Reproduced:

    draft: item (idless) + excluded "R-content-01" in section "Content"
    → minted item id: R-content-01      (collision!)
    → inventory-check: error: duplicate id: R-content-01

The failure surfaces at the next command, not at mint time, pointing at a
file the driver didn't hand-edit. Drivers then "fix" it by hand-assigning
ids — exactly what the section-anchored numbering scheme exists to prevent
(humans get the within-section document-order interleaving wrong).

Exposure by track: shape (rules.json) and pressure (rules.json) always
exclude routed rules; retrieval (facts.json) always records dropped facts
— note retrieval's excluded entries carry no `kind` field, so a fix must
not require one. Trigger uses no inventory (`inventory_kind = None`) and
is unaffected.

Suggested fix, uniform across both kinds: (1) build mint's used-number
set from both items and already-ided excluded entries — this alone kills
the collision; (2) walk `excluded` after items and mint id-less entries
with the same `mint_inventory_id` scheme; (3) preserve the byte-identical
no-op guarantee so re-mint stays silent and inventory-diff trustworthy;
(4) no kind special-casing needed — the R/F prefix comes from
`INVENTORY_KINDS`, and excluded entries need no kind/entries/statement.
Add tests in tools/test-harness/tests/test_inventory.py: id-less excluded
get section-anchored ids; numbers already used by either list are
skipped; the collision repro yields distinct ids passing inventory-check;
re-mint is byte-identical; fact-kind excluded mint without a kind field.

Residual gap deliberately not addressed: mint cannot detect semantic
renumbering mistakes (hand-assigned old ids attached to the wrong rules) —
that remains inventory-diff's job at proposal time, which is the right
place for it.

## B2. (RESOLVED) Evidence --compare can't see v0

Investigated 2026-09-23 against current harness code.

Root cause — a mismatch between the campaign workflow and the evidence
CLI, not the comparison logic:

1. The workflow mandates separate files: phase 1 `suite --arms v0` ->
  results-control.json; phase 2 `suite --arms v1,v2,v3` on failing
  entries -> results-variants.json; a restraint gate is a third
  invocation (--fixture-key counter-example). The spend confirmation
  between phases makes a single combined invocation impossible by design.
2. evidence reads exactly one file: --results is a single string
  (evaluator.py:853); shape.print_evidence does Path(args.results) ->
  load_results_json on that one path (shape.py:610-611).
3. --compare looks for the v0 arm inside that one file
  (_print_shape_compare, shape.py:343-352). A variants-only file prints
  "no v0 control arm; comparison skipped" and exits 0 — a silent skip,
  not an error. This is worst for pattern rules, where the skill names
  the with/without-control frequency comparison the primary detector, so
  the driver must hand-merge a union JSON.

The fix mostly already exists: union_results (common.py:237) merges N
results files per entry id with a per-track entry_hook;
_shape_union_hook (shape.py:364) already validates arms/kind consistency
and sums duplicate-arm occurrences across files (its docstring names the
restraint-rerun case); scored-check already accepts repeated --results
(action="append", evaluator.py:867) gated by track.multi_results with
the reusable error message "exactly one --results file is valid with
--track <name>" (evaluator.py:417-420). Only evidence is single-file.

Suggested fix, shape-scoped and minimal:

1. Parser: make evidence --results action="append", mirroring
   scored-check.
2. cmd_evidence: for any non-shape track require exactly one file and
   pass it through as a plain string — trigger/retrieval/pressure
   behavior stays byte-for-byte (all four print_evidence implementations
   do Path(args.results) today; none need changes).
3. shape.print_evidence: with multiple files, merge entries by id
   (first-appearance order = union_results semantics); merge arms dicts,
   concatenating duplicate arm keys' run lists in file order with a
   printed note — matching what _shape_union_hook already does for
   scored counts, so evidence and scored-check agree on what an arm's
   evidence is. Single-file invocation keeps the current code path.
4. Config-drift warning: if merged files' config blocks differ on
   model/variant/reps, print a warning naming the differing keys — runs
   must stay attributable to the exact model selection that produced
   them.
5. Fixture-key guard: results-restraint.json carries
   fixture_key: counter-example under the same arm key (v2) as
   application-fixture runs; silently pooling them would contaminate the
   property-frequency comparison. Rule: merge an arm across files only
   when config.fixture_key matches; otherwise keep the runs visible
   under a suffixed display key (e.g. v2@counter-example) that --compare
   never treats as the same arm.

Tests to add: union of control+variants yields EXCEEDS/does-not-exceed
lines per candidate arm; single variants file still prints the skip
note; multiple --results on a non-shape track fails with the
scored-check message; duplicate arm across files concatenates with a
note; fixture-key mismatch disambiguates and is excluded from compare.

Conflict check: trigger/retrieval untouched (single-file, no
--compare/--arm); pressure keeps single-file evidence with the same gate
message (multi_results is for scored-check only); scored-check/record/
suite untouched — the union semantics are the ones _shape_union_hook
already implements, so the commands stay consistent by construction.
Skill doc touch-up after the fix: shape-testing-skills step 13 can show
--results control --results variants --compare.

Resolves "Test script gaps" item 4 (compare-union merge) once fixed.

Implemented 2026-09-23 as suggested, plus review amendments:

- `evidence --results` is now `action="append"`; cmd_evidence gates
  non-shape tracks to exactly one file with the scored-check message and
  passes their printers a plain string, so trigger/retrieval/pressure are
  byte-for-byte unchanged (evaluator.py).
- shape merges N files by entry id in first-appearance order
  (_merge_shape_results, shape.py): same-fixture_key arms pool their runs
  with a stderr note; fixture-mismatched reruns stay visible under
  `vN@<fixture-key>` and are never --compare candidates; config drift on
  model/variant/reps/timeout warns on stderr naming the differing keys
  (date excluded — it always differs).
- The "no v0 control arm" skip note moved to stderr so a scripted
  --compare pipeline cannot mistake the silence for a clean comparison;
  the exit stays 0.
- Deliberate asymmetry, documented in _merge_shape_results and skill
  step 15: scored-check's union still pools same-named arms
  unconditionally (the driver narrows the skeleton by hand) — pushing the
  fixture-key guard into scored-check would change the recorded
  marker_counts schema, so the guard lives in evidence where the
  frequency comparison happens.
- Tests: union compare verdicts, same-fixture concatenation with note,
  fixture-key disambiguation excluded from compare, config-drift warning,
  kind-mismatch error, non-shape multi-results rejection, skip note on
  stderr (test_shape.py ShapeEvidenceMergeTests, test_trigger.py).
- Skill doc: step 13 and the evidence paragraph show the multi-file
  invocation and merge semantics.

## B3. Default timeout too low for local endpoints

Symptom: at the documented 120s default, shape campaigns against the
local llama.cpp endpoint (llama.cpp/gemma-4-26B-A4B) drown in
empty-answer timeout voids under the suite's 10-way per-arm concurrency —
53/70 control reps voided at 120s vs 0/70 at 300s (writing-skills
campaign 2026-09-22; calibration files kept as
results-control-timeout120.json). The shape skill's gotcha already records
the same observation from earlier calibration (2 empty-answer voids at
120s, 0 at 300s). These are endpoint-latency artifacts, not agent
defects, but they burn spend and can void-score clean runs.

Where the defaults live (evaluator.py + tracks): suite deliberately has
no parser default — a code comment (evaluator.py:795-797) explains that a
parser default would flatten the four tracks' distinct historical
defaults, so each track applies its own in pre_spend_gates:
shape.py:454, pressure.py:260, retrieval.py:265 all default 120;
trigger.py:373 defaults 30. The standalone `run` command defaults 30
(evaluator.py:773) and `meta` defaults 120 (evaluator.py:887).

Fix: make 300s the default timeout everywhere --timeout is accepted —
the suite track defaults above, plus run and meta. Note the tension with
the evaluator.py:795-797 design comment: prefer updating each track's
pre_spend_gates default (or introducing a shared DEFAULT_TIMEOUT
constant the tracks reference) over a parser-level default, preserving
the per-track-defaults architecture; either way the parser comment needs
updating so the next reader doesn't "restore" the split. Trigger's 30s
may warrant a smaller bump (its queries are short single-shot loads) —
decide per track by measured latency, not symmetry; the calibration
evidence covers shape/retrieval-style workloads.

Secondary improvement (optional): emit a calibration hint when a suite
finishes with >20% empty-answer timeout voids, pointing at --timeout —
the 120s failure mode is silent until scoring and wastes a full phase.
Relationship to B5: complementary and independent — a higher timeout
reduces per-rep latency sensitivity but is not a license for concurrent
suites.

## B4. Marker gaps in shape-test triage

Investigated 2026-09-23 against writing-skills campaign 2026-09-22
results; all four sub-gaps reproduced and measured.

Markers are driver-authored line-regexes in entries.json. The harness
gate is compile-only (_check_marker_tokens, shape.py:39-52); nothing
checks that a wrong-shape marker fires on real failures or that a
right-shape/property marker stays silent on compliant output.
marker_triage_counts (shape.py:303) is a per-line re.search — no file
scope, no context. "Grep is triage, not verdict" contained the damage to
verdicts (hand-reads), not to triage quality, phase-gating signal, or
the --compare EXCEEDS detector that pattern rules rely on.

The four gaps, measured:

1. decline_explicit — false negatives on the converged phrasing
   (severe for pattern detection). Marker
   (?i)(i (won't|can't|cannot|decline)|not going to|instead,|however,
   i|forbidden|violates). v2 arm declined 5/5 by hand-read; the marker
   caught 1/5. The dominant phrasing "I am not producing a fill-in-the-
   blank template… as these violate / the conventions prohibit / the
   conventions forbid…" trips nothing: violate != violates,
   prohibit/forbid/precludes unlisted, "I am not producing" absent.
   --compare measured control at 0.0 (2/5 control reps did verbally
   decline) and v2 at ~2 lines instead of 5/5 reps — direction survived
   here, but a variant declining 2/5 with marker-visible phrasing would
   look identical to one declining 5/5.

2. name_gerund — false negatives on compliant verb-first names.
   Marker ^name: [a-z]+ing(-|$) scored 0 on the compliant
   "name: profile-postgresql-queries" (rule allows gerund OR verb-
   first). One-sided: also never catches the actual failure mode
   (noun-first like sql-query-profiler). Right-shape signal
   systematically undercounts; verdicts only held via hand-reads.

3. inline_matrix_row — backtick undercount plus cross-file false
   positives (worst). Marker ^\| ?(get|list|watch|...) ?\|. Control
   reps 1,2,3,5 had 8-12 matrix rows each, 100% backticked first cells
   (| `get` |) -> 0 marker hits; only the unbackticked rep4 tripped.
   Marker reported "1/5 flagged" where hand-read showed 5/5 full-matrix
   inlining — severity actively hidden. Separately, the marker counts
   rows across the whole answer including the companion
   references/*.md file, where a table is the CORRECT shape: v2's 22
   pooled hits vs v3's 11 conflated correct placement with wrongful
   inlining, inverting apparent severity (actual extraction v2 4/5,
   v3 3/5). No line-regex can scope to file sections.

4. template_blanks — ~100% false-positive rate on this fixture domain.
   The <[-_a-zA-Z0-9 ]+> alternative tripped on <name> from --no-<name>
   convention notation in every v2 rep, and on <subcommand>, <arg1>,
   <category> etc. inside complete worked examples (standard CLI usage
   syntax). Pure noise as a wrong-shape signal for CLI-flag fixtures.

Root causes: (a) process — markers are authored once and frozen; no
calibration step exists even though phase-1 controls plus prior
campaigns' results JSONs provide free real samples; note the skill's
verbatim-freeze list covers fixtures, variant texts, and section spans —
NOT markers, so amendment between campaigns is legitimate; (b)
capability — line-regexes can't express file scope (3b), exclusion
lists drift (4), or per-model phrasing drift (1-2).

Suggested fixes, layered:

A. Process — marker calibration at proposal time (no harness change):
after building the proposal and before spend, run every marker against
prior-campaign results (or pilot reps); require each wrong-shape marker
to fire on >=1 known-bad sample and each property marker to stay silent
on known-good samples. Amend entries.json before snapshot; freeze for
the campaign.

B. Harness — a compact marker x rep hit matrix (formalizes "Test script
gaps" item 3): e.g. evidence --matrix, one row per entry/arm with
per-rep hit counts per marker, so a never-firing wrong-shape marker or
an always-on right-shape marker is visible at a glance. The matrix must
also carry per-arm void-signal and timeout counts — that closes the
void/timeout-summary part of gap S3 as well (the 2026-09-22 driver
wrote a custom summarizer for exactly this to diagnose B3). Shape-scoped;
no conflict with trigger/retrieval/pressure.

C. Regex amendments for the next entries.json revision (writing-skills
shape-tests; same classes apply to other shape inventories):

   - decline_explicit — broaden to the semantic act:
       (?i)(i am not (producing|providing|creating)|i (won't|will not|
       can't|cannot) (produce|provide|create)|\bforbid|\bprohibit|
       violate|preclud)
     Apply the same broadening to the entry's restraint_markers (the
     gate passed trivially on the narrow pattern).

   - inline_matrix_row — tolerate backticked first cells:
       ^\| ?`?(get|list|watch|create|update|patch|delete|
       deletecollection|impersonate|bind|escalate|use)`? ?\|
     Fixes the pure-regex class only.

   - template_blanks — drop the bare <...> alternative, or gate angle
     brackets behind strict template signals:
       (\{\{|REPLACE_ME|\bTODO\b|PLACEHOLDER|<insert|YOUR_[A-Z])
     Angle-bracket usage tokens cannot be distinguished from template
     blanks by line-regex.

   - name_gerund — keep for gerunds and document the verb-first
     undercount (regex can't morphology-tag); optionally add a
     noun-first failure marker with nominal suffixes as heuristic
     triage:
       ^name: [a-z0-9-]*(profiler|formatter|handler|parser|builder|
       wrapper|manager|helper|utility|tool)(-|$)

   - Gap 3b (file scope) has no regex fix: either apply wrong-shape
     markers only to the portion before the first references/*.md path
     header (driver convention) or note in the skill that multi-file
     entries require section-scoped hand-reads.

D. Skill-doc touch-up: add gotchas for the observed false-positive
classes (convention-notation tokens, correct-shape-in-second-file,
per-model phrasing drift) and state the calibration expectation in the
entries/marker section.

No conflicts with other tracks: markers are a shape-track concept only
(retrieval scores rubric expectations, pressure scored-signals, trigger
outcomes); A-D are shape-scoped.

Application note (2026-09-23): the amendments in C are recorded here
ONLY — not applied to
skills-workspace/writing-skills/shape-tests/entries.json. That file is
campaign-frozen (campaign-2026-09-22 measured it as-is; the skill's
freeze list plus the no-mid-campaign-fix rule cover the current
campaign, and prior campaigns' results JSONs remain the calibration
baseline). When the next writing-skills shape campaign is proposed, an
agent should: run fix A's calibration against the prior campaigns'
results, apply the applicable C amendments to entries.json at proposal
time (before snapshot), and freeze them with the fixtures for that
campaign. Do not hand-edit markers between campaigns outside that
proposal step.

## B5. Concurrent suites voided the restraint gate

Observed 2026-09-22 (writing-skills shape campaign, driver error).
The restraint gate (suite --arms v2 --fixture-key counter-example, 5
reps) and the round-2 mini-campaign (suite --arms v1, 10 reps) were
dispatched in the same message, concurrently. Each suite batches reps
at up to 10 workers against the single local llama.cpp endpoint, so
the endpoint saw ~20 concurrent requests: 4/5 gate reps returned
empty-answer voids at 300s (results-restraint-timeoutvoids.json). Re-run
serially: 5/5 clean. The voided file looks exactly like an agent defect
— the failure mode is silent and misattributable.

Root cause: the shape skill owns serialization discipline but only
within one suite invocation — "one entry, one arm at a time; only reps
within one arm batch parallelize" (Quick ref lines 66-68; suite
mechanics line 277). The restraint gate and round-2 are separate suite
processes, and nothing says only one suite may be in flight at a time.
The skill's timeout gotcha (line 454) contains the mechanism
("concurrent reps share one endpoint, so per-rep latency rises with
parallelism") but frames it as a reps-within-a-batch phenomenon and as
a reason to raise --timeout — which pointed at the wrong lever (see B3:
no per-rep timeout absorbs 2x concurrency on a saturated endpoint).

Agreed fix (2026-09-23): harden skills/shape-testing-skills/SKILL.md —
no harness change. Four edits:

1. Quick reference, Serialization bullet — extend from
   arms-within-a-suite to suites-within-a-campaign: never run two
   suite invocations concurrently (restraint gate alongside a round-2
   mini-campaign, or any two suites against the same endpoint); each
   suite already batches up to 10 reps, and concurrent suites multiply
   per-rep latency into empty-answer timeout voids that misattribute as
   agent defects. One suite process at a time, for the whole campaign.
2. Workflow step 13 (restraint gate) — add: run only after the
   variants suite has fully exited; never concurrently with any other
   suite invocation (Serialization).
3. Workflow step 14 (round-2 mini-campaign) — same sentence.
4. Gotchas — add the observed instance (4/5 gate reps voided at 300s
   concurrently, 5/5 clean serially, 2026-09-22), noting that
   "serially" includes across processes: check the previous suite
   exited before launching the next.
5. Checklist — add: every suite invocation ran one at a time; restraint
   gate and round-2 never overlapped.

Scope: the same principle applies to any track whose suites batch reps
against a shared endpoint (pressure, retrieval — same harness, same
batching); this entry fixes the shape skill where the failure was
observed. Hardening the pressure/retrieval skills is an optional
follow-up, recorded here so it is not lost.

Relationship to B3: complementary and independent. B3 (default timeout
300s) reduces per-rep latency sensitivity; it is not a license for
concurrent suites. Do not conflate the two fixes — a future agent
applying B3 must not read it as permission to parallelize suites.

## B6. Campaign layout misuses the -2 suffix; mini-campaigns belong inside the full-campaign dir

Surface report (2026-09-22 campaign): "made two campaign log
directories for the same run: 2026-09-22 and 2026-09-22-2."
Investigation (2026-09-23) found no duplicate logs: campaign-2026-09-22-2
holds the round-2 mini-campaign (2 filtered entries with changed-form
variants + its results + snapshot copies), and the shape skill's
Campaign layout section explicitly sanctions top-level
campaign-YYYY-MM-DD-2/ for mini-campaigns. The driver followed the doc.

The doc is wrong. Intended convention (user, 2026-09-23): the -n suffix
exists to support multiple FULL campaigns run on a single day — not to
separate rounds within one campaign, and not to hold mini-campaigns.
Campaign directories are for full campaign runs: one campaign dir per
full run, with subdirectories inside it when separation between
campaign artifacts is needed (round-2 mini-campaigns, post-write-back
confirmation runs).

Fixes to apply:

1. skills/shape-testing-skills/SKILL.md, Campaign layout section:
   replace the top-level campaign-YYYY-MM-DD-2/ mini-campaign entry
   with subdirectories of the single campaign dir, e.g.:
       campaign-YYYY-MM-DD[-n]/      # -n = nth FULL campaign that day
       ├── ... (existing full-run artifacts)
       ├── round-2/                   # mini-campaign: filtered entries +
       │   │                          # changed-form variants + results
       │   └── ...
       └── confirm/                   # post-write-back confirmation
           └── ...                    # mini-campaign; never recorded
   State the one-dir-per-full-run rule and the -n meaning explicitly.

2. Repo state: move campaign-2026-09-22-2/ to
   campaign-2026-09-22/round-2/ and update the two references in
   campaign-2026-09-22/report.md (references-one-level-deep and
   flowchart-table-list-selection blocks). The voided first-attempt
   restraint files stay in the main dir (same run, same phase).

3. Same-day full campaigns keep the incrementing suffix (e.g. a second
   full campaign on 2026-09-22 would be campaign-2026-09-22-2/) — after
   fix 1 the suffix is unambiguous because mini-campaigns no longer
   live at top level. The .tmp 2026-09-14 series used -2 for round-2
   and -3 for confirmation; that usage is legacy, do not imitate it.

4. Check the pressure/retrieval/trigger skill layout sections for the
   same wrong convention and apply the same rule (recorded here so it
   is not lost; shape is where the failure was observed).

5. Optional harness hardening: with mini-campaign results in
   subdirectories, the natural-glob hazard (campaign-*/results-*.json
   pulling in mini-campaign files) mostly disappears, but
   union_results (scored-check today, evidence --compare under B2)
   still silently sums same-named arms from different files. An
   exact-dir equality guard on unioned files (all --results paths in
   the same directory, else an exact error naming the dirs) costs the
   legitimate same-dir unions nothing and blocks cross-boundary
   pooling, including round-2 subdir files.

The never-recorded rule for mini-campaigns is unchanged; only their
location moves.

## B7. No pre-spend way to check section-span drift at proposal time

Gap S1. When reusing a previous campaign's fixtures, the driver must
verify that every entry's `section` span still occurs verbatim exactly
once in the current skill body BEFORE committing to the fixtures —
otherwise the campaign is built on spans the suite will reject. Today
only the suite pre-spend gate checks span uniqueness (doc drift aborts
before spend), which is too late: by then the campaign dir, entries,
and proposal are already built.

Observed 2026-09-22: the writing-skills driver wrote a one-off Python
check for this against the .tmp entries before rebuilding the
inventory; without it, drift would have surfaced at the suite gate
after all setup work.

Suggested fix, shape-scoped (the span assertion is a shape-track
concept; pressure/retrieval do not match section spans): add a no-spend
span check to the harness, either as `suite --dry-run` (run the
pre-spend gates including the section-span assertion, dispatch
nothing) or as a dedicated mode on `check` taking --entries and
--skill-file. Exit 0 with a per-entry occurrence report; exit 1
naming the first span that is missing or duplicated. This is the
cheapest of the B-series fixes and removes a whole class of
late-discovery aborts.

## B8. Campaign-file generation is driver-side

Gap S6. `suite` consumes but never produces entries files. Every
campaign the driver hand-builds: entries-failing.json (filter to
control-failing rules), entries-restraint.json (filter to pattern
winners), and the round-2 mini-campaign contents (per B6's layout:
campaign-dir/round-2/ with filtered entries carrying changed-form
variants, plus the rules/skill-body/skill snapshot copies the pre-spend
gates require). All were ad-hoc Python in 2026-09-22.

Suggested fix: one small file-shaping subcommand, e.g.
`evaluator.py select --entries in.json --ids rule-a,rule-b --out
out.json` — pure filtering plus optional pretty-print; precedent is the
existing `split` command for trigger queries. Keep changed-form variant
authoring driver-side (it is judgment, not filtering); the subcommand
only filters and copies. Track-agnostic: entries-file schema is shared
across shape/pressure, and retrieval's queries file can use the same
mechanism.

## B9. No end-of-campaign verification command

Gap S8. Before `record`, the driver must verify: (1) campaign
snapshots byte-identical to the canonical rules.json/entries.json;
(2) manifest<->entries wiring (every entry's rule id exists and that
rule's entries array names exactly this entry); (3) every section span
occurs exactly once in skill-body.txt and skill-body.txt matches the
source SKILL.md with frontmatter stripped; (4) scored.json verdicts
consistent with the track record about to be written. All four were
hand-scripted in 2026-09-22.

Suggested fix: a `verify`/`doctor` subcommand —
`evaluator.py verify --manifest rules.json --entries entries.json
--scored scored.json --results <files...> --campaign-dir <dir>` —
running the four checks above and printing ok/error lines, exit 1 on
any failure. scored-check already covers scored<->results consistency,
so verify covers only what scored-check does not (file identity,
wiring, spans) and should call or mirror scored-check rather than
duplicate it. Track-agnostic where cheap: wiring/identity checks apply
to shape and pressure; retrieval's manifest<->queries wiring is the
same shape with facts.json.
