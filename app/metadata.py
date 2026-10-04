"""Deterministic per-document metadata for the advanced missions (NB5-NB8).

Why derive instead of regenerate?
---------------------------------
`scripts/seed_corpus.py` builds the corpus from a seeded RNG stream. Adding
fields inside that loop would consume extra randomness and shift every
downstream draw, silently changing all 1000 documents -- which would
invalidate the golden set and every rubric threshold in NB1-NB4.

So the advanced missions derive their metadata from the `doc_id` string via a
stable hash. Same doc_id always yields the same metadata, on every machine, in
every Python version, with zero risk to the existing corpus.

    >>> doc_metadata("cloud_000")["tenant"] in TENANTS
    True
    >>> doc_metadata("cloud_000") == doc_metadata("cloud_000")
    True
"""
from __future__ import annotations

import hashlib
from datetime import date, timedelta
from functools import lru_cache

# Three fictional customers sharing one index -- the setup for the
# multi-tenancy isolation exercise in NB7 (deck: OWASP LLM08).
TENANTS = ("acme", "globex", "initech")
ACCESS_LEVELS = ("public", "internal")

# Corpus "publication" window. NB5 filters on `published` to build filters of
# controlled selectivity, which is what triggers the post-filter recall cliff.
EPOCH = date(2023, 1, 1)
SPAN_DAYS = 1275  # 2023-01-01 .. 2026-06-29


def _digest(doc_id: str, salt: str) -> int:
    """Stable non-negative int from (doc_id, salt).

    Uses blake2b rather than builtin hash(): PYTHONHASHSEED randomises str
    hashing per process, so builtin hash() would give different metadata on
    every run and make the mission un-gradable.
    """
    h = hashlib.blake2b(f"{salt}:{doc_id}".encode("utf-8"), digest_size=8)
    return int.from_bytes(h.digest(), "big")


@lru_cache(maxsize=4096)
def doc_metadata(doc_id: str) -> dict:
    """Return the derived metadata payload for one document."""
    published = EPOCH + timedelta(days=_digest(doc_id, "date") % SPAN_DAYS)
    return {
        "tenant": TENANTS[_digest(doc_id, "tenant") % len(TENANTS)],
        # Skewed on purpose: ~25% internal. A filter on access="internal"
        # is selective enough to hurt a naive post-filter search.
        "access": ACCESS_LEVELS[0] if _digest(doc_id, "access") % 4 else ACCESS_LEVELS[1],
        "published": published.isoformat(),
        "published_ts": int(published.strftime("%Y%m%d")),  # int -> range filters
        "lang": "vi",
    }


def enrich(doc: dict) -> dict:
    """Return a copy of `doc` with derived metadata merged in."""
    return {**doc, **doc_metadata(doc["doc_id"])}


def selectivity(docs: list[dict], predicate) -> float:
    """Fraction of `docs` matching `predicate` -- used to label filter strength."""
    if not docs:
        return 0.0
    return sum(1 for d in docs if predicate(d)) / len(docs)
