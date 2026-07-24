# research-findings.md Template

**Load this when writing the research-findings.md artifact.**

Contract: `research-findings.md` is the skill's only output. It must be complete enough that a downstream consumer (human or agent) never needs to redo the research. Fill every section. "None" is a valid entry; a missing section is not.

## The Template

```markdown
---
artifact: research-findings
date: YYYY-MM-DD
git_commit: <full commit hash at research time>
branch: <branch name>
request: <the user's request, verbatim>
status: complete | partial
---

# Research Findings

## 1. Request Summary

Precise restatement of what was asked, plus explicit scope:

- **In scope:** ...
- **Out of scope:** ...

## 2. File Map

Full paths grouped by purpose, one-line role each. Directory file counts and observed naming conventions. No file contents.

### Implementation
- `path/to/file.ext` — one-line role

### Tests
- `path/to/test.ext` — one-line role (or "no tests found" per implementation file)

### Configuration
- ...

### Type Definitions
- ...

### Documentation
- ...

### Entry Points
- ...

### Related Directories
- `path/to/dir/` — N files; naming convention: ...

## 3. Implementation Analysis

- **Overview:** ...
- **Entry points:** `file:line` — ...
- **Exit points:** `file:line` — ...
- **Data flow:** numbered trace, each step cited `file:line`
  1. `file:line` — ...
- **Key logic:** ...
- **Error handling:** ...
- **Configuration & flags:** ...

Every claim in this section carries a `file:line` citation.

## 4. Patterns & Idioms

Each pattern: name, location, working snippet, key aspects. ALL variations shown; none recommended.

### Pattern: <name>
- **Location:** `file:line`
- **Snippet:**
  ```<lang>
  <working code>
  ```
- **Key aspects:** ...

### Testing Patterns
Never empty when tests exist. Snippet + location per test pattern.

### Pattern Usage Map
| Pattern | Used at |
|---------|---------|
| <name> | `file:line`, `file:line` |

## 5. References & Usages

For each affected symbol:

### `<symbol>`
- **Definition:** `file:line`
- **Call sites / dependents:** `file:line`, `file:line` (or explicit "no callers found")

## 6. Agent Provenance

| Sub-agent | Asked to | Outcome |
|-----------|----------|---------|
| Locator | ... | one-line outcome; flag failed / timed-out / thin |

## 7. Known Gaps

What could not be found or confirmed, and why. "None" is valid; silence is not.
```

## Citation Rule

No statement in §3–§5 without a `file:line` reference. Snippets must be working code — never fragments with `...` elisions, never pseudocode.

## Language Rule

The artifact documents; it never evaluates. Forbidden vocabulary: "should", "better", "clean", "smell", "issue with", "unfortunately".

**Before (forbidden):**
> The retry loop in `src/worker.ts:88` should use backoff; the current busy-wait is a smell and a cleaner approach would be better.

**After (correct):**
> The retry loop in `src/worker.ts:88` polls in a fixed 50ms interval with no backoff. A backoff variant exists in `src/scheduler.ts:141`.
