import os
import sys
import json
from datetime import datetime, date
from sqlmodel import Session, select

# Add root folder to sys.path to enable backend imports
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.api.database import init_db, engine
from backend.api.models import Document, Clause, Edge, ClauseEmbedding, AuditLog
from backend.kb.vector_helper import get_text_embedding

def parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None

def seed_database():
    print("Initializing database schemas and tables...")
    init_db()
    
    corpus_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sample", "corpus.json")
    if not os.path.exists(corpus_path):
        print(f"Error: Sample data not found at {corpus_path}")
        return
        
    with open(corpus_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    session = Session(engine)
    
    # 1. Seed Documents to dwh
    print("Seeding Documents to dwh...")
    for doc_data in data.get("documents", []):
        existing = session.get(Document, doc_data["doc_code"])
        if not existing:
            doc = Document(
                doc_code=doc_data["doc_code"],
                title=doc_data["title"],
                type=doc_data["type"],
                issuer=doc_data["issuer"],
                issue_date=parse_date(doc_data.get("issue_date")),
                effective_date=parse_date(doc_data["effective_date"]),
                visibility=doc_data["visibility"],
                status="active",
                department=doc_data.get("department", "phap_ly")
            )
            session.add(doc)
    session.commit()
    
    # 2. Seed Clauses and their Embeddings to dwh and vector_store
    print("Seeding Clauses to dwh...")
    for clause_data in data.get("clauses", []):
        existing = session.get(Clause, clause_data["clause_id"])
        if not existing:
            metric_data = clause_data.get("metric")
            metric_value = metric_data.get("value") if metric_data else None
            metric_unit = metric_data.get("unit") if metric_data else None
            
            clause = Clause(
                clause_id=clause_data["clause_id"],
                doc_code=clause_data["doc_code"],
                path=clause_data["path"],
                text=clause_data["text"],
                effective_date=parse_date(clause_data["effective_date"]),
                expiry_date=parse_date(clause_data.get("expiry_date")),
                topic=clause_data["topic"],
                visibility=clause_data["visibility"],
                status="active",
                metric_value=metric_value,
                metric_unit=metric_unit,
                department=clause_data.get("department", "phap_ly")
            )
            session.add(clause)
            
            # Seed embedding to vector_store
            embedding = get_text_embedding(clause_data["text"])
            clause_emb = ClauseEmbedding(
                clause_id=clause_data["clause_id"],
                embedding=embedding
            )
            session.add(clause_emb)
            
    session.commit()
    
    # 3. Seed Edges to dwh
    print("Seeding Edges to dwh...")
    for edge_data in data.get("edges", []):
        # Verify both clauses exist in DB first to satisfy foreign key constraints
        from_clause = session.get(Clause, edge_data["from"])
        to_clause = session.get(Clause, edge_data["to"])
        if not from_clause or not to_clause:
            print(f"Skipping edge {edge_data['from']} -> {edge_data['to']} due to missing clause(s).")
            continue
            
        statement = select(Edge).where(
            Edge.from_clause == edge_data["from"],
            Edge.to_clause == edge_data["to"],
            Edge.type == edge_data["type"]
        )
        existing = session.exec(statement).first()
        if not existing:
            edge = Edge(
                from_clause=edge_data["from"],
                to_clause=edge_data["to"],
                type=edge_data["type"],
                note=edge_data.get("note")
            )
            session.add(edge)
            
    # 4. Write audit log entry
    log = AuditLog(
        job="SEED_DATABASE",
        flag=1,
        schema_name="staging"
    )
    session.add(log)
    
    session.commit()
    session.close()
    print("Database seeding completed successfully!")

if __name__ == "__main__":
    seed_database()
