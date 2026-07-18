import os
import sys
import re
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlmodel import Session, select

# Add root folder to sys.path to enable backend imports
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.kb.kb import KnowledgeBase
from backend.pipeline.pipeline import run_pipeline
from backend.api.database import init_db, engine
from backend.api.models import Document, Clause, Edge, ClauseEmbedding, StagingExternal, StagingInternal, AuditLog
from backend.ingest.extractor import process_pdf_ingestion
from backend.kb.vector_helper import get_text_embedding
from backend.pipeline.consolidate import consolidate_document
from backend.pipeline.session_analyze import (
    build_session_analysis,
    build_session_consolidated,
)
from backend.kb.session_store import (
    SessionClause,
    SessionDoc,
    SessionRelation,
    get_session_clauses,
    get_session_docs,
    get_session_relations,
    put_session_clauses,
    put_session_doc,
    remove_session_doc,
)
from backend.ingest.pdf_ingest import clauses_from_text, extract_text
from backend.ingest.doc_analyze import analyze_document, quick_metadata
from backend.providers.llm import get_llm, is_configured

# Initialize database tables on startup
try:
    print("Ensuring database tables exist...")
    init_db()
except Exception as e:
    print(f"Warning: Database tables check failed (might be offline): {e}")

# Load initial KnowledgeBase
try:
    current_kb = KnowledgeBase.load_from_db()
except Exception as e:
    print(f"Warning: Failed to load KnowledgeBase on startup: {e}")
    # Fallback to an empty KnowledgeBase to prevent crash
    current_kb = KnowledgeBase()

app = FastAPI(title="Compliance Copilot API", version="1.0.0")

# Setup CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "clauses": len(current_kb.clauses_dict) if current_kb else 0,
    }


class ChatRequest(BaseModel):
    question: str
    asOf: Optional[str] = None
    mode: Optional[str] = "system"  # "system" | "baseline"
    role: Optional[str] = "employee"  # "employee" | "customer"
    audience: Optional[str] = None   # alias for role / access control
    department: Optional[str] = None # "tin_dung" | "quan_ly_rui_ro" | "phap_ly"
    sessionId: Optional[str] = None  # tài liệu đính kèm phiên (AD-13, Story 7.6)


class PageSummaryRequest(BaseModel):
    title: str = ""
    url: str = ""
    text: str
    question: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    truncated: bool = False


def _local_page_summary(text: str, question: Optional[str] = None) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    sentences = re.split(r"(?<=[.!?;:])\s+", clean)
    useful = []
    seen = set()
    for sentence in sentences:
        sentence = sentence.strip()
        key = sentence.casefold()
        if 45 <= len(sentence) <= 500 and key not in seen:
            useful.append(sentence)
            seen.add(key)
        if len(useful) == 10:
            break
    if not useful:
        return "## Kết quả\n- Không tìm thấy đủ nội dung văn bản phù hợp."
    heading = "## Các đoạn liên quan trên trang" if question else "## Tóm tắt trang"
    return heading + "\n" + "\n".join(f"- {item}" for item in useful)


@app.post("/api/summarize-page")
def summarize_page_endpoint(req: PageSummaryRequest):
    started = datetime.now()
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Trang không có nội dung văn bản có thể đọc.")
    # Giới hạn phía server để tránh một trang bất thường làm cạn bộ nhớ/token.
    text = text[:80_000]
    if is_configured():
        system = (
            "Bạn là trợ lý đọc hiểu tài liệu. Chỉ sử dụng nội dung trang được cung cấp; "
            "không suy diễn hoặc bổ sung dữ kiện bên ngoài. Trả lời bằng Markdown tiếng Việt."
        )
        task = (
            f"Hãy trả lời câu hỏi sau dựa duy nhất trên nội dung trang: {req.question}"
            if req.question
            else "Hãy đọc và tóm tắt trang sau."
        )
        output_format = (
            "## Trả lời\n## Bằng chứng trên trang\n## Nội dung cần kiểm chứng"
            if req.question
            else "## Tóm tắt\n## Ý chính\n## Nghĩa vụ, con số và mốc thời gian\n## Nội dung cần kiểm chứng"
        )
        prompt = f"""{task}

Tiêu đề: {req.title}
URL: {req.url}
Từ khóa đã dùng để thu hẹp phạm vi: {', '.join(req.keywords) or 'Không có'}

Yêu cầu đầu ra:
{output_format}
Nếu phần nào không có dữ liệu, ghi rõ "Không thấy trong nội dung đã đọc".

NỘI DUNG TRANG:
{text}"""
        answer = get_llm().generate(system, prompt, timeout=60.0)
        confidence = "Đã phân tích nội dung trang"
    else:
        answer = _local_page_summary(text, req.question)
        confidence = "Tóm tắt cục bộ"
    warnings = list(dict.fromkeys(req.warnings))
    if req.truncated or len(req.text) > len(text):
        warnings.append("Trang quá dài; kết quả chỉ dựa trên phần nội dung đã trích xuất trong giới hạn 80.000 ký tự.")
    return {
        "answer": answer,
        "sources": [{
            "name": req.title or req.url or "Trang đang xem",
            "description": req.url,
            "body": text[:1_200],
            "url": req.url,
            "is_current": True,
        }],
        "conflictWarning": " ".join(warnings) if warnings else None,
        "confidence": confidence,
        "answerType": "Hỏi đáp theo trang" if req.question else "Tóm tắt trang web",
        "latencyMs": int((datetime.now() - started).total_seconds() * 1000),
    }

@app.get("/api/graph")
def get_graph_endpoint(audience: Optional[str] = "employee"):
    session = Session(engine)
    scope = "all" if audience == "employee" else "public"
    
    # Query all active clauses
    stmt = select(Clause).where(Clause.status == "active")
    if scope == "public":
        stmt = stmt.where(Clause.visibility == "public")
    clauses = session.exec(stmt).all()
    clause_ids = {c.clause_id for c in clauses}
    
    nodes = [
        {
            "id": c.clause_id,
            "doc_code": c.doc_code,
            "path": c.path,
            "topic": c.topic,
            "visibility": c.visibility,
            "expiry_date": c.expiry_date.isoformat() if c.expiry_date else None,
            "department": c.department
        }
        for c in clauses
    ]
    
    # Query edges
    stmt_edges = select(Edge)
    edges_list = session.exec(stmt_edges).all()
    edges = [
        {
            "from": e.from_clause,
            "to": e.to_clause,
            "type": e.type,
            "note": e.note
        }
        for e in edges_list
        if e.from_clause in clause_ids and e.to_clause in clause_ids
    ]
    session.close()
    
    return {"nodes": nodes, "edges": edges}

@app.post("/api/chat")
def chat_endpoint(req: ChatRequest):
    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="Trường 'question' không được để trống.")
    
    # Default to today's date if asOf is not provided
    as_of_str = req.asOf or date.today().strftime("%Y-%m-%d")
    
    # Support both req.audience and req.role (fail-closed)
    target_role = req.audience or req.role or "employee"
    if target_role not in ("employee", "staff"):
        target_role = "customer"
        
    # AD-13: tài liệu đính kèm phiên (không persist) — trộn read-only vào pipeline.
    session_clauses = get_session_clauses(req.sessionId) if req.sessionId else None

    try:
        response = run_pipeline(
            question=req.question,
            as_of_str=as_of_str,
            mode=req.mode or "system",
            role=target_role,
            kb=current_kb,
            department=req.department,
            session_clauses=session_clauses
        )
        return response
    except Exception as e:
        print(f"Error in pipeline execution: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống: {str(e)}")

@app.post("/api/admin/reload")
def reload_endpoint():
    try:
        current_kb.reload_from_db()
        return {
            "message": "Cơ sở dữ liệu tri thức đã được tải lại thành công.",
            "clause_count": len(current_kb.clauses_dict),
            "edge_count": current_kb.graph.number_of_edges()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tải lại thất bại: {str(e)}")

@app.post("/api/admin/ingest-pdf")
def ingest_pdf_endpoint(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận tệp định dạng PDF.")
        
    import tempfile
    import shutil
    
    try:
        # Save upload to a temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
            
        # Process ingestion (extract and save to PostgreSQL in STAGING schema)
        extracted_data = process_pdf_ingestion(tmp_path)
        
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
            
        return {
            "message": "Đã tải lên và bóc tách thành công văn bản nháp vào phân vùng Staging. Đang chờ phê duyệt từ quản trị viên.",
            "document": extracted_data["document"],
            "clause_count": len(extracted_data["clauses"]),
            "edge_count": len(extracted_data["edges"])
        }
    except Exception as e:
        print(f"Error ingesting PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi tải lên và trích xuất PDF: {str(e)}")

@app.get("/api/admin/staging-documents")
def get_staging_documents_endpoint():
    """
    Lists all raw documents waiting for approval in the staging schema (merged from ngoai and noi_bo).
    """
    session = Session(engine)
    external_items = session.exec(select(StagingExternal)).all()
    internal_items = session.exec(select(StagingInternal)).all()
    session.close()
    
    docs_dict = {}
    
    # Process external staging clauses
    for item in external_items:
        if item.doc_code not in docs_dict:
            docs_dict[item.doc_code] = {
                "doc_code": item.doc_code,
                "title": item.doc_title,
                "type": item.doc_type,
                "issuer": item.issuer,
                "effective_date": str(item.effective_date),
                "visibility": "public",
                "status": item.status,
                "clauses_count": 0
            }
        docs_dict[item.doc_code]["clauses_count"] += 1
        
    # Process internal staging clauses
    for item in internal_items:
        if item.doc_code not in docs_dict:
            docs_dict[item.doc_code] = {
                "doc_code": item.doc_code,
                "title": item.doc_title,
                "type": item.doc_type,
                "issuer": item.issuer,
                "effective_date": str(item.effective_date),
                "visibility": "internal",
                "status": item.status,
                "clauses_count": 0
            }
        docs_dict[item.doc_code]["clauses_count"] += 1
        
    return list(docs_dict.values())

@app.post("/api/admin/approve-document/{doc_code}")
def approve_document_endpoint(doc_code: str):
    """
    Promotes a document and its clauses from staging.ngoai/staging.noi_bo to dwh tables,
    computes and stores vector embeddings in dwh.dieu_khoan_vector,
    writes to audit log, and performs hot-reload on the KnowledgeBase.
    """
    session = Session(engine)
    
    # 1. Fetch clauses from staging.ngoai or staging.noi_bo
    ext_clauses = session.exec(select(StagingExternal).where(StagingExternal.doc_code == doc_code)).all()
    int_clauses = session.exec(select(StagingInternal).where(StagingInternal.doc_code == doc_code)).all()
    
    if not ext_clauses and not int_clauses:
        session.close()
        raise HTTPException(status_code=404, detail=f"Không tìm thấy tài liệu nháp '{doc_code}' trong phân vùng Staging.")
        
    is_internal = len(int_clauses) > 0
    staging_clauses = int_clauses if is_internal else ext_clauses
    first_clause = staging_clauses[0]
    
    # 2. Upsert Document in dwh.van_ban
    doc = session.get(Document, doc_code)
    if not doc:
        doc = Document(
            doc_code=first_clause.doc_code,
            title=first_clause.doc_title,
            type=first_clause.doc_type,
            issuer=first_clause.issuer,
            issue_date=None,
            effective_date=first_clause.effective_date,
            visibility=first_clause.visibility,
            status="active",
            department=first_clause.department
        )
        session.add(doc)
    else:
        doc.title = first_clause.doc_title
        doc.type = first_clause.doc_type
        doc.issuer = first_clause.issuer
        doc.effective_date = first_clause.effective_date
        doc.visibility = first_clause.visibility
        doc.status = "active"
        doc.department = first_clause.department
        session.add(doc)
        
    session.commit()
    
    # 3. Upsert Clauses in dwh.dieu_khoan & vector embeddings in dwh.dieu_khoan_vector
    for s_clause in staging_clauses:
        clause = session.get(Clause, s_clause.clause_id)
        if not clause:
            clause = Clause(
                clause_id=s_clause.clause_id,
                doc_code=doc_code,
                path=s_clause.path,
                text=s_clause.text,
                effective_date=s_clause.effective_date,
                expiry_date=s_clause.expiry_date,
                topic=s_clause.topic,
                visibility=s_clause.visibility,
                status="active",
                metric_value=s_clause.metric_value,
                metric_unit=s_clause.metric_unit,
                department=s_clause.department
            )
            session.add(clause)
        else:
            clause.text = s_clause.text
            clause.path = s_clause.path
            clause.effective_date = s_clause.effective_date
            clause.expiry_date = s_clause.expiry_date
            clause.topic = s_clause.topic
            clause.visibility = s_clause.visibility
            clause.status = "active"
            clause.metric_value = s_clause.metric_value
            clause.metric_unit = s_clause.metric_unit
            clause.department = s_clause.department
            session.add(clause)
            
        # Generate & save embedding to dwh.dieu_khoan_vector
        embedding = get_text_embedding(s_clause.text)
        clause_emb = session.get(ClauseEmbedding, s_clause.clause_id)
        if not clause_emb:
            clause_emb = ClauseEmbedding(
                clause_id=s_clause.clause_id,
                embedding=embedding
            )
            session.add(clause_emb)
        else:
            clause_emb.embedding = embedding
            session.add(clause_emb)
            
    # Seed default edges if this is QD312
    if doc_code == "QD312":
        edges_to_create = [
            ("QD312/Điều 1.1", "TT39/Điều 8.5", "AMENDS", "Đính chính cụm từ 'trả nợ khoản nợ vay' thành 'trả nợ khoản cấp tín dụng'"),
            ("QD312/Điều 1.2", "TT39/Điều 8.5", "AMENDS", "Đính chính cụm từ 'dự toán xây dựng công trình' thành 'tổng mức đầu tư xây dựng'"),
            ("QD312/Điều 1.3", "TT39/Điều 8.6", "AMENDS", "Đính chính cụm từ 'trả nợ khoản nợ vay tại tổ chức tín dụng khác' thành 'trả nợ khoản cấp tín dụng tại tổ chức tín dụng khác'"),
            ("QD312/Điều 1.4", "TT39/Điều 29.1.c", "AMENDS", "Sửa đổi điều kiện báo cáo tài chính trong thời gian vay vốn")
        ]
        for from_id, to_id, e_type, note in edges_to_create:
            statement = select(Edge).where(
                Edge.from_clause == from_id,
                Edge.to_clause == to_id,
                Edge.type == e_type
            )
            existing_edge = session.exec(statement).first()
            if not existing_edge:
                edge = Edge(from_clause=from_id, to_clause=to_id, type=e_type, note=note)
                session.add(edge)
                
    # 4. Update approved data status in staging instead of deleting it
    for s_clause in staging_clauses:
        s_clause.status = "approved"
        session.add(s_clause)
        
    # 5. Write Compliance Audit Log
    log = AuditLog(
        job=f"APPROVE_DOCUMENT: {doc_code}",
        flag=1,
        schema_name="staging"
    )
    session.add(log)
    
    session.commit()
    session.close()
    
    # 6. Hot-Reload the KnowledgeBase to apply changes instantly
    try:
        current_kb.reload_from_db()
    except Exception as e:
        print(f"Warning: Failed to reload KnowledgeBase: {e}")
        
    return {"message": f"Duyệt và phát hành thành công văn bản '{doc_code}' lên môi trường vận hành (DWH & Vector Store)."}

@app.get("/api/kb/graph")
def get_kb_graph(role: Optional[str] = "employee"):
    """
    Returns the graph nodes and edges for react-force-graph-2d.
    """
    nodes = []
    edges = []
    
    # Compile nodes based on visibility
    for clause_id, c in current_kb.clauses_dict.items():
        if role == "customer" and c.visibility == "internal":
            continue
            
        nodes.append({
            "id": c.clause_id,
            "label": c.clause_id,
            "text": c.text,
            "doc_code": c.doc_code,
            "path": c.path,
            "effective_date": str(c.effective_date),
            "expiry_date": str(c.expiry_date) if c.expiry_date else None,
            "topic": c.topic,
            "visibility": c.visibility,
            "metric_value": c.metric_value,
            "metric_unit": c.metric_unit
        })
        
    # Compile edges connecting the visible nodes
    visible_node_ids = {n["id"] for n in nodes}
    for u, v, data in current_kb.graph.edges(data=True):
        if u in visible_node_ids and v in visible_node_ids:
            edges.append({
                "source": u,
                "target": v,
                "type": data["type"],
                "note": data.get("note")
            })
            
    return {"nodes": nodes, "edges": edges}

@app.get("/api/kb/timeline/{clause_id}")
def get_clause_timeline(clause_id: str):
    """
    Returns the version history timeline for a clause topic.
    """
    clause = current_kb.clauses_dict.get(clause_id)
    if not clause:
        raise HTTPException(status_code=404, detail="Không tìm thấy điều khoản yêu cầu.")
    
    # Find all clauses sharing the same topic
    topic_clauses = [
        c for c in current_kb.clauses_dict.values()
        if c.topic == clause.topic
    ]
    # Sort chronologically by effective_date
    topic_clauses.sort(key=lambda x: x.effective_date)
    
    timeline = []
    for c in topic_clauses:
        timeline.append({
            "clause_id": c.clause_id,
            "doc_code": c.doc_code,
            "path": c.path,
            "effective_date": str(c.effective_date),
            "expiry_date": str(c.expiry_date) if c.expiry_date else None,
            "text": c.text,
            "visibility": c.visibility,
            "status": "active" if current_kb.is_active(c.clause_id, date.today()) else "superseded"
        })
    return timeline

@app.get("/api/consolidate")
def consolidate_endpoint(
    docCode: str = "",
    asOf: Optional[str] = None,
    audience: Optional[str] = None,
    role: Optional[str] = "employee",
    sessionId: str = "",
):
    """Văn bản hợp nhất của một văn bản gốc (FR-17, Story 7.3).

    Gộp các điều khoản của `docCode`, đánh dấu active/amended/superseded dựa trên
    quan hệ AMENDS/SUPERSEDES + is_active(asOf). `sessionId` → gộp read-only clause
    phiên đính kèm (AD-13). Scope fail-closed: chỉ 'employee'/'staff' thấy internal.
    """
    if not docCode:
        raise HTTPException(status_code=400, detail="Thiếu tham số docCode.")
    try:
        as_of = date.fromisoformat(asOf) if asOf else date.today()
    except ValueError:
        raise HTTPException(
            status_code=400, detail="asOf phải theo định dạng YYYY-MM-DD."
        )
    target_role = audience or role or "employee"
    if target_role not in ("employee", "staff"):
        target_role = "customer"
    session_clauses = get_session_clauses(sessionId) if sessionId else None
    result = consolidate_document(
        current_kb, docCode, as_of, target_role, session_clauses
    )
    if not result["sections"]:
        raise HTTPException(
            status_code=404,
            detail=f"Không tìm thấy điều khoản nào của văn bản '{docCode}'.",
        )
    return result

class SessionUploadRequest(BaseModel):
    sessionId: str
    clauses: List[Dict[str, Any]]  # clause thô; parse lỏng, bỏ qua clause hỏng

def _parse_session_clause(raw: Dict[str, Any]) -> SessionClause:
    """Parse dict thô → SessionClause. Chấp nhận 'text' hoặc 'body'. Ném lỗi nếu thiếu."""
    text = raw.get("text") or raw.get("body")
    doc_code = raw["doc_code"]
    path = raw["path"]
    clause_id = raw.get("clause_id") or f"{doc_code}/{path}"
    eff = raw["effective_date"]
    exp = raw.get("expiry_date")
    if not text or not doc_code or not path:
        raise ValueError("Thiếu trường bắt buộc (text/doc_code/path).")
    return SessionClause(
        clause_id=clause_id,
        doc_code=doc_code,
        path=path,
        text=text,
        effective_date=date.fromisoformat(eff),
        expiry_date=date.fromisoformat(exp) if exp else None,
        topic=raw.get("topic", ""),
        visibility=raw.get("visibility", "public"),
        metric_value=raw.get("metric_value"),
        metric_unit=raw.get("metric_unit"),
        department=raw.get("department", "phap_ly"),
    )

@app.post("/api/session/upload")
def session_upload(req: SessionUploadRequest):
    """Đính kèm tài liệu theo phiên bằng JSON (FR-18, AD-13). KHÔNG persist vào DB.

    Clause hỏng (thiếu field/sai định dạng) bị bỏ qua, báo số nạp được.
    """
    if not req.sessionId:
        raise HTTPException(status_code=400, detail="Thiếu sessionId.")
    parsed: List[SessionClause] = []
    for raw in req.clauses:
        try:
            parsed.append(_parse_session_clause(raw))
        except (KeyError, ValueError, TypeError):
            continue
    total = put_session_clauses(req.sessionId, parsed)
    return {
        "sessionId": req.sessionId,
        "added": len(parsed),
        "skipped": len(req.clauses) - len(parsed),
        "sessionClauses": total,
    }

@app.post("/api/session/upload-pdf")
async def session_upload_pdf(
    sessionId: str = Form(...),
    file: UploadFile = File(...),
    docCode: str = Form(""),
):
    """PDF số → phân tích (metadata + quan hệ liên-văn-bản) + cắt Điều → clause
    phiên (FR-17/FR-18, AD-13). Dùng dữ liệu TỪ FILE UPLOAD, không đụng DB."""
    if not sessionId:
        raise HTTPException(status_code=400, detail="Thiếu sessionId.")
    data = await file.read()
    filename = file.filename or "TAILIEU.pdf"
    text = extract_text(data)

    # NHANH: chỉ cắt Điều + metadata regex, KHÔNG gọi LLM. Phân tích quan hệ (LLM)
    # để dành cho lúc gửi chat qua POST /api/session/analyze.
    meta = quick_metadata(text, filename)
    dc = docCode or meta["doc_code"]
    eff = meta["effective_date"] or date.today()

    clauses = clauses_from_text(text, dc, eff)
    if not clauses:
        raise HTTPException(
            status_code=422,
            detail=(
                "Không trích được điều khoản. PDF có thể là bản scan/ảnh, sai mã "
                "font, hoặc không có cấu trúc 'Điều N'."
            ),
        )
    total = put_session_clauses(sessionId, clauses)

    doc = SessionDoc(
        doc_code=dc,
        title=dc,  # tiêu đề đầy đủ sẽ có sau khi phân tích LLM
        doc_type="",
        issuer="",
        issue_date=None,
        effective_date=eff,
        num_clauses=len(clauses),
        filename=filename,
        raw_text=meta["head"],
        analyzed=False,
    )
    put_session_doc(sessionId, doc, [])

    return {
        "sessionId": sessionId,
        "docCode": dc,
        "added": len(clauses),
        "sessionClauses": total,
        "analyzed": False,
        "chars": len(text),
    }


def _run_analysis(sessionId: str) -> dict:
    """Phân tích LLM TRỄ: doc nào chưa analyzed thì gọi LLM trích quan hệ, rồi dựng
    bản đồ. Gọi lúc gửi chat để 'ấn Gửi mới phân tích'."""
    docs = get_session_docs(sessionId)
    pending = [d for d in docs if not d.analyzed and d.raw_text]
    if pending:
        llm = get_llm()
        for d in pending:
            res = analyze_document(d.raw_text, d.filename, llm)
            d.title = res["title"] or d.doc_code
            d.doc_type = res["doc_type"]
            d.issuer = res["issuer"]
            if res["effective_date"]:
                d.effective_date = res["effective_date"]
            d.analyzed = True
            relations = [
                SessionRelation(
                    from_doc=d.doc_code,
                    to_doc=r["target_doc"],
                    rel_type=r["type"],
                    from_article=None,
                    to_article=r["target_article"],
                    note=r["note"],
                )
                for r in res["relations"]
            ]
            put_session_doc(sessionId, d, relations)
    docs = get_session_docs(sessionId)
    relations = get_session_relations(sessionId)
    result = build_session_analysis(docs, relations)
    result["sessionId"] = sessionId
    return result


@app.post("/api/session/analyze")
def session_analyze(sessionId: str = ""):
    """Chạy phân tích LLM (trích quan hệ) cho tài liệu chưa phân tích, trả bản đồ
    quan hệ + thứ tự đọc + hướng dẫn (FR-17). Gọi khi người dùng gửi câu hỏi."""
    if not sessionId:
        raise HTTPException(status_code=400, detail="Thiếu sessionId.")
    return _run_analysis(sessionId)


@app.get("/api/session/analysis")
def session_analysis(sessionId: str = ""):
    """Đọc bản đồ đã phân tích (KHÔNG chạy LLM). Dùng để hiển thị lại."""
    if not sessionId:
        raise HTTPException(status_code=400, detail="Thiếu sessionId.")
    docs = get_session_docs(sessionId)
    relations = get_session_relations(sessionId)
    result = build_session_analysis(docs, relations)
    result["sessionId"] = sessionId
    return result


@app.get("/api/session/consolidated")
def session_consolidated(sessionId: str = "", asOf: Optional[str] = None):
    """MỘT văn bản hợp nhất TỔNG HỢP quanh văn bản nền của phiên (FR-17): gộp các
    sửa đổi từ những tài liệu khác trong phiên vào bản gốc. KHÔNG chạy LLM."""
    if not sessionId:
        raise HTTPException(status_code=400, detail="Thiếu sessionId.")
    try:
        as_of = date.fromisoformat(asOf) if asOf else date.today()
    except ValueError:
        raise HTTPException(status_code=400, detail="asOf phải theo YYYY-MM-DD.")
    docs = get_session_docs(sessionId)
    relations = get_session_relations(sessionId)
    clauses = get_session_clauses(sessionId)
    result = build_session_consolidated(docs, relations, clauses, as_of)
    if not result.get("docCode"):
        raise HTTPException(
            status_code=404, detail="Chưa có tài liệu để hợp nhất trong phiên."
        )
    result["sessionId"] = sessionId
    return result


@app.delete("/api/session/doc")
def session_remove_doc(sessionId: str = "", docCode: str = ""):
    """Xoá 1 tài liệu đã đính kèm khỏi phiên (metadata + clause + quan hệ)."""
    if not sessionId or not docCode:
        raise HTTPException(status_code=400, detail="Thiếu sessionId hoặc docCode.")
    removed = remove_session_doc(sessionId, docCode)
    if not removed:
        raise HTTPException(
            status_code=404,
            detail=f"Không tìm thấy tài liệu '{docCode}' trong phiên.",
        )
    docs = get_session_docs(sessionId)
    relations = get_session_relations(sessionId)
    analysis = build_session_analysis(docs, relations)
    analysis["sessionId"] = sessionId
    return {"removed": docCode, "remaining": len(docs), "analysis": analysis}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
