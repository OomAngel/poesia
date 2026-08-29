"""BriefBuilder — assembles rich generation briefs from personal context.

The BriefBuilder is the bridge between MemorIA's retrieval layer and the
generation loop. It takes user inputs (form, theme, tone, seeds) and assembles
a dense, grounded prompt.

P2: BriefBuilder now calls the injected GraphRAGRetriever (when available)
via retrieve_with_paths() to obtain graph-traversal context. The retrieved
paths are stored in GenerationBrief.graph_paths for CLI display.

See docs/ENRICHMENT.md (Generation Brief section) for the full specification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

from poesia.forms.definitions import FormSpec, get_form
from poesia.memoria.records import FragmentRecord, InfluenceRecord, SeedExpansion
from poesia.memoria.seed_expander import SeedExpander

if TYPE_CHECKING:
    from poesia.memoria.embeddings import EmbeddingClient
    from poesia.memoria.graphrag import GraphRAGRetriever


@dataclass
class GenerationBrief:
    """A rich, grounded prompt for poem generation.

    P2 additions:
    - ``graph_paths``: explainable retrieval paths from GraphRAGRetriever
      (list of (node_id, score, GraphPath|None) triples).  Empty when only
      dense retrieval was used.
    """

    form_spec: FormSpec
    theme: str
    tone: list[str] = field(default_factory=list)
    fragments: list[tuple[FragmentRecord, float]] = field(default_factory=list)
    seeds_expanded: dict[str, SeedExpansion] = field(default_factory=dict)
    rhyme_options: dict[str, list[str]] = field(default_factory=dict)
    exemplar_lines: list[str] = field(default_factory=list)
    influences: list[InfluenceRecord] = field(default_factory=list)
    # Phase 4E: literary movement filter for influence matching
    movement: str | None = None
    # P2: graph retrieval results — (node_id, score, GraphPath|None)
    graph_paths: list[tuple[str, float, Any]] = field(default_factory=list)
    level: str = "standard"
    created_at: datetime = field(default_factory=datetime.now)

    def _lang_name(self) -> str:
        """Human-readable language name for the hard constraint line."""
        return {"es": "Spanish", "en": "English", "nl": "Dutch"}.get(
            self.form_spec.language, self.form_spec.language
        )

    def _form_section(self) -> list[str]:
        """Form metadata block."""
        lines = ["## FORM"]
        lines.append(f"- Name: {self.form_spec.name}")
        lines.append(f"- Language: {self.form_spec.language}")
        lines.append(f"- Lines: {self.form_spec.total_lines}")
        if self.form_spec.syllables_per_line > 0:
            lines.append(f"- Syllables/line: {self.form_spec.syllables_per_line}")
        if self.form_spec.rhyme_scheme:
            lines.append(f"- Rhyme: {self.form_spec.rhyme_scheme}\n")
        return lines

    def _tone_section(self) -> list[str]:
        """Tone block, when a tone list is set."""
        if not self.tone:
            return []
        lines = ["## TONE"]
        lines.extend(f"- {t}" for t in self.tone)
        lines.append("")
        return lines

    def _quality_section(self) -> list[str]:
        """Static poetic-quality directive."""
        return [
            "## QUALITY\n"
            "- Write with poetic imagery, metaphor, and musicality.\n"
            "- Prefer concrete images over abstract statements.\n"
            "- Each line should stand on its own as a beautiful phrase.\n"
            "- Avoid clichés, inverted word order for the sake of rhyme, "
            "and padding syllables with unnecessary words.\n"
        ]

    def _theme_section(self) -> list[str]:
        """Theme block."""
        return [f"## THEME\n- {self.theme}\n"]

    def _fragments_section(self) -> list[str]:
        """Personal-context fragment block, when fragments exist."""
        if not self.fragments:
            return []
        lines = ["## PERSONAL CONTEXT\n"]
        for frag, sim in self.fragments[:5]:
            lines.append(f"### {frag.id} (sim: {sim:.2f})")
            for ln in frag.content.strip().split("\n"):
                lines.append(f"> {ln}")
            lines.append("")
        return lines

    def _seeds_section(self) -> list[str]:
        """Seed-word expansion block, when seeds were expanded."""
        if not self.seeds_expanded:
            return []
        lines = ["## SEEDS + EXPANSIONS\n"]
        for word, exp in self.seeds_expanded.items():
            lines.append(f'### "{word}"')
            if exp.synonyms:
                lines.append(f"- Syn: {', '.join(exp.synonyms[:6])}")
            if exp.rhymes_consonant:
                for _end, rhy in list(exp.rhymes_consonant.items())[:1]:
                    if rhy:
                        lines.append(f"- Rhyme: {', '.join(rhy[:6])}")
            if exp.semantic_neighbors:
                lines.append(f"- Related: {', '.join(exp.semantic_neighbors[:5])}")
            lines.append("")
        return lines

    def _exemplars_section(self) -> list[str]:
        """Exemplar block (hidden for the minimal level)."""
        if not self.exemplar_lines or self.level == "minimal":
            return []
        lines = ["## EXEMPLARS\n"]
        lines.extend(f'> "{ex}"' for ex in self.exemplar_lines[:4])
        lines.append("")
        return lines

    def _influences_section(self) -> list[str]:
        """Influence block (hidden for the minimal level)."""
        if not self.influences or self.level == "minimal":
            return []
        lines = ["## INFLUENCES\n"]
        for inf in self.influences[:2]:
            movement_tag = f" ({inf.movement})" if inf.movement else ""
            lines.append(f"**{inf.name}**{movement_tag}: {', '.join(inf.tone[:3])}")
        lines.append("")
        return lines

    def _examples_section(self) -> list[str]:
        """Few-shot example block for the current form/language."""
        form_name = self.form_spec.name.lower()
        lang = self.form_spec.language
        if form_name == "haiku" and lang == "es":
            return [
                "## EXAMPLES (Spanish haiku)\n",
                "Tarde me viste,",
                "y al verte yo en el agua,",
                "tarde, lloraste.\n",
                "---\n",
                "Lluvia en el campo:",
                "sobre la tierra seca,",
                "olor a vida.\n",
            ]
        if form_name == "haiku" and lang == "en":
            return [
                "## EXAMPLES (English haiku)\n",
                "An old silent pond",
                "A frog jumps into the pond—",
                "Splash! Silence again.\n",
                "---\n",
                "Light of the moon",
                "Moves west, flowers' shadows",
                "Creep eastward.\n",
            ]
        if form_name == "soneto" and lang == "es":
            return [
                "## EXAMPLE (Spanish soneto — 11 syllables, ABBA ABBA CDC DCD)\n",
                "Un soneto me manda hacer Violante,",
                "que en mi vida me he visto en tal aprieto;",
                "catorce versos dicen que es soneto:",
                "burla burlando, van los tres delante.\n",
                "Yo pensé que no hallara consonante",
                "y estoy a la mitad de otro cuarteto;",
                "mas si me veo en el primer terceto,",
                "no hay cosa en los cuartetos que me espante.\n",
                "Por el primer terceto voy entrando,",
                "y parece que entré con pie derecho,",
                "pues fin con este verso le voy dando.\n",
                "Ya estoy en el segundo, y aun sospecho",
                "que voy los trece versos acabando:",
                "contad si son catorce, y está hecho.\n",
            ]
        return []

    def to_prompt(self) -> str:
        """Render the brief as an LLM prompt string."""
        lines = [f"# Generation Brief — {self.created_at.isoformat()}\n"]
        lines.append(
            f"IMPORTANT: You MUST write in {self._lang_name()}. Do NOT write in any other language.\n"
        )
        lines.extend(self._form_section())
        lines.extend(self._tone_section())
        lines.extend(self._quality_section())
        lines.extend(self._theme_section())
        lines.extend(self._fragments_section())
        lines.extend(self._seeds_section())
        lines.extend(self._exemplars_section())
        lines.extend(self._influences_section())
        lines.extend(self._examples_section())
        lines.append("---")
        lines.append(f"Generate a {self.form_spec.name} on '{self.theme}'.")
        return "\n".join(lines)


class BriefBuilder:
    """Assembles GenerationBriefs from user inputs + retrieved context."""

    def __init__(
        self,
        embedding_client: EmbeddingClient | None = None,
        retriever: GraphRAGRetriever | None = None,
        fragments: list[FragmentRecord] | None = None,
        influences: list[InfluenceRecord] | None = None,
    ) -> None:
        """Initialize BriefBuilder.

        Args:
            embedding_client: For semantic similarity (optional).
            retriever: GraphRAG retriever for past poems (optional).
            fragments: Pre-loaded personal fragments (optional).
            influences: Pre-loaded influence records (optional).
        """
        self._embedding_client = embedding_client
        self._retriever = retriever
        self._fragments = fragments or []
        self._influences = influences or []
        self._fragment_embeddings: list[list[float]] | None = None

    def add_fragments(self, fragments: list[FragmentRecord]) -> None:
        """Add personal context fragments."""
        self._fragments.extend(fragments)
        self._fragment_embeddings = None  # Invalidate cache

    def add_influences(self, influences: list[InfluenceRecord]) -> None:
        """Add influence records."""
        self._influences.extend(influences)

    def build(
        self,
        form: str | FormSpec,
        theme: str,
        tone: list[str] | None = None,
        seeds: list[str] | None = None,
        level: Literal["minimal", "standard", "maximal"] = "standard",
        language: str | None = None,
        movement: str | None = None,
    ) -> GenerationBrief:
        """Build a generation brief.

        Args:
            form: Form name (str) or FormSpec.
            theme: Central theme for the poem.
            tone: List of tonal qualities (e.g., ["melancholic", "tender"]).
            seeds: List of seed words to expand.
            level: Brief verbosity (minimal/standard/maximal).
            language: Override language for seed expansion.
            movement: Filter influences by literary movement (e.g., "Generacion del 98").

        Returns:
            GenerationBrief ready for LLM prompt rendering.
        """
        # Resolve form (validated against `language` if the caller knows it
        # yet — see `get_form`'s docstring for why that matters)
        form_spec = get_form(form, language) if isinstance(form, str) else form
        lang = language or form_spec.language

        # Expand seeds
        seeds_expanded = {}
        if seeds:
            expander = SeedExpander(language=lang)
            reference_corpus = self._build_reference_corpus()
            for word in seeds:
                seeds_expanded[word] = expander.expand(
                    word,
                    embedding_client=self._embedding_client,
                    reference_corpus=reference_corpus if self._embedding_client else None,
                )

        # Retrieve similar fragments
        fragments_scored: list[tuple[FragmentRecord, float]] = []
        if self._fragments and self._embedding_client:
            fragments_scored = self._retrieve_fragments(theme, k=5)

        # P2: retrieve from graph when retriever is wired and embedding is available
        graph_paths: list[tuple[str, float, Any]] = []
        if self._retriever is not None and self._embedding_client is not None:
            query_emb = self._embedding_client.embed_one(theme, text_type="query")
            try:
                graph_paths = self._retriever.retrieve_with_paths(query_emb, k=5, max_hops=2)
            except Exception:
                # Graph retrieval is best-effort; never crash brief assembly
                graph_paths = []

        # Match influences by tone and/or movement
        matched_influences: list[InfluenceRecord] = []
        if self._influences:
            matched_influences = self._match_influences(tone or [], movement)

        return GenerationBrief(
            form_spec=form_spec,
            theme=theme,
            tone=tone or [],
            fragments=fragments_scored,
            seeds_expanded=seeds_expanded,
            influences=matched_influences,
            movement=movement,
            graph_paths=graph_paths,
            level=level,
        )

    def _retrieve_fragments(self, query: str, k: int = 5) -> list[tuple[FragmentRecord, float]]:
        """Retrieve fragments most similar to the query."""
        import math

        if not self._embedding_client or not self._fragments:
            return []

        # Embed query — retrieval queries use "query: " prefix in e5 models
        query_emb = self._embedding_client.embed_one(query, text_type="query")

        # Lazy-compute fragment embeddings — stored documents use "passage: " prefix
        if self._fragment_embeddings is None:
            texts = [f.content for f in self._fragments]
            self._fragment_embeddings = self._embedding_client.embed(texts, text_type="passage")

        # Score fragments
        scores = []
        for frag, emb in zip(self._fragments, self._fragment_embeddings, strict=True):
            dot = sum(a * b for a, b in zip(query_emb, emb, strict=True))
            norm_q = math.sqrt(sum(a * a for a in query_emb))
            norm_e = math.sqrt(sum(b * b for b in emb))
            sim = dot / (norm_q * norm_e) if norm_q > 0 and norm_e > 0 else 0.0
            scores.append((frag, sim))

        # Sort and return top k
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:k]

    def _match_influences(
        self, tone: list[str], movement: str | None = None
    ) -> list[InfluenceRecord]:
        """Find influences matching the requested tone and/or literary movement.

        Args:
            tone: List of tonal qualities to match.
            movement: Optional literary movement to filter by (e.g. "Romanticism").

        Returns:
            Up to 3 best-matching influence records.
        """
        candidates = self._influences

        # Filter by movement first if specified
        if movement:
            from poesia.memoria.influence_loader import get_influences_by_movement

            movement_ids = {i.id for i in get_influences_by_movement(movement)}
            candidates = [i for i in candidates if i.id in movement_ids]
            if not candidates:
                # Movement filter narrowed to zero — return empty gracefully
                return []

        # Then score by tone overlap
        if not tone:
            return candidates[:3]

        tone_set = set(t.lower() for t in tone)
        scored = []
        for inf in candidates:
            inf_tones = set(t.lower() for t in inf.tone)
            overlap = len(tone_set & inf_tones)
            if overlap > 0:
                scored.append((inf, overlap))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [inf for inf, _ in scored[:3]]

    def _build_reference_corpus(self) -> list[str]:
        """Build a word corpus for semantic expansion."""
        words = set()
        for frag in self._fragments:
            words.update(frag.content.lower().split())
        for inf in self._influences:
            words.update(t.lower() for t in inf.tone)
        return list(words)
