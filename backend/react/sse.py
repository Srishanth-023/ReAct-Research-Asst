import json
from flask import Blueprint, request, Response, jsonify
from react.engine import run_agent_trace
from database.db import get_session
from database.vector_store import get_or_create_collection
from models.schema import Query, TrajectoryStep, Paper, Citation

sse_bp = Blueprint("sse_bp", __name__)

@sse_bp.route("/api/query/stream", methods=["POST"])
def stream_query():
    """
    Server-Sent Events (SSE) streaming endpoint for ReAct traces.
    Payload: {"query": str, "mode": "react"|"cot"|"act"|"standard"}
    """
    data = request.get_json(silent=True) or {}
    user_query = data.get("query", "").strip()
    mode = data.get("mode", "react").strip()

    if not user_query:
        return jsonify({"error": "Query parameter is required."}), 400

    def event_generator():
        try:
            # Yield initial status event
            yield f"data: {json.dumps({'type': 'status', 'content': f'Agent started in [{mode.upper()}] ablation mode...'})}\n\n"
            
            for event in run_agent_trace(user_query=user_query, mode=mode):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            err_payload = {"type": "error", "content": f"Internal Server Error during ReAct execution: {str(e)}"}
            yield f"data: {json.dumps(err_payload)}\n\n"

    return Response(event_generator(), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no"
    })

@sse_bp.route("/api/queries", methods=["GET"])
def get_queries():
    """Return all historical research queries and their final answers."""
    with get_session() as session:
        queries = session.query(Query).order_by(Query.created_at.desc()).limit(50).all()
        return jsonify([q.to_dict() for q in queries])

@sse_bp.route("/api/queries/<int:query_id>", methods=["GET"])
def get_query_details(query_id: int):
    """Return exact steps and citations of a historical trajectory."""
    with get_session() as session:
        q = session.query(Query).filter_by(id=query_id).first()
        if not q:
            return jsonify({"error": "Query not found."}), 404
        return jsonify(q.to_dict())

@sse_bp.route("/api/papers", methods=["GET"])
def get_papers():
    """Return all indexed papers and their ChromaDB chunk counts for the Sources sidebar."""
    collection = get_or_create_collection("research_papers")
    with get_session() as session:
        papers = session.query(Paper).order_by(Paper.indexed_at.desc()).all()
        results = []
        for p in papers:
            p_dict = p.to_dict()
            try:
                # Count chunks for this paper in Chroma
                chunks = collection.get(where={"paper_id": p.id})
                p_dict["chunk_count"] = len(chunks["ids"]) if chunks and chunks.get("ids") else 0
            except Exception:
                p_dict["chunk_count"] = 0
            results.append(p_dict)
        return jsonify(results)

@sse_bp.route("/api/papers/<string:paper_id>/chunks", methods=["GET"])
def get_paper_chunks(paper_id: str):
    """Return exact prose chunks stored in ChromaDB for a given paper."""
    collection = get_or_create_collection("research_papers")
    try:
        chunks = collection.get(where={"paper_id": paper_id})
        items = []
        if chunks and chunks.get("ids"):
            for idx, doc_id in enumerate(chunks["ids"]):
                items.append({
                    "id": doc_id,
                    "text": chunks["documents"][idx],
                    "metadata": chunks["metadatas"][idx]
                })
        return jsonify({"paper_id": paper_id, "chunks": items})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
