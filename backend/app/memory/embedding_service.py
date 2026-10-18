import logging
from typing import List, Optional
from google import genai
from google.genai import types
from backend.app.config import settings

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 768

_client: Optional[genai.Client] = None
_cache: dict = {}

def get_gemini_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client

def generate_embedding(text: str) -> List[float]:
    """Generate 768-dimensional semantic embedding using Gemini embed_content."""
    clean_text = text.strip()
    if not clean_text:
        return [0.0] * EMBEDDING_DIM
    
    if clean_text in _cache:
        return _cache[clean_text]

    client = get_gemini_client()
    try:
        resp = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=clean_text,
            config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIM)
        )
        if resp and resp.embeddings and len(resp.embeddings) > 0:
            vec = resp.embeddings[0].values
            _cache[clean_text] = vec
            return vec
    except Exception as e:
        logger.error(f"Error generating Gemini embedding: {e}")

    # Fallback to zero vector if external call fails
    return [0.0] * EMBEDDING_DIM

async def generate_embedding_async(text: str) -> List[float]:
    """Async wrapper for generating semantic embedding."""
    import asyncio
    return await asyncio.to_thread(generate_embedding, text)
