"""
Preprocessing — section 6.2.

Two variants are produced, for different downstream consumers:

- natural-text (sentence-segmented, original casing, no stopword removal,
  no lemmatization): feed this into NER, sentiment, framing, and the bias
  classifier. Transformers are trained on natural text — stripping
  stopwords or lemmatizing hurts them, it doesn't help.
- lemmatized/stopword-free: only for the TF-IDF/KeyBERT omission-topic stage.
"""
import spacy
from readability import Document

_nlp = None


def get_nlp():
    """Lazy-load spaCy so importing this module doesn't require the model to be present."""
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp


def clean_html(raw_html: str) -> str:
    """Strip boilerplate (nav, ads, footers) from a raw article page, keep the article body."""
    return Document(raw_html).summary()


def to_sentences(text: str) -> list[str]:
    """Natural-text variant: sentence-segmented, casing and stopwords untouched."""
    nlp = get_nlp()
    return [s.text.strip() for s in nlp(text).sents if s.text.strip()]


def to_lemmatized_tokens(text: str) -> list[str]:
    """Lemmatized, stopword-free, punctuation-stripped variant — TF-IDF/KeyBERT only."""
    nlp = get_nlp()
    doc = nlp(text)
    return [
        tok.lemma_.lower()
        for tok in doc
        if not tok.is_stop and not tok.is_punct and not tok.is_space
    ]


def preprocess_article(raw_text: str, is_html: bool = False) -> dict:
    """Convenience wrapper producing both variants an article needs downstream."""
    text = clean_html(raw_text) if is_html else raw_text
    return {
        "clean_text": text,
        "sentences": to_sentences(text),
        "lemmatized_tokens": to_lemmatized_tokens(text),
    }
