"""Demo 5 query cho HybridMemoryAgent (bonus Lab 19).

Vai trò file: chứng minh agent ghép đúng ngữ cảnh cho 5 kiểu câu hỏi khác nhau
trong đề — mỗi kiểu cần một nguồn khác nhau (vector / profile / hoạt động gần đây / ...).
Kết thúc bằng 1 kiểm tra cô lập user; vi phạm thì thoát mã ≠ 0.

Chạy từ thư mục gốc repo (cần đã `make seed` + chạy NB4 để Feast có dữ liệu):
    python bonus/demo.py

Dấu (keyword) / (vector) / (keyword+vector) trong mỗi ký ức cho biết retriever
nào đã tìm ra nó — đó chính là bằng chứng hybrid hoạt động.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bonus.agent import HybridMemoryAgent

# Ký ức "đã đọc" của u_001: tiếng Việt xen thuật ngữ tiếng Anh (code-switching).
NOTES_U001 = [
    "Hôm qua mình đọc bài về Kubernetes: HPA (Horizontal Pod Autoscaler) tự động tăng giảm "
    "số pod theo CPU. Cluster autoscaler thì thêm node khi pod bị pending. "
    "Cần đặt resource requests đúng thì autoscaling mới chạy chuẩn.",
    "Ghi chú về serverless: Cloud Run và Lambda co về 0 khi không có request, "
    "đổi lại bị cold start vài trăm mili giây.",
    "Đọc về bảo mật cloud: IAM theo nguyên tắc least privilege, bật MFA, "
    "mã hoá dữ liệu at rest bằng KMS và xoay vòng secret định kỳ.",
    "Tài liệu về bảo mật API: dùng OAuth2 với JWT ngắn hạn, kiểm tra scope ở mỗi endpoint, "
    "tránh lưu token trong localStorage.",
    "Ghi chú Postgres: tạo index B-tree cho cột hay lọc, dùng EXPLAIN ANALYZE để xem query plan.",
    "Hôm nay thử fine-tune một mô hình embedding nhỏ cho tiếng Việt, "
    "loss giảm nhưng recall@10 chưa cải thiện nhiều.",
]

# 5 query theo đúng thứ tự và ý đồ trong BONUS-CHALLENGE.md.
QUERIES = [
    ("1. Chỉ vector/keyword hit", "Tôi đã đọc gì về Kubernetes?"),
    ("2. Cần profile (topic_affinity)", "Recommend đọc gì tiếp"),
    ("3. Cần hoạt động gần đây (queries_last_hour)", "Tôi đang quan tâm gì gần đây?"),
    ("4. Paraphrase (vector thắng)", "Tài liệu về tự động mở rộng hạ tầng?"),
    ("5. Mixed (hybrid + profile)", "Cho tôi summary cloud security"),
]


def main() -> int:
    agent = HybridMemoryAgent()

    n = sum(agent.remember(t, user_id="u_001") for t in NOTES_U001)
    print(f"Đã nhớ {len(NOTES_U001)} ghi chú -> {n} chunk cho u_001\n")

    for title, query in QUERIES:
        print("=" * 78)
        print(f"{title}\n  Q: {query}")
        print("-" * 78)
        print(agent.recall(query, user_id="u_001"))
        print()

    # ── Kiểm tra cô lập: memory của u_002 tuyệt đối không được lọt sang u_001 ──
    secret = "Kế hoạch riêng của u_002: ra mắt sản phẩm Zephyr vào tháng 12."
    agent.remember(secret, user_id="u_002")
    leaked = agent.search("kế hoạch ra mắt sản phẩm Zephyr", user_id="u_001", top_k=10)
    own = agent.search("kế hoạch ra mắt sản phẩm Zephyr", user_id="u_002", top_k=1)
    print("=" * 78)
    print("Kiểm tra cô lập user")
    print(f"  u_002 tự tìm thấy ký ức của mình : {bool(own) and 'Zephyr' in own[0].memory.text}")
    print(f"  u_001 thấy ký ức của u_002        : {any('Zephyr' in h.memory.text for h in leaked)}")
    if any('Zephyr' in h.memory.text for h in leaked) or not own:
        print("LỖI: cô lập user bị vi phạm")
        return 1
    print("OK — mỗi user chỉ thấy memory của chính mình")
    return 0


if __name__ == "__main__":
    sys.exit(main())
