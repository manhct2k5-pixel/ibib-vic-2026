---
name: 'Review — Xác thực phiên bản công nghệ (Stack)'
type: architecture-review
target: ARCHITECTURE-SPINE.md (§Stack)
reviewer: version-verification-gate
date: '2026-07-17'
method: WebSearch (tra web phiên bản ổn định mới nhất tại 7/2026)
---

# Review phiên bản công nghệ — Compliance Copilot (7/2026)

Xác thực từng mục trong mục `## Stack` của spine. Với mỗi công nghệ: phiên bản ổn định mới nhất tra được trên web (tháng 7/2026), khuyến nghị pin, và cờ nếu spine đang giả định sai.

## Bảng xác thực

| Công nghệ | Spine ghi | Thực tế web (7/2026) | Cờ / ghi chú |
| --- | --- | --- | --- |
| Python | 3.11 | Ổn định khuyến nghị: **3.12** (EOL 2028-10). 3.13 đã ra (free-threaded còn experimental). **3.11 EOL 2026-10-31** — chỉ còn ~3 tháng. | 🟡 **CỜ**: 3.11 sắp hết vòng đời trong 2026. Với dự án khởi tạo 2026 nên pin **3.12** (an toàn, dep đã hỗ trợ đầy đủ). 3.13 chỉ chọn nếu cần free-threading. |
| FastAPI | [GIẢ ĐỊNH] mới nhất | **0.139.2** (2026-07-16). Yêu cầu Python ≥ 3.10. | 🟢 Còn hợp. Pin `fastapi>=0.139,<0.140`. Vẫn ở dải 0.x (SemVer minor có thể breaking) → pin chặt. |
| NetworkX | [GIẢ ĐỊNH] mới nhất | **3.6.1** (2025-12-08). 3.7 đang ở rc (2026-07). | 🟢 Còn hợp, active. Pin `networkx>=3.6,<3.7`. Đủ cho đồ thị demo (immutable, in-memory) theo AD-2. |
| rank_bm25 | [GIẢ ĐỊNH] mới nhất | **0.2.2** (2022-02-16) — **không cập nhật ~4 năm**, gần như không maintained. | 🔴 **CỜ**: lib gần như bỏ hoang. Vẫn chạy được (thuần Python, ổn định, API tối giản) nên OK cho demo 48h. Nếu cần tốc độ/tương lai: cân nhắc **BM25S** (`pip install bm25s`, nhanh tới ~500x, active 2026). Cho hackathon: rank_bm25 vẫn chấp nhận được vì corpus nhỏ. |
| ChromaDB (nhúng) *hoặc* numpy cosine | [GIẢ ĐỊNH] | ChromaDB **1.5.9** (2026-05-05). Chế độ nhúng/in-process `PersistentClient` (và in-memory) **VẪN được hỗ trợ**. | 🟢 Chế độ embedded còn sống → thỏa AD-7 (sau interface provider). Spine đã hoãn "chọn dứt điểm Chroma vs numpy cosine" (§Deferred) — hợp lý. Với corpus demo nhỏ, **numpy cosine** thậm chí đơn giản hơn, ít phụ thuộc hơn. |
| httpx | [GIẢ ĐỊNH] | **0.28.1** (ổn định). Lưu ý: 2026-02 maintainer gốc đóng issues/discussions; fork **httpx2 (2.5.0, 2026-06)** do Pydantic đỡ đầu, active. | 🟡 **CỜ nhẹ**: httpx gốc vẫn dùng tốt (ổn định, không bug chặn) cho demo. Theo dõi: nếu cần bảo trì/security dài hạn → cân nhắc **httpx2**. Cho 48h: `httpx==0.28.1` ổn. |
| React + TS + Vite | 19 / ~6 / 8 (đã pin repo) | (Ngoài phạm vi tra lần này — đã pin trong repo) | 🟢 Giữ nguyên theo repo. |
| react-force-graph | [GIẢ ĐỊNH] | **1.48.2** (~5 tháng trước, tức đầu 2026). Vẫn active (release trong 12 tháng qua, ~34k downloads/tuần). Có biến thể `react-force-graph-2d` (chỉ 2D, nhẹ hơn). | 🟢 Còn maintained. Cho demo dùng **react-force-graph-2d** (nhẹ, không kéo three.js/3D). Thay thế phổ biến hơn nếu muốn: **Cytoscape.js** (~500k dl/tuần, mạnh về thuật toán/layout — hợp đồ thị pháp lý có phân tích), **vis-network** (~200k, diagram tương tác). Với AD-1/AD-4 (node = clause_id), Cytoscape là lựa chọn "an toàn/phổ biến" hơn nếu cần layout & path-finding. |
| Streamlit (admin/ingest) | [GIẢ ĐỊNH] | **1.59.2** (2026-07-13). | 🟢 Còn hợp, rất active. Pin `streamlit>=1.59,<1.60`. |
| LLM: Claude / GPT-4 (API) | "model mới nhất" | Claude: **Sonnet 5** (2026-06-30, agentic/rẻ) và **Fable 5** (2026-06-09, mạnh nhất). GPT: **GPT-5.6** (Sol/Terra/Luna, GA 2026-07-09, default ChatGPT). | 🔴 **CỜ**: "GPT-4" đã **lỗi thời** ở 7/2026. Cập nhật spine: dùng **Claude Sonnet 5** (default agentic, rẻ — hợp synthesize stage AD-3) hoặc **GPT-5.6**; Fable 5 khi cần chất lượng cao nhất. Vẫn giữ sau interface provider (AD-7) để đổi dễ. |
| Embedding: multilingual-e5-large / bge-m3 (API) | [GIẢ ĐỊNH] "(API)" | Cả hai là **open-weight, chủ yếu SELF-HOST** (HuggingFace). bge-m3: đa ngôn ngữ 100+, 8192 token, dense+sparse+multi-vector; e5-large: ~94 ngôn ngữ. Không có "embedding API" đại chúng, sẵn-dùng như LLM API (một số host bên thứ ba có, nhưng không phải chuẩn mặc định). | 🔴 **CỜ QUAN TRỌNG**: Spine ghi các model này là **"(API)"** ngang hàng LLM API — **GIẢ ĐỊNH SAI**. e5/bge-m3 **thường phải tự host** (cần GPU: bge-m3 tối thiểu ~A10G; hoặc chạy CPU chậm cho demo nhỏ), KHÔNG có endpoint API tiện lợi như Claude/OpenAI. Hệ quả kiến trúc: `providers/embedding.py` (AD-7/AD-8) không thể chỉ là "gọi HTTP tới embedding API" như LLM. **Khuyến nghị demo 48h**: (a) dùng **OpenAI/Voyage embedding API** thật (có endpoint sẵn) để giữ mô hình "provider gọi API"; HOẶC (b) nếu bám e5/bge → chạy local qua `sentence-transformers`/FastEmbed (in-process, CPU cho corpus nhỏ), KHÔNG phải "API"; HOẶC (c) numpy cosine trên vectors dựng sẵn. Sửa nhãn "(API)" trong spine cho đúng bản chất self-host. |

## Tóm tắt cờ (ưu tiên xử lý)

1. 🔴 **Embedding e5/bge-m3 KHÔNG phải "API" sẵn-dùng** — là open-weight self-host (cần GPU hoặc chạy local qua sentence-transformers). Spine gán nhãn "(API)" gây hiểu nhầm rằng có endpoint tiện như LLM. → Sửa mô hình provider hoặc đổi sang embedding API thật (OpenAI/Voyage) cho demo.
2. 🔴 **"GPT-4" lỗi thời** (7/2026): cập nhật sang Claude Sonnet 5 / GPT-5.6 (Fable 5 nếu cần mạnh nhất).
3. 🟡 **Python 3.11 EOL 2026-10-31** (còn ~3 tháng): pin **3.12**.
4. 🔴 **rank_bm25 gần như bỏ hoang** (0.2.2 từ 2022): chấp nhận cho 48h (corpus nhỏ); cân nhắc **BM25S** nếu cần tốc độ/tương lai.
5. 🟡 **httpx**: maintainer gốc giảm hoạt động (2026-02); 0.28.1 vẫn ổn cho demo, theo dõi fork **httpx2** cho dài hạn.

## Phiên bản chốt được (khuyến nghị pin)

- Python **3.12**
- FastAPI **0.139.2** (`>=0.139,<0.140`)
- NetworkX **3.6.1** (`>=3.6,<3.7`)
- rank_bm25 **0.2.2** (chấp nhận; hoặc BM25S)
- ChromaDB **1.5.9** (embedded `PersistentClient` — còn hỗ trợ) *hoặc* numpy cosine
- httpx **0.28.1** (hoặc httpx2 2.5.0 nếu ưu tiên bảo trì)
- react-force-graph **1.48.2** (khuyên dùng biến thể `-2d`); thay thế: Cytoscape.js / vis-network
- Streamlit **1.59.2**
- LLM: **Claude Sonnet 5** hoặc **GPT-5.6** (Fable 5 khi cần cao cấp)
- Embedding: bge-m3 / e5-large **self-host** (không phải API) — hoặc chuyển sang embedding API thật

## Nguồn (URL)

- Python EOL: https://endoflife.date/python , https://devguide.python.org/versions/
- FastAPI: https://pypi.org/project/fastapi/ , https://github.com/fastapi/fastapi/releases
- NetworkX: https://pypi.org/project/networkx/ , https://networkx.org/documentation/stable/release/index.html
- rank_bm25: https://pypi.org/project/rank-bm25/ , https://github.com/dorianbrown/rank_bm25 ; BM25S: https://github.com/xhluca/bm25s
- ChromaDB: https://pypi.org/project/chromadb/ , https://github.com/chroma-core/chroma/releases
- httpx: https://pypi.org/project/httpx/ , https://github.com/encode/httpx/releases ; httpx2: https://pypi.org/project/httpx2/
- react-force-graph: https://www.npmjs.com/package/react-force-graph , https://github.com/vasturiano/react-force-graph/releases ; alternatives: https://www.pkgpulse.com/guides/cytoscape-vs-vis-network-vs-sigma-graph-visualization-2026
- Streamlit: https://pypi.org/project/streamlit/ , https://docs.streamlit.io/develop/quick-reference/release-notes/2026
- Embedding (self-host): https://huggingface.co/BAAI/bge-m3 , https://presenc.ai/research/best-open-weight-embedding-models-2026
- LLM: https://platform.claude.com/docs/en/about-claude/models/overview , https://techcrunch.com/2026/06/30/anthropic-launches-claude-sonnet-5-as-a-cheaper-way-to-run-agents/
