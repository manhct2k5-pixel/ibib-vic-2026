---
baseline_commit: f12c67d723f79a905aad1904d0d41343906bb622
---

# Story 1.5: Tổng hợp câu trả lời bằng LLM + trích nguồn

Status: review

## Story

As a nhân viên,
I want câu trả lời tiếng Việt được LLM tổng hợp từ đúng các điều khoản còn hiệu lực, kèm trích nguồn,
so that tôi đọc một câu trả lời mạch lạc thay vì danh sách điều khoản thô — và tin được vì có nguồn.

## Acceptance Criteria

1. **Provider LLM sau interface (AD-7).** `providers/llm.py` có `LLMProvider` Protocol `generate(system, prompt) -> str`, một `MockLLM` (deterministic, KHÔNG gọi mạng) và một `AnthropicLLM` (gọi API thật qua httpx). `get_llm()` trả `AnthropicLLM` nếu có `LLM_API_KEY`, ngược lại `MockLLM`. Key chỉ đọc ở backend (AD-8).
2. **Stage synthesize.** `pipeline/synthesize.py::synthesize(llm, question, views) -> str` dựng prompt yêu cầu: trả lời tiếng Việt, CHỈ dùng điều khoản được cung cấp, trích `clause_id`, và nêu rõ nếu có điều đã bị thay thế. Gọi `llm.generate`.
3. **Nối `/api/chat`.** `answer` = `synthesize(...)` (thay tóm tắt stub Story 1.3). `sources` giữ nguyên (từ Story 1.4, có `isCurrent`/`supersededBy`). Rỗng ứng viên → giữ hành vi "không tìm thấy".
4. **Không có key vẫn chạy (AD-9).** `MockLLM` tạo câu trả lời tiếng Việt từ views (template, deterministic) — dev/test và demo dự phòng chạy được không cần key.
5. **Không rò key.** `AnthropicLLM` không log key; `providers` là nơi duy nhất gọi model (AD-8).

## Tasks / Subtasks

- [x]**Task 1 — Provider LLM** (AC: 1, 4, 5)
  - [x]UPDATE `providers/llm.py`: `LLMProvider` Protocol; `MockLLM.generate` (template từ prompt/views); `AnthropicLLM.generate` (httpx POST Anthropic Messages API, model mới nhất); `get_llm()` factory theo `is_configured()`
- [x]**Task 2 — Stage synthesize** (AC: 2)
  - [x]NEW `pipeline/synthesize.py`: build system+prompt từ `list[CandidateView]` (kèm clause_id, path, body, trạng thái) → `llm.generate`
- [x]**Task 3 — Nối endpoint** (AC: 3)
  - [x]UPDATE `api/main.py`: dùng `synthesize(get_llm(), question, views)` cho `answer`; giữ sources; giữ nhánh rỗng
- [x]**Task 4 — Test (dùng MockLLM, không mạng)**
  - [x]`synthesize` với MockLLM trả chuỗi không rỗng, có nhắc clause_id của nguồn
  - [x]`synthesize` khi có nguồn đã thay thế → chuỗi nhắc "thay thế"
  - [x]`/api/chat` (không key → MockLLM) trả `answer` không rỗng + sources có clause_id
  - [x]`get_llm()` trả MockLLM khi không có key

## Dev Notes

### Bối cảnh (tái dùng)
- ✅ `providers/llm.py` (Story 1.1) đã có `get_api_key()`, `is_configured()` — mở rộng, giữ chúng.
- ✅ `pipeline/annotate.py` cho `list[CandidateView]` (clause + is_current + superseded_by) — synthesize nhận đầu vào này.
- ✅ `api/main.py` endpoint đã có `views = annotate(...)`. Chỉ đổi cách sinh `answer`.
- ✅ httpx đã trong requirements. `date`, HTTPException đã import.
- ✅ 21 test pass — giữ nguyên; test mới KHÔNG gọi mạng (dùng MockLLM).

### Anthropic Messages API (cho AnthropicLLM — KHÔNG test live)
- `POST https://api.anthropic.com/v1/messages`
- Headers: `x-api-key: <LLM_API_KEY>`, `anthropic-version: 2023-06-01`, `content-type: application/json`
- Body: `{model, max_tokens, system, messages:[{role:"user", content: prompt}]}`
- Đọc: `resp.json()["content"][0]["text"]`
- Model: dùng bản Claude mới nhất (VD `claude-sonnet-4-6`); timeout hợp lý (~15s).
- Lỗi mạng/timeout → raise; endpoint để nhánh lỗi trả 500 hoặc rơi về fallback (đường lui demo là mock mode FE, AD-9).

### Prompt (định hướng)
- System: "Bạn là trợ lý pháp lý ngân hàng. CHỈ dùng các điều khoản được cung cấp. Trả lời tiếng Việt, ngắn gọn, trích dẫn clause_id. Nếu một điều đã bị thay thế, nói rõ và ưu tiên bản còn hiệu lực."
- User: câu hỏi + danh sách views (clause_id · path · trạng thái · nội dung).

### Guardrail
- **AD-7/AD-8:** LLM sau provider; key chỉ backend; `pipeline`/`api` không gọi httpx trực tiếp tới Anthropic — chỉ qua `providers`.
- **AD-9:** MockLLM là đường chạy không-key (dev/test); tách khỏi logic pipeline.
- **AD-6:** contract `/api/chat` không đổi (answer vẫn là chuỗi).
- **Phạm vi:** KHÔNG sửa frontend; KHÔNG conflict (Epic 3).
- [Source: ARCHITECTURE-SPINE.md#AD-7,AD-8,AD-9]

### File sẽ chạm
| File | NEW/UPDATE |
|---|---|
| `providers/llm.py` | UPDATE (Protocol + MockLLM + AnthropicLLM + get_llm) |
| `pipeline/synthesize.py` | NEW |
| `api/main.py` | UPDATE (answer = synthesize) |
| `backend/tests/test_synthesize.py` | NEW |

### Testing standards
- pytest; **không gọi mạng** — ép MockLLM (không set key trong test). `cd backend && source .venv/bin/activate && python -m pytest` giữ 21 test cũ pass.

### References
- [Source: epics.md#Story 1.5 (FR-4, FR-6); ARCHITECTURE-SPINE.md#AD-7,AD-8,AD-9]
- [Source: backend/providers/llm.py, backend/pipeline/annotate.py, backend/api/main.py]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (cc/claude-opus-4-8) — bmad-dev-story

### Debug Log References

- `pytest`: **25 passed** (21 cũ + 4 mới), không regression. Test dùng `MockLLM` (không gọi mạng, `LLM_API_KEY` bị xóa qua monkeypatch).

### Completion Notes List

- **Provider LLM (AD-7/8):** `providers/llm.py` — `LLMProvider` Protocol; `MockLLM` (deterministic, không mạng); `AnthropicLLM` (httpx POST Messages API, model `claude-sonnet-4-6`, timeout 15s, không log key); `get_llm()` chọn theo `is_configured()`.
- **Stage synthesize:** `pipeline/synthesize.py` dựng system+prompt từ `list[CandidateView]` (kèm trạng thái đã-thay-thế) → `llm.generate`. Chỉ gọi provider, không httpx trực tiếp.
- **Endpoint:** `answer` = `synthesize(get_llm(), question, views)` thay tóm tắt stub. Sources giữ nguyên (isCurrent/supersededBy từ 1.4). Nhánh rỗng giữ nguyên.
- **Không key vẫn chạy (AD-9):** MockLLM cho dev/test/đường lui; có key thật thì tự gọi Anthropic. **Chưa test live** (không có key trong môi trường) — cần chạy thử với key thật trước demo.
- Phạm vi giữ đúng: KHÔNG sửa frontend (Story 1.6); KHÔNG conflict (Epic 3).

### File List

NEW:
- `backend/pipeline/synthesize.py`
- `backend/tests/test_synthesize.py`

UPDATE:
- `backend/providers/llm.py` (Protocol + MockLLM + AnthropicLLM + get_llm)
- `backend/api/main.py` (answer = synthesize; import synthesize/get_llm; bỏ answer stub)

## Change Log

- 2026-07-17: Story 1.5 — LLM tổng hợp câu trả lời sau provider interface (MockLLM + AnthropicLLM). 25 test pass. Status → review. [Cần chạy thử với LLM_API_KEY thật trước demo.]
