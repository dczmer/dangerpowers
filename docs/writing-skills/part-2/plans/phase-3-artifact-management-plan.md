# Phase 3: Artifact Management — Implementation Plan

Companion to `developing-a-better-harness.md`, section "Artifact Management" (the
deferred "next phase" item from phases 2a–2c). This plan is decision-complete:
every choice below is either a locked decision from the design review or an
explicitly registered assumption (see "Assumptions register"). The implementing
agent should not introduce new decisions; anything ambiguous is called out here
with the chosen behavior.

**Scope: persistent campaign artifacts and a test-status manifest.** This phase
replaces the ephemeral campaign scratch dir (`/tmp/trigger-test-campaign.*`) with
persistent, per-campaign directories under `skills-workspace/<skill>/trigger-tests/`,
captures full campaign logs to files, persists per-iteration description revisions,
and adds a `manifest.json` recording the last successful trigger test (date, score,
skill-file checksum). The temp **eval workspace** (`/tmp/trigger-test.*`) lifecycle
is unchanged.

NOT in scope: pi/claude harness strategies, retries/budget enforcement, recording
failed campaigns in the manifest, pruning/rotation of old campaign dirs.

**Line-number caveat.** Line numbers below are as of commit `3ea7e64` (2026-09-02)
and are paired with file paths and section/heading names throughout. Per AGENTS.md,
the path + heading references are authoritative; line numbers drift as edits land.

## Locked decisions (from design review with the user, 2026-09-02)

1. **Checksum = sha256 of the whole `SKILL.md`**, computed at record time — i.e.
   *after* the write-back decision resolves, so the checksum covers the validated
   description (post-write-back file, or the unchanged file when the winner is the
   source description).
2. **Manifest score = validate score**, falling back to the winner's train score
   when no validate set exists (the <= 10 queries case).
3. **Successes only in the manifest.** A campaign is recorded only when the sanity
   check passed AND the write-back decision is resolved (write-back applied, or
   winner == source). A declined write-back is NOT recorded — the source checksum
   would falsely attribute the score to the untested old description. Failed and
   inconclusive campaigns are never recorded; their campaign dir is the only record.
4. **Logs are captured script-side** in `evaluator.py` (no agent-side `tee`, no
   pipefail fragility).
5. **The manifest is written by a new `evaluator.py record` subcommand** —
   deterministic and unit-testable, per the "AI never does math/counting" principle.
6. **Campaign dirs are committed to git.** No `.gitignore` change; repo growth is
   accepted (manual pruning later if ever needed).

## Deliverables

- **Modified:** `skills/trigger-testing-skills/scripts/workspace-manager.sh` — new
  `campaign-init` subcommand.
- **Modified:** `skills/trigger-testing-skills/scripts/evaluator.py` — suite log
  capture; new `record` subcommand.
- **Modified:** `skills/trigger-testing-skills/scripts/test_evaluator.py` — tests
  for `record` (and any logging seams worth pinning).
- **Modified:** `skills/trigger-testing-skills/SKILL.md` — campaign-dir workflow,
  manifest recording rule, updated diagram/report/error-handling/gotchas/checklist.
- **Unchanged:** `skills/trigger-testing-skills/agents/trigger-evaluator.opencode.md`;
  the eval-workspace lifecycle in `workspace-manager.sh` (`init`/`sync`/`status`/
  `cleanup`); `queries.json` handling (already at the target path per the phase-2c
  locked decision on the `trigger-tests/` convention); `docs/README.md` (phase plans
  are not indexed there today).
- **Conditional:** one-line `AGENTS.md` layout note about campaign dirs — applied
  only with the user's explicit confirmation (repo rule).

## Target layout

```
<source-root>/skills-workspace/<skill>/trigger-tests/
├── queries.json                        # existing; unchanged
├── manifest.json                       # NEW — written only by `evaluator.py record`
└── campaign-YYYY-MM-DD[-N]/            # NEW — one per campaign, always kept
    ├── split.json                      # seed + sizes (existing split output)
    ├── train.json / validate.json      # the split sets
    ├── sealed-pool.json                # 3 fresh sanity queries for this campaign
    ├── iter-1-train.json / .log        # per-iteration suite result + full log
    ├── iter-1-description.md           # the description iteration 1 evaluated
    ├── iter-2-train.json / .log        #   (iteration 1 = the source description)
    ├── iter-2-description.md
    ├── validate-results.json / .log    # held-out pass (when validate non-empty)
    ├── sanity.json                     # the single sealed query actually used
    └── sanity-results.json / .log
```

Manifest schema (real JSON; only the `trigger-test` key is managed this phase —
unknown keys must be preserved for future test types):

```json
{
  "skill": "writing-skills",
  "trigger-test": {
    "date": "2026-09-02",
    "checksum": "sha256:<hex of the whole SKILL.md>",
    "score": 0.81,
    "campaign": "campaign-2026-09-02"
  }
}
```

Record-decision flow (locked decision 3):

```
sanity check outcome
├── fail / inconclusive ──> no record; campaign dir is the only artifact
└── pass
    ├── winner == source ──────────────> record (checksum of unchanged file)
    ├── write-back confirmed + applied ─> record (checksum of post-write-back file)
    └── write-back declined ───────────> NO record
```

## Step 1 — `workspace-manager.sh`: add `campaign-init`

File: `skills/trigger-testing-skills/scripts/workspace-manager.sh`.

**1a. Usage text** (usage block, command list currently at lines 6–10): add after
the `init` line:

```
  trigger-test.sh campaign-init --root DIR
```

and in the description block (currently lines 12–19), after the `init` description:

```
campaign-init creates one persistent campaign directory under --root, named
        campaign-YYYY-MM-DD (suffixed -2, -3, ... on same-day reruns), and
        prints its path on stdout.
```

(The usage block's `trigger-test.sh` name is a pre-existing inconsistency with the
actual filename; out of scope — see assumption 6.)

**1b. New function**, placed directly after `cmd_init` (currently lines 32–37):

```bash
cmd_campaign_init() {
  local root=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --root) root="$2"; shift 2 ;;
      *) usage ;;
    esac
  done
  [ -n "$root" ] || { echo "error: --root DIR is required" >&2; usage; }
  local datestamp base dir n
  datestamp="$(date +%F)"
  base="$root/campaign-$datestamp"
  dir="$base"
  n=2
  while [ -e "$dir" ]; do
    dir="$base-$n"
    n=$((n + 1))
  done
  mkdir -p "$dir"
  echo "$dir"
}
```

`mkdir -p "$dir"` also creates a missing `--root` (first campaign for a skill).
No removal logic, so no path-prefix paranoia is needed here (unlike `cleanup`).

**1c. Dispatcher** (currently lines 111–116): add after the `init)` arm:

```bash
  campaign-init) cmd_campaign_init "$@" ;;
```

## Step 2 — `evaluator.py`: suite log capture

File: `skills/trigger-testing-skills/scripts/evaluator.py`.

Design: a module-level log handle plus an `emit()` helper; `cmd_suite` opens
`<out>.with_suffix(".log")` (write mode — one fresh log per suite invocation, e.g.
`iter-1-train.log`, `validate-results.log`, `sanity-results.log`) right after the
`--out` parent-dir check, and every progress line goes through `emit()`. `cmd_run`
never sets the handle, so single-query debugging stays stdout-only. stdout behavior
is unchanged in all cases.

**2a. Helper**, inserted at the top of the "Batch mechanics" section (immediately
before `log_start`, currently line 366):

```python
_log_file = None  # campaign log handle; set by cmd_suite, None under `run`


def emit(msg: str = "", *, err: bool = False) -> None:
    """Print a progress line and mirror it to the campaign log when one is set."""
    print(msg, file=sys.stderr if err else sys.stdout, flush=True)
    if _log_file is not None:
        _log_file.write(msg + "\n")
        _log_file.flush()
```

**2b. Repoint prints to `emit()`:**

| Location (as of 3ea7e64) | Current | Change |
|---|---|---|
| `log_start`, line 367 | `print(f"[rep {n:>3}] started", flush=True)` | `emit(...)` |
| `log_complete`, line 376 | `print(line, flush=True)` | `emit(line)` |
| `eval_batch` smoke-rep error, lines 397–398 | two `print(..., file=sys.stderr)` | `emit(..., err=True)` (keep `sys.exit(1)`) |
| `eval_batch` batch-abort error, lines 419–421 | three `print(..., file=sys.stderr)` | `emit(..., err=True)` (keep `sys.exit(1)`) |
| `cmd_suite` header, lines 663–667 | `print(...)` x3 | `emit(...)` |
| `cmd_suite` empty-query note, line 657 | `print("note: ...")` | `emit(...)` |
| `cmd_suite` per-query line, lines 690–692 | `print(..., flush=True)` | `emit(...)` |
| `cmd_suite` final tally, lines 709–710 | `print(f"suite: ...")` | `emit(...)` |

`print_report` (used only by `cmd_run`) keeps plain `print`. All pre-spend
validation errors (`load_queries`, arg checks, `check_harness`) keep plain
stderr prints — they run before the log opens (assumption 2).

**2c. Open the log in `cmd_suite`.** Add `global _log_file` at the top of
`cmd_suite` (currently starts line 623), and open the log immediately after the
`--out` parent check (currently lines 641–645), before the `empty_result`
definition:

```python
    log_path = out.with_suffix(".log")
    _log_file = log_path.open("w")
```

No explicit close on the success path (process exit closes it); `emit` flushes
every line, and abort paths `sys.exit(1)` after emitting the error, so the log
always contains the abort reason.

## Step 3 — `evaluator.py`: new `record` subcommand

**3a. Imports** (currently lines 13–24): add `hashlib` to the stdlib import block
(alphabetical: between `argparse` and `json`) and add the datetime import to the
from-import block (between `dataclasses` and `pathlib`):

```python
import hashlib
from datetime import date
```

**3b. `cmd_record`**, placed after `cmd_suite`'s `return 0` (currently line 711),
before the `main()` section comment:

```python
def cmd_record(args: argparse.Namespace) -> int:
    """Write/update trigger-tests/manifest.json after a successful campaign.
    Overwrites only the `trigger-test` key; unknown keys are preserved."""
    skill_md = Path(args.skill_path)
    if not skill_md.exists():
        print(f"error: skill file not found: {skill_md}", file=sys.stderr)
        return 1
    if not (0.0 <= args.score <= 1.0):
        print("error: --score must be in [0, 1]", file=sys.stderr)
        return 1
    checksum = "sha256:" + hashlib.sha256(skill_md.read_bytes()).hexdigest()

    manifest = Path(args.manifest)
    data: dict = {}
    if manifest.exists():
        try:
            data = json.loads(manifest.read_text())
        except json.JSONDecodeError as e:
            print(f"error: invalid JSON in {manifest}: {e}", file=sys.stderr)
            return 1
        if not isinstance(data, dict):
            print(f"error: {manifest}: expected a JSON object",
                  file=sys.stderr)
            return 1

    entry = {"date": args.date or date.today().isoformat(),
             "checksum": checksum, "score": args.score}
    if args.campaign is not None:
        entry["campaign"] = args.campaign
    data["skill"] = args.skill
    data["trigger-test"] = entry

    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(data, indent=2) + "\n")
    print(f"recorded: {manifest} "
          f"(date {entry['date']}, score {args.score}, {checksum[:26]}…)")
    return 0
```

A malformed existing manifest fails loudly and leaves the file untouched (never
clobbered).

**3c. Argparse** in `main()`, after the `suite` subparser block (currently lines
739–748):

```python
    record = sub.add_parser("record")
    record.add_argument("--skill", required=True)
    record.add_argument("--skill-path", required=True)
    record.add_argument("--manifest", required=True)
    record.add_argument("--score", type=float, required=True)
    record.add_argument("--campaign")
    record.add_argument("--date")
```

**3d. Dispatch** (currently lines 751–757): insert before `return cmd_run(args)`:

```python
    if args.command == "record":
        return cmd_record(args)
```

Canonical invocation (what SKILL.md will instruct):

```bash
python3 skills/trigger-testing-skills/scripts/evaluator.py record \
  --skill <name> \
  --skill-path <resolved SKILL.md> \
  --manifest <source-root>/skills-workspace/<skill>/trigger-tests/manifest.json \
  --score <validate score; else winner train score> \
  --campaign <campaign dir name, e.g. campaign-2026-09-02-2>
```

## Step 4 — `test_evaluator.py`: tests for `record`

File: `skills/trigger-testing-skills/scripts/test_evaluator.py` (unittest; run from
the scripts dir so `import evaluator` resolves).

**4a. Imports** (currently lines 9–13): add `argparse`, `hashlib`, `tempfile`.

**4b. New `RecordTests` class**, inserted after `VerdictTests` (ends line 133),
before the `if __name__ == "__main__"` guard (line 136):

```python
class RecordTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.skill_md = self.root / "SKILL.md"
        self.skill_md.write_text("---\nname: test-skill\n---\nbody\n")
        self.manifest = self.root / "trigger-tests" / "manifest.json"

    def tearDown(self):
        self.tmp.cleanup()

    def _record(self, **overrides) -> int:
        args = argparse.Namespace(
            skill="test-skill", skill_path=str(self.skill_md),
            manifest=str(self.manifest), score=0.81,
            campaign="campaign-2026-09-02", date=None)
        for k, v in overrides.items():
            setattr(args, k, v)
        return evaluator.cmd_record(args)

    def test_creates_manifest_with_schema(self):
        # parent dirs created; skill/date/checksum/score/campaign present
    def test_checksum_is_whole_file_sha256(self):
        # "sha256:" + hashlib.sha256(skill_md.read_bytes()).hexdigest()
    def test_update_preserves_unknown_keys(self):
        # pre-write {"future-test": {...}}; re-record; both keys present,
        # trigger-test overwritten
    def test_malformed_manifest_refused_untouched(self):
        # write "not json"; rc == 1; file content unchanged
    def test_missing_skill_file(self):
        # rc == 1, no manifest created
    def test_campaign_omitted_when_not_given(self):
        # campaign=None -> "campaign" key absent from entry
    def test_score_out_of_range(self):
        # score=1.5 -> rc == 1
```

## Step 5 — `SKILL.md`: campaign-dir workflow + manifest rule

File: `skills/trigger-testing-skills/SKILL.md` (169 lines as of 3ea7e64).
Edits are listed in file order. Mechanical path substitutions (`<scratch>` →
`<campaign>`) are called out individually so none is missed.

**5a. Overview, second paragraph (line 15).** Extend the scripts sentence:
"Looping, counting, splitting, and scoring all live in the scripts" →
"Looping, counting, splitting, scoring, and manifest recording all live in the
scripts". No other Overview change.

**5b. Replace the "## Campaign scratch" section (lines 27–29)** with:

```markdown
## Campaign directory

Create one persistent directory per campaign via `workspace-manager.sh campaign-init --root <source-root>/skills-workspace/<skill>/trigger-tests` — named `campaign-YYYY-MM-DD`, suffixed `-2`, `-3`, … on same-day reruns; the command prints the path. It holds the split files, per-round result JSON and logs, the sealed pool, and per-iteration description copies. Keeping these out of the temp eval workspace preserves the sterile testbed: eval reps run with `--dir <ws>`, so artifacts under the source root are invisible to them. The campaign dir is never removed — pass, fail, or abort, it is the persistent record of the run and is committed to the repo.
```

**5c. Mermaid diagram (lines 35–64).** Three edits:

- Line 38: `D["3. Workspace init + sync + status; create scratch dir"]` →
  `D["3. Workspace init + sync + status; campaign-init"]`
- Line 41: `SP --> F["6. Sealed pool — 3 fresh queries written to scratch"]` →
  `... written to the campaign dir"]`
- Lines 59–63, insert the record node per locked decision 3. Current:

```mermaid
    S["replace only the description field in source SKILL.md"]
    S --> P["12. Cleanup — remove workspace + scratch"]
    R -->|"no"| P
    QN --> P
    O --> P
```

New:

```mermaid
    S["replace only the description field in source SKILL.md"]
    S --> REC["record manifest — evaluator.py record"]
    QN --> REC
    REC --> P["12. Cleanup — remove workspace"]
    R -->|"no"| P
    O --> P
```

**5d. Step 3 (line 71).** Replace "Create the scratch dir." with:

```markdown
Create the campaign dir: `workspace-manager.sh campaign-init --root <source-root>/skills-workspace/<skill>/trigger-tests` (prints the path; same-day reruns get a `-2`, `-3`, … suffix). All artifact paths below live inside this `<campaign>` dir.
```

**5e. Step 4 (line 72).** `--out-dir <scratch>` → `--out-dir <campaign>`;
`<scratch>/split.json` → `<campaign>/split.json`.

**5f. Step 5 (line 73).** `<scratch>/split.json` → `<campaign>/split.json`.

**5g. Step 6 (line 74).** `<scratch>/sealed-pool.json` →
`<campaign>/sealed-pool.json`. Append the freshness rule:

```markdown
Old campaign dirs keep their sealed pools as history; every campaign generates a fresh pool — never reuse one.
```

**5h. Step 7a (line 76).** `--queries <scratch>/train.json --out <scratch>/iter-<i>-train.json`
→ `--queries <campaign>/train.json --out <campaign>/iter-<i>-train.json`. Append:
"the suite mirrors all progress output to `<campaign>/iter-<i>-train.log`".

**5i. Step 7b (line 77).** Append the persistence rule (crediting matches the
phase-2c rule — the file is named for the iteration that EVALUATED the
description, so `iter-1-description.md` holds the source description):

```markdown
Save the evaluated description to `<campaign>/iter-<i>-description.md` (a frontmatter-only copy of the stub as evaluated this iteration).
```

**5j. Step 9 (line 80).** `<scratch>/validate.json` → `<campaign>/validate.json`;
`<scratch>/validate-results.json` → `<campaign>/validate-results.json`.

**5k. Step 10 (line 81).** `<scratch>/sanity.json` → `<campaign>/sanity.json`;
`<scratch>/sanity-results.json` → `<campaign>/sanity-results.json`.

**5l. Step 11 (line 82).** Append the manifest rule (locked decisions 1–3):

```markdown
On a passed sanity check, after the write-back decision is resolved, record the result: `evaluator.py record --skill <name> --skill-path <resolved SKILL.md> --manifest <source-root>/skills-workspace/<skill>/trigger-tests/manifest.json --score <validate score; the winner's train score when no validate set exists> --campaign <campaign dir name>`. Record only when write-back was applied (the checksum then covers the winning description) or the winner IS the source description. Never record a declined write-back — the source checksum would falsely attribute the score to the untested description — and never record failed or inconclusive campaigns; their campaign dir is the only record.
```

**5m. Step 12 (line 83).** Replace with:

```markdown
12. **Cleanup.** On completion (pass or fail): `workspace-manager.sh cleanup --workspace <ws>`. The campaign dir is never removed. On abort/error: keep the workspace; print its path and the campaign dir path for debugging.
```

**5n. Description revision mechanics (lines 107–109).** Append one sentence:
"Every evaluated description is also saved to the campaign dir as
`iter-<i>-description.md` (workflow step 7b), so the winning revision is auditable
after the campaign."

**5o. Report format (lines 111–131).** In the example block, add an `artifacts:`
line directly under the header line (the header's `campaign: writing-skills`
already means the skill name — do NOT reuse that key), and a `manifest:` line after
the sanity line:

```
campaign: writing-skills   harness: opencode   model: <m>   variant: <v>
artifacts: skills-workspace/writing-skills/trigger-tests/campaign-2026-09-02/
...
sanity: "<sealed query>" -> triggered 9/10 -> pass
manifest: updated (score 0.810, sha256:d034c1…)
```

Annotate below the block: the `manifest:` line reads `updated (...)` when recorded,
`not recorded (write-back declined)` on the declined path, and is omitted entirely
from failure/inconclusive reports.

**5p. Error handling (line 139).** "keep workspace and scratch, print their paths"
→ "keep the workspace; print its path and the campaign dir path (campaign
artifacts persist by design)".

**5q. Gotchas (lines 143–153).** Append two bullets:

```markdown
- Campaign artifacts (split files, result JSON, logs, sealed pool, per-iteration description copies) live in the persistent campaign dir under `trigger-tests/`; never inside the temp eval workspace.
- The manifest is written only by `evaluator.py record`, only after a passed sanity check and a resolved write-back decision; never hand-write or edit it mid-campaign.
```

**5r. Checklist (lines 155–169).** Update/add:

- Before the split-seed item (line 161): add
  `- [ ] Campaign dir created via campaign-init; every artifact path points inside it`
- Add after the "--out" item (line 162):
  `- [ ] Each iteration's evaluated description saved to <campaign>/iter-<i>-description.md`
- Add after the write-back item (line 168):
  `- [ ] Manifest recorded via `record` on sanity pass after the write-back decision; declined write-back NOT recorded`
- Line 169: `Workspace + scratch removed on completion; kept and reported on abort` →
  `- [ ] Workspace removed on completion (kept and reported on abort); campaign dir always kept`

## Verification (exact commands)

Run from the repo root unless noted. No campaign spend is required for any of this.

```bash
# 1. Unit tests (cwd must be the scripts dir for `import evaluator`)
cd /home/dave/source/dangerpowers/skills/trigger-testing-skills/scripts
python3 test_evaluator.py -v
```

```bash
# 2. Shell syntax + lint
cd /home/dave/source/dangerpowers
bash -n skills/trigger-testing-skills/scripts/workspace-manager.sh
command -v shellcheck >/dev/null && \
  shellcheck skills/trigger-testing-skills/scripts/workspace-manager.sh || true
```

```bash
# 3. campaign-init smoke: same-day suffixing
rm -rf /tmp/phase3-smoke
skills/trigger-testing-skills/scripts/workspace-manager.sh campaign-init \
  --root /tmp/phase3-smoke/trigger-tests
skills/trigger-testing-skills/scripts/workspace-manager.sh campaign-init \
  --root /tmp/phase3-smoke/trigger-tests
ls /tmp/phase3-smoke/trigger-tests/
# expect: campaign-<today>  campaign-<today>-2
```

```bash
# 4. record smoke: schema + checksum
python3 skills/trigger-testing-skills/scripts/evaluator.py record \
  --skill writing-skills \
  --skill-path skills/writing-skills/SKILL.md \
  --manifest /tmp/phase3-smoke/trigger-tests/manifest.json \
  --score 0.81 --campaign "campaign-$(date +%F)"
cat /tmp/phase3-smoke/trigger-tests/manifest.json
sha256sum skills/writing-skills/SKILL.md   # must match the checksum field (minus the "sha256:" prefix)
```

```bash
# 5. record preserves unknown keys
python3 - <<'EOF'
import json, pathlib
p = pathlib.Path("/tmp/phase3-smoke/trigger-tests/manifest.json")
d = json.loads(p.read_text())
d["future-test"] = {"date": "x"}
p.write_text(json.dumps(d))
EOF
python3 skills/trigger-testing-skills/scripts/evaluator.py record \
  --skill writing-skills --skill-path skills/writing-skills/SKILL.md \
  --manifest /tmp/phase3-smoke/trigger-tests/manifest.json --score 0.9
python3 -c "import json; d=json.load(open('/tmp/phase3-smoke/trigger-tests/manifest.json')); assert 'future-test' in d and d['trigger-test']['score']==0.9; print('ok')"
```

```bash
# 6. malformed manifest refused (exit 1, file untouched)
echo 'not json' > /tmp/phase3-smoke/trigger-tests/manifest.json
python3 skills/trigger-testing-skills/scripts/evaluator.py record \
  --skill writing-skills --skill-path skills/writing-skills/SKILL.md \
  --manifest /tmp/phase3-smoke/trigger-tests/manifest.json --score 0.9
echo "exit=$?"   # expect exit=1; file still contains 'not json'
```

```bash
# 7. split into a campaign dir (no harness spend)
python3 skills/trigger-testing-skills/scripts/evaluator.py split \
  --queries skills-workspace/writing-skills/trigger-tests/queries.json \
  --out-dir "/tmp/phase3-smoke/trigger-tests/campaign-$(date +%F)" --seed 42
ls "/tmp/phase3-smoke/trigger-tests/campaign-$(date +%F)"
# expect: split.json  train.json  validate.json
```

```bash
# 8. cleanup
rm -rf /tmp/phase3-smoke
```

## Skill-level live validation (requires harness spend)

Run in a live session after the script checks pass, mirroring the phase-2c
validation style:

1. **Mini-campaign, no-split path:** invoke the skill against `writing-skills`
   with a <= 10-query file, `--reps 3`, cheap model. Expected: a
   `campaign-YYYY-MM-DD/` dir under
   `skills-workspace/writing-skills/trigger-tests/` containing `split.json`,
   `train.json`, `validate.json` (empty), `sealed-pool.json`,
   `iter-*-train.json` + matching `.log` files, `iter-*-description.md`,
   `sanity.json`, `sanity-results.json` + `.log`. Logs contain the full suite
   progress output.
2. **Write-back "yes":** answer yes at the confirmation. Expected: only the
   `description` field changed in the source; `manifest.json` updated with
   `checksum == sha256sum` of the post-edit file, `score` = winner's train score
   (no validate set on this path), `campaign` = the dir name.
3. **Write-back "no":** rerun and decline. Expected: source untouched AND
   `manifest.json` NOT updated (locked decision 3); report shows
   `manifest: not recorded (write-back declined)`.
4. **Second same-day campaign:** verify the new dir is `campaign-YYYY-MM-DD-2`.
5. **Abort path:** force a harness failure (e.g. unreachable model). Expected:
   campaign dir retained with partial artifacts and the abort reason in the
   current iteration's `.log`; workspace kept; both paths printed; no manifest
   change.

## Assumptions register (flag any you want reversed before implementation)

1. The manifest key is `trigger-test` (matching the user's schema sketch); the
   directory stays `trigger-tests/` (phase-2c locked decision 8). No unification
   this phase.
2. Log files are named `out.with_suffix(".log")`, opened in write mode per suite
   invocation. Output printed before the `--out` parent check (including the
   `check_harness` "ok" line) is not logged.
3. `record` defaults the date to local `date +%F`; `--date` exists as an override
   for tests/backfills.
4. `record` rejects scores outside [0, 1] and checksums the whole SKILL.md at
   invocation time; skill-name (`--skill`) and skill-file (`--skill-path`) are
   separate arguments because a name alone doesn't locate the file.
5. Campaign dirs are committed; repo growth accepted. No rotation/pruning
   mechanism this phase.
6. `campaign-init` is the only new workspace-manager subcommand; the usage
   block's pre-existing `trigger-test.sh` naming inconsistency is left as-is.
7. Per-iteration description files are credited to the iteration that evaluated
   them (`iter-<i>-description.md` written at step 7b; iteration 1 = source
   description) — same crediting rule as phase 2c, avoiding the off-by-one noted
   in the dev notes.
8. `docs/README.md` is not updated (phase plans are not indexed there today);
   `AGENTS.md` gets a one-line layout note only with the user's confirmation.
9. `emit()` uses a module-global log handle rather than threading a parameter
   through `eval_batch`/`run_rep` — smallest diff, and `cmd_run` simply never
   sets it.

## Known limitations / accepted risks

- Same-day suffix allocation is an existence check, not a lock — fine for
  agent-driven serial campaigns; two concurrent same-day campaigns on one skill
  could race (accepted).
- The manifest records only the latest successful campaign; history lives in the
  campaign dirs, not the manifest.
- Single-query `run` output is not logged (debug-only path).
- Old sealed pools persist in the repo; the "never train on sealed queries"
  policy (not deletion) is what protects them — now stated explicitly in SKILL.md.
- Failed/inconclusive campaigns leave no manifest trace by design; the campaign
  dir (including per-iteration logs with abort reasons) is the record.
