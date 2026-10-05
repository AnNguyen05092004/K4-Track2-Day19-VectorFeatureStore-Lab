"""Tests cho bonus/agent.py — chunking, tiền xử lý tiếng Việt, cô lập user, degrade khi mất Feast.

Vai trò file: khoá các hành vi mà ARCHITECTURE.md khẳng định, để sửa agent không
âm thầm phá chúng. Không test Feast thật (phụ thuộc dữ liệu đã materialize và TTL).
"""
from __future__ import annotations

import pytest

from app.embeddings import Embedder
from bonus.agent import HybridMemoryAgent, chunk_text, normalize_vi


@pytest.fixture(scope="module")
def embedder() -> Embedder:
    return Embedder()          # load model 1 lần cho cả module


@pytest.fixture()
def agent(embedder, tmp_path) -> HybridMemoryAgent:
    # feast_repo trỏ vào thư mục rỗng -> Feast chắc chắn lỗi -> kiểm tra được đường degrade
    return HybridMemoryAgent(feast_repo=tmp_path, embedder=embedder)


def test_chunk_text_short_stays_one_chunk():
    assert chunk_text("Một câu ngắn.") == ["Một câu ngắn."]
    assert chunk_text("   ") == []


def test_chunk_text_splits_on_sentence_boundary_under_limit():
    text = " ".join(f"Câu số {i} có vài từ để đếm." for i in range(30))
    chunks = chunk_text(text, max_words=20)
    assert len(chunks) > 1
    assert all(len(c.split()) <= 20 for c in chunks)
    assert all(c.endswith(".") for c in chunks)          # không cắt giữa câu


def test_chunk_text_hard_splits_overlong_sentence():
    chunks = chunk_text(" ".join(["từ"] * 130), max_words=60)
    assert [len(c.split()) for c in chunks] == [60, 60, 10]


def test_normalize_vi_strips_diacritics_so_unaccented_query_matches():
    assert normalize_vi("Tự động mở rộng") == normalize_vi("tu dong mo rong")
    assert normalize_vi("Đám mây") == ["dam", "may"]


def test_normalize_vi_drops_function_words_but_keeps_tu():
    toks = normalize_vi("Tôi đã đọc gì về tự động")
    assert "toi" not in toks and "ve" not in toks and "gi" not in toks
    assert "tu" in toks and "dong" in toks


def test_user_isolation_in_search(agent):
    agent.remember("Kế hoạch riêng: ra mắt sản phẩm Zephyr vào tháng 12.", user_id="u_002")
    agent.remember("Ghi chú Kubernetes về autoscaling.", user_id="u_001")
    seen_by_u1 = agent.search("Zephyr ra mắt sản phẩm", user_id="u_001", top_k=10)
    assert all("Zephyr" not in h.memory.text for h in seen_by_u1)
    seen_by_u2 = agent.search("Zephyr ra mắt sản phẩm", user_id="u_002", top_k=1)
    assert seen_by_u2 and "Zephyr" in seen_by_u2[0].memory.text


def test_exact_term_found_by_keyword_branch(agent):
    agent.remember("Ghi chú Postgres: dùng EXPLAIN ANALYZE để xem query plan.", user_id="u_001")
    agent.remember("Bài về cách pha cà phê buổi sáng.", user_id="u_001")
    top = agent.search("EXPLAIN ANALYZE", user_id="u_001", top_k=1)[0]
    assert "Postgres" in top.memory.text
    assert "keyword" in top.via


def test_recall_degrades_without_feast_but_reports_it(agent):
    agent.remember("Ghi chú về cold start của serverless.", user_id="u_001")
    ctx = agent.recall("cold start", user_id="u_001")
    assert "không đọc được từ Feast" in ctx        # lỗi phải hiện ra, không im lặng
    assert "cold start" in ctx                      # ký ức vẫn được trả về


def test_recall_for_unknown_user_is_empty_not_error(agent):
    assert "chưa có ký ức" in agent.recall("bất kỳ", user_id="u_999")


def test_assemble_never_fills_expired_hot_feature():
    # feature "nóng" hết TTL -> None -> phải nói rõ là hết hạn, không bịa số
    ctx = HybridMemoryAgent._assemble(
        {"topic_affinity": "cloud", "preferred_language": "vi", "reading_speed_wpm": 187,
         "queries_last_hour": None, "distinct_topics_24h": None}, [])
    assert "hết hạn TTL" in ctx and "chủ đề quan tâm=cloud" in ctx
