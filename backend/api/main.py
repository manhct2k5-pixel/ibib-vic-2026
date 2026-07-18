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
from time import perf_counter
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from kb.factory import get_repository
from kb.repository_protocol import Repository
from pipeline.annotate import CandidateView, annotate
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
    audience: str | None = "employee"  # manager|employee|customer


class Source(BaseModel):
    clause_id: str
    name: str
    description: str
    body: str
    effective_date: str
    metric_value: float | None = None
    metric_unit: str | None = None
    is_current: bool = True
    superseded_by: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
    conflictWarning: str | None = None
    requestId: str
    latencyMs: float


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
        # manager/employee thấy nội bộ; vai trò khác chỉ thấy dữ liệu public.
        repo: Repository = app.state.repo
        scope = "all" if audience in {"manager", "employee"} else "public"
        return repo.export_graph(scope)

    @app.post("/api/chat", response_model=ChatResponse)
    def chat(req: ChatRequest) -> ChatResponse:
        started_at = perf_counter()
        request_id = f"req-{uuid4().hex[:12]}"
        repo: Repository = app.state.repo

        # Parse as-of (mặc định hôm nay); sai định dạng -> 400 + detail (AD-6)
        try:
            as_of = date.fromisoformat(req.asOf) if req.asOf else date.today()
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="asOf phải theo định dạng YYYY-MM-DD.",
            )

        # manager/employee thấy nội bộ; mọi giá trị lạ/None → public (AD-11).
        scope = "all" if req.audience in {"manager", "employee"} else "public"
        # Baseline (RAG thường) vs system: benchmark dùng chung pipeline (AD-3).
        is_baseline = req.mode == "baseline"
        clauses = gather_candidates(repo, req.question, as_of, scope, req.mode or "system")

        if not clauses:
            return ChatResponse(
                answer="Không tìm thấy điều khoản còn hiệu lực phù hợp với câu hỏi.",
                sources=[],
                conflictWarning=None,
                requestId=request_id,
                latencyMs=round((perf_counter() - started_at) * 1000, 2),
            )

        # Baseline KHÔNG có trí tuệ temporal: view thô (không đánh dấu thay thế),
        # không conflict — để lộ trung thực điểm yếu RAG thường (NFR-6).
        if is_baseline:
            views = [
                CandidateView(clause=c, is_current=True, superseded_by=None)
                for c in clauses
            ]
        else:
            views = annotate(repo, clauses, as_of, scope)

        # answer = LLM tổng hợp từ các điều khoản đã annotate (AD-7).
        # LLM thật lỗi/timeout → rơi về MockLLM để demo không sập (NFR-3, AD-9, P1).
        try:
            answer = synthesize(get_llm(), req.question, views, req.audience or "employee")
        except Exception:  # noqa: BLE001 — chủ đích: mọi lỗi LLM đều fallback
            answer = synthesize(MockLLM(), req.question, views, req.audience or "employee")

        # Stage conflict_check (AD-3): cảnh báo nếu có 2 quy định cùng hiệu lực
        # mâu thuẫn số liệu ở chủ đề candidate (không rò internal khi customer).
        # Baseline không có stage này (RAG thường không biết cảnh báo).
        conflict_warning = (
            None if is_baseline else check_conflicts(repo, clauses, as_of, scope)
        )

        sources = [
            Source(
                clause_id=v.clause.clause_id,
                name=f"{v.clause.doc_code} — {v.clause.path}",
                description=v.clause.body,
                body=v.clause.body,
                effective_date=v.clause.effective_date.isoformat(),
                metric_value=v.clause.metric_value,
                metric_unit=v.clause.metric_unit,
                is_current=v.is_current,
                superseded_by=v.superseded_by,
            )
            for v in views
        ]
        return ChatResponse(
            answer=answer,
            sources=sources,
            conflictWarning=conflict_warning,
            requestId=request_id,
            latencyMs=round((perf_counter() - started_at) * 1000, 2),
        )

    return app


# Cho uvicorn: `cd backend && uvicorn api.main:app --reload --port 8000`
app = create_app()
