"""spaCy layer: skill extraction (PhraseMatcher + longest-match resolution), NER, sentence splitting."""
import functools, logging, re
import spacy
from spacy.matcher import PhraseMatcher
from spacy.util import filter_spans
from .skills import SKILLS, CASE_SENSITIVE_ALIASES

log = logging.getLogger("nlp")


@functools.lru_cache(maxsize=1)
def get_nlp():
    """en_core_web_sm gives NER + sentence boundaries; a blank pipeline is used if the model is missing."""
    try:
        return spacy.load("en_core_web_sm", disable=["lemmatizer", "tagger", "attribute_ruler"])
    except OSError:
        log.warning("en_core_web_sm not installed (python -m spacy download en_core_web_sm); NER disabled")
        nlp = spacy.blank("en")
        nlp.add_pipe("sentencizer")
        return nlp


@functools.lru_cache(maxsize=1)
def _matcher():
    nlp = get_nlp()
    m = PhraseMatcher(nlp.vocab, attr="LOWER")
    for canon, aliases in SKILLS.items():
        names = set(aliases) | (set() if canon == "Go" else {canon.lower()})  # bare "go" is an ordinary verb
        m.add(canon, [nlp.make_doc(a) for a in names])
    return m


def skill_spans(text: str):
    """[(canonical_skill, start_char, end_char)] in text order. Overlaps resolved by longest match,
    so 'Spring Boot' is never also reported as 'Spring', and 'Java' never fires inside 'JavaScript'."""
    doc = get_nlp().make_doc(text or "")
    spans = []
    for mid, s, e in _matcher()(doc):
        sp = doc[s:e]
        canon = get_nlp().vocab.strings[mid]
        if sp.text.lower() in CASE_SENSITIVE_ALIASES and sp.text == sp.text.lower():
            continue
        spans.append(doc.char_span(sp.start_char, sp.end_char, label=canon, alignment_mode="expand") or sp)
    out = []
    for sp in filter_spans([s for s in spans if hasattr(s, "label_") and s.label_]):
        out.append((sp.label_, sp.start_char, sp.end_char))
    return out


def extract_skills(text: str) -> set:
    return {c for c, _, _ in skill_spans(text)}


def person_name(text: str):
    """First PERSON entity near the top of the resume (2-4 words)."""
    nlp = get_nlp()
    if not nlp.has_pipe("ner"):
        return None
    for ent in nlp(text[:400]).ents:
        if ent.label_ == "PERSON" and 2 <= len(ent.text.split()) <= 4 and "\n" not in ent.text.strip():
            return ent.text.strip()
    return None


def orgs(text: str):
    nlp = get_nlp()
    return [e.text for e in nlp(text).ents if e.label_ == "ORG"] if nlp.has_pipe("ner") else []


def sentences(text: str):
    out = []
    for line in re.split(r"\n+", text):
        line = line.strip(" •-*·▪●◦\t")
        if len(line) < 15:
            continue
        out += [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z])", line) if len(s.strip()) >= 15]
    return out
