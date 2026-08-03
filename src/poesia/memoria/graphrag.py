"""Graph RAG retrieval layer — Phase 3 / P2.

Storage: networkx in-memory directed graph, persisted as JSON alongside the
poem library at ~/.poesia/graphrag.json.

Graph schema (P2 typed):
    Nodes: any record ID → attributes (node_type, theme, form, language,
           tags, embedding)
    Edges (directed): typed relations (RelationType) weighted by cosine score
                      for semantic edges, or 1.0 for structural edges.

Retrieval: given a query embedding, return the k most semantically similar
records via cosine similarity against all stored embeddings, OR via bounded
typed graph traversal that returns explainable paths.

Ingestion: call ingest(records) to add/update poem nodes and rebuild edges.
Use add_fragment_node() / add_influence_node() for typed non-poem nodes.

P0 hardening: validates embedding dimensions and exposes failures explicitly.
P2 additions: NodeType/RelationType enums, GraphPath, traverse(),
              versioned JSON persistence header.
P3 source fingerprints: content_fingerprint in JSON header; is_stale(records)
              detects when the persisted index is out of date.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from poesia.memoria.embedding_validation import (
    EmbeddingValidationError,
    validate_embedding_vector,
)
from poesia.memoria.library import PoemRecord
from poesia.memoria.records import NodeType, RelationType

# Persistence format version — bump when the JSON schema changes incompatibly.
_SCHEMA_VERSION = "2"


from poesia.exceptions import (  # noqa: E402 - lazy import to avoid a cycle
    IndexCompatibilityError as _PoesiaIndexError,
)


class IndexCompatibilityError(_PoesiaIndexError, RuntimeError):
    """Raised when an embedding client is incompatible with the loaded index.

    This prevents silently mixing embeddings from different models or
    dimension sizes, which would corrupt cosine similarity without any
    visible error.

    Multiple inheritance: caught by ``except PoesiaError`` (generic handling)
    or ``except RuntimeError`` (legacy compatibility).

    Attributes:
        stored_model_id: The model ID recorded in the persisted index.
        stored_dimension: The embedding dimension recorded in the persisted index.
        client_model_id: The model ID of the client being used.
        client_dimension: The embedding dimension of the client being used.
    """

    def __init__(
        self,
        stored_model_id: str | None,
        stored_dimension: int | None,
        client_model_id: str,
        client_dimension: int,
    ) -> None:
        self.stored_model_id = stored_model_id
        self.stored_dimension = stored_dimension
        self.client_model_id = client_model_id
        self.client_dimension = client_dimension
        super().__init__(
            f"Embedding model mismatch: index was built with "
            f"model='{stored_model_id}' dim={stored_dimension}, "
            f"but current client is model='{client_model_id}' dim={client_dimension}. "
            f"Call retriever.rebuild(records, embedding_client) to re-index with the "
            f"new model, or use the original model to continue."
        )


@dataclass
class GraphHop:
    """A single hop along a graph path.

    Attributes:
        node_id: ID of the node reached by this hop.
        node_type: Type of the node (poem, fragment, influence, …).
        relation_type: The relation that was followed to reach this node.
        weight: Edge weight (cosine similarity for ``similar_to`` edges,
                1.0 for structural edges).
    """

    node_id: str
    node_type: NodeType
    relation_type: RelationType
    weight: float


@dataclass
class GraphPath:
    """A traversal path through the semantic graph.

    A path starts at ``origin_id`` and follows a sequence of typed hops.
    The path can be rendered as a human-readable explanation string such as::

        pattern-finder -[similar_to 0.82]-> hound -[inspired_by]-> Garcia Lorca

    Attributes:
        origin_id: ID of the node where traversal started.
        hops: Ordered list of hops from the origin.
    """

    origin_id: str
    hops: list[GraphHop] = field(default_factory=list)

    @property
    def endpoint_id(self) -> str:
        """Return the ID of the final node in the path."""
        return self.hops[-1].node_id if self.hops else self.origin_id

    @property
    def depth(self) -> int:
        """Return the number of hops in the path."""
        return len(self.hops)

    def to_display_string(self, node_labels: dict[str, str] | None = None) -> str:
        """Render the path as a human-readable explanation.

        Args:
            node_labels: Optional mapping of node_id → display label.
                         If absent, node IDs are used directly.

        Returns:
            A string like::

                pattern-finder -[similar_to 0.82]-> hound -[inspired_by]-> Garcia Lorca
        """
        labels = node_labels or {}

        def _label(node_id: str) -> str:
            return labels.get(node_id, node_id)

        parts = [_label(self.origin_id)]
        for hop in self.hops:
            rel = hop.relation_type.value
            w = f" {hop.weight:.2f}" if hop.weight < 1.0 else ""
            parts.append(f"-[{rel}{w}]->")
            parts.append(_label(hop.node_id))
        return " ".join(parts)


def _compute_fingerprint(records: list[PoemRecord]) -> str:
    """Compute a deterministic SHA-256 fingerprint over the ingested record set.

    The fingerprint is a hex digest of a sorted sequence of
    ``(record.id, embeddable_text)`` pairs, so it changes whenever:

    * A record is added or removed.
    * A record's theme or lines change.

    The pairs are sorted by ID so the result is independent of the order in
    which records are passed.

    Args:
        records: The list of PoemRecord objects to fingerprint.

    Returns:
        A 64-character hex string (SHA-256 digest).
    """
    hasher = hashlib.sha256()
    sorted_records = sorted(records, key=lambda r: r.id or "")
    for rec in sorted_records:
        text_parts = [rec.id or "", rec.theme or ""]
        if hasattr(rec, "lines") and rec.lines:
            text_parts.extend(rec.lines)
        entry = "\x00".join(text_parts)
        hasher.update(entry.encode("utf-8"))
        hasher.update(b"\n")  # Record separator
    return hasher.hexdigest()


def _cosine(a: list[float], b: list[float]) -> float:
    """Pure Python cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


class GraphRAGRetriever:
    """NetworkX-backed Graph RAG retriever for the MemorIA poem library.

    Builds a typed semantic neighbourhood graph over ingested records.
    Persists the graph data to ``~/.poesia/graphrag.json`` as plain JSON so
    no networkx version-specific pickle format is relied on.

    P2: Nodes carry a ``node_type`` attribute (NodeType enum). Edges carry a
    ``relation_type`` attribute (RelationType enum). The ``traverse()`` method
    returns ``GraphPath`` objects with explainable hop sequences.

    Persistence header carries ``schema_version``, ``model_id``, and
    ``embedding_dimension`` — these are checked on load and warn (or discard)
    on mismatch, providing the P3 compatibility foundation.

    Lazy-imports ``networkx`` — requires ``pip install -e ".[graphrag]"``.
    """

    SIMILARITY_THRESHOLD = 0.70  # Minimum cosine score to add an edge

    def __init__(self, storage_path: str | Path | None = None) -> None:
        if storage_path is None:
            storage_path = Path.home() / ".poesia" / "graphrag.json"
        self.storage_path = Path(storage_path) if str(storage_path) != ":memory:" else None

        # P2/P3: track the embedding model used for this index (for compatibility)
        self._index_model_id: str | None = None
        self._index_embedding_dimension: int | None = None

        # P3: source fingerprint — SHA-256 over the ingested (id, text) pairs.
        # Allows callers to detect a stale index without a full rebuild.
        self._index_content_fingerprint: str | None = None

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

        # P3: enforce index compatibility before mutating the graph
        if embedding_client is not None:
            self.check_index_compatibility(embedding_client)
            # Record model identity for versioned persistence
            self._index_model_id = embedding_client.model_id
            self._index_embedding_dimension = embedding_client.dimension
            expected_dim = embedding_client.dimension
            for rec in records:
                if rec.id and rec.id not in embeddings:
                    # Build embeddable text from record
                    text_parts = [rec.theme or ""]
                    if hasattr(rec, "lines") and rec.lines:
                        text_parts.extend(rec.lines)
                    embeddable_text = " ".join(text_parts).strip()
                    if embeddable_text:
                        try:
                            # Use embed_one() for scalar text, not embed() which expects list[str]
                            # text_type="passage": stored documents use passage prefix in e5 models
                            raw_embedding = embedding_client.embed_one(
                                embeddable_text, text_type="passage"
                            )
                            # P0: validate embedding shape and values
                            validated = validate_embedding_vector(
                                raw_embedding,
                                expected_dimension=expected_dim,
                                context=f"auto-embed record {rec.id}",
                            )
                            embeddings[rec.id] = validated
                        except EmbeddingValidationError as e:
                            # P0: expose validation failures explicitly
                            raise ValueError(f"Failed to auto-embed record {rec.id}: {e}") from e
                        except Exception as e:
                            # Other embedding failures (network, model load, etc.)
                            raise RuntimeError(
                                f"Embedding client failed for record {rec.id}: {e}"
                            ) from e

        # P0: validate all embeddings before storing
        for rec in records:
            if not rec.id:
                continue

            embedding = embeddings.get(rec.id, [])
            # Validate non-empty embeddings
            if embedding and embedding_client:
                try:
                    embedding = validate_embedding_vector(
                        embedding,
                        expected_dimension=embedding_client.dimension,
                        context=f"record {rec.id} embedding",
                    )
                except EmbeddingValidationError as e:
                    raise ValueError(f"Invalid embedding for record {rec.id}: {e}") from e

            # P2: store node_type on all poem nodes
            self._graph.add_node(
                rec.id,
                node_type=NodeType.poem.value,
                theme=rec.theme,
                form=rec.form,
                language=rec.language,
                tags=rec.tags,
                embedding=embedding,
            )

        # Rebuild semantic edges from embeddings — P2: tag with relation_type
        node_ids = [n for n in self._graph.nodes if self._graph.nodes[n].get("embedding")]
        for i, node_a in enumerate(node_ids):
            emb_a = self._graph.nodes[node_a]["embedding"]
            for node_b in node_ids[i + 1 :]:
                emb_b = self._graph.nodes[node_b]["embedding"]
                score = _cosine(emb_a, emb_b)
                if score >= self.SIMILARITY_THRESHOLD:
                    self._graph.add_edge(
                        node_a,
                        node_b,
                        weight=round(score, 4),
                        relation_type=RelationType.similar_to.value,
                    )
                    self._graph.add_edge(
                        node_b,
                        node_a,
                        weight=round(score, 4),
                        relation_type=RelationType.similar_to.value,
                    )

        # P3: update content fingerprint after every ingest
        self._index_content_fingerprint = _compute_fingerprint(records)

        if self.storage_path:
            self._save()

    def is_stale(self, records: list[PoemRecord]) -> bool:
        """Return True if the persisted index is out of sync with *records*.

        The check is a pure fingerprint comparison: it hashes the given records
        the same way :func:`_compute_fingerprint` did at ingest time and
        compares with the stored value. This is O(N) in the number of records
        and requires no embedding computation.

        A ``None`` stored fingerprint (index built before P3 or never saved)
        is treated as stale so callers know they should rebuild.

        Args:
            records: The current set of PoemRecord objects to compare against.

        Returns:
            ``True`` if the fingerprints differ (or the stored fingerprint is
            unknown), ``False`` if the index matches the records exactly.
        """
        if self._index_content_fingerprint is None:
            return True
        return _compute_fingerprint(records) != self._index_content_fingerprint

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

        Raises:
            ValueError: If query_embedding is invalid (P0 hardening).
        """
        # P0: validate query embedding
        try:
            query_embedding = validate_embedding_vector(query_embedding, context="query embedding")
        except EmbeddingValidationError as e:
            raise ValueError(f"Invalid query embedding: {e}") from e

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

    def retrieve_graph_based(
        self,
        query_embedding: list[float],
        k: int = 5,
        depth: int = 1,
        form_filter: str | None = None,
        language_filter: str | None = None,
    ) -> list[tuple[str, float]]:
        """Graph-based retrieval: find seed nodes, then expand via ego_graph.

        This is more efficient than brute-force cosine when the graph is large,
        and provides contextually-related results by traversing semantic edges.

        Algorithm:
            1. Find top-m seed nodes by cosine similarity (m = k // 2 + 1)
            2. For each seed, expand to `depth`-hop neighbours via ego_graph
            3. Score all candidates by cosine similarity to query
            4. Return top-k unique results

        Args:
            query_embedding: Query vector to match against.
            k: Number of results to return.
            depth: Number of hops in ego_graph expansion (default 1).
            form_filter: Optional form name to restrict results.
            language_filter: Optional language code to restrict results.

        Returns:
            List of (poem_id, cosine_score) sorted by descending similarity.

        Raises:
            ValueError: If query_embedding is invalid (P0 hardening).
        """
        # P0: validate query embedding
        try:
            query_embedding = validate_embedding_vector(
                query_embedding, context="query embedding (graph-based)"
            )
        except EmbeddingValidationError as e:
            raise ValueError(f"Invalid query embedding: {e}") from e

        try:
            import networkx as nx  # type: ignore[import-untyped]
        except ImportError:
            return self.retrieve(query_embedding, k, form_filter, language_filter)

        if self._graph.number_of_nodes() == 0:
            return []

        # Step 1: Find seed nodes (top-m by cosine)
        m = max(k // 2 + 1, 3)  # At least 3 seeds
        seed_results = self.retrieve(query_embedding, m, form_filter, language_filter)
        if not seed_results:
            return []

        # Step 2: Expand each seed via ego_graph
        candidate_ids: set[str] = set()
        for seed_id, _ in seed_results:
            candidate_ids.add(seed_id)
            ego = nx.ego_graph(self._graph, seed_id, radius=depth)
            for node_id in ego.nodes:
                if node_id != seed_id:
                    # Apply filters to expanded nodes
                    attrs = self._graph.nodes.get(node_id, {})
                    if form_filter and attrs.get("form") != form_filter:
                        continue
                    if language_filter and attrs.get("language") != language_filter:
                        continue
                    candidate_ids.add(node_id)

        # Step 3: Score all candidates by cosine similarity
        scores: list[tuple[str, float]] = []
        for node_id in candidate_ids:
            attrs = self._graph.nodes.get(node_id, {})
            emb = attrs.get("embedding", [])
            if emb:
                score = _cosine(query_embedding, emb)
                scores.append((node_id, score))

        # Step 4: Return top-k
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:k]

    # ------------------------------------------------------------------
    # P2: Typed node/edge management
    # ------------------------------------------------------------------

    def add_fragment_node(
        self,
        fragment_id: str,
        content: str,
        language: str = "es",
        tags: list[str] | None = None,
        embedding: list[float] | None = None,
        embedding_client: Any | None = None,
    ) -> None:
        """Add a FragmentRecord as a typed graph node."""
        if embedding_client is not None:
            self.check_index_compatibility(embedding_client)
        emb = embedding or []
        if not emb and embedding_client and content:
            try:
                raw = embedding_client.embed_one(content, text_type="passage")
                emb = validate_embedding_vector(raw, context=f"fragment {fragment_id}")
                self._index_model_id = embedding_client.model_id
                self._index_embedding_dimension = embedding_client.dimension
            except (EmbeddingValidationError, Exception):
                emb = []

        self._graph.add_node(
            fragment_id,
            node_type=NodeType.fragment.value,
            content=content,
            language=language,
            tags=tags or [],
            embedding=emb,
        )
        if self.storage_path:
            self._save()

    def add_influence_node(
        self,
        influence_id: str,
        name: str,
        language: str = "es",
        tone: list[str] | None = None,
        movement: str | None = None,
        embedding: list[float] | None = None,
        embedding_client: Any | None = None,
    ) -> None:
        """Add an InfluenceRecord as a typed graph node."""
        if embedding_client is not None:
            self.check_index_compatibility(embedding_client)
        emb = embedding or []
        if not emb and embedding_client and tone:
            text = f"{name} {' '.join(tone)}"
            try:
                raw = embedding_client.embed_one(text, text_type="passage")
                emb = validate_embedding_vector(raw, context=f"influence {influence_id}")
                self._index_model_id = embedding_client.model_id
                self._index_embedding_dimension = embedding_client.dimension
            except (EmbeddingValidationError, Exception):
                emb = []

        self._graph.add_node(
            influence_id,
            node_type=NodeType.influence.value,
            name=name,
            language=language,
            tone=tone or [],
            movement=movement or "",
            embedding=emb,
        )
        if self.storage_path:
            self._save()

    def add_typed_edge(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType,
        weight: float = 1.0,
    ) -> None:
        """Add a typed directed edge between two existing nodes."""
        if source_id not in self._graph:
            raise ValueError(f"Source node '{source_id}' not found. Add it first.")
        if target_id not in self._graph:
            raise ValueError(f"Target node '{target_id}' not found. Add it first.")
        self._graph.add_edge(
            source_id,
            target_id,
            weight=round(weight, 4),
            relation_type=relation_type.value,
        )
        if self.storage_path:
            self._save()

    # ------------------------------------------------------------------
    # P2: Bounded typed traversal with explainable paths
    # ------------------------------------------------------------------

    def traverse(
        self,
        start_id: str,
        max_hops: int = 2,
        budget: int = 20,
        relation_types: list[RelationType] | None = None,
        node_types: list[NodeType] | None = None,
    ) -> list[GraphPath]:
        """Bounded typed BFS traversal returning explainable GraphPaths.

        Args:
            start_id: Node to start from.
            max_hops: Maximum hops from start (default 2).
            budget: Maximum total nodes to visit (default 20).
            relation_types: Edge type whitelist (None = all).
            node_types: Node type whitelist for results (None = all).

        Returns:
            List of GraphPath objects, shortest paths first.
        """
        if start_id not in self._graph:
            return []

        allowed_relations = {rt.value for rt in relation_types} if relation_types else None
        allowed_node_types = {nt.value for nt in node_types} if node_types else None

        from collections import deque

        paths: list[GraphPath] = []
        visited: set[str] = {start_id}
        queue: deque[GraphPath] = deque()

        for nbr in self._graph.successors(start_id):
            edge_data = self._graph[start_id][nbr]
            rel_val = edge_data.get("relation_type", RelationType.similar_to.value)
            if allowed_relations and rel_val not in allowed_relations:
                continue
            nbr_type_val = self._graph.nodes[nbr].get("node_type", NodeType.poem.value)
            try:
                nbr_type = NodeType(nbr_type_val)
                rel_type = RelationType(rel_val)
            except ValueError:
                nbr_type = NodeType.poem
                rel_type = RelationType.similar_to
            hop = GraphHop(
                node_id=nbr,
                node_type=nbr_type,
                relation_type=rel_type,
                weight=edge_data.get("weight", 1.0),
            )
            queue.append(GraphPath(origin_id=start_id, hops=[hop]))
            visited.add(nbr)

        while queue and len(paths) < budget:
            current_path = queue.popleft()
            endpoint = current_path.endpoint_id
            ep_type = self._graph.nodes[endpoint].get("node_type", NodeType.poem.value)
            if allowed_node_types is None or ep_type in allowed_node_types:
                paths.append(current_path)
            if current_path.depth < max_hops and len(paths) + len(queue) < budget:
                for nbr in self._graph.successors(endpoint):
                    if nbr in visited:
                        continue
                    edge_data = self._graph[endpoint][nbr]
                    rel_val = edge_data.get("relation_type", RelationType.similar_to.value)
                    if allowed_relations and rel_val not in allowed_relations:
                        continue
                    nbr_type_val = self._graph.nodes[nbr].get("node_type", NodeType.poem.value)
                    try:
                        nbr_type = NodeType(nbr_type_val)
                        rel_type = RelationType(rel_val)
                    except ValueError:
                        nbr_type = NodeType.poem
                        rel_type = RelationType.similar_to
                    hop = GraphHop(
                        node_id=nbr,
                        node_type=nbr_type,
                        relation_type=rel_type,
                        weight=edge_data.get("weight", 1.0),
                    )
                    queue.append(GraphPath(origin_id=start_id, hops=current_path.hops + [hop]))
                    visited.add(nbr)
        return paths

    def retrieve_with_paths(
        self,
        query_embedding: list[float],
        k: int = 5,
        max_hops: int = 2,
        budget: int = 30,
        relation_types: list[RelationType] | None = None,
        form_filter: str | None = None,
        language_filter: str | None = None,
    ) -> list[tuple[str, float, GraphPath | None]]:
        """Graph-enhanced retrieval returning (node_id, score, GraphPath|None).

        Seeds found by dense cosine; each seed is expanded via traverse().
        Results include the path from the nearest seed for display.

        Returns:
            (node_id, cosine_score, GraphPath|None) sorted by descending score.
        """
        try:
            query_embedding = validate_embedding_vector(
                query_embedding, context="query (retrieve_with_paths)"
            )
        except EmbeddingValidationError as e:
            raise ValueError(f"Invalid query embedding: {e}") from e

        if self._graph.number_of_nodes() == 0:
            return []

        m = max(k // 2 + 1, 3)
        seed_results = self.retrieve(query_embedding, m, form_filter, language_filter)
        if not seed_results:
            return []

        candidate_paths: dict[str, tuple[float, GraphPath | None]] = {}
        for seed_id, seed_score in seed_results:
            candidate_paths[seed_id] = (seed_score, None)

        seed_ids = [sid for sid, _ in seed_results]
        budget_per_seed = max(budget // len(seed_ids), 5) if seed_ids else budget
        for seed_id in seed_ids:
            for path in self.traverse(
                seed_id, max_hops=max_hops, budget=budget_per_seed, relation_types=relation_types
            ):
                ep = path.endpoint_id
                attrs = self._graph.nodes.get(ep, {})
                if form_filter and attrs.get("form") != form_filter:
                    continue
                if language_filter and attrs.get("language") != language_filter:
                    continue
                emb = attrs.get("embedding", [])
                if emb:
                    score = _cosine(query_embedding, emb)
                    if ep not in candidate_paths or score > candidate_paths[ep][0]:
                        candidate_paths[ep] = (score, path)

        scored = [(nid, sc, p) for nid, (sc, p) in candidate_paths.items()]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]

    def get_connected_influences(
        self,
        poem_id: str,
        influence_prefix: str = "influence:",
    ) -> list[tuple[str, float]]:
        """Get influences connected to a poem via semantic edges.

        Useful for finding which literary influences resonate with a given poem.

        Args:
            poem_id: The poem node ID.
            influence_prefix: Prefix used for influence node IDs.

        Returns:
            List of (influence_id, edge_weight) sorted by descending weight.
        """
        if poem_id not in self._graph:
            return []

        influences = []
        for nbr in self._graph.successors(poem_id):
            if nbr.startswith(influence_prefix):
                weight = self._graph[poem_id][nbr].get("weight", 0.0)
                influences.append((nbr, weight))

        # Also check reverse edges (influence → poem)
        for pred in self._graph.predecessors(poem_id):
            if pred.startswith(influence_prefix):
                weight = self._graph[pred][poem_id].get("weight", 0.0)
                if not any(inf_id == pred for inf_id, _ in influences):
                    influences.append((pred, weight))

        influences.sort(key=lambda x: x[1], reverse=True)
        return influences

    def node_count(self) -> int:
        return self._graph.number_of_nodes()

    def edge_count(self) -> int:
        return self._graph.number_of_edges()

    # ------------------------------------------------------------------
    # P3: Index compatibility and rebuild
    # ------------------------------------------------------------------

    def check_index_compatibility(self, embedding_client: Any) -> None:
        """Assert that embedding_client is compatible with the loaded index.

        Raises ``IndexCompatibilityError`` when the index was built with a
        different model or dimension than the client being used.  This
        prevents silently mixing incompatible embeddings — which produces
        wrong cosine scores with no visible error.

        The check is a no-op when the index is empty (no model recorded yet),
        because an empty index accepts any client.

        Args:
            embedding_client: An ``EmbeddingClient`` instance to check.

        Raises:
            IndexCompatibilityError: If model_id or embedding_dimension
                does not match the stored index metadata.
        """
        if self._index_model_id is None and self._index_embedding_dimension is None:
            # Empty index — no constraint yet
            return

        model_mismatch = (
            self._index_model_id is not None and self._index_model_id != embedding_client.model_id
        )
        dim_mismatch = (
            self._index_embedding_dimension is not None
            and self._index_embedding_dimension != embedding_client.dimension
        )

        if model_mismatch or dim_mismatch:
            raise IndexCompatibilityError(
                stored_model_id=self._index_model_id,
                stored_dimension=self._index_embedding_dimension,
                client_model_id=embedding_client.model_id,
                client_dimension=embedding_client.dimension,
            )

    def rebuild(
        self,
        records: list[PoemRecord],
        embedding_client: Any,
    ) -> None:
        """Clear the graph and re-ingest records with a new embedding client.

        Use this when swapping embedding models.  The graph is cleared first
        so that no old-model vectors survive — mixing vectors from different
        models would corrupt cosine similarity silently.

        After ``rebuild()`` the ``_index_model_id`` and
        ``_index_embedding_dimension`` reflect the new client, and the
        persisted JSON is updated atomically.

        Args:
            records: PoemRecord list to ingest fresh.
            embedding_client: The new EmbeddingClient.  Its model_id and
                dimension become the new index identity.
        """
        # Wipe all graph state
        self._graph = self._make_graph()
        self._index_model_id = None
        self._index_embedding_dimension = None

        # Re-ingest — compatibility check passes because index is empty
        self.ingest(records, embedding_client=embedding_client)

    def index_info(self) -> dict[str, Any]:
        """Return a summary of the current index metadata.

        Returns a dict with keys:
        - ``schema_version``: the format version string
        - ``model_id``: the embedding model recorded in the index (or ``None``)
        - ``embedding_dimension``: the vector size (or ``None``)
        - ``content_fingerprint``: SHA-256 hex digest of the ingested records
          (or ``None`` if the index was built before P3)
        - ``node_count``: number of nodes
        - ``edge_count``: number of edges
        """
        return {
            "schema_version": _SCHEMA_VERSION,
            "model_id": self._index_model_id,
            "embedding_dimension": self._index_embedding_dimension,
            "content_fingerprint": self._index_content_fingerprint,
            "node_count": self.node_count(),
            "edge_count": self.edge_count(),
        }

    # ------------------------------------------------------------------
    # Persistence (plain JSON, no pickle)
    # ------------------------------------------------------------------

    def _save(self) -> None:
        if not self.storage_path:
            return
        os.makedirs(self.storage_path.parent, exist_ok=True)
        data = {
            # Versioned header — enables compatibility checks on load
            "schema_version": _SCHEMA_VERSION,
            "model_id": self._index_model_id,
            "embedding_dimension": self._index_embedding_dimension,
            # P3: source fingerprint — SHA-256 over ingested (id, text) pairs
            "content_fingerprint": self._index_content_fingerprint,
            "nodes": {n: dict(attrs) for n, attrs in self._graph.nodes(data=True)},
            "edges": [
                {
                    "source": u,
                    "target": v,
                    "weight": d.get("weight", 0.0),
                    "relation_type": d.get("relation_type", RelationType.similar_to.value),
                }
                for u, v, d in self._graph.edges(data=True)
            ],
        }
        # P3: atomic write — write to a temp file then rename so a crash
        # mid-write can never leave a partially-written (corrupt) JSON.
        tmp_path = self.storage_path.with_suffix(".tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self.storage_path)
        finally:
            # Clean up the temp file if the rename didn't happen
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

    def _load(self) -> None:
        if not self.storage_path or not self.storage_path.exists():
            return
        try:
            with open(self.storage_path, encoding="utf-8") as f:
                data = json.load(f)

            # P2/P3: restore versioning metadata
            self._index_model_id = data.get("model_id")
            self._index_embedding_dimension = data.get("embedding_dimension")
            # P3: restore source fingerprint
            self._index_content_fingerprint = data.get("content_fingerprint")

            for node_id, attrs in data.get("nodes", {}).items():
                self._graph.add_node(node_id, **attrs)
            for edge in data.get("edges", []):
                self._graph.add_edge(
                    edge["source"],
                    edge["target"],
                    weight=edge.get("weight", 0.0),
                    relation_type=edge.get("relation_type", RelationType.similar_to.value),
                )
        except Exception:
            # Corrupt or incompatible JSON — start fresh
            self._graph = self._make_graph()
