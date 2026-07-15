import os
import re
import uuid
import requests
from pathlib import Path
from datetime import datetime, timezone

import pdfplumber
import fitz  # PyMuPDF fallback

from config import PDF_STORAGE_DIR
from database.db import get_session
from database.vector_store import get_or_create_collection
from models.schema import Paper

SECTION_PATTERNS = [
    (re.compile(r'^\s*(\d+(\.\d+)*\s*)?(abstract)\b', re.IGNORECASE), 'Abstract'),
    (re.compile(r'^\s*(\d+(\.\d+)*\s*)?(introduction|background)\b', re.IGNORECASE), 'Introduction'),
    (re.compile(r'^\s*(\d+(\.\d+)*\s*)?(related work|prior work|literature review)\b', re.IGNORECASE), 'Related Work'),
    (re.compile(r'^\s*(\d+(\.\d+)*\s*)?(methodology|methods|approach|model|architecture|proposed method|react framework)\b', re.IGNORECASE), 'Methodology'),
    (re.compile(r'^\s*(\d+(\.\d+)*\s*)?(experiments|evaluation|experimental setup|datasets)\b', re.IGNORECASE), 'Experiments & Setup'),
    (re.compile(r'^\s*(\d+(\.\d+)*\s*)?(results|findings|empirical results|performance|ablation)\b', re.IGNORECASE), 'Results & Discussion'),
    (re.compile(r'^\s*(\d+(\.\d+)*\s*)?(discussion|limitations|future work|analysis)\b', re.IGNORECASE), 'Discussion & Limitations'),
    (re.compile(r'^\s*(\d+(\.\d+)*\s*)?(conclusion|summary|concluding remarks)\b', re.IGNORECASE), 'Conclusion'),
    (re.compile(r'^\s*(\d+(\.\d+)*\s*)?(references|bibliography)\b', re.IGNORECASE), 'References'),
]

def guess_section(line: str, current_section: str) -> str:
    """Guess section header from text line heuristics."""
    clean_line = line.strip()
    if len(clean_line) < 4 or len(clean_line) > 80:
        return current_section
    for pattern, section_name in SECTION_PATTERNS:
        if pattern.match(clean_line):
            return section_name
    return current_section

def extract_text_with_pdfplumber(pdf_path: str) -> list[dict]:
    """Extract page-by-page text using pdfplumber."""
    pages_data = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text and text.strip():
                pages_data.append({"page_number": i + 1, "text": text})
    return pages_data

def extract_text_with_fitz(pdf_path: str) -> list[dict]:
    """Extract page-by-page text using PyMuPDF (fitz) as fallback."""
    pages_data = []
    doc = fitz.open(pdf_path)
    for i, page in enumerate(doc):
        text = page.get_text()
        if text and text.strip():
            pages_data.append({"page_number": i + 1, "text": text})
    doc.close()
    return pages_data

def chunk_text_by_paragraphs_and_sections(pages_data: list[dict], max_words: int = 350, overlap_words: int = 50) -> list[dict]:
    """
    Chunk entire paper prose while tracking page numbers and heading heuristics.
    Returns list of dicts: {text, page_number, section_guess}
    """
    chunks = []
    current_section = "Introduction/Body"

    for page_info in pages_data:
        page_num = page_info["page_number"]
        page_text = page_info["text"]
        lines = page_text.split("\n")

        current_paragraph_lines = []
        for line in lines:
            new_sec = guess_section(line, current_section)
            if new_sec != current_section and new_sec != "References":
                # Flush current paragraph before switching section
                if current_paragraph_lines:
                    p_text = " ".join(current_paragraph_lines).strip()
                    if len(p_text.split()) > 15:
                        chunks.append({
                            "text": p_text,
                            "page_number": page_num,
                            "section_guess": current_section
                        })
                    current_paragraph_lines = []
                current_section = new_sec

            if current_section == "References":
                # Optionally skip reference list from semantic prose search
                continue

            current_paragraph_lines.append(line)

        # Process accumulated lines on the page into word chunks with overlap
        if current_paragraph_lines:
            full_page_sec_text = " ".join(current_paragraph_lines).strip()
            words = full_page_sec_text.split()
            if len(words) <= max_words:
                if len(words) > 15:
                    chunks.append({
                        "text": full_page_sec_text,
                        "page_number": page_num,
                        "section_guess": current_section
                    })
            else:
                start_idx = 0
                while start_idx < len(words):
                    end_idx = min(start_idx + max_words, len(words))
                    chunk_words = words[start_idx:end_idx]
                    chunk_str = " ".join(chunk_words).strip()
                    if len(chunk_words) > 15:
                        chunks.append({
                            "text": chunk_str,
                            "page_number": page_num,
                            "section_guess": current_section
                        })
                    if end_idx == len(words):
                        break
                    start_idx += (max_words - overlap_words)

    return chunks

def download_pdf(url: str, save_path: str) -> bool:
    """Download PDF file safely."""
    try:
        headers = {"User-Agent": "AcademicResearchAssistant/1.0 (Python/requests)"}
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        with open(save_path, "wb") as f:
            f.write(resp.content)
        return True
    except Exception as e:
        print(f"Failed to download PDF from {url}: {e}")
        return False

def ingest_and_index_paper(paper_id: str, title: str = "", authors: list[str] = None, year: int = None, abstract: str = "", pdf_url: str = None) -> dict:
    """
    Download PDF (or use cached/arXiv URL), parse text, chunk entire body, and index in ChromaDB.
    Idempotent: if already indexed, returns immediately.
    """
    if not authors:
        authors = []

    # Check database first for idempotency
    with get_session() as session:
        existing_paper = session.query(Paper).filter_by(id=paper_id).first()
        if existing_paper and existing_paper.indexed_at:
            # Also verify if chunks exist in ChromaDB
            collection = get_or_create_collection("research_papers")
            existing_chunks = collection.get(where={"paper_id": paper_id})
            if existing_chunks and existing_chunks["ids"]:
                return {
                    "status": "already_indexed",
                    "paper_id": paper_id,
                    "title": existing_paper.title,
                    "chunks_count": len(existing_chunks["ids"]),
                    "message": f"Paper '{existing_paper.title}' is already indexed (`{paper_id}`) with {len(existing_chunks['ids'])} chunks in RAG."
                }

    # Determine PDF URL if not provided explicitly
    if not pdf_url:
        if re.match(r"^\d{4}\.\d{4,5}$", paper_id) or re.match(r"^[a-z\-]+/\d+$", paper_id, re.I):
            pdf_url = f"https://arxiv.org/pdf/{paper_id}.pdf"
        else:
            return {
                "status": "error",
                "paper_id": paper_id,
                "message": f"No direct PDF URL provided and '{paper_id}' is not a recognized arXiv ID format."
            }

    # Download PDF
    safe_name = re.sub(r"[^\w\-\.]", "_", paper_id) + ".pdf"
    local_pdf_path = os.path.join(PDF_STORAGE_DIR, safe_name)

    if not os.path.exists(local_pdf_path):
        success = download_pdf(pdf_url, local_pdf_path)
        if not success:
            return {
                "status": "error",
                "paper_id": paper_id,
                "message": f"Failed to download PDF from URL: {pdf_url}"
            }

    # Extract text with pdfplumber, fallback to fitz
    pages_data = []
    try:
        pages_data = extract_text_with_pdfplumber(local_pdf_path)
    except Exception as e:
        print(f"[PDFIngester] pdfplumber error on {local_pdf_path}, falling back to fitz: {e}")

    if not pages_data:
        try:
            pages_data = extract_text_with_fitz(local_pdf_path)
        except Exception as e:
            return {
                "status": "error",
                "paper_id": paper_id,
                "message": f"Failed to parse text from PDF using both pdfplumber and PyMuPDF (fitz): {e}"
            }

    if not pages_data:
        return {
            "status": "error",
            "paper_id": paper_id,
            "message": "PDF downloaded but extracted 0 text pages (possibly scanned/image-only PDF without OCR)."
        }

    # Chunk text
    chunks = chunk_text_by_paragraphs_and_sections(pages_data)
    if not chunks and abstract:
        chunks = [{"text": abstract, "page_number": 1, "section_guess": "Abstract"}]

    if not chunks:
        return {
            "status": "error",
            "paper_id": paper_id,
            "message": "Extracted text could not be chunked properly."
        }

    # Index into ChromaDB
    collection = get_or_create_collection("research_papers")
    
    # First remove any existing partial/stale chunks for this paper_id
    try:
        stale = collection.get(where={"paper_id": paper_id})
        if stale and stale["ids"]:
            collection.delete(ids=stale["ids"])
    except Exception:
        pass

    documents = []
    metadatas = []
    ids = []

    for idx, c in enumerate(chunks):
        doc_id = f"{paper_id}_chunk_{idx}"
        documents.append(c["text"])
        metadatas.append({
            "paper_id": paper_id,
            "paper_title": title or paper_id,
            "page_number": int(c["page_number"]),
            "section_guess": str(c["section_guess"]),
            "chunk_index": idx
        })
        ids.append(doc_id)

    # Batch insert into ChromaDB (max 500 per batch to avoid limits)
    batch_size = 300
    for i in range(0, len(ids), batch_size):
        collection.add(
            documents=documents[i:i+batch_size],
            metadatas=metadatas[i:i+batch_size],
            ids=ids[i:i+batch_size]
        )

    # Save metadata to SQLite Paper table
    import json
    with get_session() as session:
        paper_record = session.query(Paper).filter_by(id=paper_id).first()
        if not paper_record:
            paper_record = Paper(
                id=paper_id,
                arxiv_id=paper_id if re.match(r"^\d{4}\.\d{4,5}$", paper_id) else None,
                title=title or f"Paper {paper_id}",
                authors=json.dumps(authors),
                year=year,
                abstract=abstract,
                pdf_path=local_pdf_path,
                indexed_at=datetime.now(timezone.utc)
            )
            session.add(paper_record)
        else:
            paper_record.pdf_path = local_pdf_path
            paper_record.indexed_at = datetime.now(timezone.utc)
            if title and not paper_record.title:
                paper_record.title = title
            if abstract and not paper_record.abstract:
                paper_record.abstract = abstract

    return {
        "status": "success",
        "paper_id": paper_id,
        "title": title or paper_id,
        "chunks_indexed": len(ids),
        "pages_parsed": len(pages_data),
        "message": f"Successfully fetched and indexed full text of '{title or paper_id}' ({len(ids)} prose chunks across {len(pages_data)} pages)."
    }
