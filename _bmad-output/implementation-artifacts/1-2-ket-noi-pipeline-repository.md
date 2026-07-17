---
baseline_commit: f12c67d723f79a905aad1904d0d41343906bb622
---

# Story 1.2: Kết nối pipeline với Repository (Epic 0)

Status: review

<!-- Ultimate context engine analysis completed - comprehensive developer guide created -->

## Story

As a hệ thống,
I want một **interface Repository ổn định** với bản **stub** hiện thực đầy đủ trên `corpus.json`, cùng một handle dùng chung trong app,
so that pipeline (Story 1.3+) gọi hàm repository mà không chạm SQL, và khi Epic 0 giao repository Postgres thì **đổi một dòng factory** là xong.

## Acceptance Criteria

1. **Hợp đồng interface khóa lại.** Có một `Repository` Protocol định nghĩa đủ 6 hàm với chữ ký + kiểu trả về rõ: `search(q, as_of, mode) -> list[Clause]`, `expand_references(clause_ids) -> list[Clause]`, `find_conflicts(as_of) -> list[ConflictPair]`, `version_timeline(clause_id) -> list[Clause]`, `export_graph() -> dict`, `insert_document(doc, clauses, edges) -> None`. `Clause` (đã có) + `ConflictPair` (mới) là dataclass, khóa `clause_id`. (AD-12)
2. **StubRepository hiện thực ĐẦY ĐỦ 6 hàm** trên dữ liệu `corpus.json` bằng Python thuần (không SQL): `search` lọc theo `is_active(as_of)` + `visibility` nếu mode=public + khớp từ khóa đơn giản; `find_conflicts` so `metric_value` các clause cùng `topic` cùng hiệu lực; `expand_references` theo cạnh REFERENCES; `version_timeline` theo chuỗi SUPERSEDES; `export_graph` trả `{nodes, edges}`.
3. **Một handle repository dùng chung.** App khởi tạo repository **một lần** (factory `get_repository()`), lưu ở `app.state.repo`; không tạo lại mỗi request. Kiểu khai báo là `Repository` (Protocol), không phải `StubRepository` cụ thể.
4. **Không SQL ngoài repository.** `api/` và `pipeline/` chỉ import `Repository`/`Clause`/`ConflictPair`; grep không thấy `psycopg`/`SELECT` ngoài `kb/`. (AD-7, AD-12)
5. **Swap-ready.** Đổi stub → Postgres chỉ sửa **một chỗ** trong factory; chữ ký hàm không đổi. Ghi chú rõ trong code chỗ cần đổi.
6. **as-of + visibility đi xuống repository.** Pipeline/API truyền `as_of`/`mode` vào `repository.search`; KHÔNG tự lọc hiệu lực/visibility ở tầng trên (tránh trùng logic với AD-5/AD-11).

## Tasks / Subtasks

- [x]**Task 1 — Khóa hợp đồng dữ liệu** (AC: 1)
  - [x]UPDATE `kb/models.py`: thêm dataclass `ConflictPair {clause_a: Clause, clause_b: Clause, topic: str, value_a, value_b, unit}` (giữ nguyên `Clause`, `Source`)
  - [x]NEW `kb/repository_protocol.py`: `class Repository(Protocol)` khai báo 6 hàm + docstring + kiểu trả về (dùng `typing.Protocol`)
- [x]**Task 2 — Hiện thực StubRepository đầy đủ** (AC: 2, 6)
  - [x]UPDATE `kb/repository.py`: mở rộng `StubRepository` hiện đủ 6 hàm (giữ `from_corpus`, `clause_count`)
  - [x]`is_active(clause, as_of)` là **một hàm dùng chung** trong `kb/` (AD-5), mọi hàm gọi lại nó
  - [x]`search`: lọc active + visibility (mode=public) + khớp từ khóa (lowercase, bỏ dấu đơn giản), `score∈[0,1]`
  - [x]`find_conflicts`: cùng `topic`, cùng active, `metric_value` khác nhau → `ConflictPair`
  - [x]`expand_references`, `version_timeline`, `export_graph`, `insert_document`
- [x]**Task 3 — Factory + wiring dùng chung** (AC: 3, 4, 5)
  - [x]NEW `kb/factory.py`: `get_repository() -> Repository` (hiện trả `StubRepository.from_corpus(...)`; **comment rõ**: đổi sang `PostgresRepository` khi Epic 0 xong)
  - [x]UPDATE `api/main.py`: lifespan gọi `get_repository()`, `app.state.repo` khai kiểu `Repository`
- [x]**Task 4 — Test** (AC: 2, 6)
  - [x]`search` với as_of hôm nay: `TT41/Điều 6.3` (8%, hết hạn) KHÔNG có, `TT22/Điều 1` (9%) CÓ
  - [x]`search` mode=public: không trả clause `internal` (`QD-INT/Điều 2`)
  - [x]`find_conflicts` hôm nay: phát hiện cặp `TT22/Điều 1` (9%) vs `QD-INT/Điều 2` (8%)
  - [x]`expand_references(["TT41/Điều 10"])` trả `TT41/Điều 6.3`
  - [x]`version_timeline("TT22/Điều 1")` gồm cả bản cũ 8%

## Dev Notes

### Bối cảnh từ Story 1.1 (đã làm — đọc kỹ để không dựng lại)
- ✅ `kb/models.py` đã có `Clause` (frozen dataclass) + `Source`. **Giữ nguyên `Clause`** — đây là khóa hợp đồng. Chỉ THÊM `ConflictPair`.
- ✅ `kb/repository.py` đã có `StubRepository` với `from_corpus/clause_count/doc_title/any_clause` + `CorpusNotFoundError` + `_parse_clause`. **Mở rộng, không viết lại.**
- ✅ `api/main.py` dùng `app.state.repo = StubRepository.from_corpus(...)` trong lifespan (factory `create_app`). Story này chuyển sang gọi `get_repository()`.
- ✅ Test ở `backend/tests/test_api.py` (pytest + TestClient). 3 test đang pass — **không được làm hỏng** (regression).
- ✅ `_parse_clause` đã map `metric.value/unit` → `Clause.metric_value/metric_unit`. Dùng lại cho `find_conflicts`.

### Chữ ký interface (khóa — Epic 0 phải khớp)
```python
class Repository(Protocol):
    def search(self, q: str, as_of: date, mode: str = "system") -> list[Clause]: ...
    def expand_references(self, clause_ids: list[str]) -> list[Clause]: ...
    def find_conflicts(self, as_of: date) -> list[ConflictPair]: ...
    def version_timeline(self, clause_id: str) -> list[Clause]: ...
    def export_graph(self) -> dict: ...   # {"nodes":[...], "edges":[...]}
    def insert_document(self, doc: dict, clauses: list[dict], edges: list[dict]) -> None: ...
```

### Guardrail kiến trúc
- **AD-12 (mấu chốt story này):** repository là **ranh giới truy cập dữ liệu duy nhất**. `api`/`pipeline` không import psycopg, không viết SQL. Stub và Postgres cùng Protocol.
- **AD-7:** `api → pipeline → repository`; tầng dưới không import tầng trên.
- **AD-5:** một hàm `is_active(clause, as_of)` duy nhất; `eff <= as_of AND (exp IS NULL OR as_of < exp)`.
- **AD-11:** lọc visibility trong `search` (không ở tầng trên).
- **AD-2:** stub nạp corpus một lần; handle dùng chung (chưa cần connection pool vì là in-memory — nhưng khai kiểu `Repository` để bản Postgres cắm pool vào).
- [Source: ARCHITECTURE-SPINE.md#AD-2,AD-5,AD-7,AD-11,AD-12]

### File sẽ chạm
| File | NEW/UPDATE |
|---|---|
| `kb/models.py` | UPDATE (thêm `ConflictPair`) |
| `kb/repository_protocol.py` | NEW (`Repository` Protocol) |
| `kb/repository.py` | UPDATE (stub đủ 6 hàm + `is_active`) |
| `kb/factory.py` | NEW (`get_repository()` — điểm swap) |
| `api/main.py` | UPDATE (dùng factory, khai kiểu `Repository`) |
| `backend/tests/test_repository.py` | NEW (test 6 hàm) |

### Phạm vi — KHÔNG làm quá
Story này dựng **interface + stub logic + wiring**. **KHÔNG** dựng các stage pipeline `retrieve/expand/...` như module riêng (đó là Story 1.3+, chúng chỉ *gọi* repository). Không đụng LLM (Story 1.5). Không đụng frontend.

### Dữ liệu test có sẵn (từ `corpus.json`)
- Bẫy số: `TT41/Điều 6.3` (8%, exp 2023-01-01) → `TT22/Điều 1` (9%, exp null)
- Thay thế một phần: `TT41/Điều 8.2` (hết hạn) / `TT41/Điều 8.1` (còn)
- Dẫn chiếu: `TT41/Điều 10` → `TT41/Điều 6.3`
- Xung đột: `TT22/Điều 1` (9%, public) vs `QD-INT/Điều 2` (8%, internal) — cùng topic `ty_le_an_toan_von`

### Testing standards
- pytest; test repository trực tiếp (không cần TestClient). Đặt `backend/tests/test_repository.py`.
- Chạy `cd backend && source .venv/bin/activate && python -m pytest` — phải giữ 3 test cũ pass + thêm test mới.

### References
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.2 + Ranh giới bàn giao Epic 0]
- [Source: _bmad-output/planning-artifacts/architecture/.../ARCHITECTURE-SPINE.md#AD-12]
- [Source: backend/kb/models.py, backend/kb/repository.py, backend/api/main.py (Story 1.1)]
- [Source: data/sample/corpus.json]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (cc/claude-opus-4-8) — bmad-dev-story

### Debug Log References

- `pytest` (backend): **10 passed** (3 cũ Story 1.1 + 7 mới) — không regression.
- Test repository bám dữ liệu mẫu: search lọc 8% (hết hạn)/giữ 9%, public loại internal, conflict TT22 vs QD-INT, expand Điều 10→6.3, timeline 6.3 trước 1.

### Completion Notes List

- **Hợp đồng khóa (AD-12):** `kb/repository_protocol.py` — `Repository` Protocol 6 hàm; `kb/models.py` thêm `ConflictPair`. `Clause` giữ nguyên (không phá hợp đồng Story 1.1).
- **StubRepository đủ 6 hàm** trên corpus RAM: `search` (lọc `is_active` + visibility + khớp từ khóa bỏ dấu), `expand_references`, `find_conflicts` (so `metric_value` cùng topic), `version_timeline` (chuỗi SUPERSEDES, theo thời gian), `export_graph` (`{nodes,edges}`), `insert_document`.
- **`is_active` là hàm DUY NHẤT** trong `kb/repository.py` (AD-5), có test cho ca `expiry_date=null` và ca hết hạn.
- **Điểm swap duy nhất:** `kb/factory.py::get_repository()` — có comment rõ chỗ đổi sang `PostgresRepository` khi Epic 0.4 xong. `api/main.py` dùng factory, khai kiểu `Repository` (không phụ thuộc lớp stub).
- **AD-7/AD-12:** không import psycopg/SQL ngoài `kb/`. `api` chỉ import `get_repository` + `Repository`.
- Phạm vi giữ đúng: KHÔNG dựng stage pipeline (Story 1.3+), không LLM, không FE. Endpoint `/api/chat` vẫn là green-pipe stub (helper `any_clause` ngoài Protocol, sẽ thay bằng `search` ở Story 1.5).

### File List

NEW:
- `backend/kb/repository_protocol.py`
- `backend/kb/factory.py`
- `backend/tests/test_repository.py`

UPDATE:
- `backend/kb/models.py` (thêm `ConflictPair`)
- `backend/kb/repository.py` (mở rộng `StubRepository` đủ 6 hàm + `is_active` + `_norm`)
- `backend/api/main.py` (dùng `get_repository`, khai kiểu `Repository`)

## Change Log

- 2026-07-17: Story 1.2 — khóa interface `Repository` (Protocol) + `StubRepository` đầy đủ trên corpus + factory swap-ready + wire app. 10 test pass. Status → review.
