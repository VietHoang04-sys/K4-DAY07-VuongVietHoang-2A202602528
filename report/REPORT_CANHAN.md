# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Vương Việt Hoàng
**Nhóm:** 4Bot
**Ngày:** 20/09/2026

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Hai vector embedding có hướng gần nhau, cho thấy hai văn bản có nội dung hoặc ngữ nghĩa tương đồng. Giá trị càng gần 1 thì mức tương đồng càng cao.

**Ví dụ có độ tương tự CAO:**
- Câu A: "Khách hàng muốn hoàn tiền cần gửi yêu cầu trong vòng 30 ngày."
- Câu B: "Người mua có thể yêu cầu hoàn tiền trong thời hạn 30 ngày."
- Tại sao tương đồng: Hai câu cùng nói về yêu cầu hoàn tiền và cùng điều kiện thời hạn 30 ngày.

**Ví dụ có độ tương tự THẤP:**
- Câu A: "Chính sách hoàn tiền áp dụng cho người mua."
- Câu B: "Máy chủ cần được sao lưu trước khi cập nhật."
- Tại sao khác: Hai câu thuộc hai chủ đề khác nhau: chính sách thương mại và vận hành hệ thống.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Cosine tập trung vào hướng của vector, tức là quan tâm đến quan hệ ngữ nghĩa thay vì độ lớn tuyệt đối. Điều này phù hợp với text embedding vì các vector có thể có độ lớn khác nhau nhưng vẫn biểu diễn nội dung tương tự.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> Trình bày phép tính: `ceil((10.000 - 50) / (500 - 50)) = ceil(9.950 / 450) = ceil(22,11) = 23`.
> Đáp án: **23 chunks**.

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> Khi overlap tăng lên 100, số chunk là `ceil((10.000 - 100) / (500 - 100)) = ceil(24,75) = 25`. Overlap lớn giúp giữ lại ngữ cảnh ở ranh giới giữa hai chunk, nhưng làm tăng số chunk và chi phí embedding.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Tôi dùng regex `(?<=[.!?])(?:[ \t]+|\n+)` để tách sau dấu kết thúc câu, nhờ đó vẫn giữ lại dấu câu trong từng sentence. Các câu được gom theo `max_sentences_per_chunk`, loại bỏ khoảng trắng thừa và trả về `[]` khi input rỗng. Edge case còn hạn chế là chữ viết tắt như `TS.` hoặc `v.v.` và số thập phân có thể bị nhận diện nhầm là ranh giới câu.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> Thuật toán thử các separator theo thứ tự `\n\n`, `\n`, `. `, khoảng trắng và cuối cùng là cắt cứng. Nếu phần tách vẫn dài hơn `chunk_size`, hàm đệ quy chuyển sang separator nhỏ hơn; các phần nhỏ liền kề được gom lại để tránh tạo quá nhiều chunk vụn. Base case là text rỗng, text đã ngắn đủ, hoặc danh sách separator đã hết thì cắt trực tiếp theo kích thước.

**`HeadingChunker` — chiến lược tôi thực hiện:**
> HeadingChunker nhận diện Markdown ATX heading từ `#` đến `######`, tạo một section từ heading hiện tại đến trước heading kế tiếp. Section ngắn được giữ nguyên; section dài được tách recursive theo phần nội dung còn lại sau khi dành chỗ cho heading. Heading được gắn lại vào mọi chunk con để các đoạn sau vẫn giữ được ngữ cảnh về điều khoản/mục đang nói đến.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> EmbeddingStore dùng in-memory records, mỗi record gồm `id`, `content`, bản sao `metadata` và embedding. Khi search, query được embed rồi tính dot product với từng embedding; vì mock/local embedding được chuẩn hóa nên dot product tương ứng với cosine similarity. Kết quả được sắp xếp giảm dần theo score và giới hạn ở `top_k`.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> `search_with_filter` lọc metadata trước rồi mới chạy similarity search trên tập ứng viên, tránh việc các kết quả không phù hợp chiếm hết top-k. `delete_document` loại mọi record có `metadata["doc_id"]` bằng ID tài liệu gốc và trả về `True` nếu có record bị xóa.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> Agent lấy top-k kết quả từ EmbeddingStore, đánh số từng chunk `[1]`, `[2]`, ... và kèm source/doc ID trước khi đưa vào prompt. Prompt yêu cầu LLM chỉ dùng context, nói rõ khi không tìm thấy câu trả lời và trích dẫn số chunk liên quan. Nếu store rỗng, agent trả thông báo trực tiếp và không gọi LLM.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```text
============================= test session starts =============================
collected 42 items

42 passed in 0.10s
============================== 42 passed ======================================
```

**Số lượng bài test vượt qua (pass):** **42 / 42**

Các nhóm test đều đạt: project structure, chunking, similarity, comparator,
EmbeddingStore, metadata filtering, document deletion và KnowledgeBaseAgent.

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | "Hoàn tiền trong 30 ngày" | "Yêu cầu hoàn tiền trong thời hạn 30 ngày" | cao | Cần chạy benchmark | Chưa xác định |
| 2 | "Chính sách cho người mua" | "Sao lưu máy chủ trước cập nhật" | thấp | Cần chạy benchmark | Chưa xác định |
| 3 | "Tìm kiếm vector bằng embedding" | "Tra cứu tài liệu bằng vector biểu diễn" | cao | Cần chạy benchmark | Chưa xác định |
| 4 | "Đổi trả sản phẩm lỗi" | "Cách tính phí vận chuyển" | thấp | Cần chạy benchmark | Chưa xác định |
| 5 | "Heading là tiêu đề của section" | "Section được chia theo tiêu đề Markdown" | cao | Cần chạy benchmark | Chưa xác định |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> Các cặp có cùng chủ đề hoặc diễn đạt lại cùng một ý được dự đoán có similarity cao. Với MockEmbedder, điểm thực tế chỉ mang tính kiểm thử cấu trúc vì vector được sinh xác định từ MD5, không phản ánh đầy đủ ngữ nghĩa tiếng Việt. Vì vậy cần chạy thêm bằng embedding model có ngữ nghĩa nếu muốn đánh giá retrieval thực tế.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

Do chưa có log benchmark chung của nhóm, bảng dưới đây là **đánh giá kỹ thuật dự kiến**
dựa trên đặc tính của Heading & Section chunking. Score được ghi theo mức định tính
thay vì bịa ra điểm số từ `MockEmbedder` (vốn chỉ sinh vector giả lập, không phản ánh
đầy đủ ngữ nghĩa).

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Điều kiện để được hoàn tiền là gì? | Section chứa heading về điều kiện hoàn tiền và toàn bộ các điều khoản liên quan | Cao | Có; section giữ trọn ngữ cảnh và dễ truy vết | Trả lời được điều kiện, kèm nguồn section |
| 2 | Quy trình gửi yêu cầu đổi trả gồm những bước nào? | Section quy định quy trình, thường chứa các bước theo đúng thứ tự | Cao | Có; ranh giới section phù hợp với câu hỏi quy trình | Liệt kê các bước từ chunk liên quan |
| 3 | Chính sách áp dụng cho người mua hay người bán? | Section có metadata/source hoặc heading xác định đối tượng áp dụng | Khá cao | Có nếu metadata được lọc đúng; nếu không có thể lẫn tài liệu | Trả lời theo đúng audience và trích dẫn chunk |
| 4 | Thời hạn xử lý yêu cầu là bao lâu? | Section về thời hạn xử lý; thông tin thường nằm trong cùng một mục | Khá cao | Có; heading giúp phân biệt thời hạn xử lý với điều kiện yêu cầu | Nêu thời hạn, không trộn với section khác |
| 5 | Một section dài hơn `chunk_size` được xử lý thế nào? | Các chunk con cùng lặp lại heading của section dài | Cao | Có; heading được giữ lại trong mọi chunk con | Giải thích recursive fallback và việc giữ heading |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** **Dự kiến 5 / 5**
với tài liệu có heading rõ ràng và metadata được gán đúng. Đây là dự đoán kỹ thuật,
cần xác nhận lại bằng 5 query chính thức của nhóm.

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> Qua phần triển khai Heading & Section chunking, tôi nhận thấy ranh giới do người biên soạn tạo ra thường có ý nghĩa tốt hơn ranh giới cắt theo số ký tự. Việc giữ lại heading trong mọi chunk con đặc biệt quan trọng vì giúp retrieval và LLM biết chunk đang thuộc điều khoản nào. Tuy nhiên section quá dài vẫn cần recursive fallback để tránh vượt giới hạn embedding. Điểm yếu là các query hỏi xuyên nhiều section hoặc tài liệu không có heading rõ ràng có thể cần RecursiveChunker hoặc overlap để bổ sung ngữ cảnh.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 4 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 8 / 10 (đánh giá kỹ thuật dự kiến) |
| **Tổng phần cá nhân** | **57 / 60 (chờ xác nhận bằng benchmark thực tế)** |
