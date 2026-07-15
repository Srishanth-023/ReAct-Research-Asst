import os
import chromadb
from chromadb import EmbeddingFunction
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from config import CHROMA_PERSIST_DIR

class LocalSentenceTransformerEmbeddingFunction(EmbeddingFunction):
    """Local, free embedding function using sentence-transformers all-MiniLM-L6-v2."""
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None

    def name(self) -> str:
        return f"LocalSentenceTransformer_{self.model_name}"



    @property
    def model(self):
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def __call__(self, input: list[str]) -> list[list[float]]:
        # Compute embeddings for a list of string texts
        embeddings = self.model.encode(input, convert_to_numpy=True, normalize_embeddings=True)
        return embeddings.tolist()

# Singleton instances
_chroma_client = None
_collection = None
_embedding_fn = None

def get_embedding_function():
    global _embedding_fn
    if _embedding_fn is None:
        _embedding_fn = LocalSentenceTransformerEmbeddingFunction("all-MiniLM-L6-v2")
    return _embedding_fn

def get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(
            path=CHROMA_PERSIST_DIR,
            settings=Settings(anonymized_telemetry=False)
        )
    return _chroma_client

def get_or_create_collection(collection_name: str = "research_papers"):
    """
    Single predictable helper for ChromaDB collection creation/retrieval.
    Called once at app startup or inside init_db.py.
    """
    global _collection
    if _collection is None or _collection.name != collection_name:
        client = get_chroma_client()
        embedding_fn = get_embedding_function()
        _collection = client.get_or_create_collection(
            name=collection_name,
            embedding_function=embedding_fn,
            metadata={"description": "Full-text research paper chunks for ReAct agent"}
        )
    return _collection

def get_vector_store():
    """Return the active collection."""
    return get_or_create_collection("research_papers")
