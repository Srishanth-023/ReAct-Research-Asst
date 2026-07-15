from services.pdf_ingester import ingest_and_index_paper
from services.arxiv_client import fetch_arxiv_metadata
from services.semantic_scholar import search_semantic_scholar_api

def fetch_paper_tool(paper_id: str, pdf_url: str = None, title: str = None) -> str:
    """
    Download PDF, parse, chunk entire body, and embed into local ChromaDB.
    Idempotent: returns status if already indexed.
    """
    # If title or url not passed, try quick lookup if possible
    authors = []
    year = None
    abstract = ""

    if not pdf_url or not title:
        # First check arXiv if ID matches arXiv pattern
        meta = fetch_arxiv_metadata(paper_id)
        if meta:
            title = title or meta.get("title")
            pdf_url = pdf_url or meta.get("pdf_url")
            authors = meta.get("authors", [])
            year = meta.get("year")
            abstract = meta.get("abstract", "")
        else:
            # Check Semantic Scholar
            s2_meta = search_semantic_scholar_api(paper_id, max_results=1)
            if s2_meta and s2_meta[0]["id"] != "error":
                p = s2_meta[0]
                title = title or p.get("title")
                pdf_url = pdf_url or p.get("pdf_url")
                authors = p.get("authors", [])
                year = p.get("year")
                abstract = p.get("abstract", "")
                if not p.get("is_downloadable") and not pdf_url:
                    return (f"Observation: Paper '{title or paper_id}' has openAccessPdf=null and no downloadable arXiv mirror. "
                            f"Full text cannot be downloaded/indexed. You can only reason over its abstract:\n{abstract}")

    result = ingest_and_index_paper(
        paper_id=paper_id,
        title=title or f"Paper {paper_id}",
        authors=authors,
        year=year,
        abstract=abstract,
        pdf_url=pdf_url
    )

    if result.get("status") in ["success", "already_indexed"]:
        return (f"Observation: {result.get('message')}\n"
                f"Status: {result.get('status').upper()} | Title: '{result.get('title')}' | ID: `{paper_id}` | "
                f"Chunks available for semantic RAG retrieval: {result.get('chunks_count', result.get('chunks_indexed', 0))}.")
    else:
        return f"Observation Error: Failed to fetch/index paper `{paper_id}`: {result.get('message')}"
