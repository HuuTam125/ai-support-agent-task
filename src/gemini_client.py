"""
Gemini API client: handles auth, and RAG-based chat 
using local vector store with strict system instructions.
"""

import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

SYSTEM_INSTRUCTION = """You are OptiBot, the customer-support bot for OptiSigns.com.
- Tone: helpful, factual, concise.
- Only answer using the uploaded docs.
- Max 5 bullet points; else link to the doc.
- Cite up to 3 'Article URL:' lines per reply."""

def get_gemini_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY chưa được set. Kiểm tra file .env hoặc GitHub Secrets."
        )
    return genai.Client(api_key=api_key)

def ask(question: str, k: int = 3) -> str:
    """
    Retrieval-augmented answer: embeds the question, retrieves top-k
    relevant chunks from the local vector store, and feeds only those
    chunks to Gemini as grounding context.
    """
    from src.vector_store import load_store, search
    
    client = get_gemini_client()
    store = load_store()
    top_chunks = search(question, store, k=k)

    if not top_chunks:
        return "No knowledge base documents found to answer the question."

    context_blocks = []
    for c in top_chunks:
        context_blocks.append(
            f"Article URL: {c['article_url']}\n\n{c['text']}"
        )
    context_text = "\n\n---\n\n".join(context_blocks)

    prompt = f"Context documents:\n\n{context_text}\n\nQuestion: {question}"
    
    response = client.models.generate_content(
        model=GEMINI_MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
        )
    )
    return response.text

if __name__ == "__main__":
    test_question = "How do I add a YouTube video?"
    print(f"🤖 Asking: {test_question}\n")
    print(ask(test_question))