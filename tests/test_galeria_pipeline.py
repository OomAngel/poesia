"""Tests for the GalerIA illustration pipeline + CLI wiring."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from poesia.cli import app
from poesia.galeria.auca import AucaComposer, AucaPanel
from poesia.galeria.backends import HostedImageBackend, StubImageBackend
from poesia.galeria.procedural import ProceduralImageBackend
from poesia.galeria.pipeline import (
    IllustrateError,
    get_image_backend,
    illustrate_poem,
    split_stanzas,
)

SONETO_LINES = [
    "En el umbral de la noche callada,",
    "brilla la luna sobre el agua fría,",
    "",
    "y el viento susurra entre las ramas",
    "la vieja historia que el tiempo olvida.",
]


class TestSplitStanzas:
    """Stanza splitting: one image per stanza."""

    def test_blank_line_separates_stanzas(self) -> None:
        stanzas = split_stanzas(SONETO_LINES)
        assert len(stanzas) == 2
        assert stanzas[0] == SONETO_LINES[:2]
        assert stanzas[1] == SONETO_LINES[3:]

    def test_single_block_chunked_when_long(self) -> None:
        lines = [f"verso {i}" for i in range(12)]
        stanzas = split_stanzas(lines, max_lines_per_stanza=5)
        assert len(stanzas) == 3
        assert len(stanzas[0]) == 5
        assert len(stanzas[-1]) == 2

    def test_short_single_block_not_chunked(self) -> None:
        assert split_stanzas(["a", "b", "c"]) == [["a", "b", "c"]]

    def test_empty_input_returns_empty_stanza(self) -> None:
        assert split_stanzas([]) == [[]]


class TestGetImageBackend:
    """Backend selection mirrors the --llm registry pattern."""

    def test_stub(self) -> None:
        assert isinstance(get_image_backend("stub"), StubImageBackend)

    def test_procedural(self) -> None:
        assert isinstance(get_image_backend("procedural"), ProceduralImageBackend)

    def test_auto_without_key_falls_back_to_procedural(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            assert isinstance(get_image_backend("auto"), ProceduralImageBackend)

    def test_auto_with_openai_key_uses_hosted(self) -> None:
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}, clear=True):
            backend = get_image_backend("auto")
        assert isinstance(backend, HostedImageBackend)

    def test_openai_explicit(self) -> None:
        assert isinstance(get_image_backend("openai"), HostedImageBackend)

    def test_unknown_backend_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown image backend"):
            get_image_backend("nope")


class TestIllustratePoem:
    """End-to-end poem -> panels pipeline."""

    def test_returns_one_panel_per_stanza(self) -> None:
        panels, prompts = illustrate_poem(SONETO_LINES, backend="stub")
        assert len(panels) == 2
        assert len(prompts) == 2
        assert all(p.image_bytes.startswith(b"\x89PNG") for p in panels)
        assert all(prompt for prompt in prompts)
        assert panels[0].caption_lines == SONETO_LINES[:2]
        assert panels[1].caption_lines == SONETO_LINES[3:]

    def test_hosted_backend_without_key_raises_illustrate_error(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(IllustrateError, match="requires an API key"):
                illustrate_poem(["una línea"], backend="openai")


class TestAucaExportPdf:
    """PDF export degrades with an actionable message without WeasyPrint."""

    def test_export_pdf_requires_weasyprint(self, tmp_path: Path) -> None:
        stub = StubImageBackend()
        panel = AucaPanel(image_bytes=stub.generate_image("x"), caption_lines=["verso uno"])
        composer = AucaComposer()
        with pytest.raises(RuntimeError, match="WeasyPrint is not installed"):
            composer.export_pdf([panel], output_path=str(tmp_path / "out.pdf"))


class TestCliGaleria:
    """CLI wiring: poesia galeria illustrate writes a real PNG sheet."""

    def test_illustrate_writes_png_sheet(self, tmp_path: Path) -> None:
        poem = tmp_path / "poema.txt"
        poem.write_text(
            "La luna brilla\nsobre el agua fría\n\nel viento susurra\nen la noche oscura\n",
            encoding="utf-8",
        )
        output = tmp_path / "auca.png"
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["galeria", "illustrate", str(poem), "--backend", "stub", "--output", str(output)],
        )
        assert result.exit_code == 0
        assert output.exists()
        assert output.read_bytes().startswith(b"\x89PNG")
        assert "Illustrated sheet saved" in result.output
        assert "Generated 2 panels" in result.output

    def test_illustrate_dry_run_prints_prompts(self, tmp_path: Path) -> None:
        poem = tmp_path / "poema.txt"
        poem.write_text("La luna brilla\nsobre el agua fría\n", encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(
            app, ["galeria", "illustrate", str(poem), "--backend", "stub", "--dry-run"]
        )
        assert result.exit_code == 0
        assert "Panel 1" in result.output

    def test_illustrate_unknown_backend_fails_cleanly(self, tmp_path: Path) -> None:
        poem = tmp_path / "poema.txt"
        poem.write_text("La luna brilla\n", encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(app, ["galeria", "illustrate", str(poem), "--backend", "nope"])
        assert result.exit_code == 1
        assert "Unknown image backend" in result.output

    def test_illustrate_procedural_writes_real_sheet(self, tmp_path: Path) -> None:
        poem = tmp_path / "poema.txt"
        poem.write_text(
            "La luna brilla\nsobre el agua fría\n\nel viento susurra\nen la noche oscura\n",
            encoding="utf-8",
        )
        output = tmp_path / "auca_procedural.png"
        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "galeria",
                "illustrate",
                str(poem),
                "--backend",
                "procedural",
                "--output",
                str(output),
            ],
        )
        assert result.exit_code == 0
        assert output.exists()
        assert output.stat().st_size > 1000  # real art, not the 1x1 stub pixel
        assert "Generated 2 panels" in result.output

    def test_illustrate_markdown_strips_frontmatter(self, tmp_path: Path) -> None:
        poem = tmp_path / "poema.md"
        poem.write_text(
            "---\n"
            "id: ejemplo\n"
            "language: es\n"
            "form: soneto\n"
            "theme: ejemplo\n"
            "---\n"
            "\n"
            "La luna brilla en la noche,\n"
            "y el viento susurra.\n",
            encoding="utf-8",
        )
        runner = CliRunner()
        result = runner.invoke(
            app, ["galeria", "illustrate", str(poem), "--backend", "stub", "--dry-run"]
        )
        assert result.exit_code == 0
        assert "Generated 1 panels" in result.output
        # frontmatter metadata must not leak into a panel caption
        assert "language:" not in result.output
