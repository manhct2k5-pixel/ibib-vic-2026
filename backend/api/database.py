import os
from sqlmodel import create_engine, SQLModel, Session, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/compliance_db"

engine = create_engine(DATABASE_URL, echo=False)

def init_db():
    try:
        with engine.connect() as conn:
            # 1. Enable pgvector extension
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            
            # 2. Create dwh and staging schemas
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS dwh;"))
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS staging;"))
            
            conn.commit()
            print("Database schemas (dwh, staging) and pgvector initialized successfully.")
    except Exception as e:
        print(f"Warning: Failed to initialize schemas: {e}")
        
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
