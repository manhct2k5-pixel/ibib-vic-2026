import os
import sys
from datetime import date, datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

# Add root folder to sys.path to enable backend imports
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.kb.kb import KnowledgeBase, tokenize_vietnamese
from backend.pipeline.session_retrieve import retrieve_session

class Candidate(BaseModel):
    clause_id: str
    score: float
    text: str
    doc_code: str
    path: str
    effective_date: date
    expiry_date: Optional[date] = None
    topic: str
    visibility: str
    department: str = "phap_ly"
    metric_value: Optional[float] = None
    metric_unit: Optional[str] = None
    why: Dict[str, Any] = {}

def run_pipeline(
    question: str,
    as_of_str: str,
    mode: str,
    role: str,
    kb: KnowledgeBase,
    department: Optional[str] = None,
    session_clauses: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    # Parse as_of date
    try:
        as_of = datetime.strptime(as_of_str, "%Y-%m-%d").date()
    except Exception:
        as_of = date.today()

    start_time = datetime.now()

    # 1. RETRIEVE STAGE (with department & role filters)
    candidates = retrieve_stage(question, kb, role, department)

    # If mode is baseline, we skip expand and temporal_filter stages
    is_baseline = (mode == "baseline")

    # 2. EXPAND STAGE
    if not is_baseline:
        candidates = expand_stage(candidates, kb, role, department)

    # 2b. SESSION OVERLAY (AD-13): trộn tài liệu đính kèm phiên (không ở baseline —
    # RAG thường không có tài liệu người dùng tự đính kèm). Clause phiên luôn coi
    # là đang hiệu lực (không suy quan hệ liên-văn-bản), không đè clause global.
    session_ids: set = set()
    if session_clauses and not is_baseline:
        session_hits = session_retrieve_stage(
            session_clauses, question, as_of, role
        )
        existing = {c.clause_id for c in candidates}
        for c in session_hits:
            if c.clause_id not in existing:
                candidates.append(c)
                existing.add(c.clause_id)
            session_ids.add(c.clause_id)

    # 3. TEMPORAL FILTER STAGE
    active_candidates = []
    superseded_candidates = []

    if is_baseline:
        # In baseline mode, all candidates are treated as active (no temporal filtering)
        active_candidates = candidates
    else:
        for c in candidates:
            # Clause phiên bỏ qua lọc temporal của KB (không nằm trong clauses_dict).
            if c.clause_id in session_ids or kb.is_active(c.clause_id, as_of):
                active_candidates.append(c)
            else:
                superseded_candidates.append(c)

    # 4. CONFLICT CHECK STAGE
    conflict_warning = None
    if not is_baseline:
        conflict_warning = conflict_check_stage(active_candidates)

    # 5. SYNTHESIZE ADVANCED RESPONSE
    answer_parts = []
    
    # Header: Quyền truy cập
    dept_label = (department or "Tất cả").upper()
    role_label = "NHÂN VIÊN" if role in ("employee", "staff") else "KHÁCH HÀNG"
    answer_parts.append(f"ℹ️ [PHÂN QUYỀN HỆ THỐNG]: Vai trò: {role_label} | Phòng ban: {dept_label} | Mốc thời gian đối soát: {as_of}")
    answer_parts.append("-" * 60)

    # Cảnh báo rà soát xung đột nếu có
    if conflict_warning:
        answer_parts.append(f"⚠️ CẢNH BÁO RÀ SOÁT TUÂN THỦ:\n{conflict_warning}\n")

    # Nội dung trả lời chính
    if active_candidates:
        answer_parts.append("📌 CÁC QUY ĐỊNH ĐANG ÁP DỤNG TRONG HỆ THỐNG:")
        for idx, c in enumerate(active_candidates, 1):
            source_info = f"({c.clause_id} - Hiệu lực từ: {c.effective_date})"
            dept_info = f" [Phòng ban: {c.department.upper()}]"
            answer_parts.append(f"\n{idx}. {c.text} {source_info}{dept_info}")
    else:
        answer_parts.append("❌ Không tìm thấy điều khoản pháp lý nào đang hiệu lực phù hợp để trả lời câu hỏi.")

    # Cảnh báo các văn bản hết hiệu lực hoặc bị thay thế liên quan đến chủ đề câu hỏi
    if superseded_candidates:
        answer_parts.append("\n" + "=" * 40)
        answer_parts.append("⚠️ THÔNG TIN LỊCH SỬ (Đã hết hiệu lực / bị thay thế):")
        for c in superseded_candidates:
            expiry_label = f"hết hiệu lực ngày {c.expiry_date}" if c.expiry_date else "được thay thế"
            answer_parts.append(f"• [{c.clause_id}]: {c.text[:150]}... ({expiry_label})")

    answer = "\n".join(answer_parts)

    # 6. COMPILE SOURCES FOR RESPONSE
    sources = compile_sources(active_candidates, superseded_candidates, kb, is_baseline)

    latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)

    return {
        "answer": answer,
        "sources": sources,
        "conflictWarning": conflict_warning,
        "requestId": f"req-{int(datetime.now().timestamp())}",
        "latencyMs": latency_ms
    }

def retrieve_stage(question: str, kb: KnowledgeBase, role: str, department: Optional[str] = None) -> List[Candidate]:
    if not kb.bm25 or not kb.indexed_clause_ids:
        return []

    tokens = tokenize_vietnamese(question)
    scores = kb.bm25.get_scores(tokens)

    # Find min and max for normalization
    min_s = min(scores) if len(scores) > 0 else 0.0
    max_s = max(scores) if len(scores) > 0 else 1.0
    range_s = max_s - min_s if max_s != min_s else 1.0

    candidates = []
    for idx, score in enumerate(scores):
        clause_id = kb.indexed_clause_ids[idx]
        clause = kb.clauses_dict[clause_id]

        # 1. Access Control (Personalization & Permission Levels)
        # - Customer: Can only see public clauses.
        # - Staff (phap_ly / Legal & Compliance): Can see everything (internal + public) across all departments.
        # - Staff (others like tin_dung, quan_ly_rui_ro): Can see public clauses + internal clauses of their own department.
        #   Internal clauses of other departments are strictly hidden.
        if role == "customer":
            if clause.visibility == "internal":
                continue
        elif role in ("employee", "staff"):
            # Enforce department access restrictions if department is specified
            if department and department != "phap_ly":
                # Check department field (default to phap_ly if not present)
                c_dept = getattr(clause, "department", "phap_ly")
                if clause.visibility == "internal" and c_dept != department:
                    continue

        norm_score = (score - min_s) / range_s
        # Keep only candidates with a positive match score
        if norm_score > 0.01:
            candidates.append(
                Candidate(
                    clause_id=clause.clause_id,
                    score=norm_score,
                    text=clause.text,
                    doc_code=clause.doc_code,
                    path=clause.path,
                    effective_date=clause.effective_date,
                    expiry_date=clause.expiry_date,
                    topic=clause.topic,
                    visibility=clause.visibility,
                    department=getattr(clause, "department", "phap_ly"),
                    metric_value=clause.metric_value,
                    metric_unit=clause.metric_unit,
                    why={"stage": "retrieve", "raw_score": float(score)}
                )
            )

    # Sort by score descending and take top 8 candidates
    candidates.sort(key=lambda x: x.score, reverse=True)
    return candidates[:8]

def expand_stage(
    candidates: List[Candidate], 
    kb: KnowledgeBase, 
    role: str, 
    department: Optional[str] = None
) -> List[Candidate]:
    expanded = list(candidates)
    existing_ids = {c.clause_id for c in candidates}

    # Traverse REFERENCES and GUIDES edges
    for c in candidates:
        if c.clause_id in kb.graph:
            for u, v, data in kb.graph.edges(c.clause_id, data=True):
                edge_type = data.get("type")
                if edge_type in ("REFERENCES", "GUIDES"):
                    if v not in existing_ids:
                        ref_clause = kb.clauses_dict.get(v)
                        if ref_clause:
                            # Apply the same Access Control rules during graph expansion
                            if role == "customer":
                                if ref_clause.visibility == "internal":
                                    continue
                            elif role in ("employee", "staff"):
                                if department and department != "phap_ly":
                                    c_dept = getattr(ref_clause, "department", "phap_ly")
                                    if ref_clause.visibility == "internal" and c_dept != department:
                                        continue

                            expanded.append(
                                Candidate(
                                    clause_id=ref_clause.clause_id,
                                    score=c.score * 0.8,
                                    text=ref_clause.text,
                                    doc_code=ref_clause.doc_code,
                                    path=ref_clause.path,
                                    effective_date=ref_clause.effective_date,
                                    expiry_date=ref_clause.expiry_date,
                                    topic=ref_clause.topic,
                                    visibility=ref_clause.visibility,
                                    department=getattr(ref_clause, "department", "phap_ly"),
                                    metric_value=ref_clause.metric_value,
                                    metric_unit=ref_clause.metric_unit,
                                    why={"stage": "expand", "referenced_by": c.clause_id}
                                )
                            )
                            existing_ids.add(v)
    return expanded

def session_retrieve_stage(
    session_clauses: List[Any],
    question: str,
    as_of: date,
    role: str,
) -> List[Candidate]:
    """Khớp từ khóa tài liệu phiên → Candidate (AD-13). Đánh dấu why.stage=session."""
    hits = retrieve_session(session_clauses, question, as_of, role)
    out: List[Candidate] = []
    for c in hits:
        out.append(
            Candidate(
                clause_id=c.clause_id,
                score=0.5,
                text=c.text,
                doc_code=c.doc_code,
                path=c.path,
                effective_date=c.effective_date,
                expiry_date=c.expiry_date,
                topic=c.topic,
                visibility=c.visibility,
                department=getattr(c, "department", "phap_ly"),
                metric_value=c.metric_value,
                metric_unit=c.metric_unit,
                why={"stage": "session", "source": "attached_document"},
            )
        )
    return out

def conflict_check_stage(active_candidates: List[Candidate]) -> Optional[str]:
    # Group by topic (skip empty/default topics)
    by_topic: Dict[str, List[Candidate]] = {}
    for c in active_candidates:
        if c.topic and c.topic.strip():
            by_topic.setdefault(c.topic, []).append(c)

    # Scan for conflicting metric values in the same topic
    for topic, clauses in by_topic.items():
        if len(clauses) > 1:
            with_metrics = [c for c in clauses if c.metric_value is not None]
            if len(with_metrics) > 1:
                first_metric = with_metrics[0].metric_value
                for c in with_metrics[1:]:
                    if c.metric_value != first_metric:
                        c1 = with_metrics[0]
                        c2 = c
                        return (
                            f"Phát hiện quy định xung đột về chủ đề '{topic}':\n"
                            f"• {c1.clause_id} ({c1.visibility.upper()} - Phòng ban: {c1.department.upper()}) quy định: {c1.metric_value} {c1.metric_unit or ''}\n"
                            f"• {c2.clause_id} ({c2.visibility.upper()} - Phòng ban: {c2.department.upper()}) quy định: {c2.metric_value} {c2.metric_unit or ''}."
                        )
    return None

def compile_sources(
    active_candidates: List[Candidate],
    superseded_candidates: List[Candidate],
    kb: KnowledgeBase,
    is_baseline: bool
) -> List[Dict[str, Any]]:
    sources = []
    added_ids = set()

    # Helper to get document title
    def get_doc_title(doc_code, default_val):
        doc = kb.documents_dict.get(doc_code)
        return doc.title if doc else default_val

    # 1. Add active sources
    for c in active_candidates:
        if c.clause_id not in added_ids:
            doc_title = get_doc_title(c.doc_code, f"Văn bản {c.doc_code}")
            sources.append({
                "name": f"{c.clause_id} — {c.path}",
                "description": f"{doc_title}. Tầm ảnh hưởng: {c.visibility.upper()} | Ban: {c.department.upper()}. Trạng thái: Đang hiệu lực (Mốc: {c.effective_date})",
                "clause_id": c.clause_id,
                "doc_code": c.doc_code,
                "is_current": True,
                "superseded_by": None,
            })
            added_ids.add(c.clause_id)

    # 2. Add superseded sources (only in non-baseline mode)
    if not is_baseline:
        for c in superseded_candidates:
            if c.clause_id not in added_ids:
                doc_title = get_doc_title(c.doc_code, f"Văn bản {c.doc_code}")
                sources.append({
                    "name": f"{c.clause_id} — {c.path}",
                    "description": f"{doc_title}. Tầm ảnh hưởng: {c.visibility.upper()} | Ban: {c.department.upper()}. Trạng thái: Đã hết hiệu lực / Bị thay thế",
                    "clause_id": c.clause_id,
                    "doc_code": c.doc_code,
                    "is_current": False,
                    "superseded_by": next((u for u, _v, d in kb.graph.in_edges(c.clause_id, data=True) if d.get("type") == "SUPERSEDES"), None) if c.clause_id in kb.graph else None,
                })
                added_ids.add(c.clause_id)

        # Also pull in connected superseded nodes of active nodes
        for c in active_candidates:
            if c.clause_id in kb.graph:
                for u, v, data in kb.graph.in_edges(c.clause_id, data=True):
                    edge_type = data.get("type")
                    if edge_type == "SUPERSEDES":
                        if u not in added_ids:
                            old_clause = kb.clauses_dict.get(u)
                            if old_clause:
                                doc_title = get_doc_title(old_clause.doc_code, f"Văn bản {old_clause.doc_code}")
                                sources.append({
                                    "name": f"{old_clause.clause_id} — {old_clause.path}",
                                    "description": f"{doc_title}. Tầm ảnh hưởng: {old_clause.visibility.upper()} | Ban: {old_clause.department.upper()}. Trạng thái: Đã hết hiệu lực / Bị thay thế",
                                    "clause_id": old_clause.clause_id,
                                    "doc_code": old_clause.doc_code,
                                    "is_current": False,
                                    "superseded_by": c.clause_id,
                                })
                                added_ids.add(old_clause.clause_id)

    return sources
