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

Drop rationales, restatements, illustrative examples, and transitions. Frontmatter-convention guidance is out of scope.

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
- `query` — a realistic, task-shaped prompt that stands alone: embed any code or context the task refers to inline, or reference staged fixtures through the `{RUN_DIR}` token (see Fixtures). Never sends the agent hunting for an artifact that does not exist, never names the section or file holding the fact, never hints at the answer, never quotes rubric text. The stored query is canonical — reported verbatim, `{RUN_DIR}` token included, across campaigns; only the per-run dispatched copy substitutes the staged path.
- `expect` — objective rubric bullets. A scenario passes only if every bullet is met by the returned answer.
- `fixtures` — optional list of fixture filenames, each existing under a `fixtures/` directory next to the queries file. Required exactly when the query contains `{RUN_DIR}`: the harness rejects a token without a fixtures entry and fixtures without a token before any spend.

### Fixtures

Default to inline, self-contained queries. "Rewrite the upload script" is not a test if there is no script for the agent to find — but a large file or multi-file state can be impractical to embed, and then the query references a fixture instead.

Store canonical fixtures under `fixtures/` next to the queries file. Staging is scripted, not improvised: the harness gives each run its own run directory inside the eval workspace — `<workspace>/fixtures/<entry-id>/<arm>` (suffixed `-repN` when reps > 1) — copies the entry's fixture files in fresh, and substitutes that run-specific path for `{RUN_DIR}` in the dispatched query. No two runs ever share a fixture file, and no run ever writes into the repository: the eval workspaces are disposable temp directories, never the repo.

Per-run path substitution is isolation mechanics, not query editing — the task text stays verbatim across campaigns.

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
   `evaluator.py check --harness <h>`.
2. `workspace-manager.sh init --prefix retrieval-test` → skill-ws;
   `workspace-manager.sh init --prefix retrieval-test` → control-ws.
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
9. Score each entry from the results JSON: bullets from `answer_text`
   only; voids via `void_signals`; classifications from `tool_calls` with
   `sources_consulted` as cross-check and `reasoning` as fallback; control
   comparison → ablation flags. Reps > 1: entry result = worst non-void
   run outcome (void only if every run is void).
10. Write `<campaign>/scored.json` (schema per the scored-check section);
    `evaluator.py scored-check --results … --scored …`.
11. Report (existing format + `artifacts:`/`manifest:` lines).
12. Confirmed doc fixes → mini-campaign re-run of failed entries only
    (second campaign dir, filtered queries file) — confirmation, never
    recorded.
13. After every completed FULL campaign (pass or fail, never aborted,
    never a mini-campaign): `evaluator.py record --skill <s> \
    --skill-path <skill dir> --manifest <root>/skills-workspace/<s>/manifest.json \
    --scope dir --campaign <name> --passes N --fails M --gaps G --voids V`
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
Before writing or running anything, present the inventory and planned entries as one self-contained card per entry, in this fixed layout:

    retrieval test proposal: acme-api — 2026-09-11
    source: skills/acme-api/SKILL.md (body: 210 lines)
    queries file: skills-workspace/acme-api/retrieval-tests/queries.json (missing — generating)
    scope: frontmatter-convention facts excluded

    ## 1. retry-after-header
    covers: F-uploads-01, F-uploads-02

    facts:
    - F-uploads-01  [Uploads]  reads Retry-After, value interpreted as seconds
    - F-uploads-02  [Uploads]  no retries on other 4xx codes

    query:
    Given this upload function — `def upload(path, url): return requests.post(url, data=open(path, 'rb'))` — add retry handling for 429 responses and return the complete updated function inline.

    expect:
    - reads the Retry-After header rather than using a fixed backoff
    - interprets the value as seconds
    - does not retry on other 4xx codes

    why: the bare function invites a fixed backoff; one realistic task pins all
    three documented behaviors — the header, its unit, and the 4xx boundary.

    ## 2. upload-chunk-size
    covers: F-uploads-03 [Uploads] — upload in 4 MiB chunks

    query:
    ...

    coverage: 6 facts / 5 entries / 0 excluded
    excluded: none
    cost: 5 entries × 2 arms = 10 runs, 120 s timeout
    fixtures: none (all queries inline)

- Fact ids are section-anchored (`F-<section-slug>-<nn>`) so doc edits never renumber other sections; keep them stable across campaigns.
- One card per entry, numbered in dispatch order: `covers:` names the facts tested, then the full query text, the rubric bullets, and a `why:` line explaining why this query and why these expectations.
- Multi-fact cards list each fact on its own line — imperative restatement, ≤15 words, no rationale; single-fact cards inline the fact on the `covers:` line.
- Show the full query text in every card — a proposal without query text is unreviewable.
- Account for every fact exactly once — in a card's `covers:` line or an exclusion with a stated reason.
- Cost is a formula — entries × 2 arms, gaining `× reps` when reps > 1 — and the fixtures line is always present, even when `none`. The per-campaign spend confirmation itself lives in Workflow step 7, not in this proposal.

## Report format

    retrieval test: acme-api — 2026-09-11
    queries: skills-workspace/acme-api/retrieval-tests/queries.json (6 entries)
    artifacts: <source-root>/skills-workspace/<skill>/retrieval-tests/campaign-YYYY-MM-DD[-n]/
    manifest: recorded (sha256:…, N pass / M fail / G gap / V void)

    id                    result   control
    retry-after-header    pass     fail (load-bearing)
    upload-chunk-size     fail     fail
    oauth-refresh-flow    pass     fail (load-bearing)
    error-code-table      pass     pass → ablation flag
    webhook-signatures    gap      —
    pagination-cursor     void     —

    summary: 3 pass / 1 fail / 1 gap / 1 void (6 scenarios)

    failures:
    upload-chunk-size — missed bullet: "uses 4 MiB chunks". Sources consulted:
      "Authentication", "Errors"; never opened "Uploads". classification:
      findability. recommended fix: add an Uploads row to the quick-reference
      table in SKILL.md.

    gaps:
    webhook-signatures — common use case absent from the doc. recommended
      fix: add a webhook signature verification section.

    ablation flags:
    error-code-table — control answered correctly without the skill;
      re-check next campaign, retire if the baseline keeps passing.

`manifest:` reads `not recorded (aborted)` or `not recorded
(mini-campaign)` on those paths — only a completed full campaign is
recorded.

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

- `result` — one of `pass`, `fail`, `gap`, `void`.
- `classification` — `findability` or `clarity`; required exactly when
  `result` is `fail` (a `gap` is a result, not a classification), absent
  or null otherwise.
- `control` — the control-arm outcome: `pass`, `fail`, or `void`.
- `ablation_flag` — boolean.
- `missed_bullets` — list of strings, required non-empty for `fail` and
  `gap`.
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

## Checklist

- [ ] Inputs collected: skill resolved name-or-path, source root derived, harness user-specified, model/variant/reps/timeout settled; fact inventory built fresh from the current doc; proposal presented in the fixed format and approved; queries file exists, is non-empty, and covers the inventory; facts manifest regenerated to match
- [ ] Every query is task-shaped, self-contained or backed by a matching `fixtures` entry and `{RUN_DIR}` token, and free of section hints and rubric text
- [ ] Preflight green: python3 >= 3.10, `evaluator.py check --harness` exit 0; two workspaces initialized with `--prefix retrieval-test`
- [ ] Skill synced `--full` into the skill workspace and verified with `status --full`; control workspace contains no skill bytes
- [ ] Campaign dir created under the retrieval-tests root; queries.json, facts.json, and the verified synced skill dir snapshotted into it with the exact commands recorded
- [ ] Planned spend (entries × 2 arms × reps) confirmed by the user before the first eval run
- [ ] `retrieval-suite` invoked with both workspaces and the agents dir; results.json written; only exit codes and JSON consumed
- [ ] Scoring from `answer_text` only, bullet by bullet; voids via `void_signals`; every failure classified (gap / findability / clarity); control comparison → ablation flags; reps > 1 resolved by the worst-non-void rule
- [ ] scored.json written for every results entry and `scored-check` exits 0
- [ ] Report shows per-scenario results, summary counts, failure classifications, recommended doc fixes, and the `artifacts:`/`manifest:` lines
- [ ] `record --scope dir` run only after a completed full campaign — never aborted, never a mini-campaign
- [ ] Doc edits applied only after the full pass completes and only with user confirmation; failed scenarios re-run afterwards as a never-recorded mini-campaign
- [ ] `cleanup --workspace` run twice — skill-ws and control-ws — with `--prefix retrieval-test`
