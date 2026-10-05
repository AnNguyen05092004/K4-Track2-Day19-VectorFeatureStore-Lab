"""HybridMemoryAgent — bonus POC: episodic memory (vector store) + stable profile (Feast).

Vai trò file: "bộ não trí nhớ" tối thiểu của trợ lý cá nhân tiếng Việt.
  * remember(text)  -> chunk -> embed -> upsert vào Qdrant (gắn user_id)
  * recall(query)   -> (1) đọc profile + hoạt động gần đây từ Feast online store
                       (2) hybrid search (BM25 + vector + RRF) CHỈ trong memory của user đó
                       (3) ghép thành 1 chuỗi ngữ cảnh — KHÔNG gọi LLM thật

Mỗi mảnh ghép lại từ một phần của lab:
  NB2 -> hybrid search + RRF (rank 1-based, k=60)
  NB4 -> Feast get_online_features
  NB5 -> filter theo payload (ở đây là user_id) nằm TRONG bước tìm vector, không lọc sau

Chạy thử: `python bonus/demo.py` (từ thư mục gốc repo).
"""
from __future__ import annotations

import re
import sys
import time
import unicodedata
import warnings
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))          # để `from app.embeddings import ...` chạy được khi gọi từ script

from qdrant_client import QdrantClient
from qdrant_client.models import (Distance, FieldCondition, Filter, MatchValue,
                                  PayloadSchemaType, PointStruct, VectorParams)
# BM25Plus thay vì BM25Okapi: idf của Okapi có thể ÂM khi corpus nhỏ (từ xuất hiện
# trong > nửa số doc). Memory của 1 user chỉ vài chục doc nên rất dễ dính lỗi này.
from rank_bm25 import BM25Plus

from app.embeddings import Embedder

COLLECTION = "bonus_memory"
RRF_K = 60                      # mặc định công nghiệp, giống NB2
SEARCH_DEPTH = 20               # lấy sâu mỗi retriever rồi mới gộp RRF
FEAST_REPO = ROOT / "app" / "feast_repo"

# Feature cần cho ngữ cảnh: 3 cái ổn định (TTL 30 ngày) + 2 cái "nóng" (TTL 1 giờ).
PROFILE_FEATURES = [
    "user_profile_features:preferred_language",
    "user_profile_features:topic_affinity",
    "user_profile_features:reading_speed_wpm",
    "query_velocity_features:queries_last_hour",
    "query_velocity_features:distinct_topics_24h",
]


# ── Tiền xử lý tiếng Việt ───────────────────────────────────────────────
# Từ chức năng tiếng Việt (đã bỏ dấu) — danh sách NHỎ, mang tính minh hoạ. Không có nó,
# BM25 khớp "về", "cho", "tôi"... và kéo ký ức không liên quan lên top (đã thấy trong
# demo). Production nên dùng danh sách đầy đủ của underthesea/pyvi. Cố ý KHÔNG đưa
# "tu" vào đây: "tự" và "từ" đều thành "tu" mà "tự động" là từ khoá có nghĩa.
VI_STOPWORDS = frozenset({
    "ve", "va", "cua", "la", "co", "cho", "toi", "minh", "gi", "de", "trong", "khi",
    "thi", "duoc", "nay", "mot", "cac", "nhung", "voi", "o", "bi", "se", "da", "dang",
    "khong", "nhu",
})


def normalize_vi(text: str) -> list[str]:
    """Token cho BM25: chữ thường, BỎ DẤU, tách theo ký tự chữ/số, bỏ stopword.

    Vì sao bỏ dấu: người dùng VN hay gõ không dấu ("tu dong mo rong") hoặc gõ sai
    dấu. Nếu BM25 so khớp theo đúng dấu thì query không dấu sẽ không khớp gì cả.
    Đổi lại ta mất phân biệt "ma" / "má" / "mà" — chấp nhận, vì nhánh vector
    (giữ nguyên text gốc) vẫn phân biệt được theo ngữ cảnh.
    """
    text = text.lower().replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return [t for t in re.findall(r"\w+", text) if t not in VI_STOPWORDS]


def chunk_text(text: str, max_words: int = 60) -> list[str]:
    """Cắt theo CÂU, gom các câu liên tiếp cho đến khi chạm max_words.

    Chọn theo câu (không cắt cứng theo số ký tự) để 1 chunk giữ trọn 1 ý; chọn
    ~60 từ để 1 chunk đủ ngữ cảnh cho embedding nhưng ngắn để recall trả về gọn.
    Câu dài hơn max_words thì bị cắt cứng theo từ.
    """
    sentences = [s.strip() for s in re.split(r"(?<=[.!?…])\s+|\n+", text) if s.strip()]
    chunks: list[str] = []
    current: list[str] = []
    count = 0
    for sent in sentences:
        words = sent.split()
        if len(words) > max_words:                       # câu quá dài: cắt cứng
            if current:
                chunks.append(" ".join(current))
                current, count = [], 0
            for i in range(0, len(words), max_words):
                chunks.append(" ".join(words[i:i + max_words]))
            continue
        if count + len(words) > max_words and current:   # chunk đầy: đóng lại
            chunks.append(" ".join(current))
            current, count = [], 0
        current.append(sent)
        count += len(words)
    if current:
        chunks.append(" ".join(current))
    return chunks


@dataclass
class Memory:
    chunk_id: int
    user_id: str
    text: str
    created_at: float


@dataclass
class Recalled:
    memory: Memory
    score: float                 # điểm RRF (chỉ để xếp hạng, không phải xác suất)
    via: tuple[str, ...]         # retriever nào tìm ra: ("keyword",) / ("vector",) / cả hai


# ── Agent ───────────────────────────────────────────────────────────────
class HybridMemoryAgent:
    def __init__(self, feast_repo: Path = FEAST_REPO, embedder: Embedder | None = None,
                 client: QdrantClient | None = None) -> None:
        self.embedder = embedder or Embedder()
        # POC: Qdrant in-memory. Production: QdrantClient(url=...) — cùng API.
        self.client = client or QdrantClient(":memory:")
        self.client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=self.embedder.dim, distance=Distance.COSINE),
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")      # local mode cảnh báo index payload là no-op
            self.client.create_payload_index(COLLECTION, "user_id", PayloadSchemaType.KEYWORD)

        self.feast_repo = Path(feast_repo)
        self._store = None                        # Feast load lazy: không có Feast vẫn remember() được
        self._memories: dict[str, list[Memory]] = {}   # user_id -> các chunk (để BM25 + trả text)
        self._bm25: dict[str, BM25Plus | None] = {}    # user_id -> index, dùng lại đến khi có memory mới
        self._next_id = 0

    # ── ghi nhớ ────────────────────────────────────────────────────────
    def remember(self, text: str, user_id: str = "u_001") -> int:
        """Thêm 1 đoạn ký ức vào memory của `user_id`. Trả về số chunk đã lưu."""
        chunks = chunk_text(text)
        if not chunks:
            return 0
        vectors = list(self.embedder.embed(chunks))
        points: list[PointStruct] = []
        now = time.time()
        for chunk, vec in zip(chunks, vectors):
            mem = Memory(self._next_id, user_id, chunk, now)
            self._memories.setdefault(user_id, []).append(mem)
            points.append(PointStruct(
                id=mem.chunk_id,
                vector=vec.tolist(),
                payload={"user_id": user_id, "chunk_id": mem.chunk_id, "created_at": now},
            ))
            self._next_id += 1
        self.client.upsert(collection_name=COLLECTION, points=points)
        self._bm25[user_id] = None                # buộc rebuild BM25 ở lần recall kế tiếp
        return len(chunks)

    # ── tìm lại ────────────────────────────────────────────────────────
    def search(self, query: str, user_id: str = "u_001", top_k: int = 3) -> list[Recalled]:
        """Hybrid (BM25 + vector + RRF), mỗi retriever đều bị giới hạn trong user_id."""
        mems = self._memories.get(user_id, [])
        if not mems:
            return []
        by_id = {m.chunk_id: m for m in mems}
        ranks: dict[str, list[int]] = {"keyword": [], "vector": []}

        # (1) BM25 trên memory của user. Chỉ nhận doc có điểm > 0 (có khớp từ thật).
        bm25 = self._bm25.get(user_id)
        if bm25 is None:
            bm25 = BM25Plus([normalize_vi(m.text) for m in mems])
            self._bm25[user_id] = bm25
        scores = bm25.get_scores(normalize_vi(query))
        order = sorted(range(len(mems)), key=lambda i: -scores[i])[:SEARCH_DEPTH]
        ranks["keyword"] = [mems[i].chunk_id for i in order if scores[i] > 0]

        # (2) Vector: filter user_id nằm TRONG truy vấn Qdrant (filtered-ANN, NB5).
        qvec = next(self.embedder.embed([query])).tolist()
        res = self.client.query_points(
            collection_name=COLLECTION,
            query=qvec,
            query_filter=Filter(must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]),
            limit=SEARCH_DEPTH,
        )
        ranks["vector"] = [p.payload["chunk_id"] for p in res.points]

        # (3) RRF: score(d) = sum 1/(k + rank), rank bắt đầu từ 1 (như NB2).
        fused: dict[int, float] = {}
        via: dict[int, list[str]] = {}
        for name, ids in ranks.items():
            for rank, cid in enumerate(ids, start=1):
                fused[cid] = fused.get(cid, 0.0) + 1.0 / (RRF_K + rank)
                via.setdefault(cid, []).append(name)
        top = sorted(fused.items(), key=lambda kv: -kv[1])[:top_k]
        return [Recalled(by_id[cid], score, tuple(via[cid])) for cid, score in top]

    def recall(self, query: str, user_id: str = "u_001", top_k: int = 3) -> str:
        """Ghép ngữ cảnh: profile + hoạt động gần đây + top-k ký ức."""
        profile = self._get_profile(user_id)
        hits = self.search(query, user_id, top_k)
        return self._assemble(profile, hits)

    # ── Feast ──────────────────────────────────────────────────────────
    def _get_profile(self, user_id: str) -> dict:
        """Đọc feature từ online store. Lỗi (chưa apply, store chết) -> {"_error": ...}.

        Cố ý KHÔNG ném lỗi: recall() vẫn phải trả ngữ cảnh từ memory khi Feast
        không sẵn sàng — nhưng lỗi phải hiện ra trong chuỗi, không được im lặng.
        """
        try:
            if self._store is None:
                from feast import FeatureStore
                self._store = FeatureStore(repo_path=str(self.feast_repo))
            row = self._store.get_online_features(
                features=PROFILE_FEATURES, entity_rows=[{"user_id": user_id}],
            ).to_dict()
        except Exception as exc:                          # noqa: BLE001 — báo cáo, không nuốt
            return {"_error": f"{type(exc).__name__}: {exc}"}
        return {name: vals[0] for name, vals in row.items() if name != "user_id"}

    @staticmethod
    def _assemble(profile: dict, hits: list[Recalled]) -> str:
        parts: list[str] = []

        if "_error" in profile:
            parts.append(f"Hồ sơ: không đọc được từ Feast ({profile['_error'][:80]}).")
        else:
            lang, topic, wpm = (profile.get("preferred_language"),
                                profile.get("topic_affinity"),
                                profile.get("reading_speed_wpm"))
            if topic is None:      # feature ổn định biến mất = user chưa có profile / hết TTL 30 ngày
                parts.append("Hồ sơ: chưa có dữ liệu cho user này.")
            else:
                parts.append(f"Hồ sơ: ngôn ngữ ưu tiên={lang}; chủ đề quan tâm={topic}; "
                             f"tốc độ đọc={wpm} wpm.")
            q1h, topics = profile.get("queries_last_hour"), profile.get("distinct_topics_24h")
            if q1h is None:        # feature "nóng" có TTL 1 giờ: hết hạn => None, tuyệt đối không điền số cũ
                parts.append("Hoạt động gần đây: không có (feature hết hạn TTL 1 giờ — "
                             "cần materialize lại).")
            else:
                parts.append(f"Hoạt động gần đây: {q1h} truy vấn trong 1 giờ qua; "
                             f"{topics} chủ đề khác nhau trong 24 giờ.")

        if hits:
            lines = []
            for i, h in enumerate(hits, 1):
                text = h.memory.text if len(h.memory.text) <= 200 else h.memory.text[:197] + "..."
                lines.append(f"  [{i}] ({'+'.join(h.via)}) {text}")
            parts.append("Ký ức liên quan:\n" + "\n".join(lines))
        else:
            parts.append("Ký ức liên quan: (chưa có ký ức nào của user này)")
        return "\n".join(parts)
