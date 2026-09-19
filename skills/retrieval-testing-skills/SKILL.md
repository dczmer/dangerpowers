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
- **Timeout** — per-run abort, in seconds; default 120.

After resolving the source root, read the skill under test fully and build the fact inventory fresh from the current doc (see Fact inventory) — the manifest is a diff baseline, never a cache. If the inventory is empty — the skill documents no facts — stop: retrieval testing is not required. Otherwise diff the inventory against the manifest (see Fact inventory for the diff rules) and present a proposal for whatever the diff requires (see Proposal format). With the user's approval, apply the changes to the queries file — creating any fixtures new entries reference under `fixtures/` and regenerating `facts.json` at the same time — and explain each generated entry: the documented fact it covers, why you chose that query, and why you chose those expectations.

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

The manifest is a diff baseline, never a cache — rebuild the inventory fresh from the doc every campaign. Regenerate the manifest at proposal time and whenever entries are added or retired; never hand-maintain it between campaigns. Each campaign's diff against the previous manifest drives the work:

- New fact (no manifest id) → propose queries.
- Changed fact (same id, different statement) → flag its entries for re-scoring this campaign; queries stay verbatim.
- Deleted fact → propose pruning its entries; a query testing an undocumented fact measures nothing.

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
5. `campaign-init --root <root>/skills-workspace/<s>/retrieval-tests`.
6. Snapshot into the campaign dir (plain cp, record the exact commands):
   `queries.json`, `facts.json`, and the verified synced skill dir — the
   exact bytes being measured.
7. Planned-spend confirmation: entries × 2 arms × reps runs, confirmed by
   the user before the first eval — EVERY campaign, including re-runs.
8. `evaluator.py retrieval-suite --harness <h> --skill <s> \
   --agents-dir <retrieval-skill-dir>/agents \
   --skill-workspace <skill-ws> --control-workspace <control-ws> \
   --queries <queries> --out <campaign>/results.json \
   [--model m] [--variant v] [--reps r] [--timeout t]`
   The two arms of each entry run in parallel (the same
   ThreadPoolExecutor pattern the trigger reps use); every progress
   line is arm-tagged — `[ skill ]` for the skill arm, `[control]`
   for the control arm — so interleaved output stays attributable.
9. `evaluator.py retrieval-evidence --results <campaign>/results.json \
   [--entry <id>]` → score from the presented evidence; never hand-roll
   JSON walks against results.json. A scenario passes only if every
   bullet in the entry's `expect` rubric is met by the returned answer.
   Bullets from `answer_text`
   only; voids via `void_signals`; classifications from `tool_calls`
   with `sources_consulted` as cross-check and `reasoning` as fallback;
   control comparison → ablation flags. Reps > 1: entry result = worst
   non-void run outcome (void only if every run is void).
10. Write `<campaign>/scored.json` (schema per the scored-check section);
    `evaluator.py scored-check --results … --scored … \
    [--passes P --fails F --gaps G --voids V]` — with the counts given
    (all four, matching the report summary), the check gates `record`.
11. Report (existing format + `artifacts:`/`manifest:` lines).
12. Confirmed doc fixes → mini-campaign re-run of failed entries only
    (second campaign dir, filtered queries file) — confirmation, never
    recorded.
13. After every completed FULL campaign (pass or fail, never aborted,
    never a mini-campaign): `evaluator.py record --skill <s> \
    --skill-path <skill dir> --manifest <root>/skills-workspace/<s>/manifest.json \
    --scope dir --campaign <name> --passes N --fails M --gaps G --voids V`
    Every record call carries `--scope dir` and all four counts, matching
    the report summary exactly.
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
| ablation flag | Re-run that scenario next campaign; retire the entry if the baseline keeps passing | Deleting on a single control pass |

Campaign rules:

- Fix between campaigns, never mid-campaign: complete the full pass, then apply edits. Mid-campaign doc edits invalidate every later result.
- Present recommended edits to the user and apply them only after confirmation.
- After edits land, re-run ONLY the failed scenarios (with their controls) as a mini-campaign to confirm: a second campaign dir, a filtered queries file holding just the re-run entries — and never recorded in the manifest.
- Keep queries verbatim across campaigns, `{RUN_DIR}` token included; editing a query invalidates comparison. If a query is bad — asks for nothing, depends on context the bare session lacks — prune it and say so in the report.
- A scenario still failing after a doc fix gets one more doc revision. Still failing after that: surface it to the user — the fact likely needs restructuring, not rewording.

## Proposal format

Present the proposal as one card per entry, numbered in dispatch order. Each card is exactly these lines in order: `## N. <entry-id>`, `covers:` (fact ids), `facts:` (one line per fact, imperative, ≤15 words), `query:` (full verbatim query text), `expect:` (one bullet per rubric item), `why:` (one line). Close with `coverage:`, `excluded:`, `cost:` (as a formula), and `fixtures:` lines. Every fact appears in exactly one card's `covers:` or in the `excluded:` line.

- Fact ids are section-anchored (`F-<section-slug>-<nn>`) so doc edits never renumber other sections; keep them stable across campaigns.

## Report format

Write the report in the fixed layout: `retrieval test: <skill> — <date>` header, `queries:`/`artifacts:`/`manifest:` lines, an id/result/control table with load-bearing and ablation annotations, a `summary: N pass / M fail / G gap / V void` line, then `failures:` (missed bullet, sources consulted, classification, recommended fix), `gaps:`, and `ablation flags:` sections.

`manifest:` reads `not recorded (aborted)` or `not recorded (mini-campaign)` on those paths — only a completed full campaign is recorded.

## scored-check

The driver scores entries offline from `results.json` (zero spend) and
writes `<campaign>/scored.json`; `evaluator.py scored-check` validates it
against the results before anything is recorded. Schema:

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
- Optional `--passes/--fails/--gaps/--voids` (all four together) must
  equal the scored sums; pass the counts from the report summary so an
  arithmetic slip fails here, before `record`.
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
- A control pass is a flag, not a verdict: one clean baseline answer doesn't prove redundancy, it schedules a re-check.
- Don't stack pressure or obstacles into retrieval queries — that's the discipline track. Plain, realistic tasks only.
- Every run in `results.json` carries its headless `session_id` (shown by `retrieval-evidence`), and harness-abort error lines end with `[session <id>]` when the harness emitted one before failing — include it when reporting an abort so the failed session can be inspected.

## Checklist

- [ ] Inputs collected: skill resolved name-or-path, source root derived, harness user-specified, model/variant/reps/timeout settled; fact inventory built fresh from the current doc; proposal presented in the fixed format and approved; queries file exists, is non-empty, and covers the inventory; facts manifest regenerated to match
- [ ] Every query is task-shaped, self-contained or backed by a matching `fixtures` entry and `{RUN_DIR}` token, and free of section hints and rubric text
- [ ] Preflight green: python3 >= 3.10, `evaluator.py check --harness` (with `--model` when a model is set) exit 0; two workspaces initialized with `--prefix retrieval-test`
- [ ] Skill synced `--full` into the skill workspace and verified with `status --full`; control workspace contains no skill bytes
- [ ] Campaign dir created under the retrieval-tests root; queries.json, facts.json, and the verified synced skill dir snapshotted into it with the exact commands recorded
- [ ] Planned spend (entries × 2 arms × reps) confirmed by the user before the first eval run
- [ ] `retrieval-suite` invoked with both workspaces and the agents dir; arms ran in parallel with arm-tagged progress lines; results.json written; only exit codes and JSON consumed
- [ ] Scoring evidence gathered with `retrieval-evidence` (no ad-hoc JSON scripts); scored from `answer_text` only, bullet by bullet; voids via `void_signals`; every failure classified (gap / findability / clarity); control comparison → ablation flags; reps > 1 resolved by the worst-non-void rule
- [ ] scored.json written for every results entry and `scored-check` exits 0 — including the report-summary counts when passed
- [ ] Report shows per-scenario results, summary counts, failure classifications, recommended doc fixes, and the `artifacts:`/`manifest:` lines
- [ ] `record --scope dir` run only after a completed full campaign — never aborted, never a mini-campaign
- [ ] Doc edits applied only after the full pass completes and only with user confirmation; failed scenarios re-run afterwards as a never-recorded mini-campaign
- [ ] `cleanup --workspace` run twice — skill-ws and control-ws — with `--prefix retrieval-test`
