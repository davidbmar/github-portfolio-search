"""Embedding pipeline using sentence-transformers for semantic search."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
CHUNK_SIZE = 512  # approximate token limit per chunk
CHUNK_OVERLAP = 64  # overlap between chunks to preserve context


class EmbeddingPipeline:
    """Generates embeddings using sentence-transformers."""

    def __init__(self, model_name: str = DEFAULT_MODEL) -> None:
        self.model_name = model_name
        self._model = None

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading model %s", self.model_name)
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_text(self, text: str) -> list[float]:
        """Embed a single text string into a 384-dim vector."""
        vec = self.model.encode(text, normalize_embeddings=True)
        return vec.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts efficiently."""
        if not texts:
            return []
        vecs = self.model.encode(texts, normalize_embeddings=True, batch_size=32)
        return [v.tolist() for v in vecs]

    def chunk_text(self, text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
        """Split text into overlapping chunks of approximately chunk_size tokens.

        Uses a simple word-based approximation (1 token ~ 0.75 words).
        """
        if not text or not text.strip():
            return []

        words = text.split()
        # Approximate: 1 token ~ 0.75 words, so chunk_size tokens ~ chunk_size * 0.75 words
        words_per_chunk = max(1, int(chunk_size * 0.75))
        overlap_words = max(0, int(overlap * 0.75))

        chunks: list[str] = []
        start = 0
        while start < len(words):
            end = start + words_per_chunk
            chunk = " ".join(words[start:end])
            if chunk.strip():
                chunks.append(chunk)
            if end >= len(words):
                break
            start = end - overlap_words

        return chunks
