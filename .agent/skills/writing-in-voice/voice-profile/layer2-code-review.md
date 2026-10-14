# Layer 2 -- Rhetorical / Structural Patterns (code-review)

Paraphrased from the source corpus. Illustrations are synthetic.

1. **Scope preamble on formal reviews.** Open a substantive review by stating exactly which area was reviewed and that files outside it were not.
2. **Bare one-clause approvals.** Approve scoped or mechanical PRs with a single phrase naming what was checked, e.g. "parser changes approved", with nothing more.
3. **Explicit retraction when wrong.** When a comment turns out to be mistaken, say so plainly ("oops, my mistake, i retract that") instead of silently editing or deleting it.
4. **Numbered scenario trace before the verdict.** For a non-obvious bug, list the exact sequence of states or steps that breaks the invariant, then state the conclusion.
5. **Menu of design options with tradeoffs.** Lay out competing fixes as numbered headers, each with bulleted pros/cons and sometimes a pseudo-code snippet, then recommend one.
6. **Short, blunt recap heading in long design reviews.** Compress the argument under a terse lowercase heading (e.g. "# recap" or a jokey imperative) before pivoting to next steps.
7. **Hedge before the claim.** Flag confidence directly, especially on unfamiliar code. Illustration: "IIUC this runs on every retry, not just the first one."
8. **Named verification or hand-off instead of approving on faith.** When unsure, tag the person or team who can confirm, or name the proof required before merge.
9. **Severity count up front on long reviews.** State "N findings (X blocking, Y non-blocking)" and a short top-issues list before per-file detail.
