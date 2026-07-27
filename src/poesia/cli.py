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
    llm: str = typer.Option("stub", help="LLM backend: 'stub', 'gemini', 'openai', 'groq', or 'auto'."),
    save: bool = typer.Option(False, "--save", help="Save the generated poem to the library (~/.poesia/poems/)."),
    tags: str = typer.Option(None, help="Comma-separated tags for the saved poem."),
    use_library: bool = typer.Option(False, "--use-library", help="Load existing poems from library for retrieval context."),
    show_alternatives: int = typer.Option(0, "--show-alternatives", help="Show top N alternative candidates per line with score breakdowns."),
    show_retrieval: bool = typer.Option(False, "--show-retrieval", help="Show which fragments and influences were retrieved for context."),
    interactive: bool = typer.Option(False, "--interactive", help="Choose each line interactively from scored candidates."),
) -> None:
    """Generate a poem using the constrained generate/validate/repair loop.

    With --brief, uses BriefBuilder to assemble rich context from personal
    fragments, seed expansions, and influence matching before generation.

    With --save, saves the generated poem to the personal library with full
    provenance metadata (model, seeds, tone, fragments used).

    With --use-library, loads existing poems from the library and uses them
    as additional context for semantic retrieval during generation.

    With --show-retrieval, prints which personal fragments and influences were
    retrieved and their similarity scores before generation begins.

    With --interactive, pauses after generating and scoring candidates for each
    line and lets you pick the one you want. Press Enter to accept the top-scored
    candidate, or type a number to choose another.

    LLM backends:
      - stub: Deterministic placeholder (default, no API key needed)
      - gemini: Google Gemini API (requires GEMINI_API_KEY env var)
      - openai: OpenAI API (requires OPENAI_API_KEY env var)
      - groq: Groq Cloud API (requires GROQ_API_KEY env var)
      - auto: Use first available API key (Gemini → Groq → OpenAI)
    """
    from poesia.generation.constrained_loop import ConstrainedLoop
    from poesia.generation.llm_client import HostedLLMClient, StubLLMClient

    # Parse comma-separated options
    tone_list = [t.strip() for t in tone.split(",")] if tone else None
    seeds_list = [s.strip() for s in seeds.split(",")] if seeds else None

    # Select LLM backend
    if llm == "stub":
        llm_client = StubLLMClient()
    elif llm in ("gemini", "openai", "groq", "auto"):
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
    library_poems = []
    semantic_mode_active = False  # Track if we have semantic scoring

    # P1: Load library poems as additional context if requested
    if use_library:
        from poesia.memoria.library import Library

        library = Library()
        library_poems = library.list_all()
        if library_poems:
            rprint(f"[dim]Loaded {len(library_poems)} poems from library for context[/dim]")

    if use_brief:
        from poesia.generation.brief_builder import BriefBuilder
        from poesia.memoria.embeddings import get_embedding_client

        # Load personal context if available
        fragments = _load_fragments()
        influences = _load_influences()

        # P1: Convert library poems to fragments for retrieval
        if library_poems:
            from poesia.memoria.records import FragmentRecord

            for poem in library_poems:
                # Convert poem content to a fragment for semantic retrieval
                frag = FragmentRecord(
                    id=f"library:{poem.id}",
                    content="\n".join(poem.lines),
                    language=poem.language,
                    tags=poem.tags,
                )
                fragments.append(frag)
            rprint(f"[dim]Added {len(library_poems)} library poems as retrieval context[/dim]")

        # Use real embedding client for semantic retrieval
        try:
            embedding_client = get_embedding_client()
            semantic_mode_active = True
            rprint("[green]✓[/green] [dim]Semantic scoring enabled (sentence-transformers)[/dim]")
        except Exception as e:
            from poesia.memoria.embeddings import StubEmbeddingClient
            embedding_client = StubEmbeddingClient()
            rprint(f"[yellow]⚠[/yellow]  [bold]Degraded mode:[/bold] No sentence-transformers available")
            rprint(f"[dim]   Theme and novelty scoring disabled. Install with: pip install -e '.[nlp]'[/dim]")
            rprint(f"[dim]   Error: {e}[/dim]")

        brief_builder = BriefBuilder(
            embedding_client=embedding_client,
            fragments=fragments,
            influences=influences,
        )

    # --show-retrieval: build a preview brief now just to show what was retrieved
    if show_retrieval and brief_builder is not None:
        from poesia.forms.definitions import get_form
        preview_brief = brief_builder.build(
            form=get_form(form),
            theme=theme,
            tone=tone_list,
            seeds=seeds_list,
            level=brief_level,
            language=language,
        )
        rprint("\n[bold]── Retrieved context ──[/bold]")
        if preview_brief.fragments:
            rprint(f"\n[bold]Fragments[/bold] ({len(preview_brief.fragments)} retrieved):")
            for frag, sim in preview_brief.fragments:
                rprint(f"  [cyan]{frag.id}[/cyan]  sim={sim:.3f}")
                first_line = frag.content.strip().split("\n")[0][:80]
                rprint(f"    [dim]{first_line}[/dim]")
        else:
            rprint("  [dim](no fragments retrieved — embeddings may be unavailable)[/dim]")
        if preview_brief.influences:
            rprint(f"\n[bold]Influences[/bold] ({len(preview_brief.influences)} matched):")
            for inf in preview_brief.influences:
                rprint(f"  [cyan]{inf.name}[/cyan]  tone: {', '.join(inf.tone[:3])}")
        if preview_brief.seeds_expanded:
            rprint(f"\n[bold]Seed expansions[/bold]:")
            for word, exp in preview_brief.seeds_expanded.items():
                syns = ", ".join(exp.synonyms[:4]) if exp.synonyms else "—"
                rprint(f"  [cyan]{word}[/cyan] → synonyms: {syns}")
        rprint()

    # --interactive: build a line_selector callback that pauses for human input
    line_selector = None
    if interactive:
        def _interactive_selector(line_index: int, candidates: list) -> str:
            rprint(f"\n[bold]── Line {line_index + 1} — choose a candidate ──[/bold]")
            for i, cand in enumerate(candidates[:8], 1):
                score_color = "green" if cand.score >= 0.7 else ("yellow" if cand.score >= 0.4 else "red")
                marker = " [bold green]★ top[/bold green]" if i == 1 else ""
                rprint(f"  [bold]{i}.[/bold] [{score_color}][{cand.score:.3f}][/{score_color}] {cand.line}{marker}")
                rprint(
                    f"     [dim]syllables={cand.scan.metrical_syllable_count}, "
                    f"metre={cand.breakdown['metre']:.2f}, "
                    f"rhyme={cand.breakdown['rhyme']:.2f}[/dim]"
                )
            while True:
                raw = input("  Pick (Enter = top, number = choice, t = type your own): ").strip()
                if raw == "":
                    return candidates[0].line
                if raw == "t":
                    own = input("  Your line: ").strip()
                    return own if own else candidates[0].line
                try:
                    idx = int(raw) - 1
                    if 0 <= idx < min(8, len(candidates)):
                        return candidates[idx].line
                    rprint(f"  [red]Enter 1–{min(8, len(candidates))}[/red]")
                except ValueError:
                    rprint("  [red]Enter a number, or press Enter[/red]")
        line_selector = _interactive_selector

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
        line_selector=line_selector,
    )

    rprint(f"[bold]Theme:[/bold] {theme}  [bold]Form:[/bold] {form}  [bold]Language:[/bold] {language}")
    if tone_list:
        rprint(f"[bold]Tone:[/bold] {', '.join(tone_list)}")
    if seeds_list:
        rprint(f"[bold]Seeds:[/bold] {', '.join(seeds_list)}")
    if result.brief:
        rprint(f"[bold]Brief level:[/bold] {result.brief.level}")
    
    # Show scoring mode status
    if not semantic_mode_active and not use_brief:
        rprint("[dim]Scoring mode: metre only (no semantic scoring)[/dim]")
    elif not semantic_mode_active and use_brief:
        rprint("[dim]Scoring mode: metre only (semantic scoring unavailable)[/dim]")
    else:
        rprint("[dim]Scoring mode: metre + theme + novelty[/dim]")
    
    rprint()
    for line in result.lines:
        rprint(line)

    # Show alternative candidates if requested
    if show_alternatives > 0 and result.scored_history:
        rprint()
        rprint("[bold cyan]═══ Alternative Candidates ═══[/bold cyan]")
        
        for line_idx, scored_candidates in enumerate(result.scored_history):
            # Get target syllables for this line
            target_syllables = loop.form_spec.syllables_for_line(line_idx)
            
            rprint(f"\n[bold]Line {line_idx + 1}[/bold] (target: {target_syllables} syllables):")
            
            # Show top N alternatives
            selected_line = result.lines[line_idx] if line_idx < len(result.lines) else None
            
            for rank, candidate in enumerate(scored_candidates[:show_alternatives], start=1):
                # Format score with color coding
                score_color = "green" if candidate.score >= 0.7 else "yellow" if candidate.score >= 0.4 else "red"
                
                # Truncate long lines for display
                display_line = candidate.line if len(candidate.line) <= 50 else candidate.line[:47] + "..."
                
                # Mark selected candidate
                selected_marker = " [bold green]✓[/bold green]" if candidate.line == selected_line else ""
                
                rprint(f"  {rank}. [{score_color}][{candidate.score:.3f}][/{score_color}] {display_line}{selected_marker}")
                
                # Show score breakdown
                rprint(
                    f"      [dim]syllables={candidate.scan.metrical_syllable_count}, "
                    f"metre={candidate.breakdown['metre']:.2f}, "
                    f"theme={candidate.breakdown['theme']:.2f}, "
                    f"novelty={candidate.breakdown['novelty']:.2f}[/dim]"
                )
                
                # Show validation issues if any
                if not candidate.scan.is_valid and candidate.scan.violations:
                    violations = ", ".join(candidate.scan.violations[:2])  # Show first 2
                    rprint(f"      [red]⚠ {violations}[/red]")

    # P1: Save to library with full provenance
    if save and result.lines:
        from poesia.memoria.library import Library, PoemProvenance, PoemRecord

        # Build provenance metadata
        provenance = PoemProvenance(
            model=getattr(llm_client, "model", None),
            embedding_model=getattr(embedding_client, "model_id", None) if embedding_client else None,
            brief_level=brief_level if use_brief else None,
            seeds=seeds_list or [],
            tone=tone_list or [],
            fragments_used=[f.id for f, _ in result.brief.fragments] if result.brief else [],
            influences_used=[i.id for i in result.brief.influences] if result.brief else [],
        )

        # Parse tags
        tags_list = [t.strip() for t in tags.split(",")] if tags else []

        record = PoemRecord(
            lines=result.lines,
            language=language,
            form=form,
            theme=theme,
            tags=tags_list,
            provenance=provenance,
        )

        library = Library()
        library.add(record)
        rprint(f"\n[green]✓[/green] Saved to library: [dim]{record.id}[/dim]")


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
    """Load influences from data/influences.yaml.

    Phase 4B+: Now uses structured YAML instead of regex-parsing markdown.
    """
    from poesia.memoria.influence_loader import load_influences

    try:
        return list(load_influences())
    except FileNotFoundError:
        return []


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
def memoria_list(
    form: str = typer.Option(None, help="Filter by form (e.g. 'soneto', 'haiku')."),
    language: str = typer.Option(None, help="Filter by language code ('es', 'en')."),
    limit: int = typer.Option(20, help="Maximum number of poems to show."),
) -> None:
    """List all poems saved in the personal library (~/.poesia/poems/)."""
    from poesia.memoria.library import Library

    library = Library()
    poems = library.list_all()

    # Apply filters
    if form:
        poems = [p for p in poems if p.form == form]
    if language:
        poems = [p for p in poems if p.language == language]

    if not poems:
        rprint("[dim]No poems in library yet. Use 'poesia write --save' to save one.[/dim]")
        return

    poems = poems[:limit]
    rprint(f"\n[bold]Library[/bold] ({len(poems)} poem{'s' if len(poems) != 1 else ''})\n")
    for poem in poems:
        date_str = poem.created_at.strftime("%Y-%m-%d %H:%M")
        tags_str = f"  [dim][{', '.join(poem.tags)}][/dim]" if poem.tags else ""
        rprint(f"  [cyan]{poem.id}[/cyan]")
        rprint(f"    [bold]{poem.theme}[/bold]  [{poem.form}, {poem.language}]  {date_str}{tags_str}")
        if poem.lines:
            preview = poem.lines[0][:70]
            rprint(f"    [dim]{preview}…[/dim]")
        rprint()


@memoria_app.command("search")
def memoria_search(
    query: str = typer.Argument(..., help="Substring to search across theme, tags and content."),
) -> None:
    """Search the personal library by substring match across theme, tags and content."""
    from poesia.memoria.library import Library

    library = Library()
    poems = library.search(query)

    if not poems:
        rprint(f"[dim]No poems found matching '{query}'.[/dim]")
        return

    rprint(f"\n[bold]Search results for '{query}'[/bold] ({len(poems)} found)\n")
    for poem in poems:
        date_str = poem.created_at.strftime("%Y-%m-%d %H:%M")
        rprint(f"  [cyan]{poem.id}[/cyan]  [{poem.form}, {poem.language}]  {date_str}")
        rprint(f"    [bold]{poem.theme}[/bold]")
        for line in poem.lines[:3]:
            rprint(f"    [dim]{line}[/dim]")
        if len(poem.lines) > 3:
            rprint(f"    [dim]… ({len(poem.lines)} lines total)[/dim]")
        rprint()


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
