from app.filters import access_filter, combo_filter, tenant_filter
from app.metadata import selectivity

QUERY = "tự động mở rộng theo lưu lượng"


def test_index_carries_topic_payload(index):
    """Regression: topic was missing, so every topic filter matched zero docs."""
    assert "topic" in index.docs[0]
    assert len({d["topic"] for d in index.docs}) >= 5


def test_filtered_ann_matches_exact_ground_truth(index):
    pred, qf = tenant_filter("acme")
    truth = index.pre_filter(QUERY, pred, k=5).doc_ids
    got = index.filtered_ann(QUERY, qf, k=5)
    assert got.recall_against(truth) == 1.0


def test_post_filter_loses_recall_when_filter_is_selective(index):
    """The whole point of NB5: this is a cliff, not a gentle slope."""
    pred, _ = combo_filter("acme", 20260101)
    if selectivity(index.docs, pred) > 0.25:
        import pytest
        pytest.skip("filter not selective enough on the mini corpus")
    truth = index.pre_filter(QUERY, pred, k=5).doc_ids
    post = index.post_filter(QUERY, pred, k=5, fetch_k=5)
    assert post.recall_against(truth) < 1.0


def test_overfetch_restores_post_filter_recall(index):
    pred, _ = access_filter("internal")
    truth = index.pre_filter(QUERY, pred, k=5).doc_ids
    wide = index.post_filter(QUERY, pred, k=5, fetch_k=len(index.docs))
    assert wide.recall_against(truth) == 1.0


def test_every_returned_doc_satisfies_the_filter(index):
    pred, qf = tenant_filter("globex")
    by_id = {d["doc_id"]: d for d in index.docs}
    for doc_id in index.filtered_ann(QUERY, qf, k=5).doc_ids:
        assert pred(by_id[doc_id])
