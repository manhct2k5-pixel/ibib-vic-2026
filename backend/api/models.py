from datetime import date, datetime, timedelta, timezone
from typing import Optional, List
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, String
from pgvector.sqlalchemy import Vector

# --- VIETNAM TIMEZONE UTILITIES ---
def current_vietnam_time() -> datetime:
    return datetime.now(timezone(timedelta(hours=7)))

def current_unix_seconds() -> int:
    return int(datetime.now().timestamp())

# --- DWH SCHEMA (MASTER APPROVED DATA + VECTOR SEARCH INDEX) ---
class Document(SQLModel, table=True):
    __tablename__ = "van_ban"
    __table_args__ = {"schema": "dwh"}
    
    doc_code: str = Field(primary_key=True)
    title: str
    type: str  # Luật, NghiDinh, ThongTu, QuyetDinh, Basel, QuyTrinhNoiBo
    issuer: str  # NHNN, ChinhPhu, SHB
    issue_date: Optional[date] = None
    effective_date: date
    visibility: str = Field(default="public")  # public, internal
    status: str = Field(default="active")  # active, draft
    department: str = Field(default="phap_ly")  # tin_dung, quan_ly_rui_ro, phap_ly

class Clause(SQLModel, table=True):
    __tablename__ = "dieu_khoan"
    __table_args__ = {"schema": "dwh"}
    
    clause_id: str = Field(primary_key=True)  # e.g., TT39/Điều 8.5
    doc_code: str = Field(foreign_key="dwh.van_ban.doc_code")
    path: str  # e.g., Điều 8.5
    text: str
    effective_date: date
    expiry_date: Optional[date] = None
    topic: str
    visibility: str = Field(default="public")  # public, internal
    status: str = Field(default="active")  # active, draft
    metric_value: Optional[float] = None
    metric_unit: Optional[str] = None
    department: str = Field(default="phap_ly")  # tin_dung, quan_ly_rui_ro, phap_ly

class ClauseEmbedding(SQLModel, table=True):
    __tablename__ = "anh_xa"
    __table_args__ = {"schema": "dwh"}  # Resides in dwh schema alongside clauses!
    
    clause_id: str = Field(primary_key=True, foreign_key="dwh.dieu_khoan.clause_id")
    # Store 768-dimension vector embeddings
    embedding: List[float] = Field(sa_column=Column(Vector(768)))

class Edge(SQLModel, table=True):
    __tablename__ = "qh_dkhoan"
    __table_args__ = {"schema": "dwh"}
    
    id: Optional[int] = Field(default=None, primary_key=True)
    from_clause: str = Field(foreign_key="dwh.dieu_khoan.clause_id")
    to_clause: str = Field(foreign_key="dwh.dieu_khoan.clause_id")
    type: str  # AMENDS, SUPERSEDES, REFERENCES, GUIDES
    note: Optional[str] = None

# --- STAGING SCHEMA (RAW / DRAFT INGEST LAYER + ETL LOGS) ---
class StagingExternal(SQLModel, table=True):
    __tablename__ = "van_ban_ngoai"
    __table_args__ = {"schema": "staging"}
    
    clause_id: str = Field(primary_key=True)
    doc_code: str
    doc_title: str
    doc_type: str
    issuer: str
    effective_date: date
    path: str
    text: str
    topic: str
    visibility: str = Field(default="public")
    status: str = Field(default="draft")
    metric_value: Optional[float] = None
    metric_unit: Optional[str] = None
    expiry_date: Optional[date] = None
    department: str = Field(default="phap_ly")  # tin_dung, quan_ly_rui_ro, phap_ly

class StagingInternal(SQLModel, table=True):
    __tablename__ = "quy_che_noi_bo"
    __table_args__ = {"schema": "staging"}
    
    clause_id: str = Field(primary_key=True)
    doc_code: str
    doc_title: str
    doc_type: str
    issuer: str
    effective_date: date
    path: str
    text: str
    topic: str
    visibility: str = Field(default="internal")
    status: str = Field(default="draft")
    metric_value: Optional[float] = None
    metric_unit: Optional[str] = None
    expiry_date: Optional[date] = None
    department: str = Field(default="phap_ly")  # tin_dung, quan_ly_rui_ro, phap_ly

class AuditLog(SQLModel, table=True):
    __tablename__ = "etl_log"
    __table_args__ = {"schema": "staging"}  # Resides in staging schema as operational logs!
    
    id: Optional[int] = Field(default=None, primary_key=True)
    job: str
    runtime_unix: int = Field(default_factory=current_unix_seconds)
    runtime_timestamp: datetime = Field(default_factory=current_vietnam_time)
    from_unix: Optional[int] = None
    to_unix: Optional[int] = None
    from_timestamp: Optional[datetime] = None
    to_timestamp: Optional[datetime] = None
    flag: int = Field(default=1)
    
    # Map class property 'schema_name' to DB column 'schema' to avoid naming conflicts in python
    schema_name: str = Field(default="staging", sa_column=Column("schema", String))
    
    business_date_unix: Optional[int] = None
    business_date: Optional[date] = None
