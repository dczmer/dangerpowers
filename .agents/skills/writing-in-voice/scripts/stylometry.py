"""Phase 1: Layer 1 stylometry -- pure stdlib, no external dependencies.

Function-word frequency (Burrows' Delta / Craig's Zeta), sentence statistics,
punctuation frequency, readability, type-token ratio, and profile scoring.
Shared verbatim between voice-profile-builder (build_profile) and
writing-in-voice (score_against_profile) -- do not fork this module.
"""

import math
import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Function word list (Mosteller & Wallace / Burrows' Delta convention):
# articles, prepositions, conjunctions, auxiliary/modal verbs, common pronouns.
# Hard-coded, not derived from the corpus.
# ---------------------------------------------------------------------------
FUNCTION_WORDS = [
    "the", "a", "an", "of", "in", "on", "at", "by", "for", "with", "about",
    "against", "between", "into", "through", "during", "before", "after",
    "above", "below", "to", "from", "up", "down", "out", "off", "over",
    "under", "again", "further", "then", "once", "and", "but", "or", "nor",
    "so", "yet", "if", "because", "as", "until", "while", "although",
    "though", "since", "unless", "whereas", "i", "me", "my", "mine",
    "myself", "we", "us", "our", "ours", "ourselves", "you", "your",
    "yours", "yourself", "yourselves", "he", "him", "his", "himself",
    "she", "her", "hers", "herself", "it", "its", "itself", "they", "them",
    "their", "theirs", "themselves", "this", "that", "these", "those",
    "who", "whom", "whose", "which", "what", "am", "is", "are", "was",
    "were", "be", "been", "being", "have", "has", "had", "having", "do",
    "does", "did", "doing", "will", "would", "shall", "should", "can",
    "could", "may", "might", "must", "not", "no", "nor", "any", "all",
    "some", "each", "every", "either", "neither", "both", "few", "more",
    "most", "other", "such", "own", "same", "than", "too", "very", "just",
    "only", "there", "here", "when", "where", "why", "how",
]

# A small fixed reference set standing in for "other authors" in Zeta's
# original formulation (there is no multi-author corpus here). Deliberately
# generic/AI-style technical prose. Adjustable parameter, not core logic.
CONTRAST_SAMPLES = [
    "This document provides an overview of the system architecture. "
    "It is important to note that the following sections describe the "
    "key components and their interactions in detail.",
    "In order to achieve the desired outcome, several steps must be "
    "followed. First, ensure that all prerequisites are met. Then, "
    "proceed with the implementation as outlined below.",
    "The purpose of this guide is to help users understand how to "
    "configure the application. Please refer to the documentation for "
    "additional information regarding advanced settings.",
    "This feature enables users to streamline their workflow and "
    "improve overall efficiency. It is recommended that teams adopt "
    "this approach as a best practice going forward.",
    "The following table summarizes the results of the analysis. As "
    "shown, the data indicates a clear trend across all categories "
    "examined during this study.",
]

WORD_RE = re.compile(r"[a-z']+")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


@dataclass
class Doc:
    identity: str
    text: str  # markdown-stripped body used for feature extraction
    weight: float = 1.0

    @property
    def words(self) -> list[str]:
        return WORD_RE.findall(self.text.lower())

    @property
    def sentences(self) -> list[str]:
        stripped = self.text.strip()
        if not stripped:
            return []
        parts = [s.strip() for s in SENTENCE_SPLIT_RE.split(stripped)]
        return [s for s in parts if s]


def strip_markdown(raw_text: str) -> str:
    """Strip frontmatter and common markdown syntax before feature extraction
    so heading markers, bullets, links, etc. don't pollute word counts."""
    text = raw_text
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            text = text[end + 5:]
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)  # fenced code blocks
    text = re.sub(r"`[^`]*`", " ", text)  # inline code
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)  # images
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)  # links -> link text
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.MULTILINE)  # headings
    text = re.sub(r"^\s{0,3}[-*+]\s+", "", text, flags=re.MULTILINE)  # bullets
    text = re.sub(r"^\s{0,3}>\s*", "", text, flags=re.MULTILINE)  # blockquotes
    text = re.sub(r"^\s*\|.*\|\s*$", " ", text, flags=re.MULTILINE)  # tables
    text = re.sub(r"\*\*([^*]*)\*\*", r"\1", text)  # bold
    text = re.sub(r"\*([^*]*)\*", r"\1", text)  # italic
    text = re.sub(r"_([^_]*)_", r"\1", text)  # italic (underscore)
    return text


def load_docs(paths: list[str]) -> list["Doc"]:
    docs = []
    for path in paths:
        with open(path, encoding="utf-8") as f:
            raw = f.read()
        docs.append(Doc(identity=path, text=strip_markdown(raw)))
    return docs


# ---------------------------------------------------------------------------
# Function-word frequency / Delta / Zeta
# ---------------------------------------------------------------------------

def freq_vector(doc: Doc, vocab: list[str]) -> dict[str, float]:
    """Per-1,000-word frequency of each vocab word in doc."""
    words = doc.words
    n = len(words)
    if n == 0:
        return {w: 0.0 for w in vocab}
    counts = {w: 0 for w in vocab}
    vocab_set = set(vocab)
    for w in words:
        if w in vocab_set:
            counts[w] += 1
    return {w: (counts[w] / n) * 1000 for w in vocab}


def _weighted_mean_stdev(values: list[float], weights: list[float]) -> tuple[float, float]:
    total_weight = sum(weights)
    if total_weight == 0:
        return 0.0, 0.0
    mean = sum(v * w for v, w in zip(values, weights)) / total_weight
    variance = sum(w * (v - mean) ** 2 for v, w in zip(values, weights)) / total_weight
    return mean, math.sqrt(variance)


def corpus_stats(docs: list[Doc], vocab: list[str]) -> dict[str, tuple[float, float]]:
    """Per-word weighted mean/stdev of freq_vector values across docs."""
    vectors = [freq_vector(d, vocab) for d in docs]
    weights = [d.weight for d in docs]
    stats = {}
    for w in vocab:
        values = [v[w] for v in vectors]
        stats[w] = _weighted_mean_stdev(values, weights)
    return stats


def delta(doc_vector: dict[str, float], stats: dict[str, tuple[float, float]]) -> float:
    """Burrows' Delta: mean absolute z-score distance across vocab words."""
    z_scores = []
    for w, (mean, stdev) in stats.items():
        if stdev == 0:
            continue
        z_scores.append(abs((doc_vector.get(w, 0.0) - mean) / stdev))
    if not z_scores:
        return 0.0
    return sum(z_scores) / len(z_scores)


def zeta(
    bucket_docs: list[Doc],
    contrast_docs: list[Doc],
    threshold: float = 0.3,
) -> tuple[list[str], list[str]]:
    """Words disproportionately present/absent in bucket_docs vs contrast_docs,
    using Craig's Zeta-style presence proportions (fraction of docs containing
    the word, not raw frequency)."""
    bucket_vocab = set()
    for d in bucket_docs:
        bucket_vocab.update(set(d.words))
    contrast_vocab = set()
    for d in contrast_docs:
        contrast_vocab.update(set(d.words))
    vocab = sorted(bucket_vocab | contrast_vocab)

    def presence(docs: list[Doc], word: str) -> float:
        if not docs:
            return 0.0
        return sum(1 for d in docs if word in set(d.words)) / len(docs)

    present_words = []
    absent_words = []
    for w in vocab:
        p_bucket = presence(bucket_docs, w)
        p_contrast = presence(contrast_docs, w)
        if p_bucket - p_contrast >= threshold:
            present_words.append(w)
        elif p_contrast - p_bucket >= threshold:
            absent_words.append(w)
    return present_words, absent_words


# ---------------------------------------------------------------------------
# Sentence / punctuation / readability / lexical diversity
# ---------------------------------------------------------------------------

def sentence_stats(doc: Doc) -> dict:
    sentences = doc.sentences
    lengths = [len(WORD_RE.findall(s.lower())) for s in sentences]
    lengths = [l for l in lengths if l > 0]
    if not lengths:
        return {"mean_len": 0.0, "stdev_len": 0.0, "distribution": []}
    mean_len, stdev_len = _weighted_mean_stdev(lengths, [1.0] * len(lengths))
    return {"mean_len": mean_len, "stdev_len": stdev_len, "distribution": lengths}


def burstiness(doc: Doc) -> float:
    """Variance of inter-occurrence gaps for the doc's own high-frequency
    content words (function words excluded, so this reflects topical/content
    word usage rather than grammar)."""
    words = doc.words
    function_set = set(FUNCTION_WORDS)
    content_words = [w for w in words if w not in function_set and len(w) > 2]
    if len(content_words) < 4:
        return 0.0
    counts: dict[str, int] = {}
    for w in content_words:
        counts[w] = counts.get(w, 0) + 1
    n_top = max(1, len(counts) // 10)
    top_words = sorted(counts, key=lambda w: -counts[w])[:n_top]
    gap_variances = []
    for w in top_words:
        positions = [i for i, tok in enumerate(content_words) if tok == w]
        if len(positions) < 2:
            continue
        gaps = [positions[i + 1] - positions[i] for i in range(len(positions) - 1)]
        _, stdev = _weighted_mean_stdev(gaps, [1.0] * len(gaps))
        gap_variances.append(stdev ** 2)
    if not gap_variances:
        return 0.0
    return sum(gap_variances) / len(gap_variances)


PUNCTUATION_PATTERNS = {
    # `--` is the author's spelling of an em dash, but in a markdown corpus the
    # bare digraph is mostly *not* punctuation: Phase 4 item 1 found the notes format's
    # 14.9/1000 was almost entirely `---` horizontal rules, `|---|` table
    # separators and CLI flags (`--limit`), which is what made Layer 1 contradict
    # Layer 4's "em dashes -- never used". The lookarounds drop all three. Cost:
    # an attached `word--word` is not counted either; the corpus contains one.
    "em_dash": re.compile(r"[—–]|(?<![-\w])--(?![-\w=])"),
    "semicolon": re.compile(r";"),
    "parenthetical": re.compile(r"\("),
    "ellipsis": re.compile(r"\.\.\.|…"),
    "exclamation": re.compile(r"!"),
}


def punctuation_freq(doc: Doc) -> dict[str, float]:
    n_words = len(doc.words)
    if n_words == 0:
        return {k: 0.0 for k in PUNCTUATION_PATTERNS}
    return {
        name: (len(pattern.findall(doc.text)) / n_words) * 1000
        for name, pattern in PUNCTUATION_PATTERNS.items()
    }


def _count_syllables(word: str) -> int:
    """Heuristic vowel-cluster syllable counter."""
    word = word.lower()
    if not word:
        return 0
    clusters = re.findall(r"[aeiouy]+", word)
    count = len(clusters)
    if word.endswith("e") and count > 1:
        count -= 1
    return max(1, count)


def readability(doc: Doc) -> dict[str, float]:
    sentences = doc.sentences
    words = doc.words
    n_sentences = max(1, len(sentences))
    n_words = max(1, len(words))
    syllables = [_count_syllables(w) for w in words]
    n_syllables = sum(syllables)
    complex_words = sum(1 for s in syllables if s >= 3)

    words_per_sentence = n_words / n_sentences
    syllables_per_word = n_syllables / n_words

    flesch_kincaid = 0.39 * words_per_sentence + 11.8 * syllables_per_word - 15.59
    flesch_reading_ease = 206.835 - 1.015 * words_per_sentence - 84.6 * syllables_per_word
    gunning_fog = 0.4 * (words_per_sentence + 100 * (complex_words / n_words))

    return {
        "flesch_kincaid": flesch_kincaid,
        "flesch_reading_ease": flesch_reading_ease,
        "gunning_fog": gunning_fog,
    }


def type_token_ratio(doc: Doc) -> float:
    words = doc.words
    if not words:
        return 0.0
    return len(set(words)) / len(words)


# ---------------------------------------------------------------------------
# Profile building / scoring
# ---------------------------------------------------------------------------

@dataclass
class LayerOneProfile:
    vocab: list[str]
    function_word_stats: dict[str, tuple[float, float]]
    metrics: dict[str, tuple[float, float]] = field(default_factory=dict)


NUMERIC_METRIC_NAMES = [
    "mean_sentence_len", "stdev_sentence_len", "ttr", "burstiness",
    "punct_em_dash", "punct_semicolon", "punct_parenthetical",
    "punct_ellipsis", "punct_exclamation",
    "flesch_kincaid", "flesch_reading_ease", "gunning_fog",
]


def _doc_numeric_metrics(doc: Doc) -> dict[str, float]:
    sstats = sentence_stats(doc)
    punct = punctuation_freq(doc)
    read = readability(doc)
    return {
        "mean_sentence_len": sstats["mean_len"],
        "stdev_sentence_len": sstats["stdev_len"],
        "ttr": type_token_ratio(doc),
        "burstiness": burstiness(doc),
        "punct_em_dash": punct["em_dash"],
        "punct_semicolon": punct["semicolon"],
        "punct_parenthetical": punct["parenthetical"],
        "punct_ellipsis": punct["ellipsis"],
        "punct_exclamation": punct["exclamation"],
        "flesch_kincaid": read["flesch_kincaid"],
        "flesch_reading_ease": read["flesch_reading_ease"],
        "gunning_fog": read["gunning_fog"],
    }


def build_profile(bucket_docs: list[Doc], vocab: list[str] = FUNCTION_WORDS) -> LayerOneProfile:
    """Runs Layer 1 stylometry over a format x era bucket's docs (secondary
    docs should already carry a reduced `weight`, e.g. 0.3, before calling
    this) and emits target ranges (mean +/- stdev) for each metric."""
    function_word_stats = corpus_stats(bucket_docs, vocab)

    weights = [d.weight for d in bucket_docs]
    per_metric_values: dict[str, list[float]] = {name: [] for name in NUMERIC_METRIC_NAMES}
    for d in bucket_docs:
        m = _doc_numeric_metrics(d)
        for name in NUMERIC_METRIC_NAMES:
            per_metric_values[name].append(m[name])

    metrics = {
        name: _weighted_mean_stdev(per_metric_values[name], weights)
        for name in NUMERIC_METRIC_NAMES
    }

    return LayerOneProfile(vocab=vocab, function_word_stats=function_word_stats, metrics=metrics)


def score_against_profile(candidate_text: str, profile: LayerOneProfile) -> dict:
    """Called by writing-in-voice at generation time. Returns per-metric
    distance (in stdevs from the profile's target mean) plus an overall
    Delta-style score."""
    doc = Doc(identity="<candidate>", text=strip_markdown(candidate_text))
    doc_vector = freq_vector(doc, profile.vocab)
    delta_score = delta(doc_vector, profile.function_word_stats)

    candidate_metrics = _doc_numeric_metrics(doc)
    metric_z = {}
    for name, (mean, stdev) in profile.metrics.items():
        value = candidate_metrics[name]
        metric_z[name] = 0.0 if stdev == 0 else (value - mean) / stdev

    overall = delta_score if not metric_z else (
        delta_score + sum(abs(z) for z in metric_z.values()) / len(metric_z)
    ) / 2

    return {"delta": delta_score, "metric_z": metric_z, "overall": overall}


def centroid_distance(doc: Doc, bucket_docs: list[Doc], vocab: list[str] = FUNCTION_WORDS) -> float:
    """Delta distance of doc from its bucket's own centroid (mean/stdev of
    function-word frequencies) -- used for exemplar selection in Phase 2."""
    stats = corpus_stats(bucket_docs, vocab)
    return delta(freq_vector(doc, vocab), stats)
