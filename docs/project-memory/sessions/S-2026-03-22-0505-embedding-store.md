# Session

Session-ID: S-2026-03-22-0505-embedding-store
Title: Implement embedding pipeline and vector store (Sprint 1 AgentB)
Date: 2026-03-22
Author: AgentB (Claude)

## Goal

Build the embedding pipeline (sentence-transformers) and SQLite-vec vector store for indexing GitHub repo content.

## Context

Sprint 1 of the github-portfolio-search project. AgentB is responsible for the embedding and storage layer while AgentA handles project scaffold and AgentC handles search/CLI.

## Plan

1. Create EmbeddingPipeline class with embed_text, embed_batch, chunk_text
2. Create VectorStore class wrapping SQLite-vec with repos/chunks/repo_files schema
3. Create Indexer class tying together the pipeline and store
4. Write comprehensive tests for both modules

## Changes Made

- `src/ghps/embeddings.py`: EmbeddingPipeline with all-MiniLM-L6-v2 model, text chunking with overlap
- `src/ghps/store.py`: VectorStore with SQLite-vec, schema creation, add_repo, search (KNN)
- `src/ghps/indexer.py`: Indexer class orchestrating repo indexing with progress logging
- `tests/test_embeddings.py`: 10 tests covering embed_text, embed_batch, chunk_text
- `tests/test_store.py`: 9 tests covering schema, add_repo, search, serialization

## Decisions Made

- Used pysqlite3 instead of stdlib sqlite3 because macOS system Python doesn't support enable_load_extension
- Used `k = ?` in WHERE clause for sqlite-vec KNN queries (required by vec0 virtual table)
- Chunking uses word-based approximation (1 token ~ 0.75 words) with configurable overlap
- Embeddings are normalized for cosine similarity via dot product

## Open Questions

- Integration with AgentA's github_client interface (Indexer.index_user depends on it)
- Whether pyproject.toml will list pysqlite3 as a dependency (AgentA owns pyproject.toml)

## Links

Commits:
- (pending)
