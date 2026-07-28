"""BriefBuilder — assembles rich generation briefs from personal context.

The BriefBuilder is the bridge between MemorIA's retrieval layer and the
generation loop. It takes user inputs (form, theme, tone, seeds) and assembles
a dense, grounded prompt.

P2: BriefBuilder now calls the injected GraphRAGRetriever (when available)
via retrieve_with_paths() to obtain graph-traversal context. The retrieved
paths are stored in GenerationBrief.graph_paths for CLI display.

See docs/GENERATION_BRIEF.md for the full specification.
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
    from poesia.memoria.graphrag import GraphPath, GraphRAGRetriever


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
    # P2: graph retrieval results — (node_id, score, GraphPath|None)
    graph_paths: list[tuple[str, float, Any]] = field(default_factory=list)
    level: str = "standard"
    created_at: datetime = field(default_factory=datetime.now)

    def to_prompt(self) -> str:
        """Render the brief as an LLM prompt string."""
        lines = [f"# Generation Brief — {self.created_at.isoformat()}\n"]

        # ── HARD LANGUAGE CONSTRAINT ────────────────────────────────
        lang_name = {"es": "Spanish", "en": "English", "nl": "Dutch"}.get(
            self.form_spec.language, self.form_spec.language
        )
        lines.append(f"IMPORTANT: You MUST write in {lang_name}. Do NOT write in any other language.\n")

        # Form
        lines.append("## FORM")
        lines.append(f"- Name: {self.form_spec.name}")
        lines.append(f"- Language: {self.form_spec.language}")
        lines.append(f"- Lines: {self.form_spec.total_lines}")
        if self.form_spec.syllables_per_line > 0:
            lines.append(f"- Syllables/line: {self.form_spec.syllables_per_line}")
        if self.form_spec.rhyme_scheme:
            lines.append(f"- Rhyme: {self.form_spec.rhyme_scheme}\n")

        # Tone
        if self.tone:
            lines.append("## TONE")
            lines.extend(f"- {t}" for t in self.tone)
            lines.append("")

        # ── POETIC QUALITY DIRECTIVE ─────────────────────────────────
        lines.append(
            "## QUALITY\n"
            "- Write with poetic imagery, metaphor, and musicality.\n"
            "- Prefer concrete images over abstract statements.\n"
            "- Each line should stand on its own as a beautiful phrase.\n"
            "- Avoid clichés, inverted word order for the sake of rhyme, "
            "and padding syllables with unnecessary words.\n"
        )

        # Theme
        lines.append(f"## THEME\n- {self.theme}\n")

        # Fragments
        if self.fragments:
            lines.append("## PERSONAL CONTEXT\n")
            for frag, sim in self.fragments[:5]:
                lines.append(f"### {frag.id} (sim: {sim:.2f})")
                for ln in frag.content.strip().split("\n"):
                    lines.append(f"> {ln}")
                lines.append("")

        # Seeds
        if self.seeds_expanded:
            lines.append("## SEEDS + EXPANSIONS\n")
            for word, exp in self.seeds_expanded.items():
                lines.append(f'### "{word}"')
                if exp.synonyms:
                    lines.append(f"- Syn: {', '.join(exp.synonyms[:6])}")
                if exp.rhymes_consonant:
                    for end, rhy in list(exp.rhymes_consonant.items())[:1]:
                        if rhy:
                            lines.append(f"- Rhyme: {', '.join(rhy[:6])}")
                if exp.semantic_neighbors:
                    lines.append(f"- Related: {', '.join(exp.semantic_neighbors[:5])}")
                lines.append("")

        # Exemplars
        if self.exemplar_lines and self.level != "minimal":
            lines.append("## EXEMPLARS\n")
            for ex in self.exemplar_lines[:4]:
                lines.append(f'> "{ex}"')
            lines.append("")

        # Influences
        if self.influences and self.level == "maximal":
            lines.append("## INFLUENCES\n")
            for inf in self.influences[:2]:
                lines.append(f"**{inf.name}**: {', '.join(inf.tone[:3])}")
            lines.append("")

        # ── FEW-SHOT EXAMPLES ────────────────────────────────────────────
        # Show the model what a good poem in *this* form looks like
        form_name = self.form_spec.name.lower()
        lang = self.form_spec.language

        if form_name == "haiku" and lang == "es":
            lines.append("## EXAMPLES (Spanish haiku)\n")
            lines.append("Tarde me viste,")
            lines.append("y al verte yo en el agua,")
            lines.append("tarde, lloraste.\n")
            lines.append("---\n")
            lines.append("Lluvia en el campo:")
            lines.append("sobre la tierra seca,")
            lines.append("olor a vida.\n")

        elif form_name == "haiku" and lang == "en":
            lines.append("## EXAMPLES (English haiku)\n")
            lines.append("An old silent pond")
            lines.append("A frog jumps into the pond—")
            lines.append("Splash! Silence again.\n")
            lines.append("---\n")
            lines.append("Light of the moon")
            lines.append("Moves west, flowers' shadows")
            lines.append("Creep eastward.\n")

        elif form_name == "soneto" and lang == "es":
            lines.append("## EXAMPLE (Spanish soneto — 11 syllables, ABBA ABBA CDC DCD)\n")
            lines.append("Un soneto me manda hacer Violante,")
            lines.append("que en mi vida me he visto en tal aprieto;")
            lines.append("catorce versos dicen que es soneto:")
            lines.append("burla burlando, van los tres delante.\n")
            lines.append("Yo pensé que no hallara consonante")
            lines.append("y estoy a la mitad de otro cuarteto;")
            lines.append("mas si me veo en el primer terceto,")
            lines.append("no hay cosa en los cuartetos que me espante.\n")
            lines.append("Por el primer terceto voy entrando,")
            lines.append("y parece que entré con pie derecho,")
            lines.append("pues fin con este verso le voy dando.\n")
            lines.append("Ya estoy en el segundo, y aun sospecho")
            lines.append("que voy los trece versos acabando:")
            lines.append("contad si son catorce, y está hecho.\n")

        # Instruction
        lines.append("---")
        lines.append(f"Generate a {self.form_spec.name} on '{self.theme}'.")

        return "\n".join(lines)


class BriefBuilder:
    """Assembles GenerationBriefs from user inputs + retrieved context."""

    def __init__(
        self,
        embedding_client: "EmbeddingClient | None" = None,
        retriever: "GraphRAGRetriever | None" = None,
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
    ) -> GenerationBrief:
        """Build a generation brief.

        Args:
            form: Form name (str) or FormSpec.
            theme: Central theme for the poem.
            tone: List of tonal qualities (e.g., ["melancholic", "tender"]).
            seeds: List of seed words to expand.
            level: Brief verbosity (minimal/standard/maximal).
            language: Override language for seed expansion.

        Returns:
            GenerationBrief ready for LLM prompt rendering.
        """
        # Resolve form
        form_spec = get_form(form) if isinstance(form, str) else form
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
                graph_paths = self._retriever.retrieve_with_paths(
                    query_emb, k=5, max_hops=2
                )
            except Exception:
                # Graph retrieval is best-effort; never crash brief assembly
                graph_paths = []

        # Match influences by tone
        matched_influences: list[InfluenceRecord] = []
        if tone and self._influences:
            matched_influences = self._match_influences(tone)

        return GenerationBrief(
            form_spec=form_spec,
            theme=theme,
            tone=tone or [],
            fragments=fragments_scored,
            seeds_expanded=seeds_expanded,
            influences=matched_influences,
            graph_paths=graph_paths,
            level=level,
        )

    def _retrieve_fragments(
        self, query: str, k: int = 5
    ) -> list[tuple[FragmentRecord, float]]:
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
        for frag, emb in zip(self._fragments, self._fragment_embeddings):
            dot = sum(a * b for a, b in zip(query_emb, emb))
            norm_q = math.sqrt(sum(a * a for a in query_emb))
            norm_e = math.sqrt(sum(b * b for b in emb))
            sim = dot / (norm_q * norm_e) if norm_q > 0 and norm_e > 0 else 0.0
            scores.append((frag, sim))

        # Sort and return top k
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:k]

    def _match_influences(self, tone: list[str]) -> list[InfluenceRecord]:
        """Find influences matching the requested tone."""
        tone_set = set(t.lower() for t in tone)
        scored = []
        for inf in self._influences:
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
