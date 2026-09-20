# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** Four bot\
**Thành viên:**
- Nguyễn Quang Hữu (FixedSizeChunker)
- Nguyễn Nhật Thăng (SentenceChunker)
- Nguyễn Minh Quyền (RecursiveChunker)
- Vương Việt Hoàng (Heading/Section-based Chunking)\
**Ngày:** 20/9/2026

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Chính sách thương mại điện tử

**Tại sao nhóm chọn chủ đề này?**
> Bộ dữ liệu về chủ đề này có sự phân hóa đối tượng sâu sắc giữa Người Mua (`buyer`) và Người Bán (`seller`), đồng thời có cấu trúc phân tầng theo điều khoản, số ngày, mốc thời gian và yêu cầu kỹ thuật cụ thể. Đây là ngữ liệu hoàn hảo để kiểm nghiệm khả năng chia nhỏ văn bản (chunking) và chứng minh sức mạnh của bộ lọc siêu dữ liệu (metadata filtering) trong hệ thống RAG thực tế.

### Danh sách tài liệu (Data Inventory)

| # | Tên tài liệu | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
|---|--------------|------------|--------------------|----------|-----------------|
| 1 | CHÍNH SÁCH TRẢ HÀNG VÀ HOÀN TIỀN | https://help.shopee.vn/portal/4/article/77251 | 2026-09-20 / not-stated | 19,637 | audience=both, category=returns-policy, language=vi |
| 2 | [Trả hàng/Hoàn tiền] Những quy định chung về Trả hàng/Hoàn tiền của Shopee | https://help.shopee.vn/portal/4/article/188931 | 2026-09-20 / not-stated | 6,378 | audience=buyer, category=returns-policy, language=vi |
| 3 | [Trả hàng/ Hoàn tiền] Hướng dẫn gửi yêu cầu Trả hàng/ Hoàn tiền | https://help.shopee.vn/portal/4/article/79233 | 2026-09-20 / not-stated | 2,570 | audience=buyer, category=returns-process, language=vi |
| 4 | [Trả hàng/Hoàn tiền] Hướng dẫn chuẩn bị bằng chứng khi yêu cầu Trả hàng/ Hoàn tiền | https://help.shopee.vn/portal/4/article/79467 | 2026-09-20 / not-stated | 3,519 | audience=buyer, category=returns-process, language=vi |
| 5 | [Trả hàng/ Hoàn tiền] Các phương thức gửi hàng hoàn trả và phí hoàn trả | https://help.shopee.vn/portal/4/article/189477 | 2026-09-20 / not-stated | 5,980 | audience=buyer, category=shipping-fee, language=vi |
| 6 | QUY CHẾ HOẠT ĐỘNG SÀN THƯƠNG MẠI ĐIỆN TỬ SHOPEE.VN | https://help.shopee.vn/portal/4/article/77245 | 2026-09-20 / not-stated | 77,900 | audience=both, category=platform-regulation, language=vi |
| 7 | QUY ĐỊNH VỀ ĐĂNG BÁN SẢN PHẨM TRÊN SHOPEE | https://help.shopee.vn/portal/4/article/77246 | 2026-09-20 / not-stated | 21,560 | audience=seller, category=seller-policy, language=vi |
| 8 | CHÍNH SÁCH CẤM/HẠN CHẾ SẢN PHẨM | https://help.shopee.vn/portal/4/article/77247 | 2026-09-20 / not-stated | 12,878 | audience=seller, category=product-restriction, language=vi |

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] Tập tài liệu (Corpus) chỉ chứa nguồn công khai/được phép dùng từ Trung tâm hỗ trợ Shopee Việt Nam (`help.shopee.vn`), không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [x] Mỗi tài liệu có đầy đủ `doc_id`, `title`, `source_url`, `retrieved_at`, `document_version`, `audience` trong metadata. File `sources.csv` khớp một-một với các file `.md`.

### Cấu trúc Metadata (Metadata Schema)

**Nguồn của nhãn:** audience/category/language được nhóm bổ sung dựa trên đối tượng và chủ đề tài liệu. Bản crawl gốc chỉ có 5 trường nguồn; các nhãn bổ sung không thay đổi nội dung chính sách. Lab yêu cầu audience và ít nhất một trường hữu ích khác, không bắt buộc đồng thời cả category và language.

Ba nơi lưu thông tin có vai trò khác nhau:

- `data/urls.csv`: đầu vào crawler, hiện gồm **8 nguồn của nhóm**; các cột `url,doc_id,title,audience,category,language,document_version,license_or_permission`.
- `data/Chinh_sach_thuong_mai_dien_tu/sources.csv`: kiểm kê **8 file đã thu thập**, đúng schema của `docs/DATA_COLLECTION.md`: `doc_id,file_path,title,source_url,retrieved_at,document_version,license_or_permission`. `file_path` tính từ gốc repo và phải tồn tại. Không yêu cầu manifest có cùng header với CSV đầu vào.
- Frontmatter từng `.md`: metadata tài liệu dùng khi ingest. Crawler ánh xạ `url` thành `source_url`, thêm `retrieved_at`; `audience/category/language` nằm trong frontmatter. `license_or_permission` được giữ trong CSV để ghi căn cứ sử dụng, không mặc định là trường lọc.

document_version ghi nhận phiên bản chính sách từ nguồn phát hành. Đối với các tài liệu hướng dẫn trực tuyến dạng bài viết hỗ trợ cập nhật động trên sàn Shopee, trường này được gán nhãn chuẩn hóa "not-stated" (hoặc ghi nhận theo phiên bản công bố trực tuyến). `retrieved_at` là ngày thu thập dữ liệu. Số ký tự trong bảng được tính trên phần thân Markdown, gồm tiêu đề, sau `strip()`, không gồm YAML frontmatter.

Khi ingest, mọi chunk kế thừa metadata nguồn; `Document.id=<doc_id>#<index>`, `metadata.doc_id` vẫn là ID file gốc và `chunk_index` là số thứ tự từ 0. Filter `audience=buyer` chỉ khớp `buyer`, không bao gồm `both`.


| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất (retrieval)? |
|----------------|------|---------------|-------------------------------|
| `doc_id` | string | `79233` | Định danh duy nhất cho tài liệu, phục vụ việc quản lý, liên kết chunk và xóa tài liệu (`delete_document`). |
| `title` | string | `[Trả hàng/ Hoàn tiền] Hướng dẫn gửi yêu cầu Trả hàng/ Hoàn tiền` | Hiển thị tiêu đề chuẩn cho người dùng và hỗ trợ kiểm tra ngữ cảnh nguồn. |
| `source_url` | string | `https://help.shopee.vn/portal/4/article/79233` | Minh bạch nguồn gốc, cho phép Agent trích dẫn URL chính thức (Source Traceability). |
| `retrieved_at` | string (date) | `2026-09-20` | Kiểm soát ngày thu thập, đánh giá độ mới của chính sách sàn TMĐT. |
| `document_version` | string | `not-stated` | Phiên bản chính sách theo văn bản gốc; chuẩn hóa "not-stated" đối với bài viết hỗ trợ trực tuyến cập nhật thường xuyên. |
| `audience` | string | `buyer`, `seller`, `both` | Phân biệt đối tượng áp dụng. Đây là trường quyết định để lọc metadata tránh nhầm lẫn giữa quy định cho Người Mua và Người Bán. |
| `category` | string | `returns-process`, `shipping-fee`, `seller-policy` | Phân loại mảng chính sách, giúp thu hẹp không gian tìm kiếm khi người dùng hỏi về chủ đề chuyên biệt. |
| `language` | string | `vi` | Phục vụ lọc theo ngôn ngữ tiếng Việt. |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

### Phân tích đường cơ sở (Baseline Analysis)

Chạy `ChunkingStrategyComparator().compare(body, chunk_size=300)` trên phần thân đã bỏ frontmatter: FixedSize overlap=30, Sentence tối đa 3 câu/chunk, Recursive size=300. Đây là baseline riêng, khác cấu hình cá nhân 500/50. Số liệu sau được chạy lại trên bản crawl mới (chỉ bổ sung nhãn frontmatter, giữ nguyên phần thân); xem log benchmark.

| Tài liệu | Chiến lược | Số chunk | Độ dài trung bình |
|---|---|---|---|
| `188931` | `fixed_size` | 24 | 294.5 |
| `188931` | `by_sentences` | 10 | 632.8 |
| `188931` | `recursive` | 27 | 234.3 |
| `79233` | `fixed_size` | 10 | 284.0 |
| `79233` | `by_sentences` | 8 | 317.8 |
| `79233` | `recursive` | 10 | 255.2 |
| `79467` | `fixed_size` | 13 | 298.4 |
| `79467` | `by_sentences` | 12 | 290.2 |
| `79467` | `recursive` | 15 | 232.7 |

### Chiến lược của từng thành viên

**Thành viên 1 — Nguyễn Quang Hữu (Cá nhân)**
- **Loại chiến lược:** FixedSizeChunker (cửa sổ trượt)
- **Mô tả & lý do chọn cho chủ đề này:**
  > Cấu hình `chunk_size=500`, `overlap=50`. Lựa chọn chiến lược chia nhỏ theo kích thước cố định để kiểm tra tính hiệu quả của phương pháp đường cơ sở (baseline). Độ chồng chéo 50 ký tự được kỳ vọng sẽ bảo toàn các từ khóa và ngữ cảnh giáp ranh giữa hai chunk liên tiếp khi trích xuất dữ liệu từ các tài liệu hướng dẫn quy trình Shopee.
- **Code snippet:**
```python
from src.chunking import FixedSizeChunker
chunker = FixedSizeChunker(chunk_size=500, overlap=50)
```

**Thành viên 2 — Nguyễn Nhật Thăng (2A202602727)**
- **Loại chiến lược:** SentenceChunker
- **Mô tả & lý do chọn:** Ban đầu cân nhắc chunker tùy chỉnh theo Q&A/Bullet points, nhưng 2 tài liệu thu thập (quy định đăng bán, chính sách cấm/hạn chế sản phẩm) là văn bản điều khoản dạng mục lớn (`1.`, `4.1.`, `4.2.`...), không phải cấu trúc hỏi-đáp — nên `SentenceChunker` phù hợp hơn để giữ trọn từng câu quy định thay vì cắt cứng theo ký tự như `FixedSizeChunker`. Baseline cho thấy `SentenceChunker` cho nhiều chunk hơn (78 và 55) và chunk ngắn hơn hẳn (avg ~228–271 ký tự) so với `recursive`/`fixed_size` — phù hợp với việc mỗi câu quy định thường đã là một đơn vị ngữ nghĩa độc lập trong văn bản này.
- **Code snippet:**
```python
from src.chunking import SentenceChunker
chunker = SentenceChunker(max_sentences_per_chunk=3)
```

**Thành viên 3 — Nguyễn Minh Quyền**
- **Loại chiến lược:** RecursiveChunker (chunk_size=200)
- **Mô tả & lý do chọn:** Lựa chọn `RecursiveChunker` vì văn bản chính sách có cấu trúc phân tầng đoạn và câu khác nhau. Thuật toán ưu tiên các dấu phân cách lớn như đoạn trống (`\n\n`) và xuống dòng (`\n`), chỉ chia nhỏ hơn khi mảnh vượt `chunk_size=200`, đồng thời gom các mảnh liền kề để hạn chế chunk vụn và duy trì ngữ cảnh tự nhiên.
- **Code snippet:**
```python
from src.chunking import RecursiveChunker
chunker = RecursiveChunker(chunk_size=200)
```

**Thành viên 4 — Vương Việt Hoàng**
- **Loại chiến lược:** Phân đoạn dựa trên Tiêu đề và Phân vùng nội dung (Heading & Section-based Chunking)
- **Mô tả & lý do chọn:**
  - **Mô tả:** Chiến lược chia nhỏ văn bản dựa trên hệ thống phân cấp tiêu đề Markdown (`#`, `##`, `###`). Mỗi chunk tương ứng với một chủ đề/tiểu mục logic hoàn chỉnh, giữ nguyên vẹn các thành phần như bảng dữ liệu hoặc danh sách các bước, đồng thời tự động lưu vết các tiêu đề cha vào phần metadata của từng chunk.
  - **Lý do chọn:**
    - *Bảo toàn tính toàn vẹn ngữ nghĩa:* Các tài liệu chính sách, quy trình (như đổi trả/hoàn tiền) gồm nhiều bước liên hoàn. Cắt theo heading giúp tránh việc một quy trình bị cắt đôi giữa chừng – điều thường gặp ở kỹ thuật cắt theo kích thước ký tự cố định (fixed-size).
    - *Cung cấp ngữ cảnh phong phú cho RAG:* Khi truy xuất (retrieval), metadata chứa hệ thống phân cấp tiêu đề (ví dụ: *Quy định chung > Giới hạn dung lượng*) giúp mô hình phân định chính xác ngữ cảnh câu hỏi, trả lời trực tiếp mà không bị nhầm lẫn giữa các điều khoản.
    - *Tương thích tốt với Markdown Table và List:* Đảm bảo các bảng biểu tra cứu và các bước hướng dẫn không bị phân mảnh hay đứt đoạn cấu trúc.
- **Code snippet:**
```python
from pathlib import Path
from langchain_text_splitters import MarkdownHeaderTextSplitter

# 1. Khai báo các cấp độ heading dùng làm ranh giới phân tách chunk
headers_to_split_on = [
    ("#", "Header_1"),
    ("##", "Header_2"),
    ("###", "Header_3"),
]

# 2. Khởi tạo bộ chia chunk theo Markdown Header
# strip_headers=False: Giữ nguyên tiêu đề trong nội dung chunk để LLM nắm trọn vẹn ngữ cảnh
markdown_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=headers_to_split_on,
    strip_headers=False
)

# 3. Đọc dữ liệu từ file Markdown đã chuẩn hóa
file_path = Path("data/return-refund-policy/request-return-refund.md")
content = file_path.read_text(encoding="utf-8")

# 4. Tiến hành chunking theo Heading/Section
chunks = markdown_splitter.split_text(content)

# 5. Kiểm tra kết quả các chunks và metadata thu được
print(f"Tổng số chunk được tạo: {len(chunks)}\n")
for i, chunk in enumerate(chunks, 1):
    print(f"=== CHUNK {i} ===")
    print(f"Metadata (Phân cấp Heading): {chunk.metadata}")
    print(f"Nội dung:\n{chunk.page_content.strip()}\n")
```

### So Sánh Giữa Các Thành Viên

| Thành viên | Chiến lược (Strategy) | Điểm truy xuất (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| **Nguyễn Quang Hữu** | FixedSizeChunker (chunk_size=500, overlap=50) | 8/10 (Thực nghiệm Gemini) | Đạt Rank 1 trên 100% câu hỏi thuộc tài liệu cá nhân (Câu 2, 3, 5), đạt 2/2 điểm nội dung ở Câu 5; tốc độ xử lý nhanh nhất, overlap 50 ký tự bảo toàn ngữ cảnh thời gian | Có thể chia tách quy trình nhiều bước (Câu 2) nếu vượt quá kích thước 500 ký tự |
| **Nguyễn Nhật Thăng** | SentenceChunker (max_sentences=3) | 8/10 | Giữ trọn vẹn từng câu quy định độc lập, đạt điểm tương tự cao (0.8098 ở Câu 5) | Dễ mất liên kết tiêu đề cha nếu quy định gồm nhiều câu dài |
| **Nguyễn Minh Quyền** | RecursiveChunker (chunk_size=200/500) | 6/10 | Linh hoạt theo cấu trúc phân đoạn tự nhiên (`\n\n`, `\n`) | Phân tách dấu đoạn có thể chia cắt 2 mốc thời gian liên quan vào 2 chunk khác nhau (như Câu 5) |
| **Vương Việt Hoàng** | Heading & Section-based Chunking | 8/10 | Giữ trọn vẹn toàn bộ một quy trình nhiều bước (như 8 bước ở Câu 2) vào chung 1 section chunk | Phụ thuộc chất lượng chuẩn hóa tiêu đề Markdown; kích thước chunk không đồng đều |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> Qua đối chiếu thực nghiệm bằng mô hình **Gemini Embedding (`gemini-embedding-001`)**:
> 1. Đối với **quy trình nhiều bước** (như Câu 2): Chiến lược **Heading & Section-based Chunking** là tốt nhất vì gom trọn vẹn toàn bộ các bước thao tác vào chung một ngữ cảnh, khắc phục triệt để nhược điểm cắt ngang quy trình của `FixedSizeChunker(500)`.
> 2. Đối với **điều khoản thời gian và điều kiện pháp lý** (như Câu 5): **FixedSizeChunker(500, 50)** và **SentenceChunker** lại vượt trội hơn **RecursiveChunker** vì giữ được cả thời gian xử lý khiếu nại (3 - 5 ngày) và thời gian nhận tiền hoàn (1 - 14 ngày) trong cùng một chunk (đạt điểm nội dung tối đa 2/2).
> 3. **Kết luận kiến trúc:** Giải pháp tối ưu nhất cho kho tài liệu chính sách TMĐT Shopee là **Hybrid Strategy**: Phân đoạn theo Section/Heading ở tầng trên, kết hợp Recursive/Fixed-size có overlap ở tầng dưới đối với các section dài.


---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
|---|-------|-------------------------------|--------------------------|
| 1 | Người mua có thời hạn bao nhiêu ngày kể từ khi đơn hàng giao thành công để gửi yêu cầu Trả hàng/Hoàn tiền đối với hàng thông thường và thực phẩm tươi sống? | Người mua có 15 ngày kể từ khi giao hàng thành công để gửi yêu cầu; riêng thực phẩm tươi sống và đông lạnh chỉ có thời hạn 24 giờ. | `188931.md` & `77251.md` (Điều 3.2) |
| 2 | Người mua có thể gửi yêu cầu Trả hàng/Hoàn tiền trực tiếp từ trang đơn hàng trên ứng dụng Shopee theo các bước như thế nào? | Bước 1: Mở app > Tôi > Chờ giao hàng/Đã giao; Bước 2: Bấm Trả hàng/Hoàn tiền; Bước 3: Chọn tình huống; Bước 4: Chọn sản phẩm; Bước 5: Chọn lý do; Bước 6: Chọn phương án; Bước 7: Điền mô tả, tải ảnh/video bằng chứng, email; Bước 8: Gửi yêu cầu. | `79233.md` (Mục 1, Cách 1) |
| 3 | Khi khiếu nại hàng bị bể vỡ hoặc lỗi, video mở kiện hàng của Người mua cần đáp ứng những tiêu chuẩn kỹ thuật nào về cách quay và dung lượng? | Video phải quay liên tục không cắt ghép, rõ nét, thấy 6 mặt kiện hàng, thấy rõ mã vận đơn và tem niêm phong. Dung lượng tối đa: video không quá 100MB (tối đa 1 phút), ảnh không quá 5MB/ảnh. | `79467.md` (Mục 2 và Mục 4) |
| 4 | Người mua có phải trả phí vận chuyển khi gửi hàng hoàn trả về cho Người bán không? | Người mua được miễn phí ship hoàn về nếu chọn hình thức "Lấy hàng tại nhà" hoặc "Gửi hàng tại bưu cục" liên kết với Shopee; nếu tự sắp xếp thì thanh toán trước và Shopee hỗ trợ hoàn lại sau. | `189477.md` (Mục 1 và 2) |
| 5 | Thời gian xử lý yêu cầu Trả hàng / Hoàn tiền là bao lâu? *(Cần filter `audience: buyer`)* | Đối với Người mua, yêu cầu Trả hàng/Hoàn tiền thường được Shopee xử lý trong khoảng 3 - 5 ngày làm việc; thời gian nhận tiền hoàn từ 1 - 14 ngày làm việc. | `79233.md` (Mục 2) |

### Tổng hợp chất lượng truy xuất của nhóm

> Cách chấm (theo `docs/SCORING.md`): **2 điểm/câu** — top-3 chứa chunk liên quan + agent trả lời đúng (2), có liên quan nhưng thiếu/không ở top-1 (1), không có trong top-3 (0).

| # | Câu hỏi | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3? | Ghi chú |
|---|---------|-------------------------------|-------------------------------|---------|
| 1 | Thời hạn gửi yêu cầu Trả hàng/Hoàn tiền đối với hàng thông thường và thực phẩm tươi sống | `SentenceChunker` / `RecursiveChunker` | Có | Giữ trọn vẹn câu điều khoản quy định số ngày (15 ngày đối với hàng thường, 24 giờ đối với thực phẩm tươi sống) |
| 2 | Các bước gửi yêu cầu Trả hàng/Hoàn tiền trực tiếp từ trang đơn hàng trên ứng dụng Shopee | `Heading & Section-based Chunking` | Có | Quy trình 8 bước là một section thao tác liền mạch; chunk theo section giữ trọn từ Bước 1 đến Bước 8 |
| 3 | Tiêu chuẩn kỹ thuật về cách quay và dung lượng video mở kiện hàng khi khiếu nại | `FixedSizeChunker(500, 50)` / `RecursiveChunker` | Có | Danh sách tiêu chuẩn kỹ thuật dài ~400 ký tự; overlap 50 ký tự giúp giữ trọn các thông số (100MB, 1 phút, 5MB) |
| 4 | Quy định phí vận chuyển khi Người mua gửi hàng hoàn trả về cho Người bán | `SentenceChunker` | Có | Tách theo ranh giới câu giữ nguyên vẹn câu khẳng định chính sách miễn phí ship và điều kiện hoàn tiền sau |
| 5 | Thời gian xử lý yêu cầu Trả hàng/Hoàn tiền là bao lâu? *(Cần filter `audience: buyer`)* | `FixedSizeChunker` + Filter `audience: buyer` | Có | Bộ lọc `audience: buyer` loại bỏ hoàn toàn quy định của Người bán, trích xuất chính xác thời gian xử lý 3-5 ngày |

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**
> Lọc bằng metadata phát huy hiệu quả quyết định ở **Câu hỏi số 5** (và hỗ trợ định hướng chính xác ở các câu 2, 3, 4). Do hệ thống chính sách Shopee có sự phân hóa sâu sắc giữa Người Mua (`buyer`) và Người Bán (`seller`), việc áp dụng bộ lọc `metadata_filter={'audience': 'buyer'}` đã loại bỏ hoàn toàn các tài liệu quy định thời hạn phản hồi dành riêng cho Người bán (48 giờ), thu hẹp không gian tìm kiếm về đúng tài liệu quy trình của Người mua. Nhờ đó, hệ thống trích xuất chính xác thời gian xử lý 3 - 5 ngày làm việc và thời gian nhận tiền hoàn 1 - 14 ngày làm việc.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**
1. **Quy trình Ingestion & Metadata:** Trực quan hóa việc trích xuất Frontmatter, kế thừa siêu dữ liệu `audience`, `category`, chia nhỏ thành 337 chunk và lưu trữ vào Vector Store.
2. **Thực nghiệm A/B Filtering (Câu hỏi 5):** Trình diễn trực quan sự khác biệt giữa truy vấn không lọc (dễ lẫn tài liệu không đúng đối tượng) và truy vấn có lọc `audience='buyer'` (tập trung chính xác vào luồng khiếu nại của Người Mua).
3. **Phân tích Failure Case (Câu hỏi 2):** Phân tích giới hạn kích thước của `FixedSizeChunker(500)` khi cắt ngang quy trình 8 bước (chỉ giữ được Bước 1-3 ở chunk đầu), đối chiếu với ưu thế gom trọn vẹn quy trình của Heading-based chunking qua thực nghiệm Gemini Embedding.

**Bài học rút ra khi so sánh trong nhóm:**
1. **Đặc thù dữ liệu chính sách:** Văn bản quy định TMĐT có cấu trúc danh sách và bảng biểu phức tạp. Quá trình tiền xử lý cần làm sạch các thành phần điều hướng web và tiêu đề lặp để bảo toàn chất lượng chunk.
2. **Hiệu quả của Metadata Pre-filtering:** Lọc siêu dữ liệu trước khi tính toán độ tương tự vector là giải pháp then chốt giúp loại bỏ triệt để nhiễu giữa các luồng nghiệp vụ khác nhau (Người mua vs Người bán).
3. **Trade-off giữa các chiến lược chia nhỏ:** Fixed-size ưu tiên tốc độ và kiểm soát bộ nhớ; Sentence ưu tiên tính toàn vẹn câu văn; Recursive cân bằng phân đoạn; còn Heading-based giữ trọn ngữ cảnh phân cấp điều khoản.

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> 1. Xây dựng bộ parser Markdown chi tiết hơn để bóc tách riêng các bảng biểu quy định thời gian (như bảng thời gian hoàn tiền theo từng ngân hàng) thành các cặp Key-Value có cấu trúc trước khi chunk.
> 2. Bổ sung thêm metadata `product_type` (thực phẩm tươi sống, hàng điện tử, hàng tiêu dùng) vì chính sách đổi trả Shopee có những mốc thời gian đặc thù theo từng ngành hàng.

---

## Tự Đánh Giá (Phần Nhóm)

Nhóm tự đánh giá dựa trên mức độ hoàn thiện đầy đủ của tập dữ liệu chuẩn, cấu trúc metadata đa chiều, mã nguồn vượt qua 100% kiểm thử (47/47 tests passed) và kịch bản demo bài bản:

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Lựa chọn tài liệu (Document Set Quality) | 10/ 10 |
| Thiết kế chiến lược (Strategy Design) | 15/ 15 |
| Chất lượng truy xuất (Retrieval Quality) | 10/ 10 |
| Thuyết trình (Demo) | 5/ 5 |
| **Tổng phần nhóm** | 40/ 40** |
