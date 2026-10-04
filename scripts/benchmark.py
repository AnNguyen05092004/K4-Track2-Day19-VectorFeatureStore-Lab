"""Benchmark harness: keyword vs semantic vs hybrid on the 50-query golden set.

Reports two tables:
  1. Quality — Precision@10 (fraction of top-10 from the relevant topic) per mode.
  2. Latency — P50 / P95 / P99 over 100 reps of the 50 queries (5000 calls/mode).

Hybrid uses Reciprocal Rank Fusion (RRF, k=60) over the two ranked lists.

The rubric asserts hybrid strictly beats both pure modes on Precision@10 — the
corpus + queries (data/corpus_vn.jsonl + data/golden_set.jsonl) are engineered
to make this true. If hybrid does not win, your fusion implementation is wrong.

Run via `make benchmark` or `python scripts/benchmark.py`.
"""
from __future__ import annotations

import json
import statistics as stats
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.search import Searcher  # noqa: E402  -- depends on sys.path above

REPS_PER_QUERY = 100   # latency rep count per mode
TOP_K = 10
RRF_K = 60


def precision_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int = TOP_K) -> float:
    """Fraction of top-k retrieved that are in the relevant set."""
    top = retrieved_ids[:k]
    if not top:
        return 0.0
    return sum(1 for d in top if d in relevant_ids) / len(top)


def main() -> int:
    print("Day 19 benchmark — keyword vs semantic vs hybrid")
    print("=" * 62)

    # ── Load golden set ─────────────────────────────────────────────────
    golden = []
    with (ROOT / "data" / "golden_set.jsonl").open(encoding="utf-8") as f:
        for line in f:
            golden.append(json.loads(line))
    print(f"  Loaded {len(golden)} golden queries")

    # ── Build searcher ──────────────────────────────────────────────────
    print("  Building Searcher (this may take ~30s on first run — embedding the corpus)...")
    t0 = time.perf_counter()
    searcher = Searcher.from_corpus(ROOT / "data" / "corpus_vn.jsonl")
    print(f"  Indexed {searcher.size} docs in {time.perf_counter() - t0:.1f}s\n")

    # ── Quality run (1 pass over golden) ────────────────────────────────
    p_kw, p_sem, p_hyb = [], [], []
    for q in golden:
        relevant = set(q["relevant_doc_ids"])
        hits_kw = [h.doc_id for h in searcher.search(q["query"], mode="keyword", top_k=TOP_K)]
        hits_sem = [h.doc_id for h in searcher.search(q["query"], mode="semantic", top_k=TOP_K)]
        hits_hyb = [h.doc_id for h in searcher.search(q["query"], mode="hybrid", top_k=TOP_K, rrf_k=RRF_K)]
        p_kw.append(precision_at_k(hits_kw, relevant))
        p_sem.append(precision_at_k(hits_sem, relevant))
        p_hyb.append(precision_at_k(hits_hyb, relevant))

    avg_kw = stats.mean(p_kw)
    avg_sem = stats.mean(p_sem)
    avg_hyb = stats.mean(p_hyb)

    print("Quality — Precision@10 (% of top-10 in matching topic)")
    print(f"  Keyword (BM25)   : {avg_kw:6.1%}")
    print(f"  Semantic (vector): {avg_sem:6.1%}")
    print(f"  Hybrid  (RRF=60) : {avg_hyb:6.1%}   <- should win")
    print()

    # Slice by query type — does hybrid help paraphrase queries the most?
    by_mode: dict[str, dict[str, list[float]]] = {}
    for q, kw, sem, hyb in zip(golden, p_kw, p_sem, p_hyb):
        by_mode.setdefault(q["mode_hint"], {"kw": [], "sem": [], "hyb": []})
        by_mode[q["mode_hint"]]["kw"].append(kw)
        by_mode[q["mode_hint"]]["sem"].append(sem)
        by_mode[q["mode_hint"]]["hyb"].append(hyb)

    print("Quality by query type:")
    print(f"  {'type':12} {'n':>3}  {'kw':>7} {'sem':>7} {'hyb':>7}")
    for mode_hint in ("exact", "paraphrase", "mixed"):
        m = by_mode.get(mode_hint, {"kw": [], "sem": [], "hyb": []})
        if not m["kw"]:
            continue
        print(
            f"  {mode_hint:12} {len(m['kw']):>3}  "
            f"{stats.mean(m['kw']):>6.1%} {stats.mean(m['sem']):>6.1%} {stats.mean(m['hyb']):>6.1%}"
        )
    print()

    # ── Latency run (REPS reps × 50 queries) ────────────────────────────
    print(f"Latency — P50 / P95 / P99 over {REPS_PER_QUERY * len(golden)} calls/mode")
    for mode in ("keyword", "semantic", "hybrid"):
        latencies = []
        for _ in range(REPS_PER_QUERY):
            for q in golden:
                t = time.perf_counter()
                searcher.search(q["query"], mode=mode, top_k=TOP_K, rrf_k=RRF_K)
                latencies.append((time.perf_counter() - t) * 1000)
        latencies.sort()
        n = len(latencies)
        p50 = latencies[n // 2]
        p95 = latencies[int(n * 0.95)]
        p99 = latencies[int(n * 0.99)]
        print(f"  {mode:9}: P50={p50:6.1f}ms  P95={p95:6.1f}ms  P99={p99:6.1f}ms")
    print()

    # ── Rubric assertion ────────────────────────────────────────────────
    if avg_hyb > avg_kw and avg_hyb > avg_sem:
        delta_kw = (avg_hyb - avg_kw) * 100
        delta_sem = (avg_hyb - avg_sem) * 100
        print(f"PASS — hybrid beats keyword by {delta_kw:+.1f}pp, semantic by {delta_sem:+.1f}pp")
        return 0
    print(f"FAIL — hybrid did NOT beat both pure modes (kw={avg_kw:.1%} sem={avg_sem:.1%} hyb={avg_hyb:.1%})")
    print("       Check your RRF implementation: score(d) = sum_r 1/(k + rank_r(d)), k=60")
    return 1


if __name__ == "__main__":
    sys.exit(main())
