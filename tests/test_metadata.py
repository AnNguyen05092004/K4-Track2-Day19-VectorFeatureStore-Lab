from app.metadata import ACCESS_LEVELS, TENANTS, doc_metadata, enrich


def test_metadata_is_deterministic():
    """Must not depend on PYTHONHASHSEED, or the rubric becomes ungradable."""
    a = doc_metadata("cloud_000")
    b = doc_metadata("cloud_000")
    assert a == b
    assert a["tenant"] in TENANTS
    assert a["access"] in ACCESS_LEVELS


def test_metadata_differs_across_docs():
    ids = [f"cloud_{i:03d}" for i in range(60)]
    assert len({doc_metadata(i)["tenant"] for i in ids}) == len(TENANTS)


def test_tenants_are_roughly_balanced():
    ids = [f"cloud_{i:03d}" for i in range(300)]
    counts = {t: sum(1 for i in ids if doc_metadata(i)["tenant"] == t) for t in TENANTS}
    assert all(60 <= c <= 140 for c in counts.values()), counts


def test_published_ts_is_sortable_int():
    m = doc_metadata("cloud_001")
    assert 20230101 <= m["published_ts"] <= 20261231
    assert m["published"].startswith(str(m["published_ts"])[:4])


def test_enrich_preserves_original_fields():
    doc = {"doc_id": "cloud_002", "title": "t", "text": "x", "topic": "cloud"}
    out = enrich(doc)
    assert out["title"] == "t" and out["topic"] == "cloud"
    assert "tenant" in out and "published_ts" in out
