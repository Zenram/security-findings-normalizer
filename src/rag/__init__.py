"""Part 2 (RAG) package: ingestion, chunking, embedding, retrieval, answering.

Step 1 lives here: `ingest.py` (loaders + clean + dedup + pipeline) and
`chunk.py` (structure-aware chunker + fixed-size baseline for the comparison).
Later steps (embed/index/retrieve/answer) are added alongside, reusing the
Part-1 infra in `src/` (config, models, prompts).
"""
