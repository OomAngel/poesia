"""Command-line entry point for PoesIA.

Mounts five subcommands, one per -IA sub-brand, plus the two root commands
(write/scan) belonging to the core poesía (generation+validation) vertical.
See README.md for the naming rationale.

Phase 0: thin Typer apps exposing interfaces for manual experimentation.
Most subcommands are stubs that raise NotImplementedError until their
respective backend lands (see docs/ROADMAP.md).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, cast

import typer
from rich import print as rprint

if TYPE_CHECKING:
    from poesia.phonology.base import PhonologyBackend


def _load_dotenv(dotenv_path: str | None = None) -> None:
    """Best-effort ``.env`` loading so credentials are one line to set up.

    ``poesia`` reads ``.env`` from the current directory at startup
    (``cp .env.example .env`` → fill in → done). Existing shell-exported
    variables take precedence (``override=False``). Never raises: a broken or
    missing ``.env`` must not stop the CLI.
    """
    from pathlib import Path

    try:
        from dotenv import load_dotenv

        load_dotenv(dotenv_path or Path.cwd() / ".env", override=False)
    except Exception:  # pragma: no cover - defensive best-effort
        pass


def _make_interactive_selector(loop, language: str, form: str):
    """Build the human-writes-first line selector used by write/workshop.

    The human keeps the editor's seat: pick a candidate (Enter = top, number
    = choice) or type your own line — which is scanned and *taught* against
    the line position's target before it is kept (POSITIONING §7.2–7.3).
    """

    def _interactive_selector(line_index: int, candidates: list) -> str:
        rprint(f"\n[bold]── Line {line_index + 1} —— choose a candidate ──[/bold]")
        for i, cand in enumerate(candidates[:8], 1):
            score_color = (
                "green" if cand.score >= 0.7 else ("yellow" if cand.score >= 0.4 else "red")
            )
            marker = " [bold green]★ top[/bold green]" if i == 1 else ""
            rprint(
                f"  [bold]{i}.[/bold] [{score_color}][{cand.score:.3f}][/{score_color}] {cand.line}{marker}"
            )
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
                if not own:
                    return candidates[0].line
                # Teaching voice: your line is scanned and explained
                # against this line position's target before it is kept.
                from poesia.teaching import teach_scan

                target_syl = loop.form_spec.syllables_for_line(line_index)
                own_scan = loop._phonology.scan_line(own)
                lesson = teach_scan(
                    own_scan,
                    target_syl,
                    language=language,
                    form_name=form,
                )
                for msg in lesson.messages:
                    rprint(f"  [cyan]•[/cyan] {msg}")
                return own
            try:
                idx = int(raw) - 1
                if 0 <= idx < min(8, len(candidates)):
                    return candidates[idx].line
                rprint(f"  [red]Enter 1–{min(8, len(candidates))}[/red]")
            except ValueError:
                rprint("  [red]Enter a number, or press Enter[/red]")

    return _interactive_selector


_load_dotenv()

app = typer.Typer(help="PoesIA: a hybrid poetry-writing engine.")


# --- Core: poesia write / poesia scan ---------------------------------------


@app.command()
def write(
    theme: str = typer.Option(..., help="Thematic anchor."),
    language: str = typer.Option("es", help="Language code: 'es', 'en', 'nl'."),
    form: str = typer.Option("soneto", help="Registered form name."),
    n_candidates: int = typer.Option(16, help="Candidate lines per position."),
    tone: str = typer.Option(None, help="Comma-separated tone descriptors."),
    seeds: str = typer.Option(None, help="Comma-separated seed words."),
    brief_level: str = typer.Option("standard", help="Brief verbosity."),
    use_brief: bool = typer.Option(False, "--brief", help="Use BriefBuilder."),
    semantic: bool = typer.Option(
        False,
        "--semantic",
        help="Enable semantic theme/novelty scoring without personal context "
        "(needs sentence-transformers).",
    ),
    llm: str = typer.Option("stub", help="LLM backend."),
    save: bool = typer.Option(False, "--save", help="Save to library."),
    no_title: bool = typer.Option(
        False,
        "--no-title",
        help="Disable automatic LLM title suggestion for the saved poem.",
    ),
    tags: str = typer.Option(None, help="Comma-separated tags."),
    reflection: str = typer.Option(
        None,
        "--reflection",
        help="What you meant or felt, stored beside the poem in memoria.",
    ),
    use_library: bool = typer.Option(False, "--use-library"),
    show_alternatives: int = typer.Option(0, "--show-alternatives"),
    show_retrieval: bool = typer.Option(False, "--show-retrieval"),
    interactive: bool = typer.Option(False, "--interactive"),
    yes: bool = typer.Option(False, "--yes"),
    lines: int = typer.Option(None, "--lines"),
    movement: str = typer.Option(None, "--movement"),
    illustrate: bool = typer.Option(
        False, "--illustrate", help="Generate an illustrated auca sheet for the poem."
    ),
    image_backend: str = typer.Option(
        "auto",
        "--image-backend",
        help="Image backend for --illustrate: auto, stub, procedural, pollinations, cloudflare, openai, replicate.",
    ),
) -> None:
    """Generate a poem using WriteConfig + Registry pattern."""
    from poesia.config.types import WriteConfig
    from poesia.generation.registry import get_llm, list_backends

    # Build validated config
    tone_list = [t.strip() for t in tone.split(",")] if tone else None
    seeds_list = [s.strip() for s in seeds.split(",")] if seeds else None

    config = WriteConfig.build(
        theme=theme,
        form=form,
        language=language,
        llm=llm,
        n_candidates=n_candidates,
        max_repair_attempts=2,
        tone=tone_list,
        seeds=seeds_list,
        brief_level=brief_level,
        use_brief=use_brief,
        semantic=semantic,
        save=save,
        tags=[t.strip() for t in tags.split(",")] if tags else None,
        use_library=use_library,
        show_alternatives=show_alternatives,
        show_retrieval=show_retrieval,
        interactive=interactive,
        yes=yes,
        lines=lines,
        movement=movement,
    )

    # Resolve LLM client via registry
    try:
        llm_client = get_llm(config.llm)
    except ValueError as e:
        rprint(f"[red]{e}[/red]")
        rprint(f"[dim]Available backends: {', '.join(list_backends())}[/dim]")
        raise typer.Exit(1) from None

    rprint(
        f"[dim]Using LLM: {llm_client.provider + ' ' if hasattr(llm_client, 'provider') else ''}"
        f"({llm_client.model if hasattr(llm_client, 'model') else config.llm})[/dim]"
    )

    # Build the loop with optional brief builder
    brief_builder = None
    embedding_client = None
    fragments = []
    influences = []
    library_poems = []
    semantic_mode_active = False  # Track if we have semantic scoring

    # P1: Load library poems as additional context if requested
    if use_library:
        from poesia.memoria.graphrag import GraphRAGRetriever
        from poesia.memoria.library import Library

        library = Library()
        library_poems = library.list_all()
        if library_poems:
            rprint(f"[dim]Loaded {len(library_poems)} poems from library for context[/dim]")

        # P3: warn when the persisted graph index may be stale relative to the
        # current library — the user should run `poesia memoria rebuild` to
        # re-index and restore accurate retrieval.
        if library_poems:
            _retriever_check = GraphRAGRetriever()
            if _retriever_check.is_stale(library_poems):
                rprint(
                    "[yellow]⚠[/yellow]  [bold]Graph index may be stale.[/bold] "
                    "Library content has changed since the last index build. "
                    "Run [bold]poesia memoria rebuild[/bold] to re-index."
                )

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
            rprint(
                "[yellow]⚠[/yellow]  [bold]Degraded mode:[/bold] No sentence-transformers available"
            )
            rprint(
                "[dim]   Theme and novelty scoring disabled. Install with: pip install -e '.[nlp]'[/dim]"
            )
            rprint(f"[dim]   Error: {e}[/dim]")

        brief_builder = BriefBuilder(
            embedding_client=embedding_client,
            fragments=fragments,
            influences=influences,
        )

    # --semantic: real theme/novelty scoring WITHOUT loading personal context
    # (no angel_fragments, no influences) — the clean path for better ranking
    # of candidates against the theme alone.
    if semantic and embedding_client is None:
        from poesia.memoria.embeddings import get_embedding_client

        try:
            embedding_client = get_embedding_client()
            semantic_mode_active = True
            rprint("[green]✓[/green] [dim]Semantic scoring enabled (sentence-transformers)[/dim]")
        except Exception as e:
            from poesia.memoria.embeddings import StubEmbeddingClient

            embedding_client = StubEmbeddingClient()
            rprint(
                "[yellow]⚠[/yellow]  [bold]Degraded mode:[/bold] No sentence-transformers available"
            )
            rprint(
                "[dim]   Theme and novelty scoring disabled. Install with: pip install -e '.[nlp]'[/dim]"
            )
            rprint(f"[dim]   Error: {e}[/dim]")

    # --show-retrieval: build a preview brief now just to show what was retrieved
    if show_retrieval and brief_builder is not None:
        from poesia.forms.definitions import get_form

        preview_brief = brief_builder.build(
            form=get_form(form),
            theme=theme,
            tone=tone_list,
            seeds=seeds_list,
            level=cast(Literal["minimal", "standard", "maximal"], brief_level),
            language=language,
            movement=movement,
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
        if preview_brief.graph_paths:
            rprint(f"\n[bold]Graph retrieval[/bold] ({len(preview_brief.graph_paths)} results):")
            for node_id, score, path in preview_brief.graph_paths:
                if path is not None:
                    path_str = path.to_display_string()
                    rprint(
                        f"  [cyan]{node_id}[/cyan]  score={score:.3f}  via: [dim]{path_str}[/dim]"
                    )
                else:
                    rprint(f"  [cyan]{node_id}[/cyan]  score={score:.3f}  [dim](dense seed)[/dim]")
        if preview_brief.influences:
            rprint(f"\n[bold]Influences[/bold] ({len(preview_brief.influences)} matched):")
            for inf in preview_brief.influences:
                rprint(f"  [cyan]{inf.name}[/cyan]  tone: {', '.join(inf.tone[:3])}")
        if preview_brief.seeds_expanded:
            rprint("\n[bold]Seed expansions[/bold]:")
            for word, exp in preview_brief.seeds_expanded.items():
                syns = ", ".join(exp.synonyms[:4]) if exp.synonyms else "—"
                rprint(f"  [cyan]{word}[/cyan] → synonyms: {syns}")
        rprint()

    # --interactive: build a line_selector callback that pauses for human input.
    # The loop must exist first (the selector scans typed lines through it), so
    # it is created right after ConstrainedLoop below.
    line_selector = None
    if not yes and llm not in ("stub",):
        # Default when using a real LLM without --yes: quick 3-choice picker
        def _quick_selector(line_index: int, candidates: list) -> str:
            rprint(f"\n[bold]Line {line_index + 1}:[/bold] pick a candidate (Enter = best)")
            for i, cand in enumerate(candidates[:3], 1):
                marker = " [bold green]★ best[/bold green]" if i == 1 else ""
                rprint(f"  [{i}] {cand.line}{marker}")
            try:
                raw = input("  Your choice [1-3, Enter=best]: ").strip()
                if raw == "":
                    return candidates[0].line
                idx = int(raw) - 1
                if 0 <= idx < min(3, len(candidates)):
                    return candidates[idx].line
            except (ValueError, EOFError):
                pass
            return candidates[0].line

        line_selector = _quick_selector

    # P5: Privacy confirmation — warn before personal context reaches a hosted provider
    _hosted_providers = {"groq", "gemini", "openai", "auto"}
    if use_brief and fragments and llm.lower() in _hosted_providers and not yes:
        provider_name = llm_client.provider if hasattr(llm_client, "provider") else llm
        rprint()
        rprint("[bold yellow]⚠ PRIVACY NOTICE[/bold yellow]")
        rprint(
            f"  [yellow]Personal fragments will be sent to [bold]{provider_name}[/bold].[/yellow]"
        )
        rprint(f"  [yellow]Fragments ({len(fragments)} loaded):[/yellow]")
        for frag in fragments[:5]:
            rprint(f"    [dim]- {frag.id}[/dim]")
        if len(fragments) > 5:
            rprint(f"    [dim]- ... and {len(fragments) - 5} more[/dim]")
        rprint()
        try:
            confirm = (
                input("  Type [bold]yes[/bold] to continue, or anything else to cancel: ")
                .strip()
                .lower()
            )
        except (EOFError, KeyboardInterrupt):
            confirm = "no"
        if confirm != "yes":
            rprint("[red]✗[/red] Generation cancelled. Use [bold]--yes[/bold] to skip this prompt.")
            raise typer.Exit(0)
        rprint()

    from poesia.generation.constrained_loop import ConstrainedLoop

    loop = ConstrainedLoop(
        language=language,
        form=form,
        llm=llm_client,
        brief_builder=brief_builder,
        embedding_client=embedding_client,
        fragments=fragments,
        influences=influences,
    )
    if interactive:
        line_selector = _make_interactive_selector(loop, language, form)
    # P5: Time the generation for latency provenance
    import time as _time

    _t0 = _time.time()
    result = loop.run(
        theme=theme,
        n_candidates=n_candidates,
        tone=tone_list,
        seeds=seeds_list,
        brief_level=brief_level,
        line_selector=line_selector,
        total_lines_override=lines,
        movement=movement,
    )
    _gen_latency_ms = int((_time.time() - _t0) * 1000)

    rprint(
        f"[bold]Theme:[/bold] {theme}  [bold]Form:[/bold] {form}  [bold]Language:[/bold] {language}"
    )
    if tone_list:
        rprint(f"[bold]Tone:[/bold] {', '.join(tone_list)}")
    if seeds_list:
        rprint(f"[bold]Seeds:[/bold] {', '.join(seeds_list)}")
    if result.brief:
        rprint(f"[bold]Brief level:[/bold] {result.brief.level}")

    # Show scoring mode status
    if semantic_mode_active:
        rprint("[dim]Scoring mode: metre + theme + novelty[/dim]")
    elif semantic and not use_brief:
        rprint("[dim]Scoring mode: metre only (semantic scoring unavailable)[/dim]")
    elif not use_brief:
        rprint("[dim]Scoring mode: metre only (no semantic scoring)[/dim]")
    else:
        rprint("[dim]Scoring mode: metre only (semantic scoring unavailable)[/dim]")

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
                score_color = (
                    "green"
                    if candidate.score >= 0.7
                    else "yellow"
                    if candidate.score >= 0.4
                    else "red"
                )

                # Truncate long lines for display
                display_line = (
                    candidate.line if len(candidate.line) <= 50 else candidate.line[:47] + "..."
                )

                # Mark selected candidate
                selected_marker = (
                    " [bold green]✓[/bold green]" if candidate.line == selected_line else ""
                )

                rprint(
                    f"  {rank}. [{score_color}][{candidate.score:.3f}][/{score_color}] {display_line}{selected_marker}"
                )

                # Show score breakdown
                rprint(
                    f"      [dim]syllables={candidate.scan.metrical_syllable_count}, "
                    f"metre={candidate.breakdown['metre']:.2f}, "
                    f"theme={candidate.breakdown['theme']:.2f}, "
                    f"novelty={candidate.breakdown['novelty']:.2f}[/dim]"
                )

                # Show teaching voice: why the line missed, and how to fix it
                if not candidate.scan.is_valid and candidate.scan.violations:
                    violations = ", ".join(candidate.scan.violations[:2])  # Show first 2
                    rprint(f"      [red]⚠ {violations}[/red]")
                elif not candidate.scan.is_valid:
                    from poesia.teaching import teach_scan

                    lesson = teach_scan(
                        candidate.scan,
                        target_syllables,
                        language=language,
                        form_name=form,
                    )
                    for msg in lesson.messages[:2]:
                        rprint(f"      [red]⚠ {msg}[/red]")

    # P1: Save to library with full provenance
    if save and result.lines:
        from poesia.memoria.library import Library, PoemProvenance, PoemRecord

        # LLM-suggested title (fail-open; skipped for the deterministic stub
        # backend and with an explicit --no-title).
        title = ""
        if not no_title and config.llm != "stub":
            from poesia.generation.titles import suggest_title

            title = suggest_title(result.lines, language, form, theme, llm_client)
            if title:
                rprint(f"\n[bold cyan]Suggested title:[/bold cyan] {title}")

        # Build provenance metadata
        provenance = PoemProvenance(
            model=getattr(llm_client, "model", None),
            provider=getattr(llm_client, "provider", None),
            embedding_model=getattr(embedding_client, "model_id", None)
            if embedding_client
            else None,
            brief_level=brief_level if use_brief else None,
            seeds=seeds_list or [],
            tone=tone_list or [],
            fragments_used=[f.id for f, _ in result.brief.fragments] if result.brief else [],
            influences_used=[i.id for i in result.brief.influences] if result.brief else [],
            n_candidates=n_candidates,
            temperature=getattr(llm_client, "temperature", None),
            latency_ms=_gen_latency_ms,
            total_tokens=getattr(llm_client, "usage", None) and llm_client.usage.total_tokens,
        )

        # Parse tags
        tags_list = [t.strip() for t in tags.split(",")] if tags else []

        # Reflection: what the person meant or felt, stored beside the poem.
        # From --reflection, or prompted after the draft is on screen
        # (reflection is a first-class step — POSITIONING §7.4). Skipped when
        # --yes, so the flow stays scriptable.
        reflection_text = reflection or ""
        if save and not reflection_text and not yes and not interactive:
            try:
                rprint()
                rprint("[bold cyan]What were you carrying when you wrote this?[/bold cyan]")
                rprint("[dim](optional — this stays private, beside your poem)[/dim]")
                reflection_text = input("  Reflection: ").strip()
            except (EOFError, KeyboardInterrupt):
                reflection_text = ""

        record = PoemRecord(
            lines=result.lines,
            language=language,
            form=form,
            title=title,
            reflection=reflection_text,
            theme=theme,
            tags=tags_list,
            provenance=provenance,
        )

        library = Library()
        library.add(record)
        saved_label = f" — [bold]{record.title}[/bold]" if record.title else ""
        reflected_label = " [dim](with reflection)[/dim]" if record.reflection else ""
        rprint(
            f"\n[green]✓[/green] Saved to library: [dim]{record.id}[/dim]"
            f"{saved_label}{reflected_label}"
        )

    # GalerIA: generate an illustrated sheet that goes with the poem
    if illustrate and result.lines:
        rprint("\n[bold]── Illustration ──[/bold]")
        saved_id = record.id if save else None
        sheet_path = _illustrate_lines(
            result.lines,
            language=language,
            theme=theme,
            backend=image_backend,
            influences=[i for i in result.brief.influences] if result.brief else None,
            poem_id=saved_id,
        )
        if sheet_path:
            rprint(f"[green]✓[/green] Illustrated sheet: [bold]{sheet_path}[/bold]")
            # Persist the link in the library frontmatter so the poem knows its
            # illustration (path relative to the poem's Markdown file).
            if save and saved_id:
                try:
                    library.attach_image(saved_id, f"illustrations/{saved_id}.png")
                except (FileNotFoundError, ValueError) as e:
                    rprint(f"[yellow]⚠[/yellow] [bold]image: not recorded:[/bold] {e}")


def _illustrate_lines(
    lines: list[str],
    *,
    language: str,
    theme: str,
    backend: str,
    influences: list | None = None,
    poem_id: str | None = None,
) -> str | None:
    """Best-effort GalerIA illustration for generated poem lines.

    Saves an auca sheet PNG under ``~/.poesia/poems/illustrations/`` when the
    poem was saved to the library, otherwise under ``galeria/`` in the current
    directory. Returns the output path, or None when illustration was skipped.
    """
    import re
    from datetime import datetime
    from pathlib import Path

    from poesia.galeria.auca import AucaComposer
    from poesia.galeria.pipeline import illustrate_poem

    try:
        panels, _prompts = illustrate_poem(
            lines,
            language=language,
            theme=theme,
            style="grabado español",
            backend=backend,
            influences=influences,
        )
    except Exception as e:
        rprint(f"[yellow]⚠[/yellow] [bold]Illustration skipped:[/bold] {e}")
        return None

    composer = AucaComposer()
    sheet_png = composer.compose_sheet(panels, title=f"PoesIA — {theme or 'Auca'}")

    if poem_id:
        out_dir = Path.home() / ".poesia" / "poems" / "illustrations"
    else:
        out_dir = Path("galeria")
    out_dir.mkdir(parents=True, exist_ok=True)
    if poem_id:
        out_path = out_dir / f"{poem_id}.png"
    else:
        slug = re.sub(r"[^\w\-]", "_", theme.lower())[:30] if theme else "poema"
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = out_dir / f"{slug}_{stamp}.png"
    out_path.write_bytes(sheet_png)
    return str(out_path)


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


def _retrieve_style_texts(
    theme: str,
    poem_text: str,
    language: str,
    k: int = 4,
) -> list[str]:
    """Retrieve library poems semantically similar to the current poem/theme.

    Used by ``galeria illustrate --style-from-retrieval``. Returns the contents
    of the top-``k`` library poems (YAML frontmatter stripped). Gracefully
    returns ``[]`` — with a printed note — when embeddings, the retrieval
    index, or matching library entries are unavailable, so the CLI never
    hard-fails on a missing optional dependency.
    """
    from poesia.memoria.library import Library

    try:
        from poesia.memoria.embeddings import get_embedding_client
        from poesia.memoria.graphrag import GraphRAGRetriever
    except ImportError:
        rprint(
            "[dim]Style-from-retrieval skipped: embeddings unavailable "
            "(pip install -e '.[nlp]').[/dim]"
        )
        return []

    try:
        retriever = GraphRAGRetriever()
        if retriever.node_count() == 0:
            rprint(
                "[dim]Style-from-retrieval skipped: no retrieval index "
                "(build one with `poesia memoria ingest`).[/dim]"
            )
            return []
        client = get_embedding_client()
        retriever.check_index_compatibility(client)
        query = theme if theme.strip() else poem_text
        query_embedding = client.embed_one(query, text_type="query")
        hits = retriever.retrieve(query_embedding, k=k)
    except Exception as exc:  # noqa: BLE001 - graceful optional-feature degradation
        rprint(f"[dim]Style-from-retrieval skipped: {exc}[/dim]")
        return []

    library = Library()
    texts: list[str] = []
    for poem_id, _score in hits:
        poem = library.get(poem_id)
        if poem is None:
            continue
        content = poem.content
        if content.lstrip().startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                content = parts[2]
        content = content.strip()
        if content:
            texts.append(content)
        if len(texts) >= k:
            break
    return texts


@app.command()
def scan(
    line: str = typer.Argument(..., help="A single line of verse to scan."),
    language: str = typer.Option("es", help="Language code: 'es', 'en', or 'nl'."),
    form: str = typer.Option(
        None,
        "--form",
        help="Poetic form to teach against (e.g. 'soneto', 'haiku').",
    ),
    syllables: int = typer.Option(
        None,
        "--syllables",
        help="Explicit target syllable count to teach against (overrides --form).",
    ),
) -> None:
    """Scan a single line — and teach *why* it does or doesn't fit a target.

    With ``--form`` or ``--syllables`` the scan becomes a lesson: it explains
    the metrical count, points at any sinalefas or final-word stress effects,
    and tells you exactly how to fix a line that is over or short.
    """
    from poesia.phonology.english import EnglishPhonology
    from poesia.phonology.spanish import SpanishPhonology
    from poesia.teaching import format_scan

    if language == "es":
        phonology: PhonologyBackend = SpanishPhonology()
    elif language == "nl":
        from poesia.phonology.dutch import DutchPhonology

        phonology = DutchPhonology()
    else:
        phonology = EnglishPhonology()
    result = phonology.scan_line(line)

    form_name = None
    target = syllables
    if form and target is None:
        from poesia.forms.definitions import get_form

        spec = get_form(form)
        form_name = spec.name
        # For patterned forms (e.g. haiku 5-7-5), teach against the first
        # line's target; the poem-level loop teaches each line position.
        target = spec.syllables_for_line(0)

    rprint(format_scan(result, target, language=language, form_name=form_name))


@app.command()
def workshop(
    outlet: str = typer.Option(
        None,
        "--outlet",
        help="What you are carrying, pre-written (skips the outlet prompt).",
    ),
    language: str = typer.Option("es", help="Language code: 'es', 'en', or 'nl'."),
    form: str = typer.Option("soneto", help="Registered form name."),
    llm: str = typer.Option("stub", help="LLM backend (drafts are scaffolding)."),
    n_candidates: int = typer.Option(16, help="Candidate lines per position."),
    save: bool = typer.Option(False, "--save", help="Save to library with the reflection."),
    no_title: bool = typer.Option(
        False,
        "--no-title",
        help="Disable automatic LLM title suggestion for the saved poem.",
    ),
    tags: str = typer.Option(None, help="Comma-separated tags."),
) -> None:
    """The four movements, guided: outlet → shaping → teaching → linking.

    You start from what you feel, not from a command. The workshop walks the
    human-first path (docs/POSITIONING.md): write what you carry (outlet),
    shape it line by line — pick or type each line, and every line you type
    is scanned and taught (shaping + teaching) — then, if you choose to
    save, the poem and your reflection are kept together in memoria
    (linking). The machine never holds the pen; it holds the craft.
    """
    from poesia.generation.constrained_loop import ConstrainedLoop
    from poesia.generation.registry import get_llm
    from poesia.teaching import format_scan

    # 1. OUTLET — what are you carrying?
    reflection_text = (outlet or "").strip()
    if outlet is not None and not reflection_text:
        rprint("[yellow]⚠[/yellow] An empty outlet has nothing to shape.")
        raise typer.Exit(1)
    if not reflection_text:
        try:
            rprint("\n[bold cyan]What are you carrying?[/bold cyan]")
            rprint(
                "[dim]A thought, a feeling, a grievance, a joy that never "
                "became words. Write it as it comes; nobody else will read it.[/dim]"
            )
            reflection_text = input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            rprint("\n[dim]Nothing carried today — closing the workshop.[/dim]")
            raise typer.Exit(0) from None
    if not reflection_text:
        rprint("[yellow]⚠[/yellow] An empty outlet has nothing to shape.")
        raise typer.Exit(1)

    theme = reflection_text[:80]
    rprint(f"\n[dim]Carrying:[/dim] [bold]“{theme}”[/bold]\n")

    # 2. SHAPING + 3. TEACHING — draft line by line, keeping the editor's seat.
    llm_client = get_llm(llm)
    loop = ConstrainedLoop(language=language, form=form, llm=llm_client)
    line_selector = _make_interactive_selector(loop, language, form)
    result = loop.run(theme=theme, n_candidates=n_candidates, line_selector=line_selector)

    rprint("\n[bold cyan]═══ Your poem, as shaped ═══[/bold cyan]\n")
    for line in result.lines:
        rprint(line)

    # Teaching recap: every line of the finished draft scanned and explained.
    rprint("\n[bold cyan]═══ The craft, explained ═══[/bold cyan]")
    phonology = loop._phonology
    for i, line in enumerate(result.lines):
        target = loop.form_spec.syllables_for_line(i)
        scan = phonology.scan_line(line)
        rprint(f"\n[bold]Line {i + 1}[/bold]")
        rprint(format_scan(scan, target, language=language, form_name=form))

    # 4. LINKING — save the poem with its reflection, if the human decides to.
    if save:
        from poesia.generation.titles import suggest_title
        from poesia.memoria.library import Library, PoemProvenance, PoemRecord

        title = ""
        if not no_title and llm != "stub":
            title = suggest_title(result.lines, language, form, theme, llm_client)
            if title:
                rprint(f"\n[bold cyan]Suggested title:[/bold cyan] {title}")

        tags_list = [t.strip() for t in tags.split(",")] if tags else []
        record = PoemRecord(
            lines=result.lines,
            language=language,
            form=form,
            title=title,
            reflection=reflection_text,
            theme=theme,
            tags=tags_list,
            provenance=PoemProvenance(
                model=getattr(llm_client, "model", None),
                provider=getattr(llm_client, "provider", None),
                n_candidates=n_candidates,
                temperature=getattr(llm_client, "temperature", None),
            ),
        )
        library = Library()
        library.add(record)
        saved_label = f" — [bold]{record.title}[/bold]" if record.title else ""
        rprint(
            f"\n[green]✓[/green] Saved to library: [dim]{record.id}[/dim]"
            f"{saved_label} [dim](with reflection)[/dim]"
        )


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
    path: str = typer.Argument(None, help="Path to a text file with the poem."),
    style: str = typer.Option("grabado español", help="Style tag appended to the image prompt."),
    backend: str = typer.Option(
        "auto",
        help="Image backend: auto, stub, procedural, pollinations, cloudflare, openai, replicate.",
    ),
    api_key: str = typer.Option(
        None,
        "--api-key",
        help="API key override (default: OPENAI_API_KEY or REPLICATE_API_TOKEN).",
    ),
    language: str = typer.Option("es", help="Language code: 'es' or 'en'."),
    theme: str = typer.Option(None, help="Optional thematic anchor for the prompts."),
    output: str = typer.Option("auca.png", help="Output path (.png illustrated sheet, or .pdf)."),
    use_influences: bool = typer.Option(
        False, "--style-from-influences", help="Derive style from matched influences."
    ),
    use_retrieval: bool = typer.Option(
        False,
        "--style-from-retrieval",
        help="Derive style from semantically-similar library poems (needs a retrieval index).",
    ),
    tone: str = typer.Option(None, help="Comma-separated tones for influence matching."),
    from_library: str = typer.Option(None, "--from-library", help="Load poem from library by ID."),
    panel_mode: str = typer.Option(
        "stanza",
        "--panel-mode",
        help="stanza = one image per stanza (auca, default); poem = a single longer image for the whole poem.",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print the image prompts without generating."
    ),
) -> None:
    """Generate an illustrated auca-style sheet for a poem.

    Provide a poem file path, or use --from-library <id> to load from the library.
    One image is generated per stanza. With --dry-run, prints the image prompts
    that would be used.
    """
    from poesia.galeria.auca import AucaComposer
    from poesia.galeria.pipeline import IllustrateError, illustrate_poem

    lines: list[str] = []

    if from_library:
        from poesia.memoria.library import Library

        library = Library()
        poem = library.get(from_library)
        if poem is None:
            rprint(f"[red]Poem '{from_library}' not found in library.[/red]")
            raise typer.Exit(1)
        lines = [line.strip() for line in poem.content.split("\n")]
        while lines and not lines[0]:
            lines.pop(0)
        while lines and not lines[-1]:
            lines.pop()
        rprint(f"[dim]Loaded poem '{poem.id}' from library ({len(lines)} lines)[/dim]")
    elif path:
        with open(path, encoding="utf-8") as f:
            lines = [ln.rstrip("\r\n") for ln in f]
        # Library poems are Markdown with YAML frontmatter; skip it so the
        # stanzas (not the metadata) get illustrated.
        if lines and lines[0].strip() == "---":
            for i in range(1, len(lines)):
                if lines[i].strip() == "---":
                    lines = lines[i + 1 :]
                    break
        # Keep interior blank lines (stanza separators) but drop leading/trailing ones.
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
    else:
        rprint("[red]Provide a poem file path or use --from-library <id>.[/red]")
        raise typer.Exit(1)

    # Phase 4C: Style anchoring from influences
    matched_influences = None
    if use_influences:
        from poesia.galeria.style_anchoring import style_from_influences

        influences = _load_influences()
        if tone:
            tone_list = [t.strip().lower() for t in tone.split(",")]
            matched = [
                inf
                for inf in influences
                if any(t in [it.lower() for it in inf.tone] for t in tone_list)
            ]
        else:
            matched = influences[:5]
        matched_influences = matched or None
        influence_style = style_from_influences(matched) if matched else ""
        if influence_style:
            rprint(f"[dim]Style from influences: {influence_style}[/dim]")

    # Style anchoring from retrieval: derive visual keywords from the
    # semantically-similar poems already in the user's own library.
    retrieval_style = ""
    if use_retrieval:
        from poesia.galeria.style_anchoring import style_from_retrieval

        poem_text = "\n".join(lines)
        retrieved_texts = _retrieve_style_texts(
            theme=theme or "", poem_text=poem_text, language=language
        )
        if retrieved_texts:
            retrieval_style = style_from_retrieval(
                retrieved_texts, language=language, theme=theme or ""
            )
            if retrieval_style:
                rprint(f"[dim]Style from retrieval: {retrieval_style}[/dim]")
            else:
                rprint("[dim]Style-from-retrieval: no style keywords derived.[/dim]")

    try:
        panels, prompts = illustrate_poem(
            lines,
            language=language,
            theme=theme or "",
            style=style,
            backend=backend,
            api_key=api_key,
            influences=matched_influences,
            retrieval_style=retrieval_style or None,
            panel_mode=cast(Literal["stanza", "poem"], panel_mode),
        )
    except (IllustrateError, ValueError) as e:
        rprint(f"[red]✗[/red] Illustration failed: {e}")
        raise typer.Exit(1) from None

    rprint(f"[dim]Generated {len(panels)} panels ({len(prompts)} image prompts)[/dim]")

    if dry_run:
        for i, (prompt, panel) in enumerate(zip(prompts, panels, strict=True), 1):
            rprint(
                f"\n[bold]Panel {i}[/bold] — {len(panel.caption_lines)} line(s)"
                f"\n  [dim]{prompt}[/dim]"
            )
        return

    composer = AucaComposer()
    title = f"PoesIA — {theme or 'Auca'}"
    if output.lower().endswith(".pdf"):
        composer.export_pdf(panels, output_path=output, title=title)
        rprint(f"[green]✓[/green] Illustrated PDF saved: [bold]{output}[/bold]")
    else:
        sheet_png = composer.compose_sheet(panels, title=title)
        with open(output, "wb") as f:
            f.write(sheet_png)
        rprint(f"[green]✓[/green] Illustrated sheet saved: [bold]{output}[/bold]")

    # Log illustration to MLflow (best effort)
    try:
        import os

        # Best-effort telemetry: allow the legacy local file store so the log
        # works even before PostgreSQL/MLflow is provisioned, and keep the CLI
        # output clean (no maintenance-mode banner).
        os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")
        import mlflow

        mlflow.set_tracking_uri(os.environ.get("DATABASE_URL", "file:./mlruns"))

        with mlflow.start_run(run_name=f"galeria-{from_library or 'manual'}", nested=True):
            mlflow.log_text("\n\n".join(prompts), "image_prompts.txt")
            mlflow.log_param("from_library", from_library or path)
            mlflow.log_param("backend", backend)
            mlflow.log_param("style", style)
            mlflow.log_param("language", language)
            mlflow.log_param("panels", len(panels))
            if panels:
                import io

                from PIL import Image

                mlflow.log_image(Image.open(io.BytesIO(panels[0].image_bytes)), "panel_1.png")
            rprint("[dim]Illustration logged to MLflow[/dim]")
    except Exception as e:
        rprint(f"[dim]MLflow logging skipped: {e}[/dim]")


app.add_typer(galeria_app, name="galeria")


# --- Helper functions for fragment frontmatter parsing -----------------------


def _parse_fragment_frontmatter(content: str) -> dict:
    """Minimal YAML frontmatter parser for markdown fragment files.

    Returns a dict with keys: id, tags, language, themes, tone, type.
    All values are optional and default to None/empty.
    """
    result: dict = {
        "tags": [],
        "language": None,
        "id": None,
        "themes": [],
        "tone": [],
        "type": None,
    }
    stripped = content.strip()
    if not stripped.startswith("---"):
        return result
    parts = stripped.split("---", 2)
    if len(parts) < 3:
        return result
    yaml_block = parts[1]
    for line in yaml_block.strip().splitlines():
        line = line.strip()
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            if key == "tags":
                # Parse list: ["a", "b"] or - a\n- b
                if val.startswith("[") or not val:
                    result["tags"] = _parse_yaml_list(yaml_block, key) or []
                else:
                    result["tags"] = [t.strip().strip('"').strip("'") for t in val.split(",")]
            elif key == "themes":
                result["themes"] = _parse_yaml_list(yaml_block, key) or []
            elif key == "tone":
                result["tone"] = _parse_yaml_list(yaml_block, key) or []
            elif key == "language":
                result["language"] = val.strip('"').strip("'")
            elif key == "id":
                result["id"] = val.strip('"').strip("'")
            elif key == "type":
                result["type"] = val.strip('"').strip("'")
    return result


def _parse_yaml_list(yaml_block: str, key: str) -> list[str] | None:
    """Helper: parse a YAML list value for *key* -- either inline [a, b] or block - a."""
    # First pass: try inline list [a, b]
    for line in yaml_block.splitlines():
        ls = line.strip()
        if ls.startswith(key + ":"):
            val = ls[len(key) + 1 :].strip()
            if val.startswith("[") and val.endswith("]"):
                raw = val[1:-1]
                return [x.strip().strip('"').strip("'") for x in raw.split(",") if x.strip()]
            # Non-empty inline value that is not a list? Not a list at all.
            if val:
                return None
            # Empty value -> fall through to block-list parser below
            break

    # Second pass: block list - item
    in_list = False
    items = []
    for line in yaml_block.splitlines():
        ls = line.strip()
        if ls.startswith(key + ":"):
            in_list = True
            continue
        if in_list:
            if ls.startswith("- "):
                items.append(ls[2:].strip().strip('"').strip("'"))
            elif not ls or ls.startswith("#") or ":" in ls.split("#")[0]:
                break
    return items or None


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
        heading = f"[bold]{poem.title}[/bold]" if poem.title else f"[bold]{poem.theme}[/bold]"
        rprint(f"    {heading}  [{poem.form}, {poem.language}]  {date_str}{tags_str}")
        if poem.lines:
            preview = poem.lines[0][:70]
            rprint(f"    [dim]{preview}…[/dim]")
        if poem.reflection:
            reflection_preview = poem.reflection.split("\n")[0][:80]
            rprint(f"    [cyan]« {reflection_preview}»[/cyan]")
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
        if poem.title:
            rprint(f"    [bold]«{poem.title}»[/bold]")
        rprint(f"    [dim]{poem.theme}[/dim]")
        if poem.reflection:
            reflection_preview = poem.reflection.split("\n")[0][:80]
            rprint(f"    [cyan]« {reflection_preview}»[/cyan]")
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
    """Add a personal fragment to the memoria collection and the graph index."""
    from pathlib import Path

    from poesia.memoria.embeddings import get_embedding_client
    from poesia.memoria.graphrag import GraphRAGRetriever

    file_path = Path(path)
    if not file_path.exists():
        rprint(f"[red]Error:[/red] File not found: {path}")
        raise typer.Exit(1)

    content = file_path.read_text(encoding="utf-8")
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    # Parse YAML frontmatter for language/tags override
    fm = _parse_fragment_frontmatter(content)
    frag_id = fm.get("id") or file_path.stem
    lang = fm.get("language") or language
    frag_tags = fm.get("tags") or tag_list

    # Copy to seeds/angel_fragments/ for persistence
    target_dir = Path(__file__).parent.parent.parent / "seeds" / "angel_fragments"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / file_path.name
    target_path.write_text(content, encoding="utf-8")
    rprint(f"[green]✓[/green] Copied fragment → {target_path}")

    # Add to graph index
    retriever = GraphRAGRetriever()
    try:
        client = get_embedding_client()
        retriever.add_fragment_node(
            frag_id, content, language=lang, tags=frag_tags, embedding_client=client
        )
        rprint(f"[green]✓[/green] Added fragment '{frag_id}' to graph index")
    except Exception as exc:
        # Fall back to no-embedding add
        retriever.add_fragment_node(frag_id, content, language=lang, tags=frag_tags)
        rprint(f"[yellow]⚠[/yellow] Added '{frag_id}' to graph index (no embeddings: {exc})")


@memoria_app.command("ingest-all")
def memoria_ingest_all() -> None:
    """Batch-ingest all fragments and library poems into the graph index.

    Reads every .md file from ``seeds/angel_fragments/`` and every saved poem
    from the library, then rebuilds the ``graphrag.json`` index with embeddings.
    """
    from pathlib import Path

    from poesia.memoria.embeddings import get_embedding_client
    from poesia.memoria.graphrag import GraphRAGRetriever
    from poesia.memoria.library import Library
    from poesia.memoria.records import FragmentRecord

    fragments_dir = Path(__file__).parent.parent.parent / "seeds" / "angel_fragments"
    if not fragments_dir.exists():
        rprint("[yellow]⚠[/yellow] No seeds/angel_fragments/ directory found")
        return

    try:
        embedding_client = get_embedding_client()
        rprint(f"[dim]Using embedding model: {embedding_client.model_id}[/dim]")
    except Exception as exc:
        rprint(f"[red]✗[/red] No embedding client available: {exc}")
        rprint("  Install with: pip install -e '.[nlp]'")
        raise typer.Exit(1) from None

    # Read fragments from disk
    fragments: list[FragmentRecord] = []
    for md_file in sorted(fragments_dir.glob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        fm = _parse_fragment_frontmatter(content)
        fragment = FragmentRecord(
            id=fm.get("id") or md_file.stem,
            content=content,
            language=fm.get("language") or "es",
            tags=fm.get("tags") or [],
        )
        fragments.append(fragment)
    rprint(f"[dim]Loaded {len(fragments)} fragments from seeds/[/dim]")

    # Load library poems
    library = Library()
    library_poems = library.list_all()
    rprint(f"[dim]Loaded {len(library_poems)} poems from library[/dim]")

    if not fragments and not library_poems:
        rprint("[yellow]⚠[/yellow] Nothing to ingest")
        return

    # Rebuild graph: start fresh, add fragments as fragment nodes, then
    # ingest library poems as poem nodes
    retriever = GraphRAGRetriever()
    for frag in fragments:
        retriever.add_fragment_node(
            frag.id,
            frag.content,
            language=frag.language,
            tags=frag.tags,
            embedding_client=embedding_client,
        )
    if library_poems:
        retriever.ingest(library_poems, embedding_client=embedding_client)

    info = retriever.index_info()
    rprint(
        f"[green]✓[/green] Index rebuilt: {info['node_count']} nodes, {info['edge_count']} edges"
    )
    rprint(f"[dim]  Model: {info['model_id']}  Dim: {info['embedding_dimension']}[/dim]")
    rprint(f"[dim]  Content fingerprint: {info['content_fingerprint']}[/dim]")


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
    rprint("[dim]  (To persist, add to docs/INFLUENCE_REGISTRY.md)[/dim]")


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
        lines = [line.strip() for line in content.split("\n") if line.strip()]
        preview = (
            lines[0][:60] + "..."
            if lines and len(lines[0]) > 60
            else (lines[0] if lines else "(empty)")
        )
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
