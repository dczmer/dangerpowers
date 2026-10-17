---
name: updating-voice-profile
description: Use when asked to ingest, add, or learn from new writing samples for the writing-in-voice skill, refresh or retrain the voice profile, or add documents to a format's stylometry. Covers merging new documents into the writing-in-voice profile without leaking source text into the distributable skill.
disable-model-invocation: true
---

# Updating Voice Profile

Fold new writing samples into the `writing-in-voice` profile so it gets more accurate while staying shareable: numbers merge by script, prose layers change only by paraphrase, and nothing reaches the live skill without passing the leak checker and the user's review of the full diff.

`SKILL_DIR` below is the installed `writing-in-voice` directory (sibling of this skill). `STAGE` is a scratch directory for this run, e.g. `` `mktemp -d`/voice-stage `` (anywhere outside both skill directories).

## Steps

1. **Collect inputs.** Get from the user: the document paths, the format (`technical-writing`, `code-review`, or `notes`), and whether the docs are primary (written entirely by the author, weight 1.0) or secondary (author's text mixed with others', weight 0.3). Use one format and one weight per run; split mixed batches into separate runs.

2. **Extend the deny-list.** Read the new docs and list every product, service, team, customer, person, username, hostname, and internal codename in them. Show the list to the user, then append the approved terms to `~/.config/writing-in-voice/denylist.txt` (create the file, and its parent directory, if they don't exist yet). Never write these terms anywhere inside either skill directory.

3. **Stage a copy.** Run `rm -rf "$STAGE" && cp -R "$SKILL_DIR" "$STAGE"`. Make every change in `STAGE`; never edit `SKILL_DIR` directly.

4. **Merge Layer 1.** Run from this skill's directory:

   ```
   python3 scripts/merge_profile.py --skill-dir "$STAGE" --format notes --weight 1.0 --docs /path/a.md /path/b.md
   ```

   This merges the new docs into `layer1-<format>.json` exactly and regenerates `layer1-<format>.md`. Add `--dry-run` first when the user wants to preview the metric shifts.

5. **Update Layers 2-4 and the shape card.** Compare the new docs against `STAGE/voice-profile/layer2-<format>.md`, `layer4-<format>.md`, `layer3-substance.md`, and `shapes/<format>.md`. Then edit those files in `STAGE`:
   - Add a pattern, tic, stance, or layout rule only when it appears in at least two of the new docs, or in one new doc plus existing profile evidence.
   - Write every entry and its example from scratch, in your own words. A source sentence never appears anywhere in the profile — not in the pattern description, not inside an example or illustration; short stock tics ("IIUC", "lgtm") are the only verbatim carry-over.
   - Give every illustration as a fresh invented example about an ordinary engineering topic -- a cache, a queue, a file export, a flaky test -- never reusing the source doc's own scenario, even renamed.
   - Never cite source files, doc IDs, PR numbers, dates, or people.
   - Tag every new Layer 3 stance `grounded` (stated directly in a doc) or `extrapolated` (inferred across docs), and update the tag summary line.
   - Strengthen or reword an existing entry instead of adding a near-duplicate.

6. **Refresh the exemplar when the shape card changed.** Rewrite `STAGE/voice-profile/exemplars/<format>.md` as a new synthetic piece on a neutral topic that follows the updated card. Validate it with `python3 "$STAGE/scripts/validate_voice.py" --format <format> --file "$STAGE/voice-profile/exemplars/<format>.md"`, and revise it until it exits 0 with every Layer 1 metric within range.

7. **Gate the stage.** Run all three and stop on any failure:

   ```
   python3 "$STAGE/scripts/check_leaks.py" "$STAGE" --source /path/a.md --source /path/b.md
   python3 -m unittest discover -s "$STAGE/scripts"
   wc -l "$STAGE/SKILL.md" "$STAGE"/voice-profile/{shapes,exemplars}/<format>.md "$STAGE"/voice-profile/layer{1,2,4}-<format>.md "$STAGE"/voice-profile/layer3-substance.md "$STAGE"/voice-profile/negative-list.md
   ```

   The leak checker must exit 0. The tests must all pass. The `wc` total must stay under 500 lines, because `writing-in-voice` loads all of those files on every run. Fix a leak by rewriting the offending entry in `STAGE`, then rerun the gate.

8. **Show the diff and get approval.** Run `diff -ru "$SKILL_DIR" "$STAGE" -x __pycache__` and show the user the complete output plus the gate results. Copy nothing back until the user approves this exact diff.

9. **Promote.** After approval, run `rsync -a --exclude __pycache__ "$STAGE"/ "$SKILL_DIR"/`, then rerun the leak checker against `SKILL_DIR` with the same `--source` paths and confirm it exits 0.

## Gotchas

- **The merge is permanent.** The profile stores only weighted means, stdevs, and total weight, so a merged doc cannot be subtracted later. Ingesting the same doc twice double-counts it. Ask before re-ingesting any path.
- **The leak checker only knows what it is given.** Its overlap check covers only the `--source` paths of this run, and its term check covers only the deny-list. Step 2 is what protects against names the deny-list doesn't have yet.
- **Paraphrase drift.** A paraphrase that keeps the source's distinctive word order trips the 8-word overlap check. Rewrite from the pattern, not from the sentence.
- **Zeta word lists are gone on purpose.** They need per-doc presence data the profile does not store, and they leaked domain nouns. Never reintroduce them.
- **A missing deny-list is a warning, not a hard stop.** `check_leaks.py` prints a warning and skips the term check rather than failing, so a run without one can pass while missing private terms. Recreate the file from the user's terms rather than running without one.

## Checklist

- [ ] Format and weight confirmed with the user; one format per run
- [ ] New private terms approved by the user and appended to the external deny-list
- [ ] All edits made in `STAGE`, none in `SKILL_DIR` before approval
- [ ] `merge_profile.py` run; `layer1-<format>.md` regenerated
- [ ] Every new Layer 2-4 entry and shape-card rule is a paraphrase backed by two or more instances, with no citations
- [ ] Exemplar revalidated (exit 0, metrics in range) when the shape card changed
- [ ] Leak checker exit 0, unit tests pass, loaded-file line count under 500
- [ ] User approved the full `diff -ru` before promotion
- [ ] Leak checker rerun against `SKILL_DIR` after promotion
