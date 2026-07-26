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
    language: str = typer.Option("es", help="Language code: 'es' or 'en'."),
    form: str = typer.Option("soneto", help="Registered form name, see poesia.forms.definitions."),
    n_candidates: int = typer.Option(16, help="Candidate lines generated per position."),
) -> None:
    """Generate a poem using the constrained generate/validate/repair loop."""
    from poesia.generation.constrained_loop import ConstrainedLoop

    loop = ConstrainedLoop(language=language, form=form)
    result = loop.run(theme=theme, n_candidates=n_candidates)
    rprint(f"[bold]Theme:[/bold] {theme}  [bold]Form:[/bold] {form}  [bold]Language:[/bold] {language}\n")
    for line in result.lines:
        rprint(line)


@app.command()
def scan(
    line: str = typer.Argument(..., help="A single line of verse to scan."),
    language: str = typer.Option("es", help="Language code: 'es' or 'en'."),
) -> None:
    """Scan a single line for syllable count, stress and validity."""
    from poesia.phonology.english import EnglishPhonology
    from poesia.phonology.spanish import SpanishPhonology

    phonology = SpanishPhonology() if language == "es" else EnglishPhonology()
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
) -> None:
    """Generate an illustrated auca-style sheet for a poem (stub, Phase 2)."""
    from poesia.galeria.auca import AucaComposer, AucaPanel
    from poesia.galeria.backends import StubImageBackend

    with open(path, encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip()]
    backend = StubImageBackend()
    image_bytes = backend.generate_image(prompt=" ".join(lines), style=style)
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
