import re
from datetime import date
from typing import List, Dict, Any, Optional
import networkx as nx
from rank_bm25 import BM25Okapi
from sqlmodel import Session, select

from backend.api.database import engine
from backend.api.models import Document, Clause, Edge

def tokenize_vietnamese(text: str) -> List[str]:
    """
    Simple Vietnamese tokenizer: lowercase, remove special characters, and split.
    """
    text = text.lower()
    text = re.sub(r"[^\w\s\-\/\.]", " ", text)
    return text.split()

class KnowledgeBase:
    def __init__(self):
        self.documents_dict: Dict[str, Document] = {}
        self.clauses_dict: Dict[str, Clause] = {}
        self.graph = nx.DiGraph()
        self.bm25: Optional[BM25Okapi] = None
        self.indexed_clause_ids: List[str] = []
        
    @classmethod
    def load_from_db(cls):
        kb = cls()
        kb.reload_from_db()
        return kb
        
    def reload_from_db(self):
        print("Loading KnowledgeBase from PostgreSQL...")
        session = Session(engine)
        
        # Load Documents
        docs = session.exec(select(Document).where(Document.status == "active")).all()
        self.documents_dict = {d.doc_code: d for d in docs}
        
        # Load Clauses
        clauses = session.exec(select(Clause).where(Clause.status == "active")).all()
        self.clauses_dict = {c.clause_id: c for c in clauses}
        
        # Rebuild Graph
        self.graph.clear()
        for clause_id in self.clauses_dict:
            self.graph.add_node(clause_id)
            
        edges = session.exec(select(Edge)).all()
        for edge in edges:
            # Only connect if both clauses are active
            if edge.from_clause in self.clauses_dict and edge.to_clause in self.clauses_dict:
                self.graph.add_edge(
                    edge.from_clause,
                    edge.to_clause,
                    type=edge.type,
                    note=edge.note
                )
                
        # Rebuild BM25 Index
        self.indexed_clause_ids = list(self.clauses_dict.keys())
        corpus = [tokenize_vietnamese(c.text) for c in self.clauses_dict.values()]
        
        if corpus:
            self.bm25 = BM25Okapi(corpus)
        else:
            self.bm25 = None
            
        session.close()
        print(f"Loaded {len(self.documents_dict)} documents, {len(self.clauses_dict)} clauses, and {self.graph.number_of_edges()} relations.")
        
    def is_active(self, clause_id: str, as_of: date) -> bool:
        clause = self.clauses_dict.get(clause_id)
        if not clause:
            return False
            
        # Rule AD-5: effective_date <= as_of AND (expiry_date IS NULL OR as_of < expiry_date)
        if clause.effective_date > as_of:
            return False
        if clause.expiry_date and as_of >= clause.expiry_date:
            return False
            
        return True
