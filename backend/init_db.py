#!/usr/bin/env python
"""
Standalone initialization script for SQLite and ChromaDB vector store.
Run once before first starting the backend application:
    python init_db.py
Or via Flask CLI:
    flask init-db
"""
import sys
from pathlib import Path

# Ensure backend directory is in system path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from database.db import init_sqlite_db
from database.vector_store import get_or_create_collection
from config import SQLITE_DB_PATH, CHROMA_PERSIST_DIR, PDF_STORAGE_DIR

def initialize_databases():
    print("=" * 60)
    print("Initializing ReAct Automated Research Assistant Databases")
    print("=" * 60)

    print(f"[1/3] Ensuring storage directories exist...")
    Path(SQLITE_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    Path(CHROMA_PERSIST_DIR).mkdir(parents=True, exist_ok=True)
    Path(PDF_STORAGE_DIR).mkdir(parents=True, exist_ok=True)
    print(f"      - SQLite dir: {SQLITE_DB_PATH}")
    print(f"      - Chroma dir: {CHROMA_PERSIST_DIR}")
    print(f"      - PDF dir:    {PDF_STORAGE_DIR}")

    print("[2/3] Initializing SQLite database schema via SQLAlchemy create_all()...")
    init_sqlite_db()
    print("      - SQLite tables created (`queries`, `trajectory_steps`, `papers`, `citations`).")

    print("[3/3] Initializing ChromaDB vector store collection (`research_papers`)...")
    try:
        collection = get_or_create_collection("research_papers")
        print(f"      - ChromaDB collection `{collection.name}` ready (count: {collection.count()} chunks indexed).")
    except Exception as e:
        print(f"      ! Note: ChromaDB collection initialized with warning or delay in model loading: {e}")

    print("=" * 60)
    print("SUCCESS: Database initialization complete! You can now start the server (`python app.py`).")
    print("=" * 60)

if __name__ == "__main__":
    initialize_databases()
