---
name: writing-in-voice
description: Use when asked to draft or rewrite an RFC, design doc, PR description, review comment, technical explainer, or engineering note "in my voice" or in the profiled author's voice. Covers workplace and technical prose matched to the stored voice profile, checked by a deterministic validator.
disable-model-invocation: true
---

# Writing In Voice

Write from the voice profile, then let the validator judge the draft: the validator is the only pass/fail authority on whether a draft is in voice. Scope is workplace and technical writing, not personal prose.

All paths below are relative to this skill's directory.

## Steps

1. **Pick the format.** One of:
   - `technical-writing` -- long-form design docs, RFCs, decision records, guides, READMEs (median ~700 words)
   - `code-review` -- PR descriptions, review comments, approvals (median ~86 words)
   - `notes` -- informal engineering notes, journal entries, research logs (median ~560 words)

   Use the format the user named. Otherwise infer it from the request and **state the format you picked** in the report -- numeric targets differ sharply between formats, so a silent wrong pick invalidates the score.

2. **Load the profile.** Read all of:
   - `voice-profile/shapes/<format>.md` -- the layout to follow
   - `voice-profile/exemplars/<format>.md` -- a synthetic exemplar of that layout
   - `voice-profile/layer1-<format>.md` -- numeric targets and top function words
   - `voice-profile/layer2-<format>.md` -- rhetorical and structural patterns
   - `voice-profile/layer4-<format>.md` -- vocabulary and tics, plus format-specific absences
   - `voice-profile/layer3-substance.md` -- shared stances and reasoning habits
   - `voice-profile/negative-list.md` -- shared hard constraints

3. **Write the draft.** Condition on everything at once:
   - Follow the shape card's opening, heading, list, and ending rules. Imitate the exemplar's document shape -- its opening, headings, lists, and ending -- never its topic, wording, or sentence-level phrasing. After drafting, diff the draft against the exemplar line by line: any sentence whose structure mirrors an exemplar sentence gets rewritten, even if every word is different.
   - Hit Layer 1's mean sentence length and its sentence-length *variance* -- uniform sentence length is itself a tell.
   - Use Layer 2's named patterns for openings, transitions, and argument structure.
   - Draw stances from Layer 3 only where the topic calls for them. Track each one you use and its `grounded` / `extrapolated` tag.
   - Treat Layer 4's positive list as suggestions. Treat Layer 4's absences and the entire negative list as hard constraints: when a sentence seems to need a listed tell, rewrite the sentence.
     **Iron Law: every negative-list hit is resolved by rewriting the sentence before the report is written -- never by keeping the sentence and documenting the violation.** "Hard constraint" means no one can waive it -- not a deadline, not a user preference, not an explicit "don't touch it," not a note in the report. No exceptions:
     - "The user asked to keep it" -> rewrite it anyway; record the user's objection in the report alongside the rewrite, quoting the original phrasing. You do not restore the tell.
     - "Surface it and stop covers this" -> no: step 6's stop governs iteration on out-of-range *metrics* (voice distance the user may want to judge themselves). A negative-list hit is binary and fixable -- rewrite it, re-validate, and report a passing run. Reporting against a non-zero exit for a fixable tell is itself the violation.
     - "Flag it as an intentional exception" -> there are no intentional exceptions. A shipped tell is a failure, noted or not.
   - Take every product, service, and system name from the user's request.

   Write the draft to a temp path (e.g. `/tmp/draft.md` or `$TMPDIR/draft.md`), or to the path the user names.

4. **Validate.** Run from this skill's directory:

   ```
   python3 scripts/validate_voice.py --format <format> --file /tmp/draft.md
   ```

   The validator regex-scans for the mechanically checkable negative-list tells, gates on table density and rhetorical-boldface density, prints title-case headings and empty sections without gating, and reports Delta plus per-metric z-distances as information. Exit 0 = pass, 1 = fail, 2 = setup problem. Never substitute your own judgment for its result.

5. **Report.** Always show:
   - the format used
   - pass/fail -- the negative-list result plus the two gating structural thresholds
   - the validator's `Structural signals` table, including the two non-gating rows
   - Delta, labelled informational
   - every metric flagged out of range
   - every negative-list hit, verbatim with line numbers
   - the Layer 3 stances used, split `grounded` vs `extrapolated`

6. **On failure, surface it and stop.** Report the full validator output. Leave iterating to the user after they see the report, so the first attempt's distance from the voice stays visible. (Negative-list hits are never left for the user: they are binary, they are always fixed by rewriting the sentence -- see step 3 -- and the report is written only against a passing validator run on the final text.)

## Gotchas

- **A clean validator run is necessary, not sufficient.** The validator does not check reflexive rule-of-three lists, inline-header bullet lists, or sourcing problems (negative-list category 5). Read the draft for those three before handing it over.
- **The exemplars are synthetic.** They were written to demonstrate the shape cards and validated against Layer 1; they are not the author's text. Copying their phrasing -- including slot-filling their sentence structures -- produces a model imitating a model.
- **A low Delta is not evidence the voice landed.** Genuine in-voice docs and a deliberately AI-flavored control measure in the same Delta band. Report the number and never present it as vouching for the draft.
- **Title-case headings and empty sections do not gate** because they did not separate real docs from AI slop. Read those two rows yourself.
- **Exit status 2 means the install is incomplete**, usually a missing `voice-profile/layer1-<format>.json`. Tell the user rather than guessing at targets.
- **This skill never edits `voice-profile/`.** Profile updates go through the `updating-voice-profile` skill.

## Checklist

- [ ] Named the format in the report
- [ ] Loaded the shape card, exemplar, all four layers, and the negative list for that format
- [ ] Draft written to a file and the validator run against that file
- [ ] Validator exited 0, with every negative-list hit resolved by rewriting the sentence
- [ ] Report covers format, pass/fail, `Structural signals` table, Delta labelled informational, out-of-range metrics, negative-list hits with line numbers, Layer 3 stances split `grounded` vs `extrapolated`
- [ ] Checked for rule-of-three lists, inline-header bullets, and category 5 sourcing
- [ ] No exemplar topic, wording, or invented names carried into the output
