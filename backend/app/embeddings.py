"""Embedding backend. Uses Sentence-Transformers (all-MiniLM-L6-v2) when installed and its model
is downloadable; otherwise falls back to TF-IDF (1-2 grams) so the app always runs offline."""
import logging, os
import numpy as np

log = logging.getLogger("embeddings")
_model = None
_tried = False


def _load_transformer():
    global _model, _tried
    if _tried:
        return _model
    _tried = True
    if os.getenv("USE_TFIDF") == "1":
        return None
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"))
        log.info("Using sentence-transformers backend")
    except Exception as e:  # not installed / offline
        log.warning("sentence-transformers unavailable (%s); using TF-IDF fallback", e)
    return _model


class Encoder:
    """encode(list[str]) -> L2-normalised matrix. `lo`/`hi` calibrate raw cosine -> 0..1."""

    def __init__(self, corpus):
        self.model = _load_transformer()
        if self.model is not None:
            self.kind, self.lo, self.hi = "sentence-transformers", 0.20, 0.65
        else:
            from sklearn.feature_extraction.text import TfidfVectorizer
            self.kind, self.lo, self.hi = "tfidf", 0.02, 0.20
            self.vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, stop_words="english").fit(corpus)

    def encode(self, texts):
        if not texts:
            return np.zeros((0, 1))
        if self.model is not None:
            return np.asarray(self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False))
        return self.vec.transform(texts).toarray()

    def calibrate(self, raw):
        return float(min(1.0, max(0.0, (raw - self.lo) / (self.hi - self.lo))))
