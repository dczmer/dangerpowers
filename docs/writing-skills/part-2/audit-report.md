# Audit Report: Trigger Testing draft (part-2/README.md)

Overall verdict: the core technical content is sound — nearly every external claim I checked against the live sources held up. The main problems are (a) one factual misquote of Anthropic's workspace convention, (b) two passages that are near-verbatim from agentskills.io (already flagged in EDITOR notes), (c) a references section that doesn't match part-1's citation machinery, and (d) the usual draft-level spelling/grammar drift. Details below, numbered so we can work through them interactively.

---

## 1. Correctness & Fact-Check

### 1a. Verified claims (no change needed, but should be cited)

I fetched every external source. These claims check out:

- **The four description-optimization tips** (imperative phrasing, user intent over implementation, "pushy," concise) — confirmed verbatim-in-spirit on `agentskills.io/skill-creation/optimizing-descriptions`.
- **1024-char hard limit on `description`** — confirmed in the Agent Skills spec (`agentskills.io/specification`, description field: "Must be 1-1024 characters").
- **"The agentskills.io guide uses a CLI script to drive a headless claude code"** — confirmed. The guide ships a bash script using `claude -p "$query" --output-format json` with a `jq` check for Skill tool calls.
- **"The claude skill creator does the same"** — confirmed. `skill-creator`'s `run_loop.py`/`run_eval.py` drive `claude -p` via subprocess (its own SKILL.md says so explicitly in the Cowork section).
- **The `claude.com/plugins/skill-creator` link** — live, correct plugin (Anthropic-verified "Skill Creator").
- **Train/validation ~60/40 split, fixed across iterations, best iteration selected by validation pass rate** — confirmed, matches agentskills.io's "Avoiding overfitting with train/validation splits" section exactly.
- **Failure-table rows 1-3** (too narrow -> broaden; too broad -> add specificity; stuck -> structurally different framing) — these map to the agentskills.io optimization-loop guidance. Row 4 (body/label conflict, "a description cannot outvote the purpose a router infers from the body") is **our own original contribution** — it appears verbatim in the repo's `old-skill.md` failure-class remediation table but in no external source. That's the answer to the `EDITOR: find source for the table below` note: cite agentskills.io for rows 1-3, claim row 4 as our own finding.
- **The `(successes + 2) / (total + 4)` shortcut** — correct; it's the "plus-four" rule, an approximation of the Wilson score interval, consistent with the repo's `confidence-intervals-eli5.md` (and Wikipedia).
- **"Generalize failures / never paste failed-query keywords"** — the concept exists on agentskills.io ("Avoid adding specific keywords from failed queries — that's overfitting"), so cite it there.

### 1b. Factual errors / misquotes to fix

1. **Opening paragraph:** *"it loads all skill front-matter into context"* — **inaccurate.** Per the spec, only `name` and `description` are loaded at startup (~100 tokens); the rest of the frontmatter and body are on-demand. Part-1 got this right ("those two fields are the only part that gets pre-loaded"), so part-2 currently contradicts part-1. Fix to "loads every skill's `name` and `description` into context."
2. **Anthropic workspace convention (misquote):** the draft says *"Anthropic recommends using a `skill-workspace` folder hierarchy as a sibling to the 'skills' directory."* The actual skill-creator text is: *"Put results in `<skill-name>-workspace/` as a sibling to **the skill directory**."* Two differences: the folder is named after the individual skill, and it's a sibling to the skill's folder, not the `skills/` root. This repo's own convention (`skills-workspace/writing-skills/` sibling to `skills/`) is a *different, adapted* convention — which is fine, but attribute each accurately. Suggested fix: quote the Anthropic convention precisely, then say "I use a single shared `skills-workspace/` sibling to `skills/` instead" and show the tree.
3. **Reference C link text:** the draft says `improving_description.py` — the actual file is **`improve_description.py`** (no "-ing"). The URL is correct; only the label is wrong.
4. **Reference D is a placeholder** ("presentation from deepmind member i mentioned in the part-1 doc"). The video is live: **"Don't Ship Skills Without Evals — Philipp Schmid, Google DeepMind"**, `https://youtu.be/0vphxNt4wyk` — same as part-1's ref `[I]`. Fill it in.
5. **"(probably because they were both made by anthropic)"** — plausible (agentskills.io hosts the Agent Skills spec Anthropic open-sourced), but agentskills.io's ownership could not be fully confirmed from the page itself. Either verify or drop the parenthetical — the claim doesn't need the speculation to work.
6. **Missing file for an EDITOR link:** the note asks to link `./example/agents/trigger-evaluator.md`, but `docs/writing-skills/part-2/example/` contains only the skill — no `agents/` dir. The real file lives at repo-root `agents/trigger-evaluator.md`. Either copy it into the example tree or fix the path.
7. **Example query inconsistency:** the demo prompt uses *"Write a new skill to drive my application using playwright."* but the stored `skills-workspace/writing-skills/trigger-tests/queries.json` has *"create a skill to drive my webapp using playwright"*. If the post claims to reuse real artifacts, align them (or note the paraphrase deliberately).

### 1c. Plagiarism risk (flagged in EDITOR notes; confirming the severity)

- **The near-miss-negative paragraphs** — *"What's the weather?" is a weak negative... same surface keywords, different need"* — the "What's the weather today?" example is **verbatim** in agentskills.io's should-not-trigger section, and the sentence structure tracks the source closely. Must be rewritten, not just cited.
- **The "Tips for realism" bullet list** — this is essentially the source's list verbatim, including the identical example path `~/Downloads/report_final_v2.xlsx`. Rewrite with original examples (the repo's own `queries.json` has real ones, e.g. "update the test-skill skill to prevent it from installing dependencies automatically").
- Note: the **axes table** (formality/explicitness/detail/complexity with the PRD examples) is fine — the axes parallel the source but the examples are original (they match the repo's `old-skill.md`). Just cite the source for the axis concept.
- Interesting wrinkle: both flagged passages also appear verbatim in the repo's own `old-skill.md` (the trigger-testing skill). So the rewrite should probably happen in **both** places, or at least the blog post.

### 1d. Citation mechanics

The body currently has **zero inline citations**, and the References section uses a loose "- A ..." format. Part-1 uses inline `[A]`-`[I]` keys with `<a id="ref-x">` anchors. Recommend:

- Adopt part-1's convention exactly: inline keys at each claim, anchored reference list.
- Needed keys: agentskills.io optimizing-descriptions, agentskills.io spec (for the 1024 limit), skill-creator plugin page, skill-creator GitHub, `improve_description.py`, DeepMind video, Wikipedia binomial proportion CI (for the Wilson shortcut), plus internal links (part-1, `confidence-intervals-eli5.md`, the skills/queries.json files).

### 1e. Missing nuance worth adding (from the sources, currently absent)

Both agentskills.io and skill-creator warn that **simple one-step queries may not trigger a skill regardless of description quality**, because the agent can handle them alone — skill-creator explicitly says "Simple queries like 'read file X' are poor test cases." This is directly relevant to the "design should-trigger queries" advice and to interpreting failures, and it's a non-obvious insight that would add real value.

Also: the sources suggest **3 reps as a starting point**; the draft prescribes 10. Not wrong (more conservative), but one sentence acknowledging the tradeoff ("the guides say 3; I use 10 because...") would preempt the sharp-eyed reader, and it sets up the Wilson-interval section nicely.

---

## 2. Spelling & Grammar

| Location | Issue | Fix |
|---|---|---|
| Intro, last paragraph | "identify specific category of failure mode" | "identify the specific failure category" |
| "What is Trigger Testing?" | "we need run multiple tests" | "we need to run" |
| Optimizing Descriptions | "Here is list of skill optimization tips" | "Here is a list" |
| Optimizing Descriptions | "Err on the side of being push" | "pushy" |
| Optimizing Descriptions | "hard limit on description length at <= 1024 characters" | "a hard limit of 1024 characters" |
| Optimizing Descriptions | "to maintain context overhead space" | "to keep context overhead low" |
| Running a "Simple" Eval | "more impact ... then you might expect" | "than" |
| Running a "Simple" Eval | "running self-optimizing trigger-testing process" | "running a self-optimizing ..." |
| Running a "Simple" Eval | "issues i have run into" | "I" |
| Simple process list | "a json or yaml file" | "JSON or YAML" |
| Run a Round, 2nd paragraph | "headless claude code", "the claude skill creator", "made by anthropic" | "Claude Code", "Claude's skill-creator", "Anthropic" |
| Example prompt | "using playwright" | "Playwright" (proper noun) |
| Repeat section | "prefect 10/10", "a prefect score" | "perfect" (x2) |
| My "Minimal" Implementation | "based on the manual process form the examples" | "from" |
| Issues With This Setup | "an perfect implementation" | "a perfect" |
| What a Full Campaign, 2nd paragraph | "Imo", "claude code with opus" | "IMO", "Claude Code with Opus" |
| Developing a Better Harness | "a hand-full of times" | "a handful" |
| Developing a Better Harness bullets | four lowercase "i" sentence-starts; "claude code or opencode" | "I"; "Claude Code or opencode" |
| Developing a Better Harness | "despite the fact that i usually prefer" | "I" |
| EDITOR note (near-miss paragraph) | "reference soruce" | moot once note is removed, but: "source" |
| Headings | "What a Full Campaign Looks like" | "Looks Like" (title case, consistent with other headings) |

---

## 3. Structure & Ambiguity

1. **"Harness" is used before it's introduced.** First use is *"If your harness supports it"* in "What is Trigger Testing?" — the term is never defined until it recurs casually later. Add a half-sentence gloss at first use ("your agent harness — Claude Code, opencode, etc.").
2. **"pi" is name-dropped without context** ("I'm using opencode and pi mostly"). Most readers won't know pi. One clause or a link fixes it.
3. **Terminology drift: prompt / query / description.** Step 6 of the simplified process says *"Modify the **prompt** to address the issues"* — but the thing being modified is the **description**. Throughout, "test prompt" and "query" are used interchangeably while "prompt" also means the subagent instructions. Recommend a one-line terminology note up front: *query* = the test input, *description* = the field being optimized, *subagent prompt* = the eval instructions. Then fix step 6 to "Modify the description."
4. **The intro's last sentence is a run-on** ("...an optimization loop, analyzing failures to identify specific category of failure mode, updating the description, and repeating..."). Split into two sentences.
5. **The dangling fragment** "Never use first-person voice in a skill description" needs its expansion to include the *why* from part-1: all descriptions share one system prompt, and a description that breaks third-person POV reads as chatter and triggers worse. Consider a cross-link to part-1's voice example instead of re-deriving it.
6. **Failure table row 4 is a wall of text** (~90 words in one cell). Split the Action cell into 2-3 short imperative sentences, or move the long explanation into a paragraph below the table and keep the cell to "resolve the body/label conflict first."
7. **Internal cross-reference invisible to readers:** "(the Generalize failures rule in Description Revision Rules)" points at the repo's own skill file, which blog readers can't see. Replace with a citation to agentskills.io's "avoid adding specific keywords" guidance.
8. **No opening hook.** Part-1 opens with three relatable pain-point questions. Part-2 dives straight into mechanism. Suggest a 2-3 sentence cold open in the same register (e.g., the skill that never fires, or the one that fires on everything).
9. **"gaslighting"** (re: the fake tool restriction) — tonally it's the author's voice, but it's a loaded word for a white lie in a prompt. "A bit of a bluff" / "a white lie" lands the same joke without the baggage. Author's call.
10. **Section ordering is fine**, but the "overfitting/grounding" EDITOR note in "Optimizing Descriptions" would land better if the term "overfitting" is defined there briefly and then *used* again in "Evaluate the Failures" — right now the word appears in three places before it's ever explained.

---

## 4. Illustrations & Analogies

1. **The improvement-over-iterations graph** (existing EDITOR note): make it do double duty — plot *train* and *validation* pass rates separately, with validation peaking at, say, iteration 3 while train keeps climbing. Caption: "Train keeps improving; validation peaks and declines. The best description is iteration 3, not the last one." One image then teaches the optimization loop, overfitting, *and* "best != last."
2. **The mermaid flowchart** (existing EDITOR note): add the loop-back edge from "Analyze failures" to "Revise description," and label the exit edge with the three stop conditions (perfect score / good enough / out of budget) — it mirrors the prose and rewards the reader who skimmed the list.
3. **Analogy for near-miss negatives:** a smoke detector tested only with clean air proves nothing — you hold it over burnt toast. Weak negatives are clean air; near-misses are the toast.
4. **Analogy for contamination:** measuring a description's trigger rate with fifteen other descriptions in context is like taste-testing your soup after someone else's spices are already in the pot. (Sets up both the "Issues" bullet and the sterile-workspace motivation later.)
5. **Analogy for train/validation:** cramming from past exams vs. sitting the real one — the validation set is the exam you didn't study for.
6. The Wilson/plus-four section already has the perfect illustration — **the repo's own cookie doc** (`confidence-intervals-eli5.md`). Link it with a one-line teaser ("explained with cookies, here") rather than re-explaining.

---

## 5. Examples (good/bad pairs with captions)

EDITOR placeholders exist for most of these; here's what each one should demonstrate:

1. **Imperative vs. descriptive:** *Bad:* "Handles CSV files." *Good:* "Analyze CSV data — summary stats, derived columns, charts. Use this skill when the user has tabular data to explore, even if they don't say 'CSV'." Caption: the bad one states a topic; the good one issues a routing decision.
2. **Pushy boundaries (good):** show one description with an explicit "even when the user didn't mention X" clause. Caption: you're not describing the skill, you're pre-answering the agent's "does this apply?" hesitation.
3. **Overfit vs. generalized fix** (the key pair for the failure section): *Bad:* after a failure on "drive my application using playwright," appending `...also use for playwright requests`. *Good:* broadening the category ("Use when the user asks to create a skill that drives external tools or libraries"). Caption: the bad version memorizes the test; the good one learns the lesson — and the bad one will fail the *next* fresh query.
4. **Weak vs. near-miss negative** — the draft already has this pair ("What's the weather?" vs. the README query); once rewritten, add explicit captions: "tests nothing — no overlap" / "shares the keywords, not the need — this is the one that proves your description has a boundary."
5. **Failed-reasoning transcript -> before/after description** (existing EDITOR note): pick one real failure from a campaign log, quote the subagent's one-line reasoning verbatim, then show the description diff. Caption: "the reasoning tells you which clause anchored the decision — fix the clause, not the query."
6. **Sentence-structure restructure for local minimum** (existing EDITOR note): show the same description as (a) one long sentence, (b) capability-first two-sentence form. Caption: when incremental word swaps stall, change the skeleton, not the adjectives.
7. **First-person vs. third-person** — don't duplicate; part-1 already has this exact good/bad pair. Cross-link it.

---

## 6. Call-Out Quotes (one per section, matching part-1's epigraph style)

- **Intro:** "A skill that never triggers is a skill that doesn't exist — and the description is the only thing that decides." (synthesized)
- **What is Trigger Testing?:** "One run tells you what happened once. Ten runs tell you what your description actually does." (synthesized)
- **Optimizing Descriptions:** "The description carries the entire burden of triggering." — agentskills.io (a real quotable line from the source; cite it)
- **Running a "Simple" Eval:** "The methodology and harness you use have more nuance and more impact on the test runs than you might expect." (the draft's own sentence — already the thesis of the section)
- **Write the Test Prompts First:** "The negative cases are where your description proves it has a boundary." (synthesized from the near-miss passage)
- **Run a Round of Evals:** "The load is the entire measurement." (lifted from the draft's own subagent prompt — nicely self-referential)
- **Evaluate the Failures and Reasoning:** "Fix the category, not the query." (synthesized from the Generalize-failures rule)
- **Repeat:** "The winner is the best-scoring iteration, not the most recent one." (synthesized)
- **Issues With This Setup:** "Anecdotal evidence is fine — as long as you know that's what you have." (synthesized)
- **What a Full Campaign Looks Like:** "If it isn't automated and easy, you won't do it consistently." (compressed from the draft's own sentence)
- **Conventions and Best Practices:** "Don't ship skills without evals." — Philipp Schmid, Google DeepMind (the talk title itself; perfect tie-in to the reference)
- **Developing a Better Harness:** "The harness has to be more disciplined than the thing it's testing." (synthesized)

---

## 7. Repetition Audit

| Concept | Occurrences | Verdict |
|---|---|---|
| "best version != last iteration" | process step 8; Repeat 2nd paragraph; Full Campaign bullet list | **Over the line** — 3x, nearly identical wording. Keep it in the process list and the Repeat section (that's the drill-in spot); in the Full Campaign bullets, cut or compress to "version tracking (see Repeat above)". |
| "runaway workflows" | intro-to-simple-eval 3rd paragraph; bullet list; subagent-prompt bullet; Issues bullet; Harness bullet | **5 mentions.** Each is contextually justified, but the "Issues" bullet and the "Developing a Better Harness" bullet repeat the same content at similar length. Trim the Issues bullet to one clause with a forward-reference ("the runaway-workflow problem — see Developing a Better Harness for what it cost me"). The token-quota war story should live in exactly one place. |
| "contamination / hijack" | intro bullet; Simple Eval 3rd paragraph; Issues bullet; Harness bullet | Acceptable — each section adds a new angle (what it is -> test problem -> judgment call -> motivation for sterile workspace). Vary the Harness bullet's wording; it currently echoes the Issues bullet. |
| "non-deterministic" | intro; What-is-TT last paragraph; Full Campaign bullets | Acceptable; it's the load-bearing concept. At the third use, reword to the symptom ("when the same query flips outcomes between runs") instead of repeating the term. |
| "10 reps" | process list; Run-a-Round bullets; example prompt (x2); Repeat; Full Campaign paragraph | Fine — it's the operational constant, and the example-prompt occurrences are functional, not prose. |
| "tokens are expensive / token budget" | Repeat paragraph; Full Campaign paragraph; Harness paragraph | Fine — three distinct framings (stop condition, stats tradeoff, war story). |

---

## Suggested work order

1. **1b** (factual fixes — quick, mechanical)
2. **1c** (the two rewrites — the only items with real downside if shipped as-is)
3. **1d** (citation pass)
4. **2** (grammar sweep)
5. **3** (structure)
6. **4-6** (illustrations, examples, quotes)
7. **7** (repetition trims last, so you can see what survived)
