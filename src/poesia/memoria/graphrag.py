"""Graph RAG retrieval layer — Phase 3.

Storage: networkx in-memory directed graph, persisted as JSON alongside the
poem library at ~/.poesia/graphrag.json.

Graph schema:
    Nodes: PoemRecord ID → attributes (theme, form, language, tags, embedding)
    Edges (directed): semantic similarity ≥ threshold, weighted by cosine score

Retrieval: given a query embedding, return the k most semantically similar
poem records via cosine similarity against all stored embeddings.

Ingestion: call ingest(records) to add/update nodes and rebuild edges.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any

from poesia.memoria.library import PoemRecord


def _cosine(a: list[float], b: list[float]) -> float:
    """Pure Python cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


class GraphRAGRetriever:
    """NetworkX-backed Graph RAG retriever for the MemorIA poem library.

    Builds a semantic neighbourhood graph over ingested PoemRecords.
    Persists the graph data to ``~/.poesia/graphrag.json`` as plain JSON so
    no networkx version-specific pickle format is relied on.

    Lazy-imports ``networkx`` — requires ``pip install -e ".[graphrag]"``.
    """

    SIMILARITY_THRESHOLD = 0.70  # Minimum cosine score to add an edge

    def __init__(self, storage_path: str | Path | None = None) -> None:
        if storage_path is None:
            storage_path = Path.home() / ".poesia" / "graphrag.json"
        self.storage_path = Path(storage_path) if str(storage_path) != ":memory:" else None

        self._graph = self._make_graph()
        if self.storage_path and self.storage_path.exists():
            self._load()

    def _make_graph(self) -> Any:
        try:
            import networkx as nx  # type: ignore[import-untyped]
            return nx.DiGraph()
        except ImportError as exc:
            raise RuntimeError(
                "networkx is not installed. Run: pip install -e '.[graphrag]'"
            ) from exc

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def ingest(
        self,
        records: list[PoemRecord],
        embeddings: dict[str, list[float]] | None = None,
        embedding_client: Any | None = None,
    ) -> None:
        """Add or update poem nodes and rebuild semantic neighbourhood edges.

        Args:
            records: PoemRecord objects to ingest (must have .id set).
            embeddings: Optional dict mapping record.id → float vector. If
                provided, semantic similarity edges are built between poems
                whose cosine score ≥ SIMILARITY_THRESHOLD.
            embedding_client: Optional EmbeddingClient for auto-embedding. If
                provided and embeddings dict is missing entries, will compute
                embeddings automatically from record content.

        Phase 4D: Auto-embed on ingest when embedding_client is provided.
        """
        embeddings = embeddings or {}

        # Phase 4D: Auto-embed records that don't have pre-computed embeddings
        if embedding_client is not None:
            for rec in records:
                if rec.id and rec.id not in embeddings:
                    # Build embeddable text from record
                    text_parts = [rec.theme or ""]
                    if hasattr(rec, "lines") and rec.lines:
                        text_parts.extend(rec.lines)
                    embeddable_text = " ".join(text_parts).strip()
                    if embeddable_text:
                        try:
                            embeddings[rec.id] = embedding_client.embed(embeddable_text)
                        except Exception:
                            pass  # Skip if embedding fails

        for rec in records:
            if not rec.id:
                continue
            self._graph.add_node(
                rec.id,
                theme=rec.theme,
                form=rec.form,
                language=rec.language,
                tags=rec.tags,
                embedding=embeddings.get(rec.id, []),
            )

        # Rebuild semantic edges from embeddings
        node_ids = [n for n in self._graph.nodes if self._graph.nodes[n].get("embedding")]
        for i, node_a in enumerate(node_ids):
            emb_a = self._graph.nodes[node_a]["embedding"]
            for node_b in node_ids[i + 1:]:
                emb_b = self._graph.nodes[node_b]["embedding"]
                score = _cosine(emb_a, emb_b)
                if score >= self.SIMILARITY_THRESHOLD:
                    self._graph.add_edge(node_a, node_b, weight=round(score, 4))
                    self._graph.add_edge(node_b, node_a, weight=round(score, 4))

        if self.storage_path:
            self._save()

    def retrieve(
        self,
        query_embedding: list[float],
        k: int = 5,
        form_filter: str | None = None,
        language_filter: str | None = None,
    ) -> list[tuple[str, float]]:
        """Return the k most semantically similar poem IDs with scores.

        Args:
            query_embedding: Float vector to compare against all poem nodes.
            k: Maximum number of results.
            form_filter: Optional form name (e.g. 'soneto') to restrict results.
            language_filter: Optional language code ('es', 'en') to restrict results.

        Returns:
            List of (poem_id, cosine_score) sorted by descending similarity.
        """
        scores: list[tuple[str, float]] = []

        for node_id, attrs in self._graph.nodes(data=True):
            emb = attrs.get("embedding", [])
            if not emb:
                continue
            if form_filter and attrs.get("form") != form_filter:
                continue
            if language_filter and attrs.get("language") != language_filter:
                continue
            score = _cosine(query_embedding, emb)
            scores.append((node_id, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:k]

    def neighbourhood(self, poem_id: str, depth: int = 1) -> list[tuple[str, float]]:
        """Return directly connected poems up to `depth` hops away.

        Useful for 'find poems similar to this one' without a query embedding.

        Returns:
            List of (poem_id, edge_weight) sorted by descending weight.
        """
        try:
            import networkx as nx  # type: ignore[import-untyped]
        except ImportError:
            return []

        if poem_id not in self._graph:
            return []

        if depth == 1:
            neighbours = [
                (nbr, self._graph[poem_id][nbr].get("weight", 0.0))
                for nbr in self._graph.successors(poem_id)
            ]
        else:
            ego = nx.ego_graph(self._graph, poem_id, radius=depth)
            neighbours = [
                (n, ego[poem_id].get(n, {}).get("weight", 0.0) if ego.has_edge(poem_id, n) else 0.0)
                for n in ego.nodes
                if n != poem_id
            ]

        neighbours.sort(key=lambda x: x[1], reverse=True)
        return neighbours

    def node_count(self) -> int:
        return self._graph.number_of_nodes()

    def edge_count(self) -> int:
        return self._graph.number_of_edges()

    # ------------------------------------------------------------------
    # Persistence (plain JSON, no pickle)
    # ------------------------------------------------------------------

    def _save(self) -> None:
        if not self.storage_path:
            return
        os.makedirs(self.storage_path.parent, exist_ok=True)
        data = {
            "nodes": {n: dict(attrs) for n, attrs in self._graph.nodes(data=True)},
            "edges": [
                {"source": u, "target": v, "weight": d.get("weight", 0.0)}
                for u, v, d in self._graph.edges(data=True)
            ],
        }
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load(self) -> None:
        if not self.storage_path or not self.storage_path.exists():
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for node_id, attrs in data.get("nodes", {}).items():
                self._graph.add_node(node_id, **attrs)
            for edge in data.get("edges", []):
                self._graph.add_edge(edge["source"], edge["target"], weight=edge["weight"])
        except Exception:
            # Corrupt or incompatible JSON — start fresh
            self._graph = self._make_graph()
