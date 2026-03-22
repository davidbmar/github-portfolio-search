"""Tests for the embedding pipeline."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np

from ghps.embeddings import EmbeddingPipeline, EMBEDDING_DIM, CHUNK_SIZE, CHUNK_OVERLAP


def _make_pipeline():
    """Create an EmbeddingPipeline with a mocked SentenceTransformer model."""
    pipeline = EmbeddingPipeline()
    mock_model = MagicMock()
    # encode returns numpy arrays of the correct dimension
    mock_model.encode.side_effect = lambda texts, **kw: (
        np.random.randn(EMBEDDING_DIM).astype(np.float32)
        if isinstance(texts, str)
        else np.random.randn(len(texts) if not isinstance(texts, str) else 1, EMBEDDING_DIM).astype(np.float32)
    )
    pipeline._model = mock_model
    return pipeline


class TestEmbedText:
    def test_returns_correct_dimension(self):
        pipeline = _make_pipeline()
        vec = pipeline.embed_text("hello world")
        assert len(vec) == EMBEDDING_DIM

    def test_returns_list_of_floats(self):
        pipeline = _make_pipeline()
        vec = pipeline.embed_text("test input")
        assert isinstance(vec, list)
        assert all(isinstance(v, float) for v in vec)


class TestEmbedBatch:
    def test_batch_returns_correct_count(self):
        pipeline = _make_pipeline()
        texts = ["hello", "world", "test"]
        vecs = pipeline.embed_batch(texts)
        assert len(vecs) == 3

    def test_batch_dimensions(self):
        pipeline = _make_pipeline()
        vecs = pipeline.embed_batch(["a", "b"])
        for vec in vecs:
            assert len(vec) == EMBEDDING_DIM

    def test_empty_batch(self):
        pipeline = _make_pipeline()
        assert pipeline.embed_batch([]) == []


class TestChunkText:
    def test_short_text_single_chunk(self):
        pipeline = EmbeddingPipeline()
        chunks = pipeline.chunk_text("hello world")
        assert len(chunks) == 1
        assert chunks[0] == "hello world"

    def test_empty_text_no_chunks(self):
        pipeline = EmbeddingPipeline()
        assert pipeline.chunk_text("") == []
        assert pipeline.chunk_text("   ") == []

    def test_long_text_multiple_chunks(self):
        pipeline = EmbeddingPipeline()
        text = " ".join(["word"] * 1000)
        chunks = pipeline.chunk_text(text)
        assert len(chunks) > 1

    def test_chunks_have_overlap(self):
        pipeline = EmbeddingPipeline()
        text = " ".join([f"word{i}" for i in range(1000)])
        chunks = pipeline.chunk_text(text, chunk_size=100, overlap=20)
        assert len(chunks) > 1
        words_1 = set(chunks[0].split())
        words_2 = set(chunks[1].split())
        assert len(words_1 & words_2) > 0
