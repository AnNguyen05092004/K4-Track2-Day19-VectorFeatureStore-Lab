# Bonus — AI Memory cho trợ lý cá nhân tiếng Việt

**Tác giả:** Nguyễn Văn An (làm cá nhân). Code và bản nháp tài liệu được soạn cùng Claude Code (AI), xem mục *Nhật ký vibe-coding* ở cuối.
**Chạy thử:** `make bonus` hoặc `python bonus/demo.py` · **Test:** `pytest tests/test_bonus_agent.py` (10 test)

## 1. Sơ đồ kiến trúc

```
  GHI                                         ĐỌC  recall(query, user_id)
  ───                                         ───────────────────────────
  remember(text, user_id)                     ┌─► Feast online store ──► hồ sơ (TTL 30 ngày)
        │                                     │                       + hoạt động gần đây (TTL 1 giờ)
        ▼                                     │
  chunk theo câu (≤ 60 từ)                    ├─► BM25Plus (chỉ chunk của user_id, bỏ dấu, bỏ stopword) ─┐
        │                                     │                                                           ├─► RRF (k=60)
        ├─► embed ─► Qdrant                   └─► Vector search, filter user_id TRONG truy vấn ───────────┘     │
        │           payload: user_id               (filtered-ANN)                                            top-3 ký ức
        └─► vô hiệu BM25 của user (rebuild lười)                                                                 │
                                                                                                                 ▼
                                              ghép chuỗi ngữ cảnh: hồ sơ + hoạt động + ký ức ─► (LLM: ngoài phạm vi POC)
```

Hai kho tách biệt vì vòng đời khác nhau: **ký ức** (vector, thêm liên tục, tìm theo nghĩa) và **hồ sơ** (feature, đổi chậm, tra theo khoá `user_id`).

## 2. Ba quyết định kiến trúc

### Quyết định 1 — Chunking: gom theo câu, ≤ 60 từ
- **Chọn:** gom các câu liên tiếp đến ~60 từ (`chunk_text`). **Không chọn:** (a) cả cuộc hội thoại là 1 vector; (b) cắt cứng 512 token.
- **Đánh đổi:** (a) rẻ nhất về lưu trữ nhưng 1 vector trung bình hoá nhiều chủ đề nên truy vấn cụ thể ("tôi đọc gì về Kubernetes") không khớp rõ. (b) giữ được độ dài đều nhưng cắt ngang ý, và 512 token mỗi chunk làm top-3 tốn ngữ cảnh. Chọn ~60 từ: top-3 ≈ 180 từ, đủ gọn để nhét vào prompt, mỗi chunk vẫn trọn một ý.
- **Chi phí lưu trữ (tính tay):** bge-m3 1024 chiều × float32 = 4 KB/chunk → 10.000 chunk ≈ 41 MB cho một người dùng nhiều ghi chú; lượng tử hoá int8 giảm khoảng 4 lần. Chunk nhỏ hơn ⇒ nhiều vector hơn ⇒ tốn hơn; đây là cái giá đổi lấy độ chính xác khi tìm.

### Quyết định 2 — Feature schema: feature dạng bảng, không dùng embedding feature
- **Chọn:** 5 feature trên 2 view, cùng entity `user_id`: `preferred_language`, `topic_affinity`, `reading_speed_wpm` (view `user_profile_features`, TTL 30 ngày) và `queries_last_hour`, `distinct_topics_24h` (view `query_velocity_features`, TTL 1 giờ).
- **Không chọn:** vector "sở thích tiềm ẩn" tính từ lịch sử đọc.
- **Đánh đổi:** feature bảng giải thích được ("gợi ý cloud vì `topic_affinity=cloud`"), rẻ, và làm được point-in-time join khi cần huấn luyện (NB4/NB8). Vector sở thích bắt được tín hiệu tinh hơn nhưng mỗi ký ức mới làm nó đổi, nên thực chất là nhân bản kho ký ức. Khi cần, có thể tính trung bình các vector ký ức từ Qdrant.
- **Vì sao hai TTL khác nhau:** hồ sơ đổi theo tuần, còn số truy vấn trong giờ qua mất ý nghĩa sau ~1 giờ. TTL ngắn khiến giá trị cũ tự biến thành `None` thay vì trả số sai.

### Quyết định 3 — Độ tươi (freshness): chia theo 3 tình huống
| Tình huống | Chiến lược | Lý do |
|---|---|---|
| "Vừa lưu ghi chú, hỏi lại ngay" | **Dưới 1 giây**: `remember()` upsert thẳng vào Qdrant, không qua batch | Người dùng kỳ vọng nhớ tức thì; test `test_exact_term_found_by_keyword_branch` ghi rồi tìm ngay |
| "Dạo này mình hỏi nhiều không" | **~5 phút** (batch `materialize`), cần streaming Push nếu muốn phát hiện mệt mỏi theo thời gian thực | Chấp nhận trễ vài phút; TTL 1 giờ là lưới an toàn |
| "Chủ đề quan tâm" | **Hằng ngày** | Đổi chậm, tính lại tốn kém |

**Đã quan sát thật:** `queries_last_hour` được materialize lúc chạy NB4. Hơn 1 giờ sau, giá trị hết TTL và agent in *"Hoạt động gần đây: không có (feature hết hạn TTL 1 giờ)"* thay vì điền số cũ (`test_assemble_never_fills_expired_hot_feature`).

## 3. Phương án đã cân nhắc rồi loại
1. **Lưu ký ức như embedding feature view trong Feast.** Loại vì store online của Feast (SQLite/Redis) không có tìm kiếm ANN, và chu kỳ làm mới khác hẳn (ký ức mới theo giây, hồ sơ theo tuần).
2. **Mỗi user một collection Qdrant.** Cô lập mạnh hơn, nhưng hàng nghìn collection tốn chi phí quản trị. Chọn **một collection + filter `user_id`**; rủi ro là quên filter sẽ rò dữ liệu, nên `user_id` là tham số của mọi hàm tìm kiếm và có test cô lập (`test_user_isolation_in_search`, cộng kiểm tra cuối `demo.py`).

## 4. Bối cảnh tiếng Việt
- **Gõ không dấu:** `normalize_vi` bỏ dấu cho nhánh BM25 để "tu dong mo rong" khớp "tự động mở rộng". Cái giá thấy được: "hạ tầng" khớp nhầm "tăng" vì cùng thành `tang`, và "mô"/"mở" cùng thành `mo`. Nhánh vector (giữ nguyên chữ có dấu) bù lại.
- **Từ chức năng:** bản đầu không loại stopword nên BM25 khớp "về", "cho", "tôi" và kéo ghi chú Postgres lên hạng 2 khi hỏi "cloud security" (chỉ vì chữ "cho" trong "tạo index B-tree cho cột"). Đã thêm danh sách stopword nhỏ (sản xuất nên dùng danh sách của underthesea/pyvi).
- **Code-switching vi/en:** ghi chú trộn "Kubernetes", "least privilege" giữa câu tiếng Việt. BM25 khớp thuật ngữ tiếng Anh nguyên văn; việc hiểu "security" ≈ "bảo mật" phụ thuộc mô hình embedding.
- **Dữ liệu cá nhân:** ký ức riêng tư là dữ liệu cá nhân theo Nghị định 13/2023/NĐ-CP (đồng ý của chủ thể, quyền xoá). POC chưa có API xoá và mã hoá, xem mục 6.

## 5. Số đo thật (chưa phải benchmark)
Chọn embedding là biến quyết định. Cùng 6 ghi chú, 5 query, chỉ đổi `EMBEDDING_BACKEND` (output đầy đủ: `demo_output.txt`, `demo_output_bge-m3.txt`):

| Query | Ký ức đúng | bge-small-en (384d) | bge-m3 (1024d) |
|---|---|---|---|
| 1. "Tôi đã đọc gì về Kubernetes?" | ghi chú Kubernetes | hạng 1 | hạng 1 |
| 4. "Tài liệu về tự động mở rộng hạ tầng?" (paraphrase) | ghi chú Kubernetes | **không vào top-3** | **hạng 1** |
| 5. "Cho tôi summary cloud security" | ghi chú bảo mật cloud | hạng 2 | **hạng 1** |

Chẩn đoán query 4 với bge-small-en: BM25 xếp đúng ghi chú đứng đầu, còn vector xếp nó **cuối cùng** (6/6) vì mô hình train cho tiếng Anh. RRF lấy hai hạng trái chiều nên đẩy nó khỏi top-3 — đúng bài học NB2: hybrid không cứu được khi một nhánh sai nặng. Đổi sang bge-m3 sửa được, nhưng đòi tải ~4,3 GB và re-index.
**Giới hạn của phép đo:** 1 user, 6 ghi chú, 5 query, nên đây là ví dụ minh hoạ, không đủ để kết luận thống kê.

## 6. POC này chưa xử lý
- **Không bền vững:** Qdrant in-memory, tắt tiến trình là mất ký ức. Production dùng Qdrant server + volume.
- **Không có CRUD:** thiếu sửa/xoá ký ức, tức chưa đáp ứng quyền xoá dữ liệu. Xoá cần xoá khỏi Qdrant và rebuild BM25.
- **Không mã hoá at rest, không đồng bộ nhiều thiết bị, không xử lý đồng thời.**
- **BM25 rebuild toàn bộ** mỗi lần có ký ức mới: ổn với vài nghìn chunk, không ổn ở quy mô lớn.
- **Nhãn `(keyword+vector)` trong demo gần như vô nghĩa:** chỉ 6 ký ức nên vector top-20 luôn chứa tất cả. Nhãn chỉ có ý nghĩa khi corpus lớn.
- **Chỉ đọc online store:** nếu dùng hồ sơ để huấn luyện mô hình thì phải dùng point-in-time join (NB4/NB8), POC chưa làm.
- **Danh sách stopword nhỏ** và việc bỏ dấu gây nhầm lẫn như đã nêu ở mục 4.

## 7. Nhật ký vibe-coding
- **Prompt hiệu quả nhất:** thay vì sửa mù khi query paraphrase sai, yêu cầu in riêng hạng của BM25 và của vector cho từng ghi chú. Từ đó thấy ngay lỗi nằm ở embedding chứ không ở RRF hay code.
- **Thất bại:** bản đầu bỏ qua stopword và kỳ vọng "vector thắng paraphrase" dù dùng mô hình tiếng Anh. Demo chạy xanh (exit 0) nhưng kết quả sai, nên phải đọc output chứ không chỉ nhìn mã thoát.
