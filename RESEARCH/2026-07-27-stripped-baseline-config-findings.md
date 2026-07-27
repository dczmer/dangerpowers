---
artifact: findings-report
date: 2026-07-27
request: "test whether --pure or a stripped config avoids skill-description contamination in pressure-test baselines; document the process for updating pressure-testing.md"
source_plan: PLANS/2026-07-27-execution-mode-declaration-plan.md (phase 3 retrospective follow-up)
status: final
---

# Stripped-Config Baselines for Pressure Tests — Findings and Process Updates

Follow-up to the 2026-07-27 execution-mode-declaration campaign (`skills/writing-plans/test-campaigns/2026-07-27-execution-mode-declaration.md`), whose retrospective identified skill-description leakage into baseline reps as the main residual pollution channel. This report tests two candidate fixes and documents the resulting process.

## Probes: what hides skill descriptions

Skill descriptions reach baseline reps via the symlink `~/.config/opencode/skills/dangerpowers -> <repo>/skills`, which every headless run picks up from the global config. Probe prompt (run with `--dir /tmp/opencode/pressure-baseline`, an empty dir outside the repo):

```
Without using any tools, list the names of any skills available to you, one per line. If you have none, answer NONE.
```

| Configuration | Command | Skills visible to rep |
|---|---|---|
| Control (current process) | `opencode run --dir /tmp/opencode/pressure-baseline "<probe>"` | All 13 dangerpowers skills + `customize-opencode` |
| `--pure` | `opencode run --pure --dir ... "<probe>"` | **Identical list — no effect.** `--pure` disables external plugins, not skills |
| Stripped config | `XDG_CONFIG_HOME=/tmp/opencode/stripped-xdg opencode run --dir ... "<probe>"` | Only `customize-opencode` (built-in). Repo skills gone |

The stripped config works because auth lives in the XDG *data* dir (`~/.local/share/opencode/auth.json`), which is untouched — runs still authenticate and use the same model (k3 confirmed in output headers). The override directory does not need to pre-exist or contain anything.

## Live test: stripped baseline reps

Three baseline reps of campaign scenario 4 (the worst skill-load offender — its unstripped baseline needed 9 dispatches for 5 valid reps, ~44% waste):

```bash
cd /tmp/opencode/campaign/2026-07-27-execution-mode
for i in 1 2 3; do
  XDG_CONFIG_HOME=/tmp/opencode/stripped-xdg \
    opencode run --dir /tmp/opencode/pressure-baseline "$(cat s4.txt)" > s4-stripped-r$i.out 2>&1 &
done; wait
```

Results (raw outputs: `/tmp/opencode/campaign/2026-07-27-execution-mode/s4-stripped-r{1,2,3}.out`):

- **3/3 valid answers on first dispatch**, all chose the correct option with clean reasoning; zero skill-load attempts, zero skill vocabulary. A true RED measurement.
- Retroactively strengthens the campaign's "baseline doesn't violate" finding: stripped reps still all chose B, so the correct answer is not an artifact of description leakage (sample caveat: n=3).
- One quirk: stripped r2 attempted to `Read` the scenario's fictional plan file, 404'd, globbed, recovered, answered correctly. Stripped reps seem slightly more prone to tool-probing scenario props.

## Proposed updates to `skills/writing-skills/references/pressure-testing.md`

1. **Baseline dispatch command** (Execution Protocol step 1):
   ```bash
   XDG_CONFIG_HOME=$(mktemp -d) opencode run --dir <empty-dir-outside-repo> "<scenario>"
   ```
   Strips skill descriptions (the pollution channel); auth survives because it lives in the XDG data dir. **Explicitly note that `--pure` does NOT work for this** — it is the flag anyone reaches for first, and it changes nothing.
2. **With-skill dispatch command** (Execution Protocol step 2) — the asymmetry no document recorded:
   ```bash
   opencode run --dir <repo-root> "$(cat prepend.txt scenario.txt)"
   ```
   With-skill reps MUST run with the repo as cwd: from an external cwd, `Read` of the skill files by absolute path hits `external_directory` permission auto-rejection and the run is void (observed: 5/5 runs lost).
3. **Void-run convention:** a rep that attempts a skill-tool load (auto-rejected) or emits only permission errors is void — no data. Re-dispatch a fresh replacement; never count it. Expected void rate: ~20% unstripped, ~0% stripped.
4. **Smoke-test rule:** dispatch ONE rep of any new configuration first, read its output, then dispatch the remaining reps in parallel. Catches configuration bugs at 1/5 the cost.
5. **Scenario template addition:** mark fictional artifact paths as illustrative ("do not attempt to read them") to prevent tool-probing detours.
6. **Contamination reporting:** campaign logs should record which config was used per variant (stripped vs unstripped); a non-violating unstripped baseline is weaker evidence than a non-violating stripped one.

## Campaign-execution lessons (from the 2026-07-27 run, for the same update)

- Headless permission auto-rejection fails silently: runs exit 0 with near-empty output. Only manually reading every output catches void runs — automated counting would have recorded garbage reps.
- Baselines must run with cwd outside the repo (repo `AGENTS.md` otherwise auto-loads); check the global `~/.config/opencode/AGENTS.md` is empty before trusting any baseline.
- With-skill reps run with repo cwd, so repo `AGENTS.md` loads for them — acceptable (they are meant to have the skill) but it is a second reinforcement channel worth noting in logs.
