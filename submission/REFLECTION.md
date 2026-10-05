# Reflection — Lab 19

**Tên:** Nguyễn Văn An
**Cohort:** A20-K4
**Path đã chạy:** both (stack Docker Qdrant + Redis + Postgres đã dựng và `verify_docker.py` xanh; notebook chạy với embedding `bge-small-en-v1.5`)

---

## Câu hỏi (≤ 200 chữ)

> Trên golden set 50 queries, mode nào thắng ở loại query nào (`exact` /
> `paraphrase` / `mixed`), và tại sao? Khi nào bạn **không** dùng hybrid
> (i.e. khi nào pure BM25 hoặc pure vector là lựa chọn đúng)?

Precision@10 trung bình: hybrid 78,6% > keyword 77,8% > semantic 73,2%.

- `exact`: BM25 và hybrid cùng 96,7%, vector 88,7%. Từ khoá kỹ thuật xuất hiện nguyên văn nên BM25 đã đủ.
- `mixed`: hybrid thắng rõ, 100% so với 97,0% (BM25) và 98,5% (vector). Hai retriever sai ở những doc khác nhau, RRF ghép lại bù cho nhau.
- `paraphrase`: cả ba đều yếu (BM25 33,3%, hybrid 32,0%, vector 24,0%). `bge-small-en` train cho tiếng Anh nên không hiểu diễn đạt lại tiếng Việt, và RRF không cứu được khi cả hai nhánh cùng sai. Mình chưa đo `bge-m3` nên không khẳng định nó sửa được.

Hybrid thắng trung bình nhờ bền trên mọi kiểu query, không nhờ thắng từng slice.

Mình không dùng hybrid khi: (1) tra cứu mã/ID/tên riêng chính xác, BM25 đủ và rẻ hơn (P99 ~1 ms so với ~8 ms); (2) query thuần ngữ nghĩa hoặc đa ngôn ngữ, không trùng từ khoá, thì dùng vector với embedding tốt; nhánh BM25 chỉ thêm nhiễu.

---

## Điều ngạc nhiên nhất khi làm lab này

Ở NB5, post-filter (lấy top-K rồi lọc) chỉ còn recall 0,00 khi filter chọn 3,8% corpus, trong khi filtered-ANN giữ 1,00. Cách lọc sau trông vô hại nhưng hỏng âm thầm, không báo lỗi nào.

---

## Bonus challenge

- [x] Đã làm bonus (xem `bonus/ARCHITECTURE.md`, `bonus/agent.py`, `bonus/demo.py`)
- [ ] Pair work với: _không, làm cá nhân_
- Phạm vi dùng AI: code và bản nháp bonus soạn cùng Claude Code; số liệu đã đối chiếu với output thật.
