# Negative list -- shared by every format

Generic anti-AI-tell checklist. Treat every item as a hard constraint: when a sentence seems to need one of these, rewrite the sentence. The validator regex-scans categories 1, 2, 4, 6, 7 and the mechanical parts of 3.

**1. Vocabulary tells.**
- Legacy/significance puffery: "stands/serves as," "testament," "pivotal role," "underscores... significance," "enduring," "indelible mark," "deeply rooted," "setting the stage for"
- Superficial-analysis connectors: "highlighting," "underscoring," "reflecting," "contributing to," "fostering," "resonate with"
- Promotional puffery: "boasts a," "vibrant," "rich," "nestled," "in the heart of," "groundbreaking," "renowned," "diverse array"
- Weasel attributions: "industry reports," "observers have cited," "experts argue" -- invoking authority without a specific source
- A documented "vocabulary drift" across model generations: early-era tells ("delve," "boasts," "meticulous," "tapestry," "intricate," "landscape," "crucial," "garner") gave way to mid/later-era tells ("align with," "showcasing," "fostering," "enhance," "emphasizing"). Different model families have their own signatures (e.g., Grok favors "causal," "empirical," "correlate," "underscore").

**2. Phrasing patterns.**
- Negative parallelism: "not only X but Y," "it's not just X, it's Y," and the reversed form "X rather than Y" (flagged as especially common in some models)
- "Not X, but Y" absolute negation constructions
- Copulative avoidance -- replacing a plain "is/are" with a more "elevated"-sounding verb: "serves as," "marks," "features," "offers," "refers to." This is a subtle one: it's stylistically "safe" and grammatically correct, which is exactly why it slips past casual review, but it's a strong tell because natural human writing uses plain "is/are" far more often.
- Formulaic "challenges/future" sections: "Despite its [positive traits], [subject] faces challenges..." resolving into vague, hedged optimism
- Rule-of-three listing (three-item parallel constructions) used reflexively rather than because three genuinely fits

**3. Structural/formatting patterns.** Title-case headings, headings that contain nothing but more headings, overuse of boldface, inline-header bullet lists, overuse of em dashes, decorative emoji, unnecessary tables, curly quotes where the source uses straight quotes, skipped heading levels, horizontal-rule section breaks, near-reflexive "Awards and recognition"-style boilerplate sections, and leads that treat a general/list-type subject as if it were a single proper-noun entity.

**4. Tone issues.** Even when explicitly told to be neutral, LLMs default to: travel-guide/advertisement cadence, press-release language ("commitment to sustainability"), disproportionate emphasis on "legacy" or "broader significance" for mundane subjects, and a hedge-then-assert pattern (downplaying importance in a preamble, then asserting importance anyway in the next breath).

**5. Sourcing/citation issues.** Broken links, invalid DOIs/ISBNs, vague claims of "several sources" not matched by actual citation count, and citations that don't actually support the claim they're attached to.

**6. Markup/technical artifacts.** Residual Markdown syntax leaking into plain text, and tool-specific citation-system debris (e.g., ChatGPT's `contentReference/oaicite`, Gemini's `[cite: 1]`) -- a giveaway that output was pasted without cleanup.

**7. Meta/communication leakage.** Conversational scaffolding meant for a chat interface leaking into the actual content -- offering multiple phrasing options, knowledge-cutoff disclaimers, unfilled placeholder text, or (in older models) visible refusal/disclaimer boilerplate.
