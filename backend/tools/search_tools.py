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
    """
    results = search_semantic_scholar_api(query, max_results=max_results)
    if not results:
        return f"No papers found on Semantic Scholar matching query: '{query}'."

    lines = [f"Found {len(results)} papers on Semantic Scholar for '{query}':"]
    for i, p in enumerate(results, 1):
        authors_str = ", ".join(p["authors"][:3]) if p["authors"] else "Unknown"
        if len(p["authors"]) > 3:
            authors_str += " et al."
        lines.append(
            f"\n[{i}] ID: {p['id']} (S2: {p['s2_id']}) | Year: {p['year'] or 'Unknown'}\n"
            f"    Title: {p['title']}\n"
            f"    Authors: {authors_str}\n"
            f"    Abstract snippet: {p['abstract'][:320]}...\n"
            f"    Download Status: {p['download_status_message']}"
        )
    return "\n".join(lines)
