"""Generate the lab corpus + golden eval set deterministically.

Outputs:
  data/corpus_vn.jsonl       — 1000 Vietnamese tech docs across 10 topic clusters
  data/golden_set.jsonl      — 50 (query, relevant_doc_id, mode_hint) tuples

Determinism: all randomness uses a fixed seed (42). Any student running this
script gets identical files — required for the rubric thresholds to be checkable.

The corpus is engineered so that:
  - BM25 wins on queries using exact technical terms ("Kubernetes Pod lifecycle")
  - Vector wins on paraphrased queries ("cách quản lý vòng đời container")
  - Hybrid (RRF k=60) strictly beats both — that's what the rubric asserts.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
SEED = 42
random.seed(SEED)

# ── 10 topic clusters × 100 docs each = 1000 ──────────────────────────────
TOPICS: dict[str, dict] = {
    "cloud": {
        "vn_name": "Điện toán đám mây",
        "key_terms": ["cloud", "serverless", "AWS", "Azure", "GCP", "Lambda", "container",
                      "Kubernetes", "auto-scaling", "multi-tenant"],
        "vn_terms": ["đám mây", "không máy chủ", "tự động mở rộng", "đa người dùng",
                     "triển khai", "hạ tầng"],
        "concepts": [
            "tự động mở rộng theo lưu lượng",
            "tách biệt môi trường dev và prod",
            "tối ưu chi phí với spot instance",
            "quản lý vòng đời container",
            "cấu hình mạng VPC riêng biệt",
        ],
    },
    "ai_ml": {
        "vn_name": "Trí tuệ nhân tạo",
        "key_terms": ["LLM", "embedding", "transformer", "fine-tuning", "RAG",
                      "neural network", "GPU", "PyTorch", "BERT", "attention"],
        "vn_terms": ["mô hình ngôn ngữ", "học sâu", "mạng nơ-ron", "tinh chỉnh",
                     "huấn luyện", "suy luận"],
        "concepts": [
            "huấn luyện mô hình trên dataset lớn",
            "tinh chỉnh trên domain cụ thể",
            "tối ưu chi phí inference",
            "đánh giá chất lượng câu trả lời",
            "phát hiện hallucination",
        ],
    },
    "security": {
        "vn_name": "Bảo mật",
        "key_terms": ["encryption", "TLS", "SSL", "OAuth", "JWT", "zero-trust", "firewall",
                      "intrusion detection", "vulnerability", "penetration testing"],
        "vn_terms": ["mã hoá", "xác thực", "bảo vệ dữ liệu", "kiểm thử bảo mật",
                     "lỗ hổng", "tấn công"],
        "concepts": [
            "bảo vệ dữ liệu nhạy cảm khi lưu trữ",
            "xác thực hai yếu tố cho người dùng",
            "phát hiện truy cập bất thường",
            "mã hoá thông tin trên đường truyền",
            "kiểm thử xâm nhập định kỳ",
        ],
    },
    "database": {
        "vn_name": "Cơ sở dữ liệu",
        "key_terms": ["PostgreSQL", "MySQL", "MongoDB", "Redis", "ACID", "replication",
                      "sharding", "index", "query optimization", "transaction"],
        "vn_terms": ["cơ sở dữ liệu", "truy vấn", "giao dịch", "chỉ mục",
                     "sao chép", "phân mảnh"],
        "concepts": [
            "tối ưu truy vấn với chỉ mục B-tree",
            "đảm bảo tính nhất quán giữa nhiều bản sao",
            "phân mảnh dữ liệu để tăng throughput",
            "khôi phục dữ liệu sau sự cố",
            "thiết kế schema cho high-write workload",
        ],
    },
    "networking": {
        "vn_name": "Mạng máy tính",
        "key_terms": ["TCP", "UDP", "HTTP", "DNS", "load balancer", "CDN", "VPN",
                      "BGP", "latency", "throughput"],
        "vn_terms": ["giao thức", "định tuyến", "cân bằng tải", "băng thông",
                     "độ trễ", "tường lửa"],
        "concepts": [
            "cân bằng tải giữa nhiều region",
            "tối ưu độ trễ end-to-end",
            "định tuyến qua nhiều ISP để dự phòng",
            "phân tích traffic bất thường",
            "thiết kế CDN edge cho video streaming",
        ],
    },
    "devops": {
        "vn_name": "DevOps",
        "key_terms": ["CI/CD", "GitOps", "Terraform", "Ansible", "blue-green", "canary",
                      "rollback", "observability", "Prometheus", "Grafana"],
        "vn_terms": ["triển khai liên tục", "tự động hoá", "giám sát", "cảnh báo",
                     "khôi phục", "phiên bản"],
        "concepts": [
            "triển khai blue-green giảm rủi ro release",
            "rollback tự động khi error rate tăng",
            "infrastructure as code với Terraform",
            "giám sát metric và log tập trung",
            "tự động hoá pipeline test trước khi merge",
        ],
    },
    "mobile": {
        "vn_name": "Phát triển di động",
        "key_terms": ["iOS", "Android", "React Native", "Flutter", "Swift", "Kotlin",
                      "push notification", "offline-first", "deep link", "biometric"],
        "vn_terms": ["ứng dụng di động", "thông báo đẩy", "đăng nhập sinh trắc",
                     "đồng bộ ngoại tuyến", "deep link", "trải nghiệm người dùng"],
        "concepts": [
            "đồng bộ dữ liệu khi mất kết nối",
            "tối ưu kích thước APK / IPA",
            "tích hợp xác thực sinh trắc",
            "xử lý push notification ở background",
            "deep link mở chính xác màn hình trong app",
        ],
    },
    "frontend": {
        "vn_name": "Frontend",
        "key_terms": ["React", "Vue", "Angular", "Svelte", "TypeScript", "WebSocket",
                      "service worker", "PWA", "lazy loading", "tree shaking"],
        "vn_terms": ["giao diện", "tải lười", "đóng gói", "thành phần",
                     "trạng thái", "định tuyến"],
        "concepts": [
            "tối ưu LCP và FID cho Core Web Vitals",
            "tải lười component theo route",
            "quản lý state phức tạp với Redux Toolkit",
            "đóng gói bundle bằng tree shaking",
            "hỗ trợ ngoại tuyến qua service worker",
        ],
    },
    "backend": {
        "vn_name": "Backend",
        "key_terms": ["FastAPI", "gRPC", "REST", "GraphQL", "OpenAPI", "rate limiting",
                      "circuit breaker", "idempotency", "saga", "event sourcing"],
        "vn_terms": ["dịch vụ web", "giới hạn lưu lượng", "đồng nhất", "luồng nghiệp vụ",
                     "ngắt mạch", "xử lý sự kiện"],
        "concepts": [
            "thiết kế API idempotent cho retry an toàn",
            "circuit breaker tránh cascading failure",
            "rate limiting công bằng giữa các tenant",
            "saga pattern cho giao dịch phân tán",
            "versioning API mà không phá vỡ client cũ",
        ],
    },
    "data_eng": {
        "vn_name": "Data engineering",
        "key_terms": ["Spark", "Flink", "Kafka", "Airflow", "dbt", "Iceberg", "Delta Lake",
                      "lakehouse", "CDC", "schema evolution"],
        "vn_terms": ["luồng dữ liệu", "kho dữ liệu", "hồ dữ liệu", "chuyển đổi",
                     "phân vùng", "chất lượng dữ liệu"],
        "concepts": [
            "xử lý sự kiện streaming với Kafka và Flink",
            "schema evolution không phá vỡ downstream",
            "CDC từ OLTP sang lakehouse",
            "phân vùng theo ngày để tối ưu query",
            "đảm bảo chất lượng dữ liệu với kiểm thử",
        ],
    },
}


def make_doc(topic_id: str, idx: int, topic: dict) -> dict:
    """Build one doc with mixed VN prose + key technical terms."""
    concept = random.choice(topic["concepts"])
    terms = random.sample(topic["key_terms"], k=min(3, len(topic["key_terms"])))
    vn_terms = random.sample(topic["vn_terms"], k=min(2, len(topic["vn_terms"])))
    qualifier = random.choice([
        "Trong môi trường production hiện đại",
        "Khi triển khai ở quy mô lớn",
        "Tại các doanh nghiệp công nghệ Việt Nam",
        "Theo khuyến nghị 2026",
        "Để tối ưu chi phí",
    ])
    body = (
        f"{qualifier}, {topic['vn_name'].lower()} đòi hỏi phải {concept}. "
        f"Các công cụ phổ biến gồm {', '.join(terms)}. "
        f"Khái niệm {vn_terms[0]} và {vn_terms[1]} là nền tảng quan trọng. "
        f"Bài viết này giải thích cách {concept} một cách thực tế, "
        f"kèm ví dụ minh hoạ với {terms[0]} và {terms[-1]}."
    )
    return {
        "doc_id": f"{topic_id}_{idx:03d}",
        "topic": topic_id,
        "title": f"{topic['vn_name']}: {concept}",
        "text": body,
    }


# ── Golden set (50 queries) ───────────────────────────────────────────────
# Engineered so:
#   - "exact" queries use a key technical term verbatim → BM25 favored
#   - "paraphrase" queries use Vietnamese paraphrase of a concept → vector favored
#   - "mixed" queries combine both → hybrid strictly best

GOLDEN = [
    # Exact-term queries (BM25 favored)
    ("Kubernetes auto-scaling cho production", "cloud", "exact"),
    ("OAuth JWT zero-trust", "security", "exact"),
    ("PostgreSQL replication sharding", "database", "exact"),
    ("BGP load balancer multi-region", "networking", "exact"),
    ("Terraform GitOps blue-green canary", "devops", "exact"),
    ("React Native push notification offline-first", "mobile", "exact"),
    ("React Redux service worker PWA", "frontend", "exact"),
    ("FastAPI gRPC GraphQL OpenAPI", "backend", "exact"),
    ("Kafka Flink Iceberg Delta Lake CDC", "data_eng", "exact"),
    ("transformer fine-tuning RAG embedding", "ai_ml", "exact"),
    ("Lambda serverless container Kubernetes", "cloud", "exact"),
    ("TLS encryption penetration testing firewall", "security", "exact"),
    ("MongoDB Redis transaction ACID", "database", "exact"),
    ("DNS CDN VPN throughput latency", "networking", "exact"),
    ("Prometheus Grafana CI/CD rollback", "devops", "exact"),

    # Paraphrase queries (vector favored — vocabulary intentionally NOT in corpus templates)
    ("co giãn linh hoạt theo nhu cầu sử dụng", "cloud", "paraphrase"),
    ("che giấu nội dung quan trọng khỏi kẻ xấu", "security", "paraphrase"),
    ("tăng tốc tìm bản ghi bằng cấu trúc B-tree", "database", "paraphrase"),
    ("rút ngắn thời gian phản hồi giữa các nơi xa nhau", "networking", "paraphrase"),
    ("chạy kiểm thử trước khi gộp nhánh code", "devops", "paraphrase"),
    ("lưu offline cache khi không có sóng wifi", "mobile", "paraphrase"),
    ("tăng tốc render trang web cảm nhận mượt hơn", "frontend", "paraphrase"),
    ("dịch vụ vẫn chạy được khi 1 service phụ thuộc gãy", "backend", "paraphrase"),
    ("chuyển sự kiện realtime từ OLTP sang analytics", "data_eng", "paraphrase"),
    ("đo lường liệu trợ lý có bịa câu trả lời không", "ai_ml", "paraphrase"),
    ("nhiều khách hàng chia sẻ chung một cluster", "cloud", "paraphrase"),
    ("nhận dạng đăng nhập từ vị trí lạ", "security", "paraphrase"),
    ("partition dữ liệu theo user_id tăng write throughput", "database", "paraphrase"),
    ("phát hiện gói tin lạ chen vào", "networking", "paraphrase"),
    ("tự khôi phục bản cũ khi bản mới lỗi", "devops", "paraphrase"),

    # Mixed queries (hybrid favored — exact term + paraphrase together)
    ("Kubernetes và cách tách biệt môi trường", "cloud", "mixed"),
    ("OAuth và xác thực hai yếu tố", "security", "mixed"),
    ("PostgreSQL và đảm bảo tính nhất quán", "database", "mixed"),
    ("CDN edge cho streaming video độ trễ thấp", "networking", "mixed"),
    ("Terraform và infrastructure as code", "devops", "mixed"),
    ("Flutter offline-first và đồng bộ dữ liệu", "mobile", "mixed"),
    ("React và Core Web Vitals tối ưu LCP", "frontend", "mixed"),
    ("FastAPI và rate limiting công bằng", "backend", "mixed"),
    ("Spark và phân vùng theo ngày", "data_eng", "mixed"),
    ("LLM và phát hiện hallucination", "ai_ml", "mixed"),
    ("AWS Lambda và tối ưu chi phí", "cloud", "mixed"),
    ("encryption và bảo vệ dữ liệu nhạy cảm", "security", "mixed"),
    ("MongoDB và high-write workload", "database", "mixed"),
    ("HTTP và cân bằng tải multi-region", "networking", "mixed"),
    ("Prometheus và giám sát log tập trung", "devops", "mixed"),
    ("Swift biometric authentication", "mobile", "mixed"),
    ("TypeScript và quản lý state phức tạp", "frontend", "mixed"),
    ("gRPC và saga pattern phân tán", "backend", "mixed"),
    ("Kafka và schema evolution", "data_eng", "mixed"),
    ("BERT và tinh chỉnh trên domain", "ai_ml", "mixed"),
]


def main() -> None:
    docs: list[dict] = []
    for topic_id, topic in TOPICS.items():
        for i in range(100):
            docs.append(make_doc(topic_id, i, topic))
    random.shuffle(docs)

    corpus_path = DATA / "corpus_vn.jsonl"
    with corpus_path.open("w", encoding="utf-8") as f:
        for d in docs:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    print(f"  wrote {len(docs)} docs → {corpus_path}")

    # Pick relevant doc per golden query: any doc in the matching topic.
    by_topic: dict[str, list[str]] = {}
    for d in docs:
        by_topic.setdefault(d["topic"], []).append(d["doc_id"])

    golden_path = DATA / "golden_set.jsonl"
    with golden_path.open("w", encoding="utf-8") as f:
        for qi, (q, topic_id, mode) in enumerate(GOLDEN):
            relevant = by_topic[topic_id]
            f.write(json.dumps({
                "query_id": f"q_{qi:03d}",
                "query": q,
                "relevant_doc_ids": relevant,
                "mode_hint": mode,
                "topic": topic_id,
            }, ensure_ascii=False) + "\n")
    print(f"  wrote {len(GOLDEN)} queries → {golden_path}")
    print(f"  seed={SEED} (deterministic)")


if __name__ == "__main__":
    main()
