# context-bundle.md Template

**Load this when writing the context-bundle.md artifact.**

Contract: `context-bundle.md` is the skill's only output. A planning agent must be able to plan from it without redoing any research. Fill every section. "None" is a valid entry; a missing section is not.

## The Template

```markdown
---
artifact: context-bundle
date: YYYY-MM-DD
git_commit: <full commit hash at bundle time>
branch: <branch name>
request: <the user's request, verbatim>
source_research: <path to research-findings.md, or none>
status: complete | partial
---

# Context Bundle

## 1. Goal

Precise restatement of what was asked, plus explicit scope:

- **In scope:** ...
- **Out of scope:** ...

## 2. Files Retrieved

Paths with line ranges and why each matters, ordered by importance.

- `path/to/file.ext:L10-L80` — why this file matters to the goal

## 3. Entry / Exit Points

Each point: `file:line` plus its contract (inputs → outputs, side effects).

- **Entry:** `file:line` — inputs → outputs; side effects: ...
- **Exit:** `file:line` — ...

## 4. Key Code

Critical types, interfaces, signatures, and small working snippets the plan must respect.

### `<name>`
- **Location:** `file:line`
- **Code:**
  ```<lang>
  <working code>
  ```

## 5. References & Usages

For each affected symbol:

### `<symbol>`
- **Definition:** `file:line`
- **Call sites / dependents:** `file:line`, `file:line` (or explicit "no callers found")

### Blast Radius
- **Likely to change:** `file` — why
- **Must not break:** `file` — consumer of `<symbol>` at `file:line`
- **Transitive dependents worth attention:** `file` — `file:line`

## 6. Patterns & Idioms

Conventions with working snippets and locations. ALL variations shown side-by-side; conflicts flagged explicitly. Evidence (which is more recent, which is more prevalent) may be noted; recommendations may not.

### Pattern: <name>
- **Location:** `file:line`
- **Snippet:**
  ```<lang>
  <working code>
  ```
- **Key aspects:** ...

### Conflicting Variations
- **Variation A:** `file:line` — snippet; evidence: used in N files, last touched YYYY-MM-DD
- **Variation B:** `file:line` — snippet; evidence: used in N files, last touched YYYY-MM-DD
- **Conflict:** <what disagrees, stated explicitly>

## 7. Testing

- **How similar code is tested:** snippet + `file:line`
- **Tests covering affected code:** `file` per implementation file (or "none found")
- **Validation commands:** commands verified against the repo (read from package.json scripts, Makefile, CI config — never invented). Each cited to the file it came from.

## 8. Constraints & Risks

- **Invariants the plan must respect:** each with a `file:line` citation (public signatures, error-handling contracts, config coupling, test conventions, dependency direction)
- **Dependencies / ordering:** ...
- **Likely failure modes:** each with evidence cited `file:line`
- **Conflicting findings:** stated explicitly, both sides cited

Evidence-backed only. No speculation without a citation.

## 9. Open Questions

- `[needs-human]` — questions requiring business/design judgment
- `[needs-deeper-research]` — questions where evidence was inconclusive

"None" is valid; silence is not.

## 10. Start Here

Exactly one file, plus reasoning a planner could audit.

- **Start:** `path/to/file.ext` — <reasoning>
```

## Citation Rule

Every claim in every section carries a `file:line` citation. No exceptions for "obvious" facts. Snippets must be working code — never fragments with `...` elisions, never pseudocode.

## Judgment Boundary

§8 records hazards with evidence; it never proposes the route.

**Correct (evidence + citation):**
> `SessionManager.close()` is depended on by `src/api/handler.ts:44` and `src/worker.ts:112`; both call sites assume it is idempotent (`src/worker.ts:115` calls it inside a retry loop). Changes to its idempotency propagate to both.

**Forbidden (solution-shaped):**
> The plan should refactor `SessionManager.close()` to be idempotent.

The second entry decides. The first entry maps. Your job ends at the map.
