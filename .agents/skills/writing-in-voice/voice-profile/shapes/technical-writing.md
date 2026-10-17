# Shape card -- technical-writing

Long-form design docs, RFCs, decision records, onboarding guides, project READMEs. Median ~700 words.

- **Opening:** a sentence-case `#` title, then `TLDR:` and one or two sentences of punchline. No preamble about what the doc will cover.
- **Headings:** sentence case, short, functional ("Background", "Options", "Open questions"). Two levels deep at most. Every heading has prose or a list directly under it.
- **Body:** short paragraphs of 1-4 sentences, first person ("I want...", "I think..."), contractions throughout. Sentence length swings widely: a 6-word aside next to a 40-word explanation.
- **Lists:** challenges and risks as `*` bullets before the plan; options as a pass/fail survey with `:x:` / `:white_check_mark:` and a bolded option name; process steps as nested numbered lists. List length matches the real item count.
- **Asides:** parentheses for caveats and confidence notes; `(CQ):` for a question to reviewers; `TODO:` lines left in place; `i.e.`, `e.g.`, and `etc.` inline.
- **Code:** before/after pairs for refactors, with little prose between them.
- **Ending:** stop at the last open item or TODO. Planning docs close with one italicized "How might we..." line. No summary, no "next steps" wrap-up.
