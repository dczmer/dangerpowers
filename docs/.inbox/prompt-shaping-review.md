# Review: "Proompting" (dangerpowers/docs/prompt-shaping/README.md)

Reviewed document: https://github.com/dczmer/dangerpowers/blob/master/docs/prompt-shaping/README.md
Review date: 2026-10-12

Line numbers refer to the raw README as fetched on the review date.

**Verification key:** **[checked]** = source fetched and read during this review. **[memory]** = cited from the reviewer's prior knowledge, not re-fetched; verify before relying on it. **[doc]** = cited by the reviewed document and not independently checked.

## Bottom line

About 70–75% of the document is accurate and is standard good practice. The frontier-model section (specificity, grounding, decomposition, verification loops) is solid. **The overselling is concentrated in the local-model and chain-of-thought (CoT) sections**, and it rests on one cited source (Wei et al.) that actually supports the opposite conclusion.

## Accuracy problems, worst first

### 1. Line 232: "simulate the reasoning process… rivaling what the frontier model can do"

This is the biggest overclaim. A prompt can make a model show its steps, but it can't add knowledge or capability. Reasoning models trained with reinforcement learning (o1, DeepSeek-R1 [R9]) beat CoT-prompted versions of the same base models by wide margins. If prompting could close that gap, labs wouldn't spend so much on that training. On narrow, repeated tasks (classification, extraction, fixed transforms), a well-optimized prompt can get a small model close to frontier results. On open-ended agentic coding it can't.

### 2. Line 172: citing Wei et al. for "CoT lifts small models"

The paper [R4] says the reverse. Its central finding is that CoT is an *emergent ability of scale*: it helped only at roughly 100B+ parameters, and it hurt or did nothing for small models, which wrote fluent but illogical chains. Modern 7–30B instruct models do benefit from CoT, but only because they were trained on CoT data. Many were trained on traces distilled from reasoning models. That is a different argument and needs different citations.

### 3. Line 212: "few-shot exemplars are far more effective than a bare trigger phrase"

This held in 2022 and is shaky now.
- Kojima et al. [R5] found zero-shot "let's think step by step" close to few-shot on many tasks.
- Cheng et al. 2025 [R7] found that for modern instruct models around 7B and up, CoT exemplars mostly fix the output format rather than improve reasoning.
- Sprague et al. 2024 [R6] found CoT helps mainly on math and symbolic logic, with little gain elsewhere. That limits its value for coding.

### 4. Line 345 (conclusion): "consistent, quality results"

This is defensible for narrow pipelines you've optimized, and oversold as a general claim about agentic coding.

### 5. Line 101: decomposition "built in at the model level once inference-time scaling slowed"

This is speculation written as fact, with no source.

### 6. Distillation section (lines 236–258): mostly right, a few loose ends

- The paper [R1] is real (Panfilov et al., Aug 2026). It does claim encrypted reasoning blocks are "fully compatible and interchangeable across different sessions, users, and models" from the same provider. It also claims a weaker, less-guarded sibling model will print a stronger model's trace in plaintext. Anthropic, OpenAI and Google are named.
- It found 182 credentials and 367 PII artifacts in 315,320 blocks scraped from public repos, so the session-data security point stands.
- The abstract doesn't name Opus→Haiku or "GPT-5.6 Luna". I couldn't verify those specifics, or whether any provider has patched the issue. The abstract mentions only responsible disclosure and proposed mitigations. The document presents the attack as currently working.
- "Distillation is the process of extracting the proprietary reasoning steps" is imprecise. Distillation means training a student model on a teacher model's outputs. Stealing traces is one way to get better training data for it.

### Minor

- Line 57 attributes recency bias / lost-in-the-middle to Chroma's context-rot report [R16]. The classic source is Liu et al. 2023 [R10].
- Line 279's claim that prompt brittleness swings accuracy by tens of points is supported, by Lu et al. [R12] and even more strongly by Sclar et al. [R11]. Small models are the most sensitive, which works against the document's optimism, not for it.
- Line 190 mixes up self-consistency (majority vote over sampled answers [R13]) with LLM-as-judge. Majority vote only works on tasks with discrete answers. For code, use tests as the judge instead.

## What actually moves the needle on local models, roughly by size of effect

1. **Model choice and agentic training, by far the largest.** Non-reasoning small models tuned for agentic coding, such as Devstral Small (24B) [R18] and Qwen3-Coder-30B-A3B [R19], score around 50% on SWE-bench Verified [R17] in good harnesses. Later versions are reportedly higher. A general instruct model of the same size scores much lower. That's a gap of tens of points, which no prompting closes. *(Scores are [memory]; check current leaderboards.)*
2. **Harness and edit format.** Aider's benchmarks showed weak models do much better with whole-file edits than with diff formats [R8, R14]. This is a real gain from shaping the environment, not the prompt.
3. **Constrained decoding instead of format templates.** llama.cpp grammars and JSON-schema modes [R15] enforce output structure deterministically. That beats the document's "rigid format templates" (line 184).
4. **Verification gates and retries.** Use tests as the judge rather than majority vote.
5. **Prompt shaping.** It gives meaningful gains on narrow classification and extraction, often several to tens of points with good few-shot examples. On agentic coding it typically adds a few points on top of items 1–4.

## Frontier model plans, local model executes

The best evidence is Aider's architect/editor benchmark [R2]:

| Setup | Pass rate |
|---|---|
| o1-preview alone (diff) | 79.7% |
| o1-preview architect + DeepSeek editor (whole) | 85.0% |
| o1-preview architect + o1-mini editor (whole) | 85.0% |
| Sonnet 3.5 alone (diff) | 77.4% |
| Sonnet 3.5 architect + Sonnet 3.5 editor | 80.5% |
| Sonnet 3.5 architect + DeepSeek editor | 78.9% |
| GPT-4o alone (diff) | 71.4% |
| GPT-4o architect + DeepSeek editor (diff) | 74.4% |

DeepSeek as editor improved every architect except Sonnet (where it beat Sonnet alone but not Sonnet paired with itself). The caveats matter:
- The editor was DeepSeek (V2.5 at the time, a 236B mixture-of-experts model [memory]), not something you'd run on a laptop. No small local editors were tested.
- The architect specified concrete changes and the editor only turned them into file edits. That's the easiest possible job for the executor.
- Aider notes the top "whole"-format results are slow and "probably not practical for interactive use."

In practice it works like this:
- **It works well when the plan is at code level:** exact files, function signatures, often code snippets, and a test command for each step. By then the frontier model has done most of the thinking. What you save is the cost of the frontier model running the tool loop and writing out the code.
- **It breaks when reality differs from the plan:** a test fails for an unexpected reason, an API doesn't match, a file has moved. Small non-reasoning models are weakest at recovering from errors and tracking state over many steps. They also tend to declare done too early or quietly edit tests to make them pass.
- **To make it usable:** keep steps small, gate every step with a deterministic check, cap retries at 2–3, escalate to the frontier model when the cap is hit, and have the frontier model review the final diff.

No rigorous public benchmark was found for "frontier plan + small local executor in a long agentic loop." The points above come from practitioner experience and the known failure modes of small models, not measured results.

## Where a local non-reasoning model actually earns its keep

- **Autocomplete and fill-in-the-middle completion**, e.g. Qwen2.5-Coder. Arguably the best fit: low latency, short context, and errors are cheap.
- **Narrow, high-volume text tasks:** commit messages, log and alert triage, classification, extraction, summarizing diffs, docstrings. This is where the document's techniques genuinely pay off.
- **Mechanical edits from an exact spec** (boilerplate, test scaffolds, repetitive transforms), gated by tests. That said, codemods and LSP refactors are often better than any model for these.
- **Private or offline work** where data can't leave the machine.
- **Avoid:** using it as a summarizing or search subagent for a frontier model. Its mistakes become invisible, wrong "facts" in the parent's context.

## Suggested edits to the document

1. Re-cite or reword line 172.
2. Qualify lines 212 and 232. Something like: "approaches frontier quality on narrow, optimized tasks; does not substitute for trained reasoning on open-ended work."
3. Add a note that model choice and harness matter more than prompting for agentic coding.
4. In the distillation section, mark the Opus/Haiku/Luna specifics as unverified, note the paper's patch status is unknown, and tighten the definition of distillation.
5. Credit lost-in-the-middle to Liu et al., and separate self-consistency from LLM-as-judge.

## References

### Checked (fetched during this review)

- **[R0]** The reviewed document: https://github.com/dczmer/dangerpowers/blob/master/docs/prompt-shaping/README.md **[checked]**
- **[R1]** Panfilov et al., "Stealing Reasoning Traces from Proprietary LLM APIs," arXiv:2608.09867, Aug 2026. https://arxiv.org/abs/2608.09867 **[checked; abstract only]**
- **[R2]** Aider, "Separating code reasoning and editing" (architect/editor benchmark), Sept 2024. https://aider.chat/2024/09/26/architect.html **[checked]**
- **[R3]** Anthropic, Extended thinking docs. https://platform.claude.com/docs/en/build-with-claude/extended-thinking **[checked]**. Confirms that the `thinking` content returned is a summary. It points to a separate "Thinking encryption" page for how the blocks are encrypted, which was not fetched.

### Cited from memory (not re-fetched; verify)

- **[R4]** Wei et al., "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models," 2022. https://arxiv.org/abs/2201.11903 **[memory]**. Also cited by the document as [H].
- **[R5]** Kojima et al., "Large Language Models are Zero-Shot Reasoners," 2022. https://arxiv.org/abs/2205.11916 **[memory]**
- **[R6]** Sprague et al., "To CoT or not to CoT? Chain-of-thought helps mainly on math and symbolic reasoning," 2024. https://arxiv.org/abs/2409.12183 **[memory]**
- **[R7]** Cheng et al., "Revisiting Chain-of-Thought Prompting: Zero-shot Can Be Stronger than Few-shot," 2025. **[memory; the arXiv ID is not confirmed, so search by title]**
- **[R8]** Aider, edit formats documentation. https://aider.chat/docs/more/edit-formats.html **[memory]**
- **[R9]** DeepSeek-AI, "DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning," 2025. https://arxiv.org/abs/2501.12948 **[memory]**
- **[R10]** Liu et al., "Lost in the Middle: How Language Models Use Long Contexts," 2023. https://arxiv.org/abs/2307.03172 **[memory]**
- **[R11]** Sclar et al., "Quantifying Language Models' Sensitivity to Spurious Features in Prompt Design," 2023. https://arxiv.org/abs/2310.11324 **[memory]**
- **[R12]** Lu et al., "Fantastically Ordered Prompts and Where to Find Them," 2021. https://arxiv.org/abs/2104.08786 **[memory]**. Also cited by the document as [M].
- **[R13]** Wang et al., "Self-Consistency Improves Chain of Thought Reasoning in Language Models," 2022. https://arxiv.org/abs/2203.11171 **[memory]**
- **[R14]** Aider LLM leaderboards. https://aider.chat/docs/leaderboards/ **[memory]**
- **[R15]** llama.cpp GBNF grammars. https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md **[memory]**
- **[R16]** Chroma, "Context Rot." https://research.trychroma.com/context-rot **[doc]**. The document's [B].
- **[R17]** OpenAI, "Introducing SWE-bench Verified." https://openai.com/index/introducing-swe-bench-verified/ **[memory]**
- **[R18]** Mistral AI, Devstral announcements. https://mistral.ai/news/devstral **[memory; the scores and URL are approximate]**
- **[R19]** Qwen team, Qwen3-Coder announcement. https://qwenlm.github.io/blog/qwen3-coder/ **[memory; the scores and URL are approximate]**

### Cited by the reviewed document, not independently checked

- Anthropic, "Detecting and Preventing Distillation Attacks." https://www.anthropic.com/news/detecting-and-preventing-distillation-attacks **[doc]**
- Reuters, "OpenAI Says China's DeepSeek Trained Its AI by Distilling US Models." https://www.reuters.com/world/china/openai-accuses-deepseek-distilling-us-models-gain-advantage-bloomberg-news-2026-02-12/ **[doc]**
