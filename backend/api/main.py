"""FastAPI app — Story 1.1 đường ống xanh.

- Nạp corpus qua repository lúc startup (fail fast — AD-2).
- `POST /api/chat` trả lời STUB đúng contract `docs/architecture/API_CONTRACT.md`
  (AD-6). Pipeline thật (retrieve/temporal/synthesize) sẽ đến ở Story 1.3-1.5.
- CORS cho frontend; key LLM chỉ ở backend (AD-8).
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import date

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from kb.factory import get_repository
from kb.repository_protocol import Repository
from pipeline.annotate import annotate
from pipeline.conflict_check import check_conflicts
from pipeline.query import gather_candidates
from pipeline.synthesize import synthesize
from providers.llm import MockLLM, get_llm

# Nạp backend/.env để LLM_API_KEY thực sự có hiệu lực (P2)
load_dotenv()

FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")


class ChatRequest(BaseModel):
    question: str
    asOf: str | None = None
    mode: str | None = "system"  # benchmark: system|baseline (Epic 4)
    audience: str | None = "employee"  # employee|customer (phạm vi dữ liệu)


class Source(BaseModel):
    clause_id: str
    name: str
    description: str
    is_current: bool = True
    superseded_by: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
    conflictWarning: str | None = None


def create_app(corpus_path: str | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Fail fast: thiếu corpus -> raise, app không khởi động (AD-2).
        # Truy cập dữ liệu chỉ qua repository (AD-12); factory là điểm swap.
        app.state.repo = get_repository(corpus_path)
        yield
        app.state.repo = None

    app = FastAPI(title="Compliance Copilot API", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[FRONTEND_ORIGIN],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict:
        repo: Repository = app.state.repo
        return {"status": "ok", "clauses": repo.clause_count()}

    @app.get("/api/graph")
    def graph(audience: str = "employee") -> dict:
        # Đồ thị tri thức cho trực quan (FR-12). Suy scope từ audience —
        # fail-closed như /api/chat: chỉ 'employee' chính xác mới thấy internal.
        repo: Repository = app.state.repo
        scope = "all" if audience == "employee" else "public"
        return repo.export_graph(scope)

    @app.post("/api/chat", response_model=ChatResponse)
    def chat(req: ChatRequest) -> ChatResponse:
        repo: Repository = app.state.repo

        # Parse as-of (mặc định hôm nay); sai định dạng -> 400 + detail (AD-6)
        try:
            as_of = date.fromisoformat(req.asOf) if req.asOf else date.today()
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="asOf phải theo định dạng YYYY-MM-DD.",
            )

        # Fail-closed: CHỈ 'employee' chính xác mới thấy nội bộ; mọi giá trị
        # khác (sai chính tả, lạ, None) → chỉ dữ liệu công khai (AD-11).
        scope = "all" if req.audience == "employee" else "public"
        clauses = gather_candidates(repo, req.question, as_of, scope)

        if not clauses:
            return ChatResponse(
                answer="Không tìm thấy điều khoản còn hiệu lực phù hợp với câu hỏi.",
                sources=[],
                conflictWarning=None,
            )

        views = annotate(repo, clauses, as_of, scope)

        # answer = LLM tổng hợp từ các điều khoản đã annotate (AD-7).
        # LLM thật lỗi/timeout → rơi về MockLLM để demo không sập (NFR-3, AD-9, P1).
        try:
            answer = synthesize(get_llm(), req.question, views)
        except Exception:  # noqa: BLE001 — chủ đích: mọi lỗi LLM đều fallback
            answer = synthesize(MockLLM(), req.question, views)

        # Stage conflict_check (AD-3): cảnh báo nếu có 2 quy định cùng hiệu lực
        # mâu thuẫn số liệu ở chủ đề candidate (không rò internal khi customer).
        conflict_warning = check_conflicts(repo, clauses, as_of, scope)

        sources = [
            Source(
                clause_id=v.clause.clause_id,
                name=f"{v.clause.doc_code} — {v.clause.path}",
                description=v.clause.body,
                is_current=v.is_current,
                superseded_by=v.superseded_by,
            )
            for v in views
        ]
        return ChatResponse(
            answer=answer, sources=sources, conflictWarning=conflict_warning
        )

    return app


# Cho uvicorn: `cd backend && uvicorn api.main:app --reload --port 8000`
app = create_app()
