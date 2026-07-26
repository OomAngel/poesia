"""MemorIA — collections and (eventually) Graph RAG retrieval.

*Memoria* (memory). Phase 0-1: a personal library of saved/generated poems,
tagged by theme, form, language and date. Phase 3: the Graph RAG layer —
poet/style nodes, influence edges, semantic-neighbourhood retrieval, used to
ground GalerIA illustration prompts and the generation loop's few-shot
exemplars.

Do not import Phase-3 retrieval helpers until a concrete storage backend
decision has landed (in-memory networkx graph vs. neo4j) — see
docs/PACKAGES_SURVEYED.md.
"""
