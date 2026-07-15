from database.vector_store import get_or_create_collection

def retrieve_context_tool(paper_id: str, query: str, top_k: int = 4) -> str:
    """
    Semantic RAG search within a specific indexed paper's chunks.
    Returns passages with section guess and page numbers.
    """
    collection = get_or_create_collection("research_papers")
    
    # Check if paper exists in Chroma
    try:
        results = collection.query(
            query_texts=[query],
            n_results=top_k,
            where={"paper_id": paper_id}
        )
    except Exception as e:
        return f"Observation Error: Failed to retrieve from vector store for paper `{paper_id}`: {e}"

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0] if results.get("distances") else [None] * len(documents)

    if not documents:
        return (f"Observation: No relevant passages found in paper `{paper_id}` for query '{query}'. "
                f"Make sure the paper has been indexed via `fetch_paper[{paper_id}]` first.")

    lines = [f"Top {len(documents)} relevant passages from paper `{paper_id}` for semantic query '{query}':"]
    for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances), 1):
        page = meta.get("page_number", "?")
        section = meta.get("section_guess", "Prose Body")
        title = meta.get("paper_title", paper_id)
        dist_str = f" | Sim Distance: {dist:.3f}" if dist is not None else ""
        lines.append(
            f"\n[Passage {i}] Section: {section} | Page: {page}{dist_str}\n"
            f"Citation: (`{paper_id}`, page {page})\n"
            f"Content: \"{doc}\""
        )
    return "\n".join(lines)

def retrieve_context_all_tool(query: str, top_k: int = 5) -> str:
    """
    Semantic RAG search across ALL indexed papers in the current session.
    Useful for cross-paper synthesis and comparative analysis.
    """
    collection = get_or_create_collection("research_papers")
    
    try:
        # Check total indexed chunks
        count = collection.count()
        if count == 0:
            return "Observation: Vector store has 0 indexed chunks across all papers. Use `fetch_paper` first to index papers."

        results = collection.query(
            query_texts=[query],
            n_results=min(top_k, count)
        )
    except Exception as e:
        return f"Observation Error: Failed to retrieve across all papers: {e}"

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0] if results.get("distances") else [None] * len(documents)

    if not documents:
        return f"Observation: No relevant passages found across any indexed papers for query '{query}'."

    lines = [f"Top {len(documents)} relevant passages across all indexed papers for semantic query '{query}':"]
    for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances), 1):
        p_id = meta.get("paper_id", "Unknown")
        p_title = meta.get("paper_title", p_id)
        page = meta.get("page_number", "?")
        section = meta.get("section_guess", "Prose Body")
        dist_str = f" | Sim Distance: {dist:.3f}" if dist is not None else ""
        lines.append(
            f"\n[Passage {i}] Paper: '{p_title}' (`{p_id}`) | Section: {section} | Page: {page}{dist_str}\n"
            f"Citation: (`{p_id}`, page {page})\n"
            f"Content: \"{doc}\""
        )
    return "\n".join(lines)
