"""Tests for merge_profile. The profile ships without its corpus, so merging
must give the same numbers as rebuilding from every doc at once -- otherwise
each ingest run silently drifts the targets the validator scores against."""

import sys
import unittest

import merge_profile as mp

sys.path.insert(0, str(mp.DEFAULT_SKILL_DIR / "scripts"))
import stylometry as sm  # noqa: E402

TEXTS = [
    "The job reads a row and writes it back. It is slow. I fixed the lookup. ",
    "The job writes a row and it is slow, so I batched the lookup for it. ",
    "It reads the rows in a loop. That is the slow part. I fixed it. ",
    "The lookup is per row and it is slow. I made it batch the reads. ",
    "i think the cache is stale? not sure. TODO: check the ttl on it. ",
]


def _docs(texts, weight):
    docs = [sm.Doc(identity=f"d{i}", text=t * 3) for i, t in enumerate(texts)]
    for d in docs:
        d.weight = weight
    return docs


class TestMergeStat(unittest.TestCase):
    def test_should_match_a_full_rebuild_when_merging_in_two_batches(self):
        old_docs, new_docs = _docs(TEXTS[:3], 1.0), _docs(TEXTS[3:], 0.3)
        old = sm.build_profile(old_docs)
        new = sm.build_profile(new_docs)
        joint = sm.build_profile(old_docs + new_docs)
        w_old, w_new = 3 * 1.0, 2 * 0.3
        for name in joint.metrics:
            merged = mp.merge_stat(list(old.metrics[name]), w_old, new.metrics[name], w_new)
            for got, want in zip(merged, joint.metrics[name]):
                self.assertAlmostEqual(got, want, places=9, msg=name)

    def test_should_leave_stats_unchanged_when_new_docs_match_the_mean_exactly(self):
        self.assertEqual(mp.merge_stat([10.0, 0.0], 5.0, (10.0, 0.0), 1.0), [10.0, 0.0])


class TestRenderMarkdown(unittest.TestCase):
    def test_should_list_only_the_top_function_words(self):
        raw = {
            "doc_count": 2,
            "total_weight": 1.3,
            "metrics": {"ttr": [0.5, 0.1]},
            "function_word_stats": {f"w{i}": [float(i), 1.0] for i in range(30)},
        }
        md = mp.render_markdown("notes", raw)
        self.assertIn("| w29 |", md)
        self.assertNotIn("| w0 |", md)
        self.assertEqual(md.count("| w"), mp.TOP_FUNCTION_WORDS)


if __name__ == "__main__":
    unittest.main()
