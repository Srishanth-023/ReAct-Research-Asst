import time
import threading
import urllib.parse
import xml.etree.ElementTree as ET
import requests
from config import RATE_LIMIT_DELAY

# Rate limiter lock and timestamp
_lock = threading.Lock()
_last_request_time = 0.0

def _rate_limit_wait():
    """Ensure at least RATE_LIMIT_DELAY seconds elapse between calls to arXiv API."""
    global _last_request_time
    with _lock:
        now = time.time()
        elapsed = now - _last_request_time
        if elapsed < RATE_LIMIT_DELAY:
            time.sleep(RATE_LIMIT_DELAY - elapsed)
        _last_request_time = time.time()

def search_arxiv_api(query: str, max_results: int = 5) -> list[dict]:
    """
    Search arXiv Atom XML API for papers matching the query.
    Returns list of dicts: {title, id, abstract, year, authors, pdf_url}
    """
    _rate_limit_wait()

    encoded_query = urllib.parse.quote(query)
    
    if query.startswith("id:"):
        arxiv_id = query[3:]
        url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}&start=0&max_results={max_results}"
    else:
        url = f"http://export.arxiv.org/api/query?search_query=all:{encoded_query}&start=0&max_results={max_results}"

    try:
        headers = {"User-Agent": "AcademicResearchAssistant/1.0 (Python/requests)"}
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()

        root = ET.fromstring(response.content)
        # Atom namespace
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        results = []
        for entry in root.findall("atom:entry", ns):
            id_url = entry.findtext("atom:id", default="", namespaces=ns)
            # Extract raw arXiv ID from URL (e.g. http://arxiv.org/abs/2210.03629v1 -> 2210.03629)
            arxiv_id = id_url.split("/abs/")[-1].split("v")[0] if "/abs/" in id_url else id_url

            title = entry.findtext("atom:title", default="Untitled", namespaces=ns).replace("\n", " ").strip()
            summary = entry.findtext("atom:summary", default="", namespaces=ns).replace("\n", " ").strip()
            published = entry.findtext("atom:published", default="", namespaces=ns)
            year = int(published[:4]) if published and len(published) >= 4 and published[:4].isdigit() else None

            authors = []
            for author_elem in entry.findall("atom:author", ns):
                name = author_elem.findtext("atom:name", default="", namespaces=ns).strip()
                if name:
                    authors.append(name)

            pdf_url = None
            for link in entry.findall("atom:link", ns):
                if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf":
                    pdf_url = link.attrib.get("href")
            if not pdf_url and arxiv_id:
                pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

            results.append({
                "id": arxiv_id,
                "title": title,
                "abstract": summary,
                "year": year,
                "authors": authors,
                "pdf_url": pdf_url,
                "source": "arXiv"
            })

        return results

    except Exception as e:
        print(f"[ArXivClient] Error querying arXiv API for '{query}': {e}")
        return []

def fetch_arxiv_metadata(arxiv_id: str) -> dict | None:
    """Fetch exact metadata for a specific arXiv ID."""
    results = search_arxiv_api(f"id:{arxiv_id}", max_results=1)
    return results[0] if results else None
