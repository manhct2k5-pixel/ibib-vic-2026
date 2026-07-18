import os
import sys
from datetime import date
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlmodel import Session, select

# Add root folder to sys.path to enable backend imports
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.kb.kb import KnowledgeBase
from backend.pipeline.pipeline import run_pipeline
from backend.api.database import init_db, engine
from backend.api.models import Document, Clause, Edge, ClauseEmbedding, StagingExternal, StagingInternal, AuditLog
from backend.ingest.extractor import process_pdf_ingestion
from backend.kb.vector_helper import get_text_embedding

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

class ChatRequest(BaseModel):
    question: str
    asOf: Optional[str] = None
    mode: Optional[str] = "system"  # "system" | "baseline"
    role: Optional[str] = "employee"  # "employee" | "customer"
    audience: Optional[str] = None   # alias for role / access control
    department: Optional[str] = None # "tin_dung" | "quan_ly_rui_ro" | "phap_ly"

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
        
    try:
        response = run_pipeline(
            question=req.question,
            as_of_str=as_of_str,
            mode=req.mode or "system",
            role=target_role,
            kb=current_kb,
            department=req.department
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
