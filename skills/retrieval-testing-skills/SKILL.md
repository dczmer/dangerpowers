---
name: retrieval-testing-skills
description: Use when the user asks to run a retrieval test or retrieval-testing campaign against a reference skill, verify that agents can find and correctly apply documented facts, or surface gaps and unclear sections in a reference doc. Runs task-shaped eval queries from a queries file through headless harness runs in sterile temp workspaces (skill arm plus an uncontaminated control arm) and reports per-fact pass/fail with failure classifications.
disable-model-invocation: true
metadata.opencode/slash: true
metadata.opencode/autoinvoke: false
---

# Retrieval Testing Skills

## Overview

Run one retrieval-test campaign for a reference skill against a file of eval queries and report the results. Reference content has no rule to violate, so there is nothing to pressure-test: each scenario checks that a fresh agent can find a documented fact and apply it, one run per scenario, and failures are doc failures — fixed by editing the doc, never by adding rules.

The skill under test is force-loaded by instruction in every scenario. Retrieval testing measures the skill *body*; whether the description triggers at all is the separate trigger-testing track.

Scope rules, up front:

- "Does the skill trigger for query X?" is a **trigger-testing** question — wrong track, do not run retrieval scenarios for it.
- A skill whose fact inventory is empty — the doc records no facts — needs **no** retrieval testing; stop instead of fabricating queries.

Staging, capture, validation, and manifest recording live in `tools/test-harness/` (`workspace-manager.sh`, `evaluator.py`), invoked from this skill's resolved directory. Consume exit codes and JSON from those scripts only — never parse their prose stdout.

## Inputs

Collect all inputs before starting. Prompt the user for any that are missing.

- **Skill name or path** — the reference skill under test. Accept either a path or a bare name: a path is used directly; a name is resolved against the known skills roots. From the resolved location, derive the **source root**: the directory containing the `skills/` directory the skill lives in — not necessarily the repo root (for `<root>/.opencode/skills/<name>`, the source root is `<root>/.opencode`). The harness measures the bytes on disk, so whether the driving session can load the skill is irrelevant.
- **Harness** — required, user-specified (e.g. `opencode`). It selects the eval strategy: the binary, the agent-file suffix, and the install location. There is no default.
- **Queries file** — path to a populated `queries.json`. Default convention: `<source-root>/skills-workspace/<skill>/retrieval-tests/queries.json`, so test artifacts live next to the skill under test, wherever it is registered.
- **Facts manifest** — path to the persisted fact inventory, `facts.json`. Default convention: `<source-root>/skills-workspace/<skill>/retrieval-tests/facts.json`, next to the queries file (see Fact inventory).
- **Model / variant** — optional passthroughs to the harness run, and the only model-selection path: the eval agents pin no model config, so sweeps measure what they claim.
- **Reps** — runs per entry per arm; default 1.
- **Timeout** — per-run abort, in seconds; default 300.

After resolving the source root, read the skill under test fully and build the fact inventory fresh from the current doc (see Fact inventory) — the manifest is a diff baseline, never a cache. If the inventory is empty — the skill documents no facts — stop: retrieval testing is not required. Otherwise diff the inventory against the manifest (see Fact inventory for the diff rules) and present a proposal for whatever the diff requires (see Proposal format). With the user's approval, apply the changes to the queries file — creating any fixtures new entries reference under `fixtures/` and regenerating `facts.json` via `inventory-mint --carry` at the same time — and explain each generated entry: the documented fact it covers, why you chose that query, and why you chose those expectations.

## Fact inventory

A fact is a body statement that changes an agent's output if unknown. Keep a statement if it passes one test:

- **directive** — prescribes or prohibits: "never passive phrasing"
- **threshold** — an unguessable number or limit: "<500 lines"
- **taxonomy** — a classification or mapping: "tables for reference data"
- **structure** — requires or forbids a document element: "include a Gotchas section"
- **routing** — where something goes instead: "durable facts → AGENTS.md"
- **scope** — when the technique does or doesn't apply: "don't create for one-offs"
- **assumption-correction** — reverses a competent default: "spell out what a frontier model does implicitly"

Drop rationales, restatements, illustrative examples, and transitions. **Frontmatter-convention guidance is always out of scope** — never list a frontmatter rule as a testable fact.

Dedupe repeated rules; mine their examples for query material. Cluster facts a single task-shaped query naturally elicits into one entry; the facets become rubric bullets. Derive each query from the failure mode — what the agent does wrong without the fact — shaped as bait (a request that asks for the violation) or review (text already committing it).

### Facts manifest

Persist the inventory as `facts.json` next to the queries file: fact id, home section, statement, covering entries, and exclusions with reasons — nothing else. Never duplicate query text or expectations into the manifest; the queries file is the single source for verbatim queries.

```json
{
  "skill": "acme-api",
  "generated": "2026-09-11",
  "facts": [
    {"id": "F-uploads-01", "section": "Uploads", "statement": "reads Retry-After, value interpreted as seconds", "entries": ["retry-after-header"]}
  ],
  "excluded": [
    {"id": "F-errors-01", "section": "Errors", "reason": "restates the HTTP spec; baseline knowledge"}
  ]
}
```

A fact may carry `status` (`"ablation"` or `"removed"`) plus `ablation_streak` (int ≥ 0, required exactly when `status` is present). `status: "ablation"` marks a removal candidate under measurement; `status: "removed"` means the fact text is already deleted from the source SKILL.md — the inventory item and its entries persist purely as regression coverage. A query runs control-only only when EVERY fact covering it (via the facts' `entries` lists) carries the same status; mixed-status or partially-normal queries run both arms as before.

The manifest is a diff baseline, never a cache — rebuild the inventory fresh from the doc every campaign, drafted id-less: ids are minted by `inventory-mint` (`evaluator.py inventory-mint --inventory <draft> --kind fact --carry <old canonical> --out <canonical>`), never assigned by hand. `--carry` carries status forward into the regenerated manifest: surviving ids keep their `status`/`ablation_streak`; old items with `status: "removed"` whose id is absent from the draft are re-appended verbatim (a removed fact is gone from the doc, so the fresh draft never contains it); dropped ablation/status-less items are NOT re-appended — the normal `deleted` diff bucket handles them. Regenerate the manifest via the script at proposal time and whenever entries are added or retired; never hand-maintain it between campaigns. Re-running `inventory-mint` on an unchanged file is a byte-identical no-op, which is what makes the diff trustworthy. Each campaign's diff against the previous manifest — the `inventory-diff` JSON (`--old`/`--new`/`--kind fact`), read by you, not computed by hand — drives the work:

- New fact (no manifest id) → propose queries.
- Changed fact (same id, different statement) → flag its entries for re-scoring this campaign; queries stay verbatim.
- Deleted fact → propose pruning its entries; a query testing an undocumented fact measures nothing.
- Removed fact (`status: "removed"`) → keep its entries, labeled regression coverage, and never propose pruning them; proposal cards show `status`/`ablation_streak`.

## Query file format

Each entry tests one fact cluster:

```json
[
  {
    "id": "retry-after-header",
    "query": "Given this upload function — `def upload(path, url): return requests.post(url, data=open(path, 'rb'))` — add retry handling for 429 responses and return the complete updated function inline.",
    "expect": [
      "reads the Retry-After header rather than using a fixed backoff",
      "interprets the value as seconds",
      "does not retry on other 4xx codes"
    ]
  },
  {
    "id": "upload-script-review",
    "query": "Review {RUN_DIR}/upload.py for the retry behavior you would add for 429 responses, and report the complete updated function inline.",
    "expect": [
      "reads the Retry-After header rather than using a fixed backoff",
      "interprets the value as seconds"
    ],
    "fixtures": ["upload.py"]
  }
]
```

- `id` — stable fact identifier; never reuse ids across facts.
The query asks for the task; only the rubric names the expected behavior.

### Fixtures

Default to inline, self-contained queries. "Rewrite the upload script" is not a test if there is no script for the agent to find — but a large file or multi-file state can be impractical to embed, and then the query references a fixture instead.

Store canonical fixtures under `fixtures/` next to the queries file. Staging is scripted, not improvised: the harness gives each run its own run directory inside the eval workspace — `<workspace>/fixtures/<entry-id>/<arm>` (suffixed `-repN` when reps > 1) — copies the entry's fixture files in fresh, and substitutes that run-specific path for `{RUN_DIR}` in the dispatched query. No two runs ever share a fixture file, and no run ever writes into the repository: the eval workspaces are disposable temp directories, never the repo.

Per-run path substitution is isolation mechanics, not query editing — the task text stays verbatim across campaigns.

Entries declare fixtures as a `fixtures` list of filenames, each existing under a `fixtures/` directory next to the queries file — required exactly when the query contains `{RUN_DIR}`: the harness rejects a token without a fixtures entry and fixtures without a token before any spend.

## Eval agents

Eval runs execute under two restricted agent definitions in this skill's
`agents/` directory, installed into each eval workspace by the harness
before the first run:

- `retrieval-evaluator.opencode.md` (skill arm) — `skill: allow`;
  read/grep/glob/list allowed; edit, bash, task, todowrite, webfetch,
  websearch, question denied. The install step substitutes
  `{{SKILL_NAME}}` with the skill under test; the per-run prompt is the
  bare query — the measured query never names the skill.
- `retrieval-control.opencode.md` (control arm) — identical except
  `skill: deny`; runs in the control workspace, which never contains the
  skill, and answers from its own knowledge.

Neither agent pins `model`/`variant`/`temperature`/`top_p` — the installer
asserts this and aborts before any spend, so campaign `--model`/`--variant`
flags are the only model-selection path and sweeps measure what they
claim. Read-only is enforced by the harness permission layer, not claimed
in a prompt; the old `git status` contamination check is retired (the repo
is never the working directory).

Known limitation: `bash: deny` means a skill whose value includes
executable `scripts/` cannot have that value exercised — the syncer copies
scripts the agent cannot run.

## Workflow

1. Preflight (no spend): resolve python3 (>= 3.10);
   `evaluator.py check --harness <h> [--model m]` (with `--model`, the
   check also validates the model against the harness's model list).
2. `workspace-manager.sh init --prefix retrieval-test` → skill-ws;
   `workspace-manager.sh init --prefix retrieval-test` → control-ws.
   Both workspaces take the `retrieval-test` prefix — never the
   trigger-test default — and cleanup later uses the same prefix.
3. `sync --skill <s> --source <root> --workspace <skill-ws> --full`
   (the control workspace is NEVER synced).
4. `status --skill <s> --source <root> --workspace <skill-ws> --full`.
5. `workspace-manager.sh campaign-init --root <root>/skills-workspace/<s>/retrieval-tests`.
6. Snapshot into the campaign dir (plain cp, record the exact commands):
   `queries.json`, `facts.json`, and the verified synced skill dir — the
   exact bytes being measured.
7. Planned-spend confirmation: entries × 2 arms × reps runs, confirmed by
   the user before the first eval — EVERY campaign, including re-runs.
   With `--manifest` in play, name the control-only (ablation/removed)
   queries and the reduced run count in the confirmation.
8. `evaluator.py suite --track retrieval-test --harness <h> --skill <s> \
   --agents-dir <retrieval-skill-dir>/agents \
   --skill-workspace <skill-ws> --control-workspace <control-ws> \
   --queries <queries> --out <campaign>/results.json \
   [--manifest <canonical facts.json>] \
   [--model m] [--variant v] [--reps r] [--timeout t]`
   With `--manifest`, ablation/removed queries run the CONTROL ARM ONLY
   (sequentially, no skill arm) and their results records carry only
   `control_arm` (no `skill_arm` key); the evidence printer tolerates
   the missing skill arm. Two-step ablation flow: control pass/fail is
   a driver judgment from evidence, never decided mid-suite. The suite
   runs control-only; inspect the control evidence (step 9), and WHEN
   THE CONTROL FAILED, run the skill arm as a follow-up suite:
   `select`-filter the queries file to that query id and run `suite`
   WITHOUT `--manifest` into the SAME campaign dir as an additional
   results file — retrieval results merge by id via the scored-check
   union, and same-dir results files need no `--label`.
   The two arms of each entry run in parallel (one `ThreadPoolExecutor`
   per entry — the skill and control arm as its two workers); every
   progress line is arm-tagged — `[ skill ]` for the skill arm,
   `[control]` for the control arm — so interleaved output stays
   attributable. One suite process at a time, for the whole campaign:
   concurrent suites against the same endpoint multiply per-rep latency
   into empty-answer timeout voids that misattribute as agent defects;
   `suite` enforces this with a machine-wide lockfile — a second
   invocation aborts pre-spend naming the lock.
9. `evaluator.py evidence --track retrieval-test --results <campaign>/results.json \
   [--entry <id>]` → score from the presented evidence; never hand-roll
   JSON walks against results.json. A scenario passes only if every
   bullet in the entry's `expect` rubric is met by the returned answer.
   Bullets from `answer_text`
   only; voids via `void_signals`; classifications from `tool_calls`
   with `sources_consulted` as cross-check and `reasoning` as fallback;
   control comparison → ablation flags. Reps > 1: entry result = worst
   non-void run outcome (void only if every run is void).
10. `evaluator.py scored-check --track retrieval-test --results … \
    --emit-skeleton <campaign>/scored.json`
    emits the skeleton from the results union — every results entry id once,
    judgment fields null (plus `control: null` and `ablation_flag: null` per
    entry); fill the null judgment fields, then `evaluator.py scored-check
    --track retrieval-test --results … --scored <campaign>/scored.json`
    validates it — the check gates `record`. An unfilled skeleton fails
    the check.
11. Report (existing format + `artifacts:`/`manifest:` lines).
12. Confirmed doc fixes → mini-campaign re-run of failed entries only —
    confirmation, never recorded, never passed to `verify`/`record`.
    Layout: `confirm/round<N>/queries.json` (filtered with
    `evaluator.py select --entries <queries> --ids <failed entry ids>
    --out $CAMP/confirm/round<N>/queries.json` — `select` creates the
    round subdir) and `confirm/round<N>/results.json` (the suite
    `--out`). The counted results file is ALWAYS named `results.json`:
    if a run is redone for any reason, rename the superseded file to
    `results-superseded.json` (then `results-superseded-2.json`, …)
    before re-running — a round dir never holds two plausibly-counted
    results files, and which file counts never rests on report prose
    alone. One campaign dir per full run;
    mini-campaigns live in subdirectories of that run's dir — never in
    top-level `-n` dirs (`-n` is the nth FULL campaign that day, assigned
    by `campaign-init`).
13. After every completed FULL campaign (pass or fail, never aborted,
    never a mini-campaign — mini-campaigns like `confirm/` or `round-2/`
    NEVER touch streaks): close out in order — score (scored.json) →
    inventory-update → verify → record. First
    `evaluator.py inventory-update --manifest
    <root>/skills-workspace/<s>/retrieval-tests/facts.json --kind fact
    --scored <campaign>/scored.json --out
    <root>/skills-workspace/<s>/retrieval-tests/facts.json` updates the
    manifest deterministically, per fact, keyed through its scored
    entries' `control` fields: ANY control-fail fails the fact; elif ANY
    control-pass passes it; else (all void / no scored rows) untouched.
    A control pass on a status-less fact auto-marks it
    `status: "ablation"`, `ablation_streak: 0`; on a statused fact it
    increments the streak. A control fail on an ablation fact CLEARS
    `status`+`ablation_streak` entirely — the fact proved load-bearing,
    back to normal testing (a `load-bearing:` line is printed); on a
    removed fact it resets the streak to 0 and prints
    `regression failure: <id> — control failed; the deletion may have
    been wrong`. A void control run neither increments nor resets.
    Then gate with `evaluator.py verify --track
    retrieval-test --manifest <root>/skills-workspace/<s>/retrieval-tests/facts.json
    --entries <root>/skills-workspace/<s>/retrieval-tests/queries.json
    --scored <campaign>/scored.json --results <campaign>/results.json
    --campaign-dir <campaign> --skill-path <skill dir>` — the end-of-campaign
    consistency proof: snapshots byte-identical to the canonical
    files, facts↔queries wiring, results covering every query, and the
    scored-check flow re-run, ending with the record preflight (the exact
    counts record will write). Record only on exit 0: `evaluator.py record
    --skill <s> \
    --skill-path <skill dir> --manifest <root>/skills-workspace/<s>/manifest.json \
    --scope dir --scored <campaign>/scored.json --campaign <name> \
    --results <campaign>/results.json [--results <follow-up results file>] \
    --inventory <root>/skills-workspace/<s>/retrieval-tests/facts.json`
    Repeat `--results` once per results file in the campaign dir; the
    manifest entry's model/variant derive from the results config blocks,
    plus a cumulative deduped `models` list, and the entry's `ablations`
    count derives from `--inventory` (the number of items carrying a
    `status`). `record` takes the track counts from the scored file;
    `--track` is optional — auto-detected from the discriminating signals
    in the scored header. The manifest `date` is taken from the
    `--campaign` dir name, so a close-out after local midnight needs no
    `--date`.
14. `cleanup --workspace <ws> --prefix retrieval-test` — twice.

(`<retrieval-skill-dir>` = this skill's own resolved absolute path, same
convention as the trigger track.)

## Improving the skill definition

Fix failures by editing the doc — never by adding behavioral rules, prohibitions, or "always read X first" discipline clauses. A reference failure means the information architecture failed, not the agent.

| Classification | Right fix | Never |
|---|---|---|
| `gap` | Add the missing content where a fresh agent would look for it | A rule forbidding the hallucination |
| `findability` | Better headings, a TOC, a quick-reference row, a direct link from SKILL.md, one-level-deep references, descriptive filenames. Agents partially read nested files (`head -n 100` previews) — move important reference content above line 100 | "Always read X first" clauses |
| `clarity` | Rewrite the section; disambiguate look-alike facts; consistent terminology | Prohibition lists |
| ablation flag | Let `inventory-update` track the streak; at 3 consecutive control passes follow the removal procedure | Deleting on a single control pass |

Campaign rules:

- Fix between campaigns, never mid-campaign: complete the full pass, then apply edits. Mid-campaign doc edits invalidate every later result.
- Present recommended edits to the user and apply them only after confirmation.
- After edits land, re-run ONLY the failed scenarios (with their controls) as a mini-campaign to confirm: a `confirm/round<N>/` subdir of this campaign's dir, a queries file `select`-filtered to just the re-run entries — and never recorded in the manifest. The counted results file is always `results.json`; superseded attempts are renamed `results-superseded.json` before re-running (see Workflow step 12).
- Keep queries verbatim across campaigns, `{RUN_DIR}` token included; editing a query invalidates comparison. If a query is bad — asks for nothing, depends on context the bare session lacks — prune it and say so in the report.
- A scenario still failing after a doc fix gets one more doc revision. Still failing after that: surface it to the user — the fact likely needs restructuring, not rewording.

## Removal procedure

At the 3-consecutive-control-passes threshold, WITH user confirmation:

1. Delete the fact text from the source SKILL.md.
2. Hand-edit the inventory item to `status: "removed"` — the streak continues; it is NOT reset.
3. Keep the entries: the query stays — it is now regression coverage.

## Proposal format

Present the proposal as one card per entry, numbered in dispatch order. Each card is exactly these lines in order: `## N. <entry-id>`, `covers:` (fact ids), `facts:` (one line per fact, imperative, ≤15 words), `query:` (full verbatim query text), `expect:` (one bullet per rubric item), `why:` (one line). Close with `coverage:`, `excluded:`, `cost:` (as a formula), and `fixtures:` lines. Every fact appears in exactly one card's `covers:` or in the `excluded:` line.

- Fact ids are section-anchored (`F-<section-slug>-<nn>`) so doc edits never renumber other sections; they are minted by `inventory-mint` (draft the inventory id-less), so keep them stable across campaigns.

## Report format

Write the report in the fixed layout: `retrieval test: <skill> — <date>` header, `queries:`/`artifacts:`/`manifest:` lines, an id/result/control table with load-bearing and ablation annotations (annotate each entry covering a statused fact with its `status` + streak), a `summary: N pass / M fail / G gap / V void` line, then `failures:` (missed bullet, sources consulted, classification, recommended fix), `gaps:`, `ablation flags:`, and `regression failures:` sections. `regression failures:` quotes inventory-update's `regression failure:` lines — a control failure on a removed fact means the deletion may have been wrong; consider restoring the fact. Close with an ablation-candidates list: each ablation fact with its streak, plus the threshold note "3 consecutive control passes → recommend removal (human flips status to removed and deletes the fact text)" — documented policy, never mechanically enforced.

`manifest:` reads `not recorded (aborted)` or `not recorded (mini-campaign)` on those paths — only a completed full campaign is recorded.

## scored-check

The driver scores entries offline from `results.json` (zero spend);
`evaluator.py scored-check --track retrieval-test --results … \
--emit-skeleton <campaign>/scored.json`
emits the skeleton from the results union — every results entry id once,
judgment fields null (plus `control: null` and `ablation_flag: null` per
entry) — and the driver fills the judgment fields before `evaluator.py
scored-check --track retrieval-test --results … --scored
<campaign>/scored.json` validates it against the results before anything
is recorded. An unfilled skeleton fails the check. Schema:

```json
{
  "campaign": "campaign-2026-09-12",
  "skill": "writing-skills",
  "entries": [
    {
      "id": "retry-after-header",
      "result": "fail",
      "missed_bullets": ["states the Retry-After header is required"],
      "classification": "findability",
      "control": "fail",
      "ablation_flag": false,
      "notes": "read uploads.md but missed the header rule"
    }
  ]
}
```

Score each entry with: result (pass/fail/gap/void); classification (findability|clarity) if and only if result is fail; the control outcome; ablation_flag = (control == pass); missed_bullets copied character-for-character from the entry's expect list — required non-empty for fail and gap, absent otherwise.
- An ablation query whose control passed (the skill arm never ran)
  scores `result: "pass"`, `control: "pass"`, with the skip noted in
  `notes` — no new result vocabulary; `ablation_flag` stays mechanically
  derived as `control == "pass"`.
- Every `results.json` entry id must be accounted for exactly once —
  missing, duplicate, or unknown ids fail validation.

## Gotchas

- Never name the section or file holding the fact in a query — that tests following directions, not retrieval.
- Score from `answer_text` only — never what the agent claims it did or found. "It clearly used the doc" is not evidence.
- Never put rubric text in a run prompt; the per-run prompt is the bare query. Extra framing contaminates the measurement.
- Never provide additional information besides the prescribed query text to the eval agent.
- Never let the eval agent know that this is a test.
- Keep the query verbatim within and across campaigns, `{RUN_DIR}` token included; editing it invalidates comparison with earlier campaigns.
- The harness is always user-specified; never assume or default it.
- Campaign artifacts (results, scored, snapshots) live in the persistent campaign dir under `skills-workspace/` — never inside the temp eval workspaces.
- NEVER sync the skill into the control workspace — one contaminated baseline voids the whole campaign.
- A missing skill-load signal is `void`, not `fail` — the doc was never in context.
- A control pass is a flag, not a verdict: one clean baseline answer doesn't prove redundancy — `inventory-update` tracks the streak, and removal takes 3 consecutive passes plus user confirmation.
- Don't stack pressure or obstacles into retrieval queries — that's the discipline track. Plain, realistic tasks only.
- Every run in `results.json` carries its headless `session_id` (shown by `evidence --track retrieval-test`), and harness-abort error lines end with `[session <id>]` when the harness emitted one before failing — include it when reporting an abort so the failed session can be inspected.

## Checklist

- [ ] Inputs collected: skill resolved name-or-path, source root derived, harness user-specified, model/variant/reps/timeout settled; fact inventory built fresh from the current doc; proposal presented in the fixed format and approved; queries file exists, is non-empty, and covers the inventory; facts manifest regenerated to match
- [ ] Every query is task-shaped, self-contained or backed by a matching `fixtures` entry and `{RUN_DIR}` token, and free of section hints and rubric text
- [ ] Preflight green: python3 >= 3.10, `evaluator.py check --harness` (with `--model` when a model is set) exit 0; two workspaces initialized with `--prefix retrieval-test`
- [ ] Skill synced `--full` into the skill workspace and verified with `status --full`; control workspace contains no skill bytes
- [ ] Campaign dir created under the retrieval-tests root; queries.json, facts.json, and the verified synced skill dir snapshotted into it with the exact commands recorded
- [ ] Planned spend (entries × 2 arms × reps) confirmed by the user before the first eval run; with `--manifest`, the control-only queries and reduced run count named in the confirmation
- [ ] `suite --track retrieval-test` invoked with both workspaces and the agents dir; arms ran in parallel with arm-tagged progress lines; `--manifest <facts.json>` passed and ablation/removed queries ran control-only; control-failed ablation queries re-run as follow-up suites without `--manifest` into the same campaign dir; results.json written; only exit codes and JSON consumed; one suite process at a time — no second suite launched while another is running (lockfile enforces)
- [ ] Scoring evidence gathered with `evidence --track retrieval-test` (no ad-hoc JSON scripts); scored from `answer_text` only, bullet by bullet; voids via `void_signals`; every failure classified (gap / findability / clarity); control comparison → ablation flags; reps > 1 resolved by the worst-non-void rule
- [ ] scored.json skeleton emitted and the null judgment fields filled for every results entry; `scored-check` exits 0
- [ ] Report shows per-scenario results, summary counts, failure classifications, recommended doc fixes, and the `artifacts:`/`manifest:` lines
- [ ] Close-out order: scored.json → `inventory-update --kind fact` (full campaigns only — mini-campaigns never touch streaks) → `verify --track retrieval-test` exits 0 (snapshots byte-identical, facts↔queries wiring, results coverage, scored↔results, record preflight) → `record --scope dir` with repeatable `--results` and `--inventory`, run only after a completed full campaign — never aborted, never a mini-campaign
- [ ] Doc edits applied only after the full pass completes and only with user confirmation; failed scenarios re-run afterwards as a never-recorded mini-campaign
- [ ] `cleanup --workspace` run twice — skill-ws and control-ws — with `--prefix retrieval-test`
