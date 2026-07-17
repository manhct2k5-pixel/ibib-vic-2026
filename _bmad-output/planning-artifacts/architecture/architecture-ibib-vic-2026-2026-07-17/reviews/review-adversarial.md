---
name: 'Adversarial Review — ARCHITECTURE-SPINE Compliance Copilot'
type: architecture-review
mode: adversarial
target: ARCHITECTURE-SPINE.md
created: '2026-07-17'
reviewer: adversarial-reviewer
verdict: 'KHÔNG SẴN SÀNG cho build song song — 8 lỗ hổng "cả hai đều đúng luật", 3 lỗ CRITICAL chặn tích hợp.'
---

# Báo cáo Reviewer Đối Nghịch — ARCHITECTURE-SPINE

## Cách đọc báo cáo

Tôi đóng vai kẻ phá hoại. Với mỗi lỗ hổng, tôi dựng **hai unit (do hai người khác nhau build)**, mỗi unit **tuân thủ đúng từng chữ mọi AD hiện có**, nhưng khi ghép lại thì **build ra không khớp / rò rỉ / sai kết quả**. Mỗi lỗ = một chỗ AD chưa khóa. Kèm đề xuất **AD mới** hoặc **siết Rule cũ**.

Bối cảnh: 6 người, 7 epic, 48h, build song song. Lỗ nguy hiểm nhất là chỗ hai người hiểu khác nhau mà **cả hai đều "đúng luật"** — không ai review ra được vì không ai vi phạm gì.

---

## LỖ #1 — [CRITICAL] `sources[]` có HAI hợp đồng đối chọi nhau

**Đây là lỗ chết người nhất. Hai tài liệu nguồn của spine mâu thuẫn trực tiếp.**

- **Spine** (§Data flow + AD-4): output là `{answer, sources[clause_id], conflictWarning?}`. AD-4 nói "trích nguồn tham chiếu `clause_id`". Convention Stage I/O: `Candidate = {clause_id, score, why}`.
- **API_CONTRACT.md** (mục 3, được AD-6 **[ADOPTED]** đóng băng): mỗi phần tử `sources` là `{name, description}`. **Không hề có `clause_id`.**

**Cặp unit lệch (cả hai đều đúng luật):**
- *Dev BE (Epic 2, tuân AD-4)* build `synthesize` trả `sources: [{clause_id: "TT41/Điều 6.3", score, why}]`. Đúng AD-4 từng chữ.
- *Dev FE (Epic 5, tuân AD-6 + API_CONTRACT)* build `SourceList` đọc `source.name` và `source.description`. Đúng AD-6 từng chữ.
- **Ghép lại:** FE render `undefined — undefined`. GraphView (Epic 5, FR-12/13) cần `clause_id` để highlight node đồ thị nhưng contract không cấp field đó → **GraphView không thể liên kết source↔node**, tính năng lõi của demo chết.

**Vì sao cả hai "đúng":** AD-6 nói contract là API_CONTRACT.md; AD-4 nói trích nguồn theo `clause_id`. Spine tự mâu thuẫn với chính companion mà nó [ADOPTED]. Không dev nào sai.

**Đề xuất — AD-6 phải được SIẾT (đây là sửa gấp nhất):**
> `sources[]` = `{clause_id, name, description}` — `clause_id` là **bắt buộc** (neo AD-4), `name`/`description` là nhãn hiển thị. Cập nhật API_CONTRACT.md mục 3 cho khớp trước khi bất kỳ ai build FE/synthesize. Đây là thay đổi "additive" hợp lệ theo AD-6 nhưng PHẢI làm ngay, không để dev tự đoán.

---

## LỖ #2 — [CRITICAL] Corpus JSON schema chưa tồn tại; `data/sample/` chỉ có `.gitkeep`

**AD-1 tuyên bố "Schema đặt tại `data/sample/` và versioned" nhưng thực tế `data/sample/` rỗng (chỉ `.gitkeep`).** Spine chỉ mô tả schema bằng ERD — mà ERD **không phải file dữ liệu**, không đủ để khóa hình dạng JSON.

**Các field CHƯA khóa chặt, mỗi field sinh một cặp unit lệch:**

**2a — `id` của document vs clause:** ERD nói `DOCUMENT.doc_code PK` và `CLAUSE.clause_id PK`. Nhưng `edges[]` trỏ vào gì? `from`/`to` là `clause_id` hay đôi khi là `doc_code`?
- *Dev ingest (Epic 1)* viết edge `{from: "TT41/Điều 6.3", to: "TT22/Điều 1", type: "SUPERSEDED_BY"}` (clause→clause). Đúng AD-4.
- *Dev graph (Epic 1)* build node loader nạp cả `documents[]` thành node để vẽ cây văn bản → edge `AMENDS` ở cấp **document** `{from: "TT22", to: "TT41"}`. Cũng "đúng luật" vì Convention không cấm.
- **Ghép:** `expand` (Epic 2) traverse tìm `REFERENCES` 1–2 hop, gặp edge cấp-document trỏ vào một key không phải `clause_id` → `KeyError` hoặc trả node không có `text` cho `synthesize`. Pipeline gãy.

**2b — Biểu diễn "thay thế một phần" ở cấp sub-clause:** AD-5 nói "Thay thế một phần = set `expiry_date` ở cấp Clause". Nhưng "một phần" của **Điều 6.3** là gì — có sub-clause 6.3.a không? clause_id `"TT41/Điều 6.3"` vs `"TT41/Điều 6.3.a"` là hai node riêng hay một?
- *Dev A* annotate cả Điều 6.3 là 1 clause, set expiry cho cả điều.
- *Dev B* tách 6.3.a, 6.3.b thành clause con để "thay thế một phần" chính xác hơn.
- **Ghép:** conflict_check gom theo `topic`; retrieve trả granularity khác nhau → cùng một quy định xuất hiện hai độ mịn, `is_active` cho kết quả mâu thuẫn, citation trỏ sai cấp.

**Đề xuất — AD-1 phải SIẾT + tạo artifact thật:**
> (1) Commit `data/sample/corpus.schema.json` (JSON Schema thật, không chỉ ERD) + tối thiểu 1 file corpus mẫu **trước giờ G**. (2) Khóa: `edges[].from`/`to` **luôn là `clause_id`** (không bao giờ `doc_code`); quan hệ cấp document biểu diễn qua clause đại diện. (3) Khóa quy tắc granularity: sub-clause chỉ tách thành clause riêng khi có `SUPERSEDES`/`expiry` riêng; nếu không, đơn vị nguyên tử là Điều. Ghi rõ vào §Conventions.

---

## LỖ #3 — [CRITICAL] Thang điểm `score` chưa có AD → RRF/hybrid fusion mỗi người trộn một kiểu

`Candidate.score` (§Conventions) **không định nghĩa thang**. AD-3 nói retrieve là "hybrid" (BM25 + vector) nhưng **không có AD nào quy định cách hợp nhất hai thang điểm**.

**Cặp unit lệch:**
- *Dev retrieve (Epic 2)* trả `score` = **BM25 raw** (0..~15, không chặn trên) cho nhánh keyword và cosine (0..1) cho nhánh vector, rồi nối hai list. Đúng luật — Convention chỉ nói có field `score`.
- *Dev khác cũng ở retrieve/expand* dùng **RRF** (Reciprocal Rank Fusion, `1/(k+rank)`, ~0.0..0.03) hoặc min-max normalize về 0..1.
- **Ghép:** `expand` thêm candidate mới — gán `score` bao nhiêu? `temporal_filter` và `conflict_check` có thể sort/threshold theo `score`. Hai thang trộn lẫn → **BM25 raw luôn áp đảo cosine**, ranking rác. `synthesize` nhận top-k sai. Tệ hơn: Benchmark (Epic 6) so baseline vs full — nếu baseline dùng thang khác thì so sánh vô nghĩa.

**Đề xuất — AD MỚI (AD-10):**
> **AD-10 — Fusion & thang điểm chuẩn hóa.** Retrieve hybrid **bắt buộc** hợp nhất bằng **RRF** (hoặc min-max về `[0,1]`) — chọn MỘT, ghi vào spine. `Candidate.score` luôn là **điểm đã chuẩn hóa `[0,1]`, càng cao càng liên quan**, cùng thang qua mọi stage. Stage nào tạo candidate mới (`expand`) phải gán score theo cùng thang (hoặc `score` kế thừa từ node gốc, ghi rõ). Baseline dùng đúng thang này.

---

## LỖ #4 — [HIGH] Reload KB giữa demo (FR-16) vs bất biến (AD-2): "reload" chưa được định nghĩa

AD-2 nói KB bất biến, "Ingest văn bản mới (FR-3) = dựng lại/nạp lại KB". Admin Streamlit "dựng/reload". Radar (FR-16) chạy "sau reload". **Nhưng không ai định nghĩa reload thao tác thế nào lên đối tượng KB in-memory đang phục vụ request.**

**Cặp unit lệch:**
- *Dev ingest/admin (Epic 1/7)* hiểu reload = **mutate tại chỗ** object KB toàn cục (rebuild index rồi gán `kb.graph = new_graph`). "Nạp lại" nghĩa đen là vậy.
- *Dev api/pipeline (Epic 2)* hiểu KB bất biến nên **giữ tham chiếu** `self.kb` suốt vòng đời request, không phòng thủ đổi ngôi.
- **Ghép — hỏng chính giữa demo:** Trong phiên demo, một request `/api/chat` đang chạy stage 3 (temporal_filter) trên `kb` cũ; admin bấm reload → object bị thay ruột → stage 4/5 đọc graph mới → **mất tính as-of nhất quán**, hoặc race condition NetworkX (đọc trong lúc ghi) → crash/kết quả lai. Đúng kịch bản FR-16 "nạp văn bản mới GIỮA phiên demo".

Ai định nghĩa "reload"? Không ai. Cả hai dev đều nghĩ mình đúng AD-2.

**Đề xuất — SIẾT AD-2:**
> "Reload" = **atomic swap tham chiếu**: dựng `KnowledgeBase` **mới hoàn toàn**, rồi swap con trỏ toàn cục bằng một thao tác nguyên tử; **KB cũ giữ nguyên** đến khi mọi request đang chạy hoàn tất (KB thật sự immutable — không mutate tại chỗ, không rebuild in-place). Mỗi request **pin** một tham chiếu KB tại lúc bắt đầu và dùng nó đến hết (snapshot per-request). Cấm `kb.graph = ...` sau startup.

---

## LỖ #5 — [HIGH] FR-7 lọc `visibility: public` — chưa chỉ stage lọc → RÒ nội bộ

Convention có `visibility: public|internal` cho Document/Clause (phục vụ FR-7). **Nhưng AD-3 định nghĩa thứ tự stage mà KHÔNG nói stage nào lọc visibility.** Không AD nào gán quyền lọc.

**Cặp unit lệch:**
- *Dev retrieve (Epic 2)* nghĩ lọc là việc của synthesize/output (giống temporal_filter là stage riêng) → retrieve trả **cả clause internal** trong Candidate[].
- *Dev synthesize (Epic 2)* nghĩ retrieve đã lọc rồi (nguồn sạch) → đưa **toàn bộ text clause vào prompt LLM** để sinh answer, chỉ lọc `sources[]` hiển thị.
- **Ghép — RÒ:** Clause `internal` lọt vào prompt LLM → **nội dung nội bộ rò ra trong `answer`** dù không xuất hiện ở `sources`. Cả hai dev đều "đúng luật" vì AD im lặng. Đây là rò bảo mật, không chỉ bug hiển thị.

Tệ hơn: `expand` 1–2 hop có thể **kéo clause internal** qua REFERENCES từ một clause public → lọt vòng lọc nếu lọc đặt trước expand.

**Đề xuất — AD MỚI (AD-11):**
> **AD-11 — Visibility lọc tại nguồn, sớm nhất, một chỗ.** FR-7 lọc `visibility` **ngay trong `retrieve`, trước khi trả Candidate đầu tiên**, và `expand` **không được vượt qua ranh giới internal** (edge dẫn tới clause internal bị bỏ khi request ở chế độ public). Clause internal **không bao giờ** vào bất kỳ stage sau, kể cả prompt LLM. Chế độ visibility là tham số request, mặc định `public`.

---

## LỖ #6 — [HIGH] `expiry_date = null` — AD-5 dùng `[eff, exp)` với exp null gây so sánh khác nhau

AD-5: active **iff** `effective_date <= asOf < expiry_date`. ERD: `expiry_date "null = còn hiệu lực"`. **Nhưng công thức `asOf < null` không định nghĩa được** — mỗi ngôn ngữ/lib xử null khác nhau, và AD-5 nói "chỉ MỘT hàm `is_active`" nhưng không viết ra cách xử null.

**Cặp unit lệch (dù chỉ 1 hàm, hai người có thể viết hai bản trong 48h trước khi hợp nhất):**
- *Dev A (Epic 3)* viết `is_active`: `eff <= asOf and (exp is None or asOf < exp)` → null = vô hạn, active. Đúng ý ERD.
- *Dev B (Epic 4 conflict_check)* trong lúc chờ hàm chung, tạm viết `eff <= asOf < exp` và **coi null như một sentinel** (ví dụ parse null thành `""` hoặc `9999-12-31`, hoặc so sánh string ISO trong đó `null` → lỗi `TypeError` bị nuốt thành `False`).
- **Ghép:** Cùng clause "còn hiệu lực vĩnh viễn" (exp=null, ví dụ TT22/Điều 1 CAR=9%) → hàm A nói active, nhánh B nói **inactive** → conflict_check **bỏ sót** clause hiện hành, hoặc temporal_filter loại nhầm clause đúng → **demo trả CAR sai (8% thay vì 9%)** — đúng kịch bản lõi trong spine (§Ví dụ chuỗi phiên bản).

**Đề xuất — SIẾT AD-5:**
> Viết rõ trong spine: `is_active(clause, asOf) := effective_date <= asOf AND (expiry_date IS NULL OR asOf < expiry_date)`. `expiry_date = null` (JSON null, KHÔNG phải chuỗi rỗng, KHÔNG phải sentinel date) = còn hiệu lực vô hạn. Cấm mọi bản `is_active` thứ hai; conflict_check/temporal_filter **phải import** hàm này, không tự viết. Thêm test-case null vào §Conventions.

---

## LỖ #7 — [MEDIUM] Cờ baseline (AD-3) — đặt ở đâu chưa khóa → FE benchmark gọi sai

AD-3: "baseline = cùng pipeline với `expand` và `temporal_filter` TẮT bằng cờ". Data flow ghi `/api/chat {question, asOf=today, mode}`. **Nhưng `mode` (cờ) đặt ở request hay config, giá trị hợp lệ là gì — không khóa.** API_CONTRACT.md thậm chí **không có** field `mode` (request chỉ `{question}`), mà AD-6 nói contract chỉ thêm additive.

**Cặp unit lệch:**
- *Dev pipeline (Epic 6)* đặt cờ ở **request body**: `{question, mode: "baseline"|"full"}`.
- *Dev FE benchmark (Epic 5/6)* đọc API_CONTRACT (chỉ `{question}`) → nghĩ baseline là **endpoint riêng** `/api/chat/baseline`, hoặc **query param** `?baseline=true`, hoặc gọi hai lần với env khác.
- **Ghép:** FE benchmark (FR-14 side-by-side) gọi **không đúng cách bật cờ** → backend chạy full cho cả hai cột → benchmark hiển thị **hai kết quả giống hệt**, mất hoàn toàn giá trị demo "chúng tôi hơn RAG thường". Không ai vi phạm AD.

**Đề xuất — SIẾT AD-3 + AD-6:**
> Khóa cờ baseline là field request **`mode: "full" | "baseline"`** (mặc định `"full"`), thêm vào API_CONTRACT.md mục 2 (additive, hợp lệ AD-6). Cấm endpoint thứ hai và query param. Ghi giá trị enum vào §Conventions để FE benchmark gọi đúng.

---

## LỖ #8 — [MEDIUM] `why` trong Candidate — cấu trúc chưa khóa, hai stage ghi khác kiểu

`Candidate = {clause_id, score, why}`. `why` **không có kiểu** — string? list? object? Mỗi stage (retrieve, expand, conflict_check) đều thêm/sửa `why`.

**Cặp unit lệch:**
- *Dev retrieve* set `why = "khớp BM25: 'CAR', 'vốn'"` (string).
- *Dev expand* set `why = {reason: "REFERENCES 1 hop", from: "TT41/Điều 6.3"}` (object), hoặc **ghi đè** `why` của retrieve.
- *Dev conflict_check* muốn **append** lý do xung đột nhưng nhận khi string khi object → hoặc crash hoặc mất thông tin retrieve.
- **Ghép:** `synthesize` và FE muốn hiển thị "vì sao clause này được chọn" (giải thích cho compliance officer) nhưng `why` là union type hỗn loạn → hiển thị thất thường; hoặc thông tin của stage trước bị stage sau ghi đè mất.

**Đề xuất — SIẾT Convention Stage I/O:**
> Khóa `why` là **`list[str]`** (mỗi stage **append**, không ghi đè) HOẶC `{stage: reason}` dict. Ghi rõ: stage chỉ được **thêm** vào `why`, không xóa/ghi đè của stage trước. Định nghĩa kiểu trong §Conventions cạnh `Candidate`.

---

## LỖ #9 — [MEDIUM] AD-9 "deterministic input" vs fallback canned — ranh giới mờ ở Radar/Conflict

AD-9: Conflict (FR-11) và Radar (FR-16) "tính từ dữ liệu đồ thị lúc chạy"; fallback canned "ở một tầng tách riêng". **Nhưng ai quyết định khi nào rơi vào fallback, và fallback trả về hình dạng gì** (có phải cùng `{answer, sources[]}` không) — không khóa.

**Cặp unit lệch:**
- *Dev pipeline* để pipeline **throw** khi LLM/embedding API lỗi (503).
- *Dev fallback (đường dự phòng demo)* bọc một `try/except` **quanh cả pipeline**, trả câu canned khi có bất kỳ exception — **kể cả khi lỗi là do corpus/logic thật**, che mất bug.
- **Ghép:** Trong demo, một clause thiếu field → pipeline lỗi thật → fallback nuốt, trả câu canned trông "đúng" → **ban giám khảo thấy câu trả lời mượt nhưng thực ra logic thật đã chết** (đúng thứ AD-9 muốn chống: "hardcode đội lốt logic thật"). Cả hai dev đều nói mình theo AD-9.

**Đề xuất — SIẾT AD-9:**
> Fallback **chỉ** kích hoạt khi lỗi thuộc nhóm **hạ tầng ngoài** (LLM/embedding API timeout/5xx) — bắt lỗi **hẹp**, không bao `except Exception` quanh pipeline. Lỗi dữ liệu/logic phải **nổi lên** (fail loud, HTTP 500 + detail), không được fallback che. Fallback trả **cùng hình dạng** `{answer, sources[]}` + cờ nội bộ `degraded: true` để phân biệt khi review.

---

## Tổng hợp mức độ

| # | Lỗ hổng | Severity | Loại đề xuất |
|---|---------|----------|--------------|
| 1 | `sources[]`: clause_id (AD-4) vs {name,description} (AD-6/CONTRACT) | CRITICAL | Siết AD-6 + sửa API_CONTRACT |
| 2 | Corpus schema chưa tồn tại; edge from/to & granularity chưa khóa | CRITICAL | Siết AD-1 + tạo schema thật |
| 3 | Thang `score` & fusion BM25+vector chưa có AD | CRITICAL | **AD-10 mới** |
| 4 | "Reload" KB chưa định nghĩa vs bất biến AD-2 | HIGH | Siết AD-2 (atomic swap + per-request pin) |
| 5 | FR-7 visibility lọc ở stage nào → rò internal vào LLM | HIGH | **AD-11 mới** |
| 6 | `expiry_date=null` trong `[eff,exp)` xử lý khác nhau | HIGH | Siết AD-5 (viết rõ null) |
| 7 | Cờ baseline đặt đâu chưa khóa → FE gọi sai | MEDIUM | Siết AD-3 + AD-6 (`mode` field) |
| 8 | `why` chưa có kiểu → stage ghi đè nhau | MEDIUM | Siết Convention (append-only) |
| 9 | Fallback canned che lỗi logic thật | MEDIUM | Siết AD-9 (bắt lỗi hẹp) |

## Ba việc phải làm TRƯỚC giờ G (nếu không, tích hợp chắc chắn gãy)

1. **Sửa AD-6 + API_CONTRACT**: `sources[] = {clause_id, name, description}`. Không có bước này, FE và BE build ra không ghép được (Lỗ #1).
2. **Commit `corpus.schema.json` thật + 1 corpus mẫu** vào `data/sample/`, khóa `edges.from/to = clause_id` (Lỗ #2). Không có file thật thì AD-1 chỉ là khẩu hiệu.
3. **Thêm AD-10 (fusion/score)** trước khi ai chạm retrieve (Lỗ #3). Ba người (Epic 2, 3, 6) cùng phụ thuộc thang điểm này.
