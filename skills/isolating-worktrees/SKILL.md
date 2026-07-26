---
name: isolating-worktrees
description: Use when starting feature work that needs an isolated checkout, when setting up workspaces for executing-plans phase executors (especially parallel ones), or when you need the correct git worktree commands and procedures. Keywords: git worktree, isolated workspace, .worktrees, worktree add, linked worktree, branch isolation, parallel executors.
---

# Isolating Worktrees

Create an isolated git worktree so work proceeds without touching the current checkout. Four steps, in order: detect, create, set up, verify. executing-plans executors assume isolation is provided by the orchestration layer — this skill is that layer.

## Step 0: Detect Existing Isolation

Before creating anything, find out where you are:

```bash
GIT_DIR=$(cd "$(git rev-parse --git-dir)" 2>/dev/null && pwd -P)
GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" 2>/dev/null && pwd -P)
BRANCH=$(git branch --show-current)
```

- **`GIT_DIR != GIT_COMMON`:** you are already inside a linked worktree. Do not create another one — skip to Step 2. First rule out a submodule, which shows the same signature:
  ```bash
  git rev-parse --show-superproject-working-tree 2>/dev/null
  ```
  If this prints a path, you are in a submodule, not a worktree — treat it as a normal repo.
- **`GIT_DIR == GIT_COMMON` (or submodule):** normal checkout. Proceed to Step 1.

Report what you found: on a branch, "Already in isolated workspace at `<path>` on branch `<name>`"; on a detached HEAD, note that branch creation is needed at finish time.

## Step 1: Create the Worktree

### Directory selection

Priority order — explicit user instruction always wins:

1. A declared worktree directory preference from the user or your instructions.
2. An existing project-local directory: `.worktrees/` preferred, `worktrees/` accepted; if both exist, use `.worktrees/`.
3. Default: `.worktrees/` at the project root.

### Ignore verification (project-local directories only)

Before creating the worktree, confirm the directory is ignored:

```bash
git check-ignore -q .worktrees 2>/dev/null || git check-ignore -q worktrees 2>/dev/null
```

If it is not ignored, add the entry to `.gitignore`, commit that change, then proceed. An unignored worktree directory can be swept into a commit by a later `git add -A`.

### Create

```bash
git worktree add "$LOCATION/$BRANCH_NAME" -b "$BRANCH_NAME"
cd "$LOCATION/$BRANCH_NAME"
```

For pipeline work, derive both names from the artifact being implemented (e.g. plan `PLANS/2026-07-26-payments-retry-plan.md` → branch and directory `payments-retry`).

If `git worktree add` fails with a permission error (sandbox denial), tell the user and work in the current directory instead.

## Step 2: Project Setup

A fresh worktree contains only tracked files — gitignored and untracked files (`.env`, local config, caches) from the main checkout do not exist here. Re-create whatever the project needs, then install dependencies per the project's own tooling:

```bash
[ -f package.json ] && npm install
[ -f Cargo.toml ] && cargo build
[ -f requirements.txt ] && pip install -r requirements.txt
[ -f go.mod ] && go mod download
```

## Step 3: Verify Baseline

Run the project's test suite before starting work. A clean baseline is what lets later failures be attributed to the new work.

- **Tests pass:** report ready:
  ```
  Worktree ready at <full-path>
  Tests passing (<N> tests, 0 failures)
  Ready to implement <feature-name>
  ```
- **Tests fail:** report the failures with evidence and ask whether to proceed. Do not report ready on a red baseline, and do not fix out-of-scope failures yourself as part of setup.

## Quick Reference

| Situation | Action |
|-----------|--------|
| `GIT_DIR != GIT_COMMON`, not a submodule | Already in a worktree; skip to Step 2 |
| `--show-superproject-working-tree` prints a path | Submodule; treat as normal repo |
| Detached HEAD in existing worktree | Use it; note branch needed at finish |
| `.worktrees/` and `worktrees/` both exist | Use `.worktrees/` |
| Neither exists | Check instructions, else default `.worktrees/` |
| Directory not ignored | Add to `.gitignore`, commit, then create |
| Permission error on `worktree add` | Tell user; work in place |
| Baseline tests fail | Report with evidence; ask before proceeding |
| No manifest files found | Skip dependency install |
