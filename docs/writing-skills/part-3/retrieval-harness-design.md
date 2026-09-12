# Retrieval-Testing CLI Harness — Design Summary

> **Disclaimer: AI-generated design**
>
> This document was designed by an AI coding assistant on 2026-09-12, based
> on the repo's `trigger-testing-skills` conventions (scripts, agent,
> campaign artifacts) and the current `retrieval-testing-skills` SKILL.md.
> It is a **design plan only** — none of the changes below exist yet.
> Decisions marked "locked" come from the requester's answers to clarifying
> questions.
>
> **Revision 2** incorporates a full independent review (fresh subagent,
> same day) and a follow-up portability discussion. The review verdict —
> "the idea is valid, the architecture is right, implement with
> modifications" — is applied here: two workspaces (control-arm isolation),
> tool-call capture + skill snapshot (offline-complete results), full-
> campaign-only manifest recording, the `{RUN_DIR}` fixture-token
> correction, `check` slimmed to binary-only, per-campaign spend
> confirmation, a `scored.json` validator, and the `--agents-dir`
> harness-neutral agent resolution replacing `--agent-file`/`--agent-name`.

## 1. Purpose

Bring `retrieval-testing-skills` up to the same campaign conventions as
`trigger-testing-skills`:

1. Record a manifest entry showing a skill has been retrieval tested,
   mapped to a hash of what was tested.
2. Keep persistent campaign log artifacts.
3. Isolate eval runs in sterile temp workspaces (workspace-manager style).
4. Replace the inline subagent prompt in the skill file with custom agent
   definitions.
5. Launch evals as headless CLI harness instances with a strategy pattern
   (selectable model/variant), capturing everything needed to evaluate
   failures offline.

And two cross-cutting requirements from the requester:

- **Centralize** the harness tooling shared by both testing skills instead
  of duplicating near-identical scripts per skill.
- **Script the deterministic parts**; reserve inference for the steps that
  genuinely need judgment.

## 2. Locked decisions (requester Q&A, 2026-09-12)

| # | Question | Decision |
|---|----------|----------|
| D1 | Where does shared tooling live? | New central `tools/` dir at repo root; trigger-testing migrates to it too |
| D2 | Manifest layout | One manifest per skill: `skills-workspace/<skill>/manifest.json`, holding both `trigger-test` and `retrieval-test` keys |
| D3 | Retrieval checksum scope | Whole skill directory (SKILL.md + references/ + scripts/), not frontmatter-only |
| D4 | Manifest entry contents | date + checksum + campaign + summary counts (pass/fail/gap/void, ablation flags) |
| D5 | Execution model | Headless CLI only; in-session subagent dispatch is fully replaced |
| D6 | Agent mapping | Two agents: `retrieval-evaluator` (skill arm) + `retrieval-control` (control arm) |
| D7 | This document's location | `docs/writing-skills/part-3/` |

## 3. Current state → target state

| Aspect | Current retrieval-testing | Target |
|--------|---------------------------|--------|
| Dispatch | In-session subagents via the task tool, driving session's harness | Headless `opencode run` per arm per entry, launched by script |
| Skill availability | Skill under test must be visible to the driving session | Path-based resolution (like trigger); session visibility irrelevant |
| Subagent rules | Inline prompt template in SKILL.md ("read-only session" guardrail, not enforced) | Two installed agent files with real permission denies (edit/bash/web denied) |
| Workspace | Current repo; fixtures staged under `/tmp/opencode/retrieval-test/`; `git status` contamination check | **Two** sterile temp workspaces per campaign: skill arm gets the full skill synced in, control arm never contains the skill; fixtures staged inside each arm's workspace; contamination structurally impossible |
| Harness/model selection | None (subagents inherit session model) | `--harness` (required, user-specified), `--model`, `--variant` as opaque passthroughs via the strategy registry; agent files forbidden from pinning model config |
| Output | Prose subagent results read by the driver | Structured results JSON: full answer text, sources-consulted, skill-load signal, **read/grep/glob tool-call targets**, reasoning, session id, per-run void signals |
| Artifacts | queries.json + facts.json only; no campaign record | Persistent `campaign-YYYY-MM-DD[-n]/` dir: results JSON, log, scored.json, snapshots of queries, facts, **and the tested skill dir** |
| Manifest | none | `skills-workspace/<skill>/manifest.json`, `retrieval-test` key with dir checksum + counts; **completed full campaigns only** |
| Scoring | Driver judgment from prose | Driver judgment from structured JSON (unchanged owner, better evidence) |

## 4. Repository layout (target)

```
tools/
  test-harness/
    evaluator.py            # moved from skills/trigger-testing-skills/scripts/;
                            # gains retrieval-suite + scored-check subcommands,
                            # generalized record
    strategies.py           # moved; harness registry generalized (agent
                            # resolution, richer stream parsing, templating)
    workspace-manager.sh    # moved; gains --prefix, sync/status --full
    test_evaluator.py       # moved; extended for new subcommands
skills/
  trigger-testing-skills/
    SKILL.md                # path + manifest-location + CLI-surface updates only
    agents/trigger-evaluator.opencode.md      # stays with its skill
  retrieval-testing-skills/
    SKILL.md                # workflow rewritten (section map in §9)
    agents/
      retrieval-evaluator.opencode.md         # new
      retrieval-control.opencode.md           # new
skills-workspace/
  <skill>/
    manifest.json           # ONE manifest per skill (migrated from
                            # trigger-tests/manifest.json)
    trigger-tests/…         # unchanged otherwise
    retrieval-tests/
      queries.json          # schema extended (optional fixtures field, §8)
      facts.json            # unchanged
      fixtures/…            # unchanged
      campaign-YYYY-MM-DD/  # new persistent campaign dirs
```

Agent files stay with their owning skills (convention per AGENTS.md layout:
"agents/ # supporting agent configs/schemas (some skills)"; endorsed by the
review). The shared scripts resolve agent files harness-neutrally via
`--agents-dir` (§5.1). Alternative considered: a central
`tools/test-harness/agents/` dir — rejected; the agents are per-track test
definitions, not harness machinery.

## 5. Centralized scripts: what moves, what generalizes

Move (git mv) all four files from `skills/trigger-testing-skills/scripts/`
to `tools/test-harness/`. Delete `__pycache__/`. Nothing is duplicated; both
skills invoke the central scripts by absolute path (the trigger SKILL.md's
phrase "by their path **inside this skill directory**" is reworded — it
becomes false after the move). `AGENTS.md` project-layout section gains the
`tools/` entry (requires requester confirmation per repo rules).

**Ride-along portability fix:** `strategies.py`'s stream parser currently
uses `except json.JSONDecodeError, ValueError:` — PEP 758 syntax valid only
on Python ≥ 3.14, while trigger's SKILL.md documents an interpreter floor
of >= 3.10. Add the parens during the move:
`except (json.JSONDecodeError, ValueError):`.

### 5.1 strategies.py

Current coupling: `SKILL_DIR`/`AGENTS_DIR` are derived from `__file__` to
locate `agents/trigger-evaluator.opencode.md` (silently breaks after the
move), and `classify()` bakes in trigger verdict semantics.

Changes:

- **Harness-neutral agent resolution: `--agents-dir`.** The CLI never
  names agent files or agent names. Each subcommand owns per-track base
  constants (`suite`/`run` → `trigger-evaluator`; `retrieval-suite` →
  `retrieval-evaluator` + `retrieval-control`); each strategy owns its file
  suffix (`.opencode.md`). The strategy resolves
  `<agents-dir>/<base>.<harness>.md`. Swapping harness changes only the
  user's `--harness` value; SKILL.md command lines stay verbatim, and
  adding a harness = one strategy class + one agent file per track. This
  formalizes the naming convention the repo already uses.
- **Name derived, never passed.** `--agent-name` does not exist. The
  strategy reads the frontmatter `name:` field with a stdlib line-scan
  (pyyaml is not in the repo's Python env; scripts stay stdlib-only for
  the "python3 >= 3.10 on PATH" preflight story), installs to
  `.opencode/agent/<name>.md`, and passes `--agent <name>` — filename
  stem, frontmatter name, and CLI value equal by construction, consistent
  under either agent-registration rule opencode uses. `install()` asserts
  the source file's stem matches the frontmatter name, failing pre-spend.
  (The dropped explicit `--agent-name` arg was two sources of truth for
  one fact; a mismatch surfaced only at the smoke rep via opencode's
  silent agent fallback — after spend had begun.)
- **Model/variant integrity assertion.** opencode agent frontmatter CAN
  pin `model:`/`variant:`/`temperature:`/`top_p:` (this repo's plugin
  whitelists those keys), which would conflict with the CLI flags driving
  model sweeps under harness-specific silent precedence. `install()`
  asserts none of those keys are present in an eval agent's frontmatter —
  exit 1 with an exact message, before any spend. Model/variant selection
  flows exclusively through `--model`/`--variant` as opaque passthrough
  strings; a strategy that cannot map one of them exits 1 rather than
  silently ignoring it.
- **Richer EventStream.** The opencode NDJSON parser additionally
  captures: concatenated final `text` events (the answer); every skill
  tool_use (control-arm contamination); **read/grep/glob tool_use targets**
  (deterministic evidence of what the agent actually consulted — strictly
  better than the self-reported "Sources consulted" list the current
  workflow already distrusts, and the evidence findability-vs-clarity
  classification needs); and denied/permission-rejected tool attempts.
  *Implementation note:* the denied-attempt event shape is **unverified**
  — denied tools may simply be absent from the model's toolset, making
  attempts impossible and the capture dead code. Mark "verify at
  implementation"; keep as belt-and-suspenders, never load-bearing.
  Trigger's `classify()` is untouched.
- **No retrieval verdict in the strategy layer.** Retrieval runs return a
  raw `RunRecord`, never a pass/fail. Scoring is rubric judgment and stays
  with the driving agent — the existing `failures`-extractor philosophy:
  "Extraction only; analysis is the agent's job."
- **Install-time templating for the skill name** (retrieval skill arm
  only). The retrieval-evaluator agent must load a *specific* skill before
  starting the task, but the measured query must never name the skill.
  The agent source carries a `{{SKILL_NAME}}` placeholder; `install()`
  substitutes the `--skill` value when copying into the workspace (plain
  string replace). The per-run prompt stays the bare query. Alternative
  considered and rejected: skill name in the run prompt — pollutes the
  measured prompt. *Accepted risk (inherited, not new):* if opencode
  surfaces the active agent's name to the model, `retrieval-evaluator`
  leaks "evaluator" — same exposure as `trigger-evaluator` today; neutral
  naming is an option if it ever bites.

### 5.2 evaluator.py CLI surface

Existing subcommands (`run`, `split`, `suite`, `failures`) keep their
semantics; `run`/`suite` gain required `--agents-dir`.

**`check` — binary validation only.** Today `check_harness` also validates
the agent source file; after generalization that validation lives where it
can actually fail — `install()` and the `retrieval-suite` pre-spend
validation. `check` verifies the CLI binary is on PATH, nothing else.

**`record` — generalized, single subcommand:**

```
evaluator.py record --skill NAME --skill-path PATH --manifest PATH \
    --scope frontmatter|dir [--date D] [--campaign NAME] \
    [--score S] [--passes N --fails M --gaps G --voids V [--ablations A]]
```

- `--scope frontmatter` (trigger): current behavior — sha256 over the
  SKILL.md frontmatter block; `--skill-path` is the SKILL.md file;
  `--score` required, counts rejected.
- `--scope dir` (retrieval): sha256 over the whole skill directory
  (deterministic: walk sorted relative paths, exclude `__pycache__/` and
  `*.pyc`, feed `relpath\0bytes\0` per file); `--skill-path` is the skill
  directory (type validated per scope); counts required, `--score`
  rejected.
- The dir hasher and `sync --full` exclude **identical** file sets
  (`__pycache__/`, `*.pyc`) and apply the same symlink policy (§5.3) —
  otherwise `status --full` and the manifest hash disagree on what "the
  content" is.
- Manifest I/O core is shared and already correct: read existing object,
  overwrite only this track's key, preserve unknown keys. Key written:
  `trigger-test` or `retrieval-test` per scope.
- Argparse details: counts use explicit `dest`s (`pass` is a keyword);
  conditional-arg validation is manual; violations exit 1 with an exact
  message. Alternative considered: separate `retrieval-record` — rejected;
  one manifest writer, one `--scope` flag.

**`retrieval-suite` — new subcommand:**

```
evaluator.py retrieval-suite --harness opencode --skill NAME \
    --agents-dir DIR --skill-workspace WS --control-workspace WS \
    --queries QUERIES.json --out RESULTS.json \
    [--model M] [--variant V] [--reps 1] [--timeout 120]
```

(No `--skill-path`: hashing lives in `record`, fixtures resolve relative
to `--queries` — an earlier draft's arg had no job and was dropped.)

Pre-spend validation (any failure → exit 1, exact message, zero spend):

- harness `check`; both agent files resolved, frontmatter-parsed,
  stem-matches-name, and free of model pins.
- Skill workspace has `<ws>/.agents/skills/<skill>/` synced (run
  `workspace-manager.sh status --full` first).
- **Control workspace must NOT contain the skill**: assert
  `<control-ws>/.agents/skills/<skill>/` is absent. The two-workspace
  model is the structural guarantee that the control baseline is
  uncontaminated — with the skill synced into a shared workspace, a
  control agent with `read: allow` could simply read the body from
  `.agents/skills/`, and `skill: deny` only blocks the skill *tool*.
- Queries file valid per §8 schema; `--out` parent exists; fixtures dir
  resolved as `<queries-file-parent>/fixtures/`.

Behavior, all deterministic:

1. Mirror the campaign log to `<out>.log` like `suite`.
2. For each entry, for each arm (skill, control), for each rep
   (default 1):
   - Stage fixtures when the entry declares them: create
     `<arm-ws>/fixtures/<entry-id>/<arm>[-repN]/`, copy the declared files
     in, substitute `{RUN_DIR}` in the query with the staged absolute
     path. Staging inside the arm's own workspace (not `/tmp`) avoids
     read-outside-workspace permission behavior in a restricted headless
     agent. No two runs share a fixture file (cheap convention, kept —
     though with mutation denied it is no longer load-bearing isolation).
   - Run `opencode run --pure --thinking --format json --dir <arm-ws>
     --agent <arm-agent> [--model m] [--variant v] <query>` with the
     timeout. Smoke-run-first then parallel batches, same as `eval_batch`.
   - Parse the stream into a run record (§7).
3. Write the results JSON (§7) and exit 0. Harness execution failure
   anywhere → stderr message, exit 1, no JSON (campaign abort, workspaces
   kept — same policy as trigger).

Deliberately absent: `split`, sealed pool, sanity check, iteration loop —
retrieval has no optimization loop; fixes land between campaigns.

**`scored-check` — new subcommand:**

```
evaluator.py scored-check --results RESULTS.json --scored SCORED.json
```

Validates the driver-written scoring artifact: every results-file entry id
accounted for exactly once, verdicts in the enum
(pass/fail/gap/void/ablation-flag semantics per §9), required fields
present. Exit 1 with exact messages. Cheap, aligned with the "account for
every entry" checklist rule, and keeps the audit artifact honest without
the script owning any judgment.

### 5.3 workspace-manager.sh

- `init --prefix P` — creates `/tmp/P.XXXXXXXXXX` with `.agents/skills/`,
  prints the path. Retrieval campaigns call it **twice** (skill-arm and
  control-arm workspaces).
- `cleanup --workspace WS --prefix P` — refuses paths not matching
  `/tmp/P.*` (same guard, parameterized). Called per workspace.
- `sync --skill S --source ROOT --workspace WS [--full]` — default is the
  existing frontmatter stub; `--full` copies the entire skill dir into
  `<ws>/.agents/skills/<skill>/`. `--full` carries over the existing
  `name:`-matches-directory check, excludes `__pycache__/` and `*.pyc`
  (identical set to the dir hasher), and **rejects symlinks escaping the
  skill dir** (syncer and hasher must agree on the file set).
- `status … [--full]` — stub: current frontmatter comparison; `--full`:
  recursive diff with the same exclusions, exit 1 on any difference.
- `campaign-init --root DIR` — unchanged; used by both tracks.
- Retrieval syncs the skill **only into the skill-arm workspace**; the
  control workspace is initialized but never synced.

## 6. The two retrieval agents

Both are `mode: primary`, installed per workspace by the strategy into
`.opencode/agent/`, exactly like `trigger-evaluator`. Neither pins
`model`/`variant`/`temperature`/`top_p` — enforced by the `install()`
assertion (§5.1), so campaign `--model`/`--variant` flags are the only
model selection path and sweeps measure what they claim.

**`retrieval-evaluator.opencode.md`** (skill arm):

- permission: `skill: allow`, `read: allow`, `grep: allow`, `glob: allow`,
  `list: allow`; `edit`, `bash`, `task`, `todowrite`, `webfetch`,
  `websearch`, `question`: deny.
- `steps: 30` guardrail (load skill + read references + compose answer);
  the 120 s default timeout stays the primary cutoff. Both are starting
  tunables endorsed by the review.
- Body: the current SKILL.md subagent-prompt rules, verbatim where
  possible: read-only is real now (the framing changes to "your tools are
  restricted by policy"), load `{{SKILL_NAME}}` first and read what it
  directs to, facts must come from the skill, inline output only (the rule
  stays as output-shape instruction), no clarifying questions — state the
  assumption in one line, end with the "Sources consulted:" list.
- Inherited limitation to keep documenting: `bash: deny` means skills
  whose value includes executable `scripts/` cannot have that value
  exercised — the syncer copies scripts the agent cannot run. Inherited
  from the current read-only design, not a regression.

**`retrieval-control.opencode.md`** (control arm):

- Same permissions except `skill: deny`; runs in the control workspace,
  which never contains the skill — the structural half of baseline purity.
- Body: answer entirely from your own knowledge; same inline-output and
  no-questions rules; no sources-consulted requirement.

Enforcement upgrade stated in the skill: the old "read-only claim is a
guardrail, not enforcement" gotcha inverts — read-only is now enforced by
the harness permission layer, and the `git status` contamination check is
retired (the repo is never the working directory).

## 7. retrieval-suite results schema

One JSON object: config block (skill, harness, model, variant, reps,
timeout, date, queries path), then `entries[]`:

```json
{
  "id": "retry-after-header",
  "query": "<verbatim from queries.json>",
  "expect": ["…"],
  "skill_arm": {
    "runs": [{
      "query_dispatched": "<post-substitution, == query when no fixtures>",
      "answer_text": "<concatenated final text events>",
      "sources_consulted": "<extracted Sources-consulted block, null if absent>",
      "tool_calls": [{"tool": "read", "target": ".agents/skills/acme-api/references/uploads.md"}],
      "skill_load_completed": true,
      "other_skill_loads": [],
      "denied_tool_attempts": [],
      "reasoning": "<concatenated thinking blocks>",
      "session_id": "…",
      "timeout": false,
      "parseable_events": 87,
      "void_signals": []
    }]
  },
  "control_arm": { "runs": [ /* same record shape */ ] }
}
```

- `tool_calls` — deterministic read/grep/glob/skill targets. This is what
  makes failure evaluation genuinely offline: findability-vs-clarity
  classification runs on what the agent *actually read*, with the
  self-reported list as cross-check, and no dependence on opencode session
  persistence (whether `--pure` headless sessions persist for a
  "transcript fallback" is unverified — a session id is a pointer, not an
  artifact).
- `void_signals` — script-computed per run, driver still owns the call:
  `skill-not-loaded` (skill arm, no completed load of the exact skill),
  `control-loaded-skill` (control arm, any skill tool_use), `empty-answer`,
  and `read-outside-workspace` (any tool target escaping the run's
  workspace root — defense-in-depth detection for the day permissions get
  reconfigured, covering e.g. a control agent reading the repo's copy of
  the skill by absolute path).
- The campaign dir additionally snapshots the **tested skill dir itself**
  (copied from the verified skill-arm workspace after `status --full`
  passes — exactly the bytes that were measured). Trigger's
  `iter-<i>-description.md` sets the precedent. Gap classification ("fact
  absent from the doc") needs the measured content at hand, and the
  manifest's dir hash becomes auditable offline.

Everything the current subagent prompt produced for failure evaluation —
inline answer, sources list, reasoning — plus the two evidence types
classification relies on most (real read targets, measured content) is in
the campaign dir.

## 8. queries.json schema extension

**Correction from review:** the existing
`skills-workspace/writing-skills/retrieval-tests/queries.json` ALREADY uses
an explicit placeholder — `{RUN_DIR}` in the `read-before-editing` entry,
with `fixtures/existing-skill.md` on disk. The placeholder is explicit in
the data; only the SKILL.md prose was vague. An earlier draft of this
design claimed otherwise and proposed a token rename plus validation that
would have rejected the existing file with no migration path.

Decision: **keep `{RUN_DIR}` as the token, verbatim.** It accurately names
what it is (the run's unique staging dir), brace tokens resist "helpful"
shell reinterpretation, and — decisive — the query text stays byte-for-byte
stable across the harness swap, honoring both skills' core rule ("keep
queries verbatim; editing a query invalidates comparison"). No sanctioned
exception needed. The only data migration: add the explicit field to the
one entry that uses fixtures.

Entries gain one optional field:

```json
{ "id": "read-before-editing",
  "query": "The skill at {RUN_DIR}/existing-skill.md is missing …",
  "expect": ["…"],
  "fixtures": ["existing-skill.md"] }
```

- `fixtures` lists files under the canonical `fixtures/` dir (sibling of
  the queries file) to stage per run. Omitted = inline self-contained
  query (the default, unchanged).
- Validation (pre-spend, in `retrieval-suite`): listed files must exist;
  query must contain `{RUN_DIR}` iff `fixtures` is present. Violations
  stop the campaign before any spend, exact message.
- `query` stays verbatim across campaigns; substitution is per-run
  dispatch mechanics, and the dispatched form is recorded in the results
  JSON as `query_dispatched`.

## 9. retrieval-testing-skills SKILL.md rewrite map

- **Overview** — add: staging, capture, validation, and manifest recording
  live in `tools/test-harness/`; consume exit codes and JSON only. Keep
  "measures the body; triggering is the other track."
- **Inputs** — replace "must appear in this session's available-skills
  list" with trigger-style name-or-path resolution + source-root
  derivation. Add required user-specified **harness**, optional
  **model/variant** (opaque passthroughs to eval executions only), **reps**
  (default 1), **timeout** (default 120 s). Queries/facts paths unchanged.
- **Fact inventory / proposal format** — untouched (pure judgment).
- **Subagent prompt section** — deleted; replaced by a short "Eval agents"
  section describing the two installed agents, install-time
  `{{SKILL_NAME}}` templating, and the no-model-pin rule.
- **Fixtures** — rewritten to the §8 schema + scripted staging; drop the
  `/tmp/opencode/retrieval-test` mktemp prose; `{RUN_DIR}` token
  documented as canonical.
- **Workflow** — preflight (`check`) → `init` **twice** →
  `sync --full` into the skill-arm workspace only → `status --full` →
  `campaign-init --root …/retrieval-tests` → snapshot `queries.json` +
  `facts.json` + the verified synced skill dir into the campaign dir
  (plain `cp`, recorded as exact commands) → **planned-spend confirmation:
  entries × 2 arms × reps runs, confirmed by the user before the first
  eval — every campaign, not just proposal time** (a repeat campaign after
  doc edits has no proposal, and the proposal's cost line is not
  per-campaign approval; mirrors trigger's workflow step 5) →
  `retrieval-suite --skill-workspace … --control-workspace …` → driver
  scores each entry from the results JSON (bullets from `answer_text`
  only; voids via `void_signals`; classifications from `tool_calls` with
  `sources_consulted` as cross-check and reasoning as fallback; control
  comparison → ablation flags) → driver writes `<campaign>/scored.json`
  (schema documented: per-entry result, missed bullets, classification,
  control result, ablation flag) → `scored-check` validates it → report
  (existing format + `artifacts:` and `manifest:` lines) → confirmed doc
  fixes → mini-campaign re-run of failed entries only (a second campaign
  dir, filtered queries file) → `record --scope dir`.
- **Reps > 1 aggregation** (driver-side scoring convention, not scripted):
  entry result = worst non-void run outcome — conservative, and consistent
  with the verdict-free strategy layer.
- **Manifest policy** — record after every completed **full** campaign
  (all entries accounted, pass or fail — a retrieval campaign with
  failures is a valid measurement of the current doc; the counts are the
  point). **Mini-campaign re-runs are never recorded**: they re-run only
  failed entries, so recording them would either write subset counts
  masquerading as a full measurement or attribute merged results measured
  against the pre-fix doc to the post-fix hash. Mini-campaigns persist as
  campaign dirs with their own scored.json — confirmation, not record.
  Post-fix state gets recorded by the next full campaign. Never record
  aborted campaigns. Never hand-edit.
- **Gotchas** — remove: session-availability, git-status contamination,
  read-only-is-a-guardrail. Add: score from `answer_text` only, never from
  reasoning or claims; keep queries verbatim including the `{RUN_DIR}`
  token; harness always user-specified; campaign artifacts never inside
  the temp workspaces; never sync the skill into the control workspace.
- **Checklist** — updated to match.

## 10. trigger-testing-skills SKILL.md touch-points

Path, CLI-surface, and manifest-location updates only; no semantic
changes:

- Script paths → `tools/test-harness/…` throughout (Inputs, Workflow,
  Gotchas, Checklist), including rewording the now-false "by their path
  inside this skill directory" phrase.
- `run`/`suite` command lines gain
  `--agents-dir skills/trigger-testing-skills/agents`.
- Manifest path: `<source-root>/skills-workspace/<skill>/manifest.json`
  (was `…/trigger-tests/manifest.json`); `record` gains
  `--scope frontmatter`.
- `check` no longer validates the agent file (binary-only) — preflight
  description updated.
- Gotcha "manifest is written only by `evaluator.py record`" reworded to
  the one-manifest-per-skill layout.

## 11. Alternatives considered

- **Central agents dir** (`tools/test-harness/agents/`) — one install
  source. Rejected: agents are per-track test definitions owned by each
  skill's semantics.
- **One shared workspace with path-scoped read denies for the control
  arm** — rejected in favor of two workspaces: the structural guarantee
  (skill bytes simply absent) does not depend on any harness permission
  path-matching behavior; `read-outside-workspace` signal adds detection
  defense-in-depth.
- **Rename `{RUN_DIR}` → `$FIXTURE_DIR`** — rejected: the existing token
  is explicit in the data, brace tokens are safer than `$VAR`, and keeping
  it preserves query-verbatim with zero exceptions.
- **Explicit `--agent-file` + `--agent-name` args** — rejected: harness
  suffix leaks into workflow docs; name/file pair is two sources of truth
  whose mismatch surfaces only after spend begins.
- **Deriving `--agent-name` but passing it explicitly anyway** — rejected:
  "agent name" is an opencode-shaped concept; harnesses without named
  primary agents would implement restriction differently. `--agents-dir`
  is expressible across harnesses.
- **Two record subcommands** instead of `record --scope` — rejected: one
  manifest writer, one flag.
- **Recording mini-campaign re-runs** — rejected: subset counts or
  cross-hash merges corrupt the manifest's "measured at this hash"
  meaning.
- **Judge-model scoring pass** — rejected: adds spend and inference
  exactly where the scripted/judgment line is drawn; the results JSON
  exists so a human/agent can evaluate.
- **Convention-based fixture detection** (stage whenever `{RUN_DIR}`
  appears, no field) — rejected: silent whole-dir copies, no pre-spend
  validation; explicit field is deterministic.
- **Keep in-session dispatch as a fallback mode** — rejected by D5.

## 12. Open questions (post-review remainder)

1. `steps: 30` and 120 s timeout defaults — reviewer-endorsed starting
   tunables; tune after the first live campaigns.
2. `denied_tool_attempts` event shape — verify against real opencode
   output at implementation; may be unobservable by construction (§5.1).
3. Whether `--pure` headless sessions persist for transcript lookup —
   unverified; mitigated by tool-call capture making offline evaluation
   independent of it.
4. Neutral agent naming to avoid leaking "evaluator" to the model —
   accepted inherited risk; revisit only if contamination is observed.

## 13. Migration plan (ordered)

1. `git mv` the four script files to `tools/test-harness/`; delete
   `__pycache__/`. Add the PEP 758 parens fix to `strategies.py`.
2. Generalize `strategies.py` (`--agents-dir` resolution, frontmatter
   name scan + stem/pin assertions, richer stream incl. tool-call
   capture, `{{SKILL_NAME}}` templating).
3. Extend `evaluator.py` (`--agents-dir` plumbing, slimmed `check`,
   `record --scope` + dir hashing, `retrieval-suite`, `scored-check`).
4. Extend `workspace-manager.sh` (`--prefix`, `--full` with aligned
   exclusions + symlink rejection).
5. Write the two retrieval agent files (no model pins).
6. Update `trigger-testing-skills/SKILL.md` (§10 touch-points).
7. Rewrite `retrieval-testing-skills/SKILL.md` sections (§9 map).
8. Migrate `skills-workspace/writing-skills/trigger-tests/manifest.json`
   → `skills-workspace/writing-skills/manifest.json`.
9. Add `"fixtures": ["existing-skill.md"]` to the `read-before-editing`
   entry in `skills-workspace/writing-skills/retrieval-tests/queries.json`
   (metadata only — query text byte-for-byte unchanged).
10. Extend `test_evaluator.py` (imports; dir-hash vectors; record scope
    validation; retrieval stream parsing incl. tool-call capture;
    `scored-check`; control-workspace absence assertion).
11. Audit: `uv run flake8`, `uv run ruff check`, `uv run black`,
    `uv run pyright`, `shellcheck`, and the unittest suite — all per
    AGENTS.md.
12. Update `AGENTS.md` project layout for `tools/` — **requires the
    requester's explicit confirmation** (repo rule).
13. Index updates (`docs/README.md`, `docs/writing-skills/part-3/README.md`)
    — left to the human; README files are not agent-edited per repo rules.

## 14. Validation

- `python3 -m unittest` in `tools/test-harness/` (stubbed subprocess; no
  live model).
- Manual smoke: one `retrieval-suite` run against the existing
  `writing-skills` retrieval queries in scratch workspaces, verifying the
  results JSON carries answer text, tool-call targets, sources, and
  signals for both arms — and that the control workspace never held the
  skill.
- `workspace-manager.sh status --full` round-trip: sync then status exits
  0; touch a reference file, status exits 1.
- `scored-check` rejects a scored.json missing one entry id and accepts a
  complete one.
- `record --scope dir` is byte-stable across repeated runs on an unchanged
  skill dir (deterministic hash).
