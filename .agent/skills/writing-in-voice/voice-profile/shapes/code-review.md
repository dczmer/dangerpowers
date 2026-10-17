# Shape card -- code-review

PR descriptions, review comments, approvals. Median ~86 words. Three sizes:

- **Bare approval (one line):** a single clause naming what was checked, e.g. "migration changes approved." or "lgtm." Nothing else.
- **Inline comment (1-5 sentences):** lowercase start, a hedge opener ("IIUC", "i think", "not sure if"), the concern, then a concrete suggestion or question. Close with "thanks" or a hand-off when the thread resolves.
- **Substantive review (150-400 words):** in this order -- the claim with a hedge; a numbered scenario trace of the failure; a self-check question ("does the server dedupe on X?"); a short bulleted menu of fixes with tradeoffs; a recommendation; bolded `**blocking:**` / `**nit:**` tags, one line each; a named hand-off for anything the author can't verify. Long design reviews add a terse lowercase recap heading before next steps, and open with "N findings (X blocking, Y non-blocking)".
- **PR description:** what changed and why, in 2-5 plain sentences or bullets; how it was tested; any reviewer caveat. No headings for short PRs.
- **Throughout:** lowercase "i", ASCII emoticons only, explicit retraction ("oops, i retract that") when a comment turns out wrong.
