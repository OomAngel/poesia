"""Command-line entry point for PoesIA.

Mounts five subcommands, one per -IA sub-brand, plus the two root commands
(write/scan) belonging to the core poesía (generation+validation) vertical.
See README.md for the naming rationale.

Phase 0: thin Typer apps exposing interfaces for manual experimentation.
Most subcommands are stubs that raise NotImplementedError until their
respective backend lands (see docs/ROADMAP.md).
"""

from __future__ import annotations

import typer
from rich import print as rprint

app = typer.Typer(help="PoesIA: a hybrid poetry-writing engine.")


# --- Core: poesia write / poesia scan ---------------------------------------


@app.command()
def write(
    theme: str = typer.Option(..., help="Thematic anchor, e.g. 'lluvia sobre piedra'."),
    language: str = typer.Option("es", help="Language code: 'es', 'en', or 'nl'."),
    form: str = typer.Option("soneto", help="Registered form name, see poesia.forms.definitions."),
    n_candidates: int = typer.Option(16, help="Candidate lines generated per position."),
    tone: str = typer.Option(None, help="Comma-separated tone descriptors, e.g. 'melancholic,intimate'."),
    seeds: str = typer.Option(None, help="Comma-separated seed words to expand for rhymes/synonyms."),
    brief_level: str = typer.Option("standard", help="Brief verbosity: minimal, standard, or maximal."),
    use_brief: bool = typer.Option(False, "--brief", help="Use BriefBuilder for rich pre-generation context."),
    llm: str = typer.Option("stub", help="LLM backend: 'stub', 'gemini', 'openai', or 'auto'."),
) -> None:
    """Generate a poem using the constrained generate/validate/repair loop.

    With --brief, uses BriefBuilder to assemble rich context from personal
    fragments, seed expansions, and influence matching before generation.

    LLM backends:
      - stub: Deterministic placeholder (default, no API key needed)
      - gemini: Google Gemini API (requires GEMINI_API_KEY env var)
      - openai: OpenAI API (requires OPENAI_API_KEY env var)
      - auto: Use first available API key (Gemini preferred)
    """
    from poesia.generation.constrained_loop import ConstrainedLoop
    from poesia.generation.llm_client import HostedLLMClient, StubLLMClient

    # Parse comma-separated options
    tone_list = [t.strip() for t in tone.split(",")] if tone else None
    seeds_list = [s.strip() for s in seeds.split(",")] if seeds else None

    # Select LLM backend
    if llm == "stub":
        llm_client = StubLLMClient()
    elif llm in ("gemini", "openai", "auto"):
        llm_client = HostedLLMClient(provider=llm)
        rprint(f"[dim]Using LLM: {llm_client.provider} ({llm_client.model})[/dim]")
    else:
        rprint(f"[red]Unknown LLM backend: {llm}. Using stub.[/red]")
        llm_client = StubLLMClient()

    # Build the loop with optional brief builder
    brief_builder = None
    embedding_client = None
    fragments = []
    influences = []

    if use_brief:
        from poesia.generation.brief_builder import BriefBuilder
        from poesia.memoria.embeddings import get_embedding_client

        # Load personal context if available
        fragments = _load_fragments()
        influences = _load_influences()

        # Use real embedding client for semantic retrieval
        try:
            embedding_client = get_embedding_client()
            rprint("[dim]Using sentence-transformers for semantic scoring[/dim]")
        except Exception as e:
            from poesia.memoria.embeddings import StubEmbeddingClient
            embedding_client = StubEmbeddingClient()
            rprint(f"[dim]Falling back to stub embeddings: {e}[/dim]")

        brief_builder = BriefBuilder(
            embedding_client=embedding_client,
            fragments=fragments,
            influences=influences,
        )

    loop = ConstrainedLoop(
        language=language,
        form=form,
        llm=llm_client,
        brief_builder=brief_builder,
        embedding_client=embedding_client,
        fragments=fragments,
        influences=influences,
    )
    result = loop.run(
        theme=theme,
        n_candidates=n_candidates,
        tone=tone_list,
        seeds=seeds_list,
        brief_level=brief_level,
    )

    rprint(f"[bold]Theme:[/bold] {theme}  [bold]Form:[/bold] {form}  [bold]Language:[/bold] {language}")
    if tone_list:
        rprint(f"[bold]Tone:[/bold] {', '.join(tone_list)}")
    if seeds_list:
        rprint(f"[bold]Seeds:[/bold] {', '.join(seeds_list)}")
    if result.brief:
        rprint(f"[bold]Brief level:[/bold] {result.brief.level}")
    rprint()
    for line in result.lines:
        rprint(line)


def _load_fragments() -> list:
    """Load personal fragments from seeds/angel_fragments/ if available."""
    from pathlib import Path

    from poesia.memoria.records import FragmentRecord

    fragments = []
    fragments_dir = Path(__file__).parent.parent.parent / "seeds" / "angel_fragments"
    if fragments_dir.exists():
        for md_file in sorted(fragments_dir.glob("*.md")):
            content = md_file.read_text(encoding="utf-8")
            frag = FragmentRecord(
                id=md_file.stem,
                content=content,
                language="es",  # Default to Spanish for now
                tags=[],
            )
            fragments.append(frag)
    return fragments


def _load_influences() -> list:
    """Load influences from docs/INFLUENCE_REGISTRY.md with full profile parsing.

    Phase 4B: Extracts movement, era, tone, forms, and exemplars from the registry.
    """
    import re
    from pathlib import Path

    from poesia.memoria.records import InfluenceRecord

    influences = []
    registry_path = Path(__file__).parent.parent.parent / "docs" / "INFLUENCE_REGISTRY.md"
    if not registry_path.exists():
        return influences

    content = registry_path.read_text(encoding="utf-8")
    current_section_lang = "es"  # Default language based on section

    # Track current poet data
    current: dict = {}

    def _save_current():
        if current.get("name"):
            influences.append(
                InfluenceRecord(
                    id=current["name"].lower().replace(" ", "_").replace(".", ""),
                    name=current["name"],
                    language=current.get("language", "es"),
                    movement=current.get("movement"),
                    era=current.get("era"),
                    tone=current.get("tone", []),
                    forms=current.get("forms", []),
                    exemplars=current.get("exemplars", []),
                )
            )

    for line in content.split("\n"):
        # Section headers determine language
        if line.startswith("## Spanish") or line.startswith("## Latin"):
            current_section_lang = "es"
            continue
        if line.startswith("## English") or line.startswith("## American"):
            current_section_lang = "en"
            continue
        if line.startswith("## Dutch"):
            current_section_lang = "nl"
            continue

        # Poet header: ### Name (years)
        if line.startswith("### "):
            _save_current()
            header = line[4:].strip()
            # Extract name and era from "Name (1875-1939)"
            match = re.match(r"^(.+?)\s*\(([^)]+)\)$", header)
            if match:
                current = {"name": match.group(1).strip(), "era": match.group(2).strip()}
            else:
                current = {"name": header}
            current["language"] = current_section_lang
            continue

        # Parse attributes (strip markdown bold markers)
        def _clean_md(s: str) -> str:
            """Remove markdown bold markers and extra whitespace."""
            return re.sub(r"\*\*", "", s).strip().strip('"')

        if "**Movement:**" in line or "- Movement:" in line:
            val = line.split(":", 1)[1].strip() if ":" in line else ""
            current["movement"] = _clean_md(val)
        elif "**Tone:**" in line or "- Tone:" in line:
            val = line.split(":", 1)[1].strip() if ":" in line else ""
            current["tone"] = [_clean_md(t) for t in val.split(",") if t.strip()]
        elif "**Forms:**" in line or "- Forms:" in line:
            val = line.split(":", 1)[1].strip() if ":" in line else ""
            current["forms"] = [_clean_md(f) for f in val.split(",") if f.strip()]
        elif "**Exemplars:**" in line or "- Exemplars:" in line:
            val = line.split(":", 1)[1].strip() if ":" in line else ""
            # Split on · or " · " separator
            current["exemplars"] = [_clean_md(e) for e in re.split(r"\s*·\s*", val) if e.strip()]

    _save_current()
    return influences


@app.command()
def scan(
    line: str = typer.Argument(..., help="A single line of verse to scan."),
    language: str = typer.Option("es", help="Language code: 'es', 'en', or 'nl'."),
) -> None:
    """Scan a single line for syllable count, stress and validity."""
    from poesia.phonology.english import EnglishPhonology
    from poesia.phonology.spanish import SpanishPhonology

    if language == "es":
        phonology = SpanishPhonology()
    elif language == "nl":
        from poesia.phonology.dutch import DutchPhonology
        phonology = DutchPhonology()
    else:
        phonology = EnglishPhonology()
    result = phonology.scan_line(line)
    rprint(result)


# --- EufonIA: sound/euphony analysis ----------------------------------------

eufonia_app = typer.Typer(help="EufonIA: sound/euphony analysis for a poem.")


@eufonia_app.command("analyze")
def eufonia_analyze(
    path: str = typer.Argument(..., help="Path to a text file, one line of verse per line."),
    language: str = typer.Option("es", help="Language code: 'es' or 'en'."),
) -> None:
    """Analyze rhyme scheme, assonance/consonance and cacophony for a poem."""
    from poesia.eufonia.analyzer import EuphonyAnalyzer
    from poesia.phonology.english import EnglishPhonology
    from poesia.phonology.spanish import SpanishPhonology

    phonology = SpanishPhonology() if language == "es" else EnglishPhonology()
    with open(path, encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip()]
    scans = [phonology.scan_line(ln) for ln in lines]
    report = EuphonyAnalyzer().analyze(scans)
    rprint(report)


app.add_typer(eufonia_app, name="eufonia")


# --- GalerIA: illustration ---------------------------------------------------

galeria_app = typer.Typer(help="GalerIA: illustration for a poem (auca-style).")


@galeria_app.command("illustrate")
def galeria_illustrate(
    path: str = typer.Argument(..., help="Path to a text file with the poem."),
    style: str = typer.Option("grabado español", help="Style tag passed to the image backend."),
    output: str = typer.Option("auca.pdf", help="Output PDF path."),
    use_influences: bool = typer.Option(False, "--style-from-influences", help="Derive style from matched influences."),
    tone: str = typer.Option(None, help="Comma-separated tones for influence matching."),
) -> None:
    """Generate an illustrated auca-style sheet for a poem.

    With --style-from-influences, derives visual style from poetic influences
    matched by the provided tones. Maps movements like Generación del 98,
    Romanticism, Surrealism to appropriate visual styles.
    """
    from poesia.galeria.auca import AucaComposer, AucaPanel
    from poesia.galeria.backends import StubImageBackend

    with open(path, encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip()]

    # Phase 4C: Style anchoring from influences
    final_style = style
    if use_influences:
        from poesia.galeria.style_anchoring import style_from_influences

        influences = _load_influences()
        if tone:
            tone_list = [t.strip().lower() for t in tone.split(",")]
            # Filter influences by matching tones
            matched = [
                inf for inf in influences
                if any(t in [it.lower() for it in inf.tone] for t in tone_list)
            ]
        else:
            matched = influences[:5]  # Use first 5 if no tone specified

        influence_style = style_from_influences(matched)
        if influence_style:
            final_style = f"{influence_style}, {style}"
            rprint(f"[dim]Style from influences: {influence_style}[/dim]")

    backend = StubImageBackend()
    image_bytes = backend.generate_image(prompt=" ".join(lines), style=final_style)
    panel = AucaPanel(image_bytes=image_bytes, caption_lines=lines)
    composer = AucaComposer()
    composer.export_pdf([panel], output_path=output)  # raises NotImplementedError today


app.add_typer(galeria_app, name="galeria")


# --- MemorIA: collections / future Graph RAG ---------------------------------

memoria_app = typer.Typer(help="MemorIA: personal poem collection (Graph RAG in Phase 3).")


@memoria_app.command("list")
def memoria_list() -> None:
    """List all poems saved in the personal library (stub, in-memory only)."""
    rprint("[dim]Library is in-memory only in Phase 0 — nothing persisted yet.[/dim]")


@memoria_app.command("search")
def memoria_search(query: str = typer.Argument(..., help="Substring to search for.")) -> None:
    """Search the personal library by naive substring match (stub)."""
    rprint(f"[dim]Search for '{query}' — persistence not yet implemented (Phase 1).[/dim]")


@memoria_app.command("add-fragment")
def memoria_add_fragment(
    path: str = typer.Argument(..., help="Path to a markdown file with the fragment content."),
    tags: str = typer.Option("", help="Comma-separated tags for the fragment."),
    language: str = typer.Option("es", help="Language code: 'es' or 'en'."),
) -> None:
    """Add a personal fragment to the memoria collection."""
    from pathlib import Path

    from poesia.memoria.records import FragmentRecord

    file_path = Path(path)
    if not file_path.exists():
        rprint(f"[red]Error:[/red] File not found: {path}")
        raise typer.Exit(1)

    content = file_path.read_text(encoding="utf-8")
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    frag = FragmentRecord(id=file_path.stem, content=content, language=language, tags=tag_list)

    # Copy to seeds/angel_fragments/ for persistence
    target_dir = Path(__file__).parent.parent.parent / "seeds" / "angel_fragments"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / file_path.name
    target_path.write_text(content, encoding="utf-8")

    rprint(f"[green]✓[/green] Added fragment '{frag.id}' → {target_path}")


@memoria_app.command("add-seed")
def memoria_add_seed(
    word: str = typer.Argument(..., help="The seed word to expand."),
    language: str = typer.Option("es", help="Language code: 'es' or 'en'."),
) -> None:
    """Add a seed word and expand it with rhymes, synonyms, etc."""
    from poesia.memoria.embeddings import StubEmbeddingClient
    from poesia.memoria.seed_expander import SeedExpander

    expander = SeedExpander(language=language)
    embedding_client = StubEmbeddingClient()
    expansion = expander.expand(word, embedding_client=embedding_client)

    rprint(f"[green]✓[/green] Seed '{word}' ({language})")
    if expansion.synonyms:
        rprint(f"  Synonyms: {', '.join(expansion.synonyms[:8])}")
    if expansion.rhymes_consonant:
        for ending, rhymes in list(expansion.rhymes_consonant.items())[:2]:
            if rhymes:
                rprint(f"  Rhymes ({ending}): {', '.join(rhymes[:6])}")


@memoria_app.command("add-influence")
def memoria_add_influence(
    name: str = typer.Argument(..., help="Name of the poet or work."),
    tone: str = typer.Option(..., help="Comma-separated tone descriptors."),
    language: str = typer.Option("es", help="Language code: 'es' or 'en'."),
) -> None:
    """Add a poetic influence to the memoria."""
    from poesia.memoria.records import InfluenceRecord

    tone_list = [t.strip() for t in tone.split(",") if t.strip()]
    influence = InfluenceRecord(
        id=name.lower().replace(" ", "_"), name=name, language=language, tone=tone_list
    )
    rprint(f"[green]✓[/green] Added influence '{influence.name}' — tone: {', '.join(tone_list)}")
    rprint(f"[dim]  (To persist, add to docs/INFLUENCE_REGISTRY.md)[/dim]")


@memoria_app.command("list-fragments")
def memoria_list_fragments() -> None:
    """List all personal fragments in seeds/angel_fragments/."""
    from pathlib import Path

    fragments_dir = Path(__file__).parent.parent.parent / "seeds" / "angel_fragments"
    if not fragments_dir.exists():
        rprint("[dim]No fragments directory found.[/dim]")
        return

    md_files = sorted(fragments_dir.glob("*.md"))
    if not md_files:
        rprint("[dim]No fragments found.[/dim]")
        return

    rprint(f"[bold]Personal fragments ({len(md_files)} total):[/bold]\n")
    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8")
        lines = [l.strip() for l in content.split("\n") if l.strip()]
        preview = lines[0][:60] + "..." if lines and len(lines[0]) > 60 else (lines[0] if lines else "(empty)")
        rprint(f"  [cyan]{md_file.stem}[/cyan]: {preview}")


@memoria_app.command("list-influences")
def memoria_list_influences() -> None:
    """List all influences from docs/INFLUENCE_REGISTRY.md."""
    influences = _load_influences()
    if not influences:
        rprint("[dim]No influences found.[/dim]")
        return

    rprint(f"[bold]Poetic influences ({len(influences)} total):[/bold]\n")
    for inf in influences:
        tone_str = ", ".join(inf.tone[:4]) if inf.tone else "(no tone)"
        rprint(f"  [cyan]{inf.name}[/cyan]: {tone_str}")


app.add_typer(memoria_app, name="memoria")


# --- ArmonIA: music -----------------------------------------------------------

armonia_app = typer.Typer(help="ArmonIA: turn a poem's prosody into music or recitation.")


@armonia_app.command("rhythm")
def armonia_rhythm(
    line: str = typer.Argument(..., help="A single line of verse to convert to rhythm."),
    language: str = typer.Option("es", help="Language code: 'es' or 'en'."),
) -> None:
    """Show the rhythmic pulse sequence derived from a line's stress pattern."""
    from poesia.armonia.prosody_to_rhythm import stress_pattern_to_pulses
    from poesia.phonology.english import EnglishPhonology
    from poesia.phonology.spanish import SpanishPhonology

    phonology = SpanishPhonology() if language == "es" else EnglishPhonology()
    result = phonology.scan_line(line)
    pulses = stress_pattern_to_pulses(result.stress_pattern)
    for pulse in pulses:
        rprint(pulse)


app.add_typer(armonia_app, name="armonia")


if __name__ == "__main__":
    app()
