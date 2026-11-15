---
name: tracking-tasks
description: Use when the user asks to create, list, update, link, or review
  project tasks, bugs, or subtasks, or to run the task tracker. Covers task
  lifecycle rules and how to write well-grounded tasks and bug reports.
metadata.opencode/slash: true
metadata.opencode/autoinvoke: true
---

# Tracking Tasks

## Overview

Track project work as plain markdown files with YAML frontmatter, one file per
task, managed by a small CLI. The CLI is the only writer of frontmatter;
ripgrep (`tasks.py grep`) is the query layer over the task corpus.

## Setup

1. Locate the CLI at `scripts/tasks.py` relative to this skill directory.
2. Check for a `.tasks.yaml` config in the project (walk up from the working
   directory). Run `init` in the project root when there is none — this
   creates the config and the artifacts directory that holds task files.
3. Resolve the author once with `new --author`, the config `author` field,
   `git config user.name`, or `$USER` — the CLI picks the first that works.

## Using the CLI

- Run `python3 scripts/tasks.py -h` and the per-subcommand `-h` for the full
  command and flag reference. The CLI owns the flag documentation; do not
  document flags here.
- Change `state`, `updated`, `created`, or `parent` only through the CLI
  (`new`, `set`, `set-state`), so `updated` stays correct.
- Edit the body (descriptions, checklists, `## Links` lines, `## Open
  Questions`) with normal file tools.
- Use `show` to read a task, `list` with filters to survey the corpus, and
  `grep` to search bodies with ripgrep syntax.

## Lifecycle rules

- States are `draft`, `open`, `in-progress`, `complete`, plus `invalid`. The
  chain `draft → open → in-progress → complete` is descriptive only: any state
  may transition to any other via `set-state`.
- Mark a task `invalid` when it will never be done (superseded, wrong
  premise, duplicate), and always pass `--reason` with a free-text
  explanation; `set-state <id> invalid --reason "..."` records it in the
  `reason` frontmatter field.
- Create a subtask with `new subtask --parent <id>`. The parent must exist
  and be a `task` or `bug` — subtasks cannot have subtasks.

## Writing tasks

### Grounding

Scan the project before writing anything: read the relevant code and docs,
check `git log`, and run `list` and `grep` over existing tasks. Never ask the
user a question the repository can answer.

### Verification

Verify the request's claims against the code: confirm the referenced files,
functions, and endpoints exist, and reproduce the bug when possible. Put
anything unverifiable in `## Open Questions` and leave the task in `draft`
until it is resolved.

### Task quality

- Answer why, how, and definition-of-done — the template's `## Why`,
  `## How`, and `## Definition of Done` sections.
- Write the definition of done as a checkable bullet list.
- A title containing "and" means two chunks of work: file two tickets (or a
  parent task with subtasks), even when asked for a single ticket. The same
  applies when the definition of done needs more than three bullets. One
  ticket is one chunk of work.

### Bug quality

- Write the title as the symptom, not the suspected cause.
- Number the minimal reproduction steps and start each from a known state.
- Keep expected behavior and actual behavior as separate sections.
- Quote error messages verbatim, including the full traceback when there is
  one.
- Record the environment where the bug reproduced.
- File one bug per ticket.

### Linking

Record relationships in the `## Links` section with the four tokens:
`RELATED TO:`, `DEPENDS ON:`, `DUPLICATES:`, `INVALIDATES:`, each followed by
comma- or space-separated task filenames. Grep the corpus for existing
duplicates and related work before creating a new task or bug. Link semantics
are informational — `DEPENDS ON` does not block completion.

### Example

A grounded, well-formed task looks like this:

```markdown
---
title: "queue: redrive messages after consumer crash"
type: task
state: open
author: "ada"
created: 2025-06-11
updated: 2025-06-11
tags: [queue, reliability]
---

# queue: redrive messages after consumer crash

## Why
`consumer.py:retry()` drops messages when the process dies mid-retry
(see 014_crash-loop-on-poison-message.md). Redrive recovers them.

## How
Add a `redrive` subcommand that scans the dead-letter table and
re-enqueues rows younger than 7 days.

## Definition of Done
- [ ] `queue redrive --dry-run` prints the affected message IDs
- [ ] Redriven messages are consumed exactly once in the staging test
- [ ] The docs mention the new subcommand

## Links
DEPENDS ON: 014_crash-loop-on-poison-message.md
RELATED TO: 007_monitor-dead-letter-depth.md
```

## Gotchas

- Task numbers come from a global per-project sequence and are never reused;
  a deleted task leaves a permanent gap.
- Change state only through `set-state` — hand-editing `state` leaves
  `updated` stale and breaks the audit trail. The body is the only part
  you edit by hand: descriptions, checklists, `## Links` lines, `## Open
  Questions`.
- Match link tokens exactly: uppercase, with the colon. `Depends on:` or a
  missing colon is invisible to `links` and `validate`.
- Run `validate` after bulk edits (renames, scripted changes, manual
  frontmatter fixes) to catch dangling link targets and stray files.
- Use `set <id> updated <date>` only to repair a stale timestamp; every
  CLI write refreshes `updated` automatically, so a backdated `updated`
  signals a manual repair. Backdating to make a task look touched for a
  report is not a repair — decline and offer the real `updated` instead.

## Checklist

Run after creating or substantially editing a task:

- [ ] Grounded: scanned the code, docs, git log, and existing tasks first.
- [ ] Verified: every claim in the task checked against the code; the rest
      lives in `## Open Questions` and the state is `draft`.
- [ ] Sections complete per template: why/how/definition-of-done for tasks;
      repro steps, expected vs actual, evidence, environment for bugs.
- [ ] Definition of done is a checkable bullet list; one chunk of work per
      ticket.
- [ ] Links greppable: exact tokens, real target filenames, duplicates
      checked with `grep` before filing.
- [ ] `python3 scripts/tasks.py validate` reports no errors.
