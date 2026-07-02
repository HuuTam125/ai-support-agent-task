"""
Minimal local Vector Store equivalent for Gemini's free tier.
Gemini has no managed vector-store product, so we build our own:
  1. Chunk each markdown article into overlapping text windows.
  2. Embed each chunk via Gemini's Embedding API (text-embedding-004).
  3. Persist {chunk_text, embedding, metadata} to a local JSON file.
  4. At query time, embed the question and retrieve top-k chunks by
     cosine similarity — a simple, zero-cost RAG retrieval layer.
"""

import os
import json
import time
import numpy as np

STORE_PATH = "data/vector_store.json"
EMBEDDING_MODEL = "gemini-embedding-2" 

CHUNK_SIZE = 800     # chars per chunk
CHUNK_OVERLAP = 100  # chars of overlap between consecutive chunks

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list:
    """Simple sliding-window chunker over raw markdown text."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= chunk_size:
            current = f"{current}\n\n{para}" if current else para
        else:
            if current:
                chunks.append(current)
            overlap_text = current[-overlap:] if current else ""
            current = f"{overlap_text}\n\n{para}".strip()

    if current:
        chunks.append(current)

    return chunks if chunks else [text[:chunk_size]]

def embed_text(text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list:
    """Calls Gemini to convert text into vector embeddings."""
    # Local import để tránh Circular Dependency
    from src.gemini_client import get_gemini_client 
    client = get_gemini_client()
    
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config={
            "task_type": task_type
        }
    )
    return response.embeddings[0].values

def load_store(path: str = STORE_PATH) -> list:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_store(store: list, path: str = STORE_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(store, f)

def remove_article_chunks(store: list, article_id: str) -> list:
    """Drop existing chunks for an article before re-embedding an update."""
    return [c for c in store if c["article_id"] != article_id]

def embed_article(article_id: str, slug: str, article_url: str, markdown_text: str) -> list:
    """Chunks + embeds one article with rate limiting."""
    chunks = chunk_text(markdown_text)
    records = []

    for i, chunk in enumerate(chunks):
        embedding = embed_text(chunk, task_type="RETRIEVAL_DOCUMENT")
        records.append({
            "article_id": article_id,
            "slug": slug,
            "article_url": article_url,
            "chunk_index": i,
            "text": chunk,
            "embedding": embedding,
        })
        time.sleep(0.2) # Rate limit protection

    return records

def cosine_similarity(a: list, b: list) -> float:
    a, b = np.array(a), np.array(b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))

def search(query: str, store: list, k: int = 3) -> list:
    """Returns top-k chunk records most similar to the query."""
    if not store:
        return []

    query_embedding = embed_text(query, task_type="RETRIEVAL_QUERY")
    scored = [
        (cosine_similarity(query_embedding, record["embedding"]), record)
        for record in store
    ]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [record for _, record in scored[:k]]