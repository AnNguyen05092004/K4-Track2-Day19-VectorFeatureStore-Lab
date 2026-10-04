# Day 19 Lab — Grading Rubric (100 pts core + 20 bonus)

Maps 1-to-1 with the slide deliverable (4 bullets) + repo conventions.
Track-2 Daily Lab weight = 30%.

The lab supports two paths (lite vs Docker). Both paths produce identical
output formats — each criterion accepts evidence from either path.

Submit screenshots + notebook output for each criterion.

| # | Notebook | Criterion | Pts |
|---|---|---|---:|
| 1 | `01_embeddings_index` | `client.count("lab19").count == 1000` | 5 |
| 1 | `01_embeddings_index` | Top-5 results visible for the keyword query (cell §5 output) | 5 |
| 1 | `01_embeddings_index` | Paraphrase query (without literal "cloud") returns top-5 dominated by `cloud` topic | 10 |
| 2 | `02_hybrid_search_rrf` | `search_hybrid` implemented per RRF formula `1/(k + rank)`, rank 1-based | 10 |
| 2 | `02_hybrid_search_rrf` | Avg Precision@10 table: hybrid > keyword AND hybrid > semantic | 10 |
| 2 | `02_hybrid_search_rrf` | Slice table by query type: hybrid wins on `mixed`, vector on `paraphrase`, BM25 on `exact` (or close) | 5 |
| 3 | `03_search_api_benchmark` | FastAPI `/search` returns valid `SearchResponse` with `latency_ms` field | 5 |
| 3 | `03_search_api_benchmark` | P50/P95/P99 latency table for 3 modes printed (server-side measurement) | 10 |
| 3 | `03_search_api_benchmark` | Hybrid P99 server-side < 50 ms after warm-up | 10 |
| 4 | `04_feast_feature_store` | `feast apply` succeeds — 3 feature views registered (`feature-views list` shows all 3) | 5 |
| 4 | `04_feast_feature_store` | `materialize-incremental` succeeds — log shows rows materialized to online store | 5 |
| 4 | `04_feast_feature_store` | `get_online_features()` returns valid dict for `user_id=u_001` | 5 |
| 4 | `04_feast_feature_store` | 100-call online lookup P99 reported (any value acceptable, but P99 < 10 ms = full credit) | 5 |
| 4 | `04_feast_feature_store` | PIT join via `get_historical_features()` returns 3 rows × N features | 5 |
| — | All notebooks      | Reproducible from clean `bash setup-lite.sh && make benchmark` (lite) or `bash setup-docker.sh && make benchmark` (docker) | 5 |
|   |                    | **Core total (NB1–NB4)** | **100** |

## Khối nâng cao NB5–NB8 (50 pts)

Bám sát phần deck mở rộng 2026. Mỗi tiêu chí chấm trên output notebook đã chạy.

| # | Notebook | Criterion | Pts |
|---|---|---|---:|
| 5 | `05_filtered_search` | Bảng recall theo độ chọn lọc: post-filter **giảm rõ rệt** khi filter chặt, filtered-ANN giữ 1.00 | 5 |
| 5 | `05_filtered_search` | Over-fetch ladder cho thấy `fetch_k` phải ≈ 50% corpus mới cứu được recall | 5 |
| 6 | `06_agent_retrieval` | Bảng 3 chiến lược ở **cùng ngân sách 16 doc**; agentic > single-shot cả `recall` lẫn `balance` | 5 |
| 6 | `06_agent_retrieval` | Giải thích được vì sao `agentic (+filter)` **thấp hơn** `agentic (no filter)` | 4 |
| 6 | `06_agent_retrieval` | `build_context()` chạy được, in ra cả feature (Feast) lẫn `doc_ids` | 3 |
| 7 | `07_semantic_cache` | Bảng sweep có **cả hai** cột: tiết kiệm và trả lời sai | 5 |
| 7 | `07_semantic_cache` | Chọn được ngưỡng có lý cho corpus này + giải thích vì sao 0,75 chưa đủ | 4 |
| 7 | `07_semantic_cache` | Demo rò chéo tenant: leak khi `namespaced=False`, MISS khi `True` | 3 |
| 8 | `08_feature_engineering` | Bảng leakage: `target-naive` gap > 0.30 trên `session_id`, in-fold ≈ 0 | 4 |
| 8 | `08_feature_engineering` | PIT vs latest join: báo cáo % dòng rò + chênh lệch AUC | 4 |
| 8 | `08_feature_engineering` | On-demand feature view: cùng user, hai `amount` → hai `amount_vs_avg` | 4 |
| — | — | `make test` và `make verify-lite` đều xanh trên máy sạch | 4 |
|   |                    | **Advanced total** | **50** |

> Tổng: 100 (core) + 50 (nâng cao) + 20 (bonus). Giảng viên có thể chọn chấm
> core-only cho lớp chạy chậm, hoặc core + chọn 2 trong 4 mission nâng cao.

## Bonus Challenge (optional, 20 bonus pts)

Open-ended — see [`BONUS-CHALLENGE.md`](BONUS-CHALLENGE.md). Brief:

| Criterion | Pts |
|---|---:|
| `bonus/ARCHITECTURE.md` exists, ≥ 600 words, has architecture diagram | 3 |
| 3 architecture decisions with **explicit tradeoff** (X vs Y, why X) | 6 |
| At least 1 decision shows Vietnamese-context awareness | 2 |
| Rejected alternative explicitly named with reason | 2 |
| `bonus/agent.py` runs (`HybridMemoryAgent.remember()` + `.recall()`) | 4 |
| `bonus/demo.py` exits 0 with 5 query outputs printed | 3 |
|  | **Bonus total** | **20** |

The bonus does **not** affect your core grade negatively; missing it is fine.
A **strong** bonus submission gets a substantive instructor written review
focused on judgment and tradeoff reasoning.

## Submission

**No PR. Submit a public GitHub URL into the VinUni LMS Day-19 box.**

1. Push your work to `<your-username>/K4-Track2-Day19-VectorFeatureStore-Lab`
   (forked or fresh repo — both fine), set repo **public**.
2. Include:
   - 4 executed notebooks (`.ipynb` with output cells preserved)
   - `submission/screenshots/` — at least one screenshot per notebook
   - `submission/REFLECTION.md` (≤ 200 words: which mode wins on what queries
     and why? When would you not use hybrid?)
   - **Optional:** `bonus/` folder for the bonus challenge
3. Paste the public repo URL into the LMS submission box.
4. **Keep the repo public until grades are released.** Private = 0.

## Late policy / regrade

Standard Track-2 policy applies — see `INDEX-Track2.md`.
