"""Tests for the embedding pipeline."""

import sys
import os

# Add src to path so imports work without pyproject.toml installed
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ghps.embeddings import EmbeddingPipeline, EMBEDDING_DIM


class TestEmbedText:
    def test_returns_correct_dimension(self):
        pipeline = EmbeddingPipeline()
        vec = pipeline.embed_text("hello world")
        assert len(vec) == EMBEDDING_DIM

    def test_returns_list_of_floats(self):
        pipeline = EmbeddingPipeline()
        vec = pipeline.embed_text("test input")
        assert isinstance(vec, list)
        assert all(isinstance(v, float) for v in vec)

    def test_similar_texts_have_close_embeddings(self):
        pipeline = EmbeddingPipeline()
        vec1 = pipeline.embed_text("machine learning algorithms")
        vec2 = pipeline.embed_text("ML algorithms for data science")
        vec3 = pipeline.embed_text("recipe for chocolate cake")

        # Cosine similarity via dot product (vectors are normalized)
        sim_related = sum(a * b for a, b in zip(vec1, vec2))
        sim_unrelated = sum(a * b for a, b in zip(vec1, vec3))
        assert sim_related > sim_unrelated


class TestEmbedBatch:
    def test_batch_returns_correct_count(self):
        pipeline = EmbeddingPipeline()
        texts = ["hello", "world", "test"]
        vecs = pipeline.embed_batch(texts)
        assert len(vecs) == 3

    def test_batch_dimensions(self):
        pipeline = EmbeddingPipeline()
        vecs = pipeline.embed_batch(["a", "b"])
        for vec in vecs:
            assert len(vec) == EMBEDDING_DIM

    def test_empty_batch(self):
        pipeline = EmbeddingPipeline()
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
        # Create a text with ~1000 words (should produce multiple chunks)
        text = " ".join(["word"] * 1000)
        chunks = pipeline.chunk_text(text)
        assert len(chunks) > 1

    def test_chunks_have_overlap(self):
        pipeline = EmbeddingPipeline()
        text = " ".join([f"word{i}" for i in range(1000)])
        chunks = pipeline.chunk_text(text, chunk_size=100, overlap=20)
        assert len(chunks) > 1
        # Check that consecutive chunks share some words
        words_1 = set(chunks[0].split())
        words_2 = set(chunks[1].split())
        assert len(words_1 & words_2) > 0
