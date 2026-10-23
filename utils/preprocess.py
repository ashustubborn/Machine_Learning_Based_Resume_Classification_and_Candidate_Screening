"""
Core NLP preprocessing used both at training time and inference time.
Kept dependency-light (regex + a small built-in stopword list) so the
project has no heavyweight NLTK/spaCy download requirement.
"""

import re

STOPWORDS = set("""
a about above after again against all am an and any are aren't as at be because
been before being below between both but by can't cannot could couldn't did
didn't do does doesn't doing don't down during each few for from further had
hadn't has hasn't have haven't having he he'd he'll he's her here here's hers
herself him himself his how how's i i'd i'll i'm i've if in into is isn't it
it's its itself let's me more most mustn't my myself no nor not of off on once
only or other ought our ours ourselves out over own same shan't she she'd
she'll she's should shouldn't so some such than that that's the their theirs
them themselves then there there's these they they'd they'll they're they've
this those through to too under until up very was wasn't we we'd we'll we're
we've were weren't what what's when when's where where's which while who
who's whom why why's with won't would wouldn't you you'd you'll you're you've
your yours yourself yourselves
""".split())


def clean_text(text: str) -> str:
    """Lowercase, strip emails/urls/phone numbers/special chars, collapse whitespace."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"http\S+|www\.\S+", " ", text)
    text = re.sub(r"\S+@\S+", " ", text)
    text = re.sub(r"\+?\d[\d\-\s]{7,}\d", " ", text)  # phone-like numbers
    text = re.sub(r"[^a-z0-9\s\.\-\+#/]", " ", text)  # keep tokens like c++, node.js, ci/cd
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text: str):
    return text.split()


def remove_stopwords(tokens):
    return [t for t in tokens if t not in STOPWORDS and len(t) > 1]


def preprocess_for_model(text: str) -> str:
    """Full pipeline producing a cleaned, stopword-free string ready for TF-IDF."""
    cleaned = clean_text(text)
    tokens = remove_stopwords(tokenize(cleaned))
    return " ".join(tokens)
