"""
Shared embedding utilities.

One SentenceTransformer instance is loaded lazily and reused across every
signal, the middleware, and the demos — loading it per-agent or per-call
would be wasteful and slow, and would make every module respawn its own
copy of a ~90MB model.
"""

from __future__ import annotations

import numpy as np

_MODEL_NAME = "all-MiniLM-L6-v2"
_model = None


def get_embedding_model():
    """Lazily load and cache the shared sentence-transformer model.

    First call downloads the model (~90MB) from Hugging Face — that needs
    normal internet access once; it's cached locally afterward. See
    README.md "Setup" for details.
    """
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(_MODEL_NAME)
    return _model


def embed(text: str) -> np.ndarray:
    return get_embedding_model().encode(text)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def extract_text(message) -> str:
    """
    Normalize a LangChain message's content down to plain text. Content can
    be a plain string OR a list of content blocks (e.g. a system message
    after a canary block has been appended to it).
    """
    content = getattr(message, "content", None)
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and "text" in block:
                parts.append(block["text"])
            elif isinstance(block, str):
                parts.append(block)
        return " ".join(parts)
    return str(content)
