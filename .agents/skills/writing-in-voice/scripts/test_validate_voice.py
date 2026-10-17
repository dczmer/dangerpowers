"""Tests for Phase 3's validation layer.

Run from this directory: python3 -m unittest discover

The point of these tests is the plan's §7 acceptance criterion: the negative-list
scan must have no false negatives on the literal Part 1 checklist items. So they
assert on tells copied verbatim out of the research doc, not on paraphrases --
if someone loosens a pattern, the corresponding assertion fails.
"""

import unittest

import stylometry as sm
import validate_voice as vv


class TestNegativeListScan(unittest.TestCase):
    def _labels(self, text: str) -> set[str]:
        return {h["label"] for h in vv.scan_negative_list(text)}

    def test_clean_text_has_no_hits(self):
        text = (
            "The sync job reads from the queue and writes to the ledger. "
            "It is slow because each row does its own lookup. I batched them.\n"
        )
        self.assertEqual(vv.scan_negative_list(text), [])

    def test_vocabulary_tells_verbatim(self):
        # Part 1, category 1 -- one sentence per sub-bullet, tells copied verbatim.
        cases = {
            "This stands as a testament to its pivotal role.": [
                "vocabulary tell: 'stands as'",
                "vocabulary tell: 'testament'",
                "vocabulary tell: 'pivotal role'",
            ],
            "The result underscores the enduring, deeply rooted design.": [
                "vocabulary tell: 'underscores'",
                "vocabulary tell: 'enduring'",
                "vocabulary tell: 'deeply rooted'",
            ],
            "It boasts a vibrant, groundbreaking, renowned diverse array.": [
                "vocabulary tell: 'boasts a'",
                "vocabulary tell: 'vibrant'",
                "vocabulary tell: 'groundbreaking'",
                "vocabulary tell: 'renowned'",
                "vocabulary tell: 'diverse array'",
            ],
            "Industry reports say experts argue otherwise.": [
                "vocabulary tell: 'industry reports'",
                "vocabulary tell: 'experts argue'",
            ],
            "We delve into the intricate tapestry of this crucial landscape.": [
                "vocabulary tell: 'delve'",
                "vocabulary tell: 'intricate'",
                "vocabulary tell: 'tapestry'",
                "vocabulary tell: 'crucial'",
            ],
            "This will align with the plan, showcasing and emphasizing scale.": [
                "vocabulary tell: 'align with'",
                "vocabulary tell: 'showcasing'",
                "vocabulary tell: 'emphasizing'",
            ],
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertLessEqual(set(expected), self._labels(text))

    def test_phrasing_tells_verbatim(self):
        cases = {
            "It is not only faster but also cheaper.": "negative parallelism: 'not only X but Y'",
            "It's not just a cache, it's a queue.": "negative parallelism: \"it's not just X, it's Y\"",
            "Despite its strengths, the service faces challenges.": "formulaic challenges/future opener: 'Despite its ...'",
            "The term refers to a retry budget.": "copulative avoidance: 'refers to' in place of is/are",
            "It serves as the entrypoint.": "vocabulary tell: 'serves as'",
        }
        for text, label in cases.items():
            with self.subTest(text=text):
                self.assertIn(label, self._labels(text))

    def test_narrowed_tells_still_catch_the_ai_construction(self):
        """Phase 4 narrowed three patterns that fired on the author's own
        held-out writing. The AI form must still be caught -- these assertions
        are what stops a future loosening from gutting the check."""
        cases = {
            "Not a cache, but a queue.": "absolute negation: sentence-initial 'Not X, but Y'",
            "It is not a rewrite, but rather an incremental migration.":
                "absolute negation: 'not X, but rather/instead Y'",
            "The report is not generated nightly, but instead streamed.":
                "absolute negation: 'not X, but rather/instead Y'",
            "Highlighting the significance of the change.": "vocabulary tell: 'highlighting'",
            "Latency correlates strongly with batch size.":
                "vocabulary tell: 'correlate' (analytical register)",
        }
        for text, label in cases.items():
            with self.subTest(text=text):
                self.assertIn(label, self._labels(text))

    def test_narrowed_tells_do_not_fire_on_the_authors_own_usage(self):
        """Each string here models a sentence shape from the held-out corpus
        that the unguarded patterns flagged. A hit means the
        negative list is calling the author's own voice an AI tell."""
        clean = [
            "The cache is not part of the write path, but it is a critical read dependency.",
            "The report will not crash, but it will return empty results.",
            "I am not familiar enough with this class yet, but I will pick it up tomorrow.",
            "Query editor with auto-complete and syntax highlighting.",
            "Failure logs must include the request id so oncall can correlate the log with the ticket.",
        ]
        for text in clean:
            with self.subTest(text=text):
                self.assertEqual(vv.scan_negative_list(text), [])

    def test_meta_leakage_and_artifacts(self):
        cases = {
            "As an AI, I cannot verify this.": "assistant self-reference leaked into content",
            "This is past my knowledge cutoff.": "knowledge-cutoff disclaimer leaked into content",
            "Let me know if you want a different tone.": "chat scaffolding leaked into content",
            "Owner: [INSERT NAME]": "unfilled placeholder text",
            "See the docs contentReference here.": "ChatGPT citation debris: 'contentReference'",
            "Per the RFC [cite: 3] this is fine.": "Gemini citation debris: '[cite: N]'",
        }
        for text, label in cases.items():
            with self.subTest(text=text):
                self.assertIn(label, self._labels(text))

    def test_curly_quotes_and_emoji(self):
        self.assertIn("curly quotes (corpus uses straight quotes)", self._labels("the “fast” path"))
        self.assertIn("decorative emoji", self._labels("shipped \U0001F680"))

    def test_hit_reports_line_number(self):
        text = "clean first line\nthis is a testament to nothing\n"
        hits = [h for h in vv.scan_negative_list(text) if h["match"].lower() == "testament"]
        self.assertEqual([h["line"] for h in hits], [2])

    def test_case_insensitive(self):
        self.assertIn("vocabulary tell: 'delve'", self._labels("DELVE into it"))


class TestStructuralScan(unittest.TestCase):
    """Calibration item 3. The gating thresholds were set above the maximum
    measured over all 69 real held-out docs, so the author's own writing must
    scan clean -- that is the property these tests defend, since a structural
    gate that fires on real docs is worse than no gate (finding 3)."""

    def _hits(self, text: str) -> list[str]:
        return [h["label"] for h in vv.scan_structure(vv.measure_structure(text))]

    def _prose(self, n_words: int) -> str:
        return ("the sync job reads a row and writes it back to billing. " * (n_words // 10))

    def test_table_heavy_doc_fails(self):
        text = self._prose(120) + """
| Concern | State | Owner |
|---|---|---|
| a | b | c |

| Team | Impact | Owner |
|---|---|---|
| x | y | z |
"""
        self.assertTrue(any("unnecessary tables" in h for h in self._hits(text)))

    def test_boldface_overuse_fails(self):
        text = ("this **change** is **fast** and **safe** and **clear** and "
                "**correct** and **cheap**.\n")
        self.assertTrue(any("boldface overuse" in h for h in self._hits(text)))

    def test_one_table_in_a_long_doc_is_fine(self):
        """Real docs do contain the occasional table; the tell is density."""
        text = self._prose(1200) + "\n| a | b |\n|---|---|\n| 1 | 2 |\n"
        self.assertEqual(self._hits(text), [])

    def test_label_style_bold_is_not_emphasis(self):
        """`**NOTE:**`/`**Impact:**` labels are the author's own convention
        (layer4-code-review positive list), so they must not count toward density."""
        text = "\n".join(f"- **Impact:** the row {i} is slow" for i in range(12))
        self.assertEqual(self._hits(text), [])

    def test_code_fences_do_not_count(self):
        """A shell transcript is full of `#` lines, `|` pipes and `**` globs. An
        early version of this scan reported 35 empty sections in a real tutorial."""
        text = self._prose(200) + """
```sh
# list the files
ls -l | grep '**' | awk '{print $1}'
# | a | b |
# |---|---|
```
"""
        self.assertEqual(self._hits(text), [])
        self.assertEqual(vv.measure_structure(text)["tables"], 0)

    def test_uncalibrated_signals_are_measured_but_do_not_gate(self):
        """Title-case headings and empty sections did not separate real docs from
        the slop control, so they are reported, not gated. If someone promotes
        them to the gate they must recalibrate first."""
        text = "# Executive Summary And Strategic Context\n\n## Immediate Actions\n\n## Next Steps\n\nok.\n"
        s = vv.measure_structure(text)
        self.assertTrue(s["title_case_headings"])
        self.assertTrue(s["empty_sections"])
        self.assertEqual(self._hits(text), [])


class TestEmDashMetric(unittest.TestCase):
    """Calibration item 1: `punct_em_dash` was counting markdown furniture, which
    put Layer 1 (14.9/1000 for notes) in direct contradiction with Layer 4
    ("em dashes -- never used"). It must count prose dashes only, because
    `writing-in-voice` is told to aim at this number and em dashes in prose are a
    Part 1 tell."""

    def _per_1000(self, text: str) -> float:
        return sm.punctuation_freq(sm.Doc(identity="t", text=text))["em_dash"]

    def test_markdown_furniture_is_not_punctuation(self):
        for text in [
            "one two three\n\n---\n\nfour five six\n",          # horizontal rule
            "| a | b |\n|---|---|\n| 1 | 2 |\n",                # table separator
            "run `deploy.py --limit host --tags trusted` now\n",  # CLI flags
        ]:
            with self.subTest(text=text):
                self.assertEqual(self._per_1000(text), 0.0)

    def test_prose_dashes_are_still_counted(self):
        self.assertGreater(self._per_1000("it worked -- barely\n"), 0.0)
        self.assertGreater(self._per_1000("it worked — barely\n"), 0.0)


class TestValidateResult(unittest.TestCase):
    """validate() plumbing, exercised against a synthetic profile so these
    tests don't depend on the real corpus being present."""

    def _profile(self) -> sm.LayerOneProfile:
        # Docs must differ from each other, or every function word has stdev 0
        # and Delta collapses to 0.0 for any input.
        texts = [
            "The job reads a row and writes it back. It is slow. I fixed the lookup. ",
            "The job writes a row and it is slow, so I batched the lookup for it. ",
            "It reads the rows in a loop. That is the slow part. I fixed it. ",
            "The lookup is per row and it is slow. I made it batch the reads. ",
        ]
        docs = [sm.Doc(identity=f"d{i}", text=t * 4) for i, t in enumerate(texts)]
        return sm.build_profile(docs)

    def _validate(self, text: str, profile: sm.LayerOneProfile) -> dict:
        """vv.validate() against the synthetic profile instead of the real
        corpus JSON, so these tests exercise the actual pass/fail wiring rather
        than a copy of it."""
        real_load = vv.load_profile
        vv.load_profile = lambda fmt: profile
        try:
            return vv.validate(text, "technical-writing")
        finally:
            vv.load_profile = real_load

    def test_negative_hit_fails_regardless_of_delta(self):
        """A tell fails the run no matter what Delta says -- the negative list
        is the gate, Delta is context."""
        profile = self._profile()
        text = "The job reads a row and writes it back. It is a testament to slowness."
        result = self._validate(text, profile)
        self.assertTrue(result["negative_hits"])
        self.assertFalse(result["passed"])

    def test_delta_outside_the_observed_band_does_not_fail_a_clean_draft(self):
        """Delta was demoted to informational after Phase 4 calibration found it
        passes deliberate AI slop and would fail real corpus docs at any tighter
        threshold. This asserts the demotion: a text far from the profile, with
        no tells in it, still passes."""
        profile = self._profile()
        far = (
            "Whereas the aforementioned subsystem, having been architected upon "
            "principles of considerable abstraction, shall thereafter be evaluated."
        )
        result = self._validate(far, profile)
        self.assertGreater(result["delta"], vv.DELTA_OBSERVED_MAX)
        self.assertFalse(result["delta_in_observed_band"])
        self.assertEqual(result["negative_hits"], [])
        self.assertTrue(result["passed"])

    def test_structural_hit_alone_fails_the_run(self):
        """A draft with no vocabulary tells but AI-shaped formatting must still
        fail -- structural hits are part of the gate, not a report line."""
        text = ("this **change** is **fast** and **safe** and **clear** and "
                "**correct** and **cheap**.\n")
        result = self._validate(text, self._profile())
        self.assertEqual(result["negative_hits"], [])
        self.assertTrue(result["structural_hits"])
        self.assertFalse(result["passed"])

    def test_in_profile_text_scores_closer_than_off_profile_text(self):
        profile = self._profile()
        near = "The job reads a row and writes it back. It is slow. I fixed the lookup."
        far = (
            "Whereas the aforementioned subsystem, having been architected upon "
            "principles of considerable abstraction, shall thereafter be evaluated."
        )
        self.assertLess(
            sm.score_against_profile(near, profile)["delta"],
            sm.score_against_profile(far, profile)["delta"],
        )


if __name__ == "__main__":
    unittest.main()
