import urllib.parse
import requests

SEMANTIC_SCHOLAR_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

def search_semantic_scholar_api(query: str, max_results: int = 5) -> list[dict]:
    """
    Query Semantic Scholar Graph API.
    Handles openAccessPdf null state explicitly so agent/user observe download status.
    """
    params = {
        "query": query,
        "limit": max_results,
        "fields": "title,abstract,year,authors,externalIds,openAccessPdf"
    }
    headers = {
        "User-Agent": "AcademicResearchAssistant/1.0 (Python/requests)"
    }

    try:
        response = requests.get(SEMANTIC_SCHOLAR_SEARCH_URL, params=params, headers=headers, timeout=20)
        if response.status_code == 429:
            # Rate limit hit on free tier
            return [{
                "id": "rate_limited",
                "s2_id": "N/A",
                "arxiv_id": None,
                "title": "API Rate Limit Notice",
                "abstract": "Semantic Scholar API rate limit exceeded on public free tier. Please retry shortly or use `search_arxiv` as fallback.",
                "year": None,
                "authors": [],
                "pdf_url": None,
                "is_downloadable": False,
                "download_status_message": "Rate limited (HTTP 429)",
                "source": "Semantic Scholar"
            }]
            
        response.raise_for_status()
        data = response.json()
        papers = data.get("data", [])

        results = []
        for p in papers:
            s2_id = p.get("paperId", "")
            title = p.get("title", "Untitled")
            abstract = p.get("abstract") or "No abstract provided."
            year = p.get("year")

            authors_raw = p.get("authors", [])
            authors = [a.get("name", "") for a in authors_raw if a.get("name")]

            external_ids = p.get("externalIds", {})
            arxiv_id = external_ids.get("ArXiv")

            open_access_pdf = p.get("openAccessPdf")
            pdf_url = None
            is_downloadable = False
            status_msg = "PDF freely downloadable via OpenAccess link."

            if open_access_pdf and isinstance(open_access_pdf, dict) and open_access_pdf.get("url"):
                pdf_url = open_access_pdf.get("url")
                is_downloadable = True
            elif arxiv_id:
                pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
                is_downloadable = True
                status_msg = f"Available via arXiv PDF mirror (`{arxiv_id}`)."
            else:
                is_downloadable = False
                status_msg = "NOTE: openAccessPdf is null for this paper (closed access or not indexed). Full-text download not available via open access APIs; only abstract and citation metadata can be used."

            primary_id = arxiv_id if arxiv_id else s2_id

            results.append({
                "id": primary_id,
                "s2_id": s2_id,
                "arxiv_id": arxiv_id,
                "title": title,
                "abstract": abstract,
                "year": year,
                "authors": authors,
                "pdf_url": pdf_url,
                "is_downloadable": is_downloadable,
                "download_status_message": status_msg,
                "source": "Semantic Scholar"
            })

        return results

    except Exception as e:
        print(f"[SemanticScholarClient] Error querying API for '{query}': {e}")
        return [{
            "id": "error",
            "s2_id": "N/A",
            "arxiv_id": None,
            "title": "Search Error",
            "abstract": f"Error querying Semantic Scholar API: {str(e)}. Please try search_arxiv.",
            "year": None,
            "authors": [],
            "pdf_url": None,
            "is_downloadable": False,
            "download_status_message": f"Error: {e}",
            "source": "Semantic Scholar"
        }]
