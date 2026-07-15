import json
from services.arxiv_client import search_arxiv_api
from services.semantic_scholar import search_semantic_scholar_api

def search_arxiv_tool(query: str, max_results: int = 4) -> str:
    """
    Search arXiv for top candidate papers.
    Returns formatted observation string with title, id, abstract, year, and authors.
    """
    results = search_arxiv_api(query, max_results=max_results)
    if not results:
        return f"No papers found on arXiv matching query: '{query}'."

    lines = [f"Found {len(results)} papers on arXiv for '{query}':"]
    for i, p in enumerate(results, 1):
        authors_str = ", ".join(p["authors"][:3])
        if len(p["authors"]) > 3:
            authors_str += " et al."
        lines.append(
            f"\n[{i}] ID: {p['id']} | Year: {p['year'] or 'Unknown'}\n"
            f"    Title: {p['title']}\n"
            f"    Authors: {authors_str}\n"
            f"    Abstract snippet: {p['abstract'][:320]}...\n"
            f"    PDF URL: {p['pdf_url'] or 'N/A'}"
        )
    return "\n".join(lines)

def search_semantic_scholar_tool(query: str, max_results: int = 4) -> str:
    """
    Search Semantic Scholar for top candidate papers + citation/download status.
    If rate-limited or an error occurs, automatically falls back to arXiv search.
    """
    results = search_semantic_scholar_api(query, max_results=max_results)
    
    # Check if we got a rate-limited or error result
    if results and results[0].get("id") in ["rate_limited", "error"]:
        reason = "rate limited" if results[0].get("id") == "rate_limited" else "encountered an error"
        # Fall back to arXiv search
        arxiv_results = search_arxiv_tool(query, max_results=max_results)
        return (f"[Notice: Semantic Scholar search {reason}. Automatically falling back to arXiv search results for your query]\n\n"
                f"{arxiv_results}")

    if not results:
        return f"No papers found on Semantic Scholar matching query: '{query}'."

    lines = [f"Found {len(results)} papers on Semantic Scholar for '{query}':"]
    for i, p in enumerate(results, 1):
        authors = p.get("authors") or []
        authors_str = ", ".join(authors[:3]) if authors else "Unknown"
        if len(authors) > 3:
            authors_str += " et al."
        
        p_id = p.get("id") or "Unknown"
        s2_id = p.get("s2_id") or "N/A"
        year = p.get("year") or "Unknown"
        title = p.get("title") or "Untitled"
        abstract = p.get("abstract") or "No abstract provided."
        download_status = p.get("download_status_message") or p.get("status_msg") or "N/A"

        lines.append(
            f"\n[{i}] ID: {p_id} (S2: {s2_id}) | Year: {year}\n"
            f"    Title: {title}\n"
            f"    Authors: {authors_str}\n"
            f"    Abstract snippet: {abstract[:320]}...\n"
            f"    Download Status: {download_status}"
        )
    return "\n".join(lines)
