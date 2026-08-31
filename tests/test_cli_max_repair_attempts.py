"""CLI tests for --max-repair-attempts wiring.

`WriteConfig.max_repair_attempts` used to be built (hardcoded to 2 in
`_build_write_config`) but never actually passed to `loop.run()`/
`loop.run_draft()` — the field, and any future CLI flag for it, would have
been a silent no-op. See docs/GENERATION_QUALITY_PLAN.md gap #14 follow-up.
"""

from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from poesia.cli import app
from poesia.config.types import WriteConfig
from poesia.generation.constrained_loop import ConstrainedLoop


def test_default_max_repair_attempts_is_four() -> None:
    config = WriteConfig.build(theme="luna", form="haiku", language="es", llm="stub")
    assert config.max_repair_attempts == 4


def test_max_repair_attempts_flag_reaches_the_generation_loop() -> None:
    runner = CliRunner()
    captured: dict = {}
    original_run = ConstrainedLoop.run

    def spy_run(self, *args, **kwargs):
        captured.update(kwargs)
        return original_run(self, *args, **kwargs)

    with patch.object(ConstrainedLoop, "run", spy_run):
        result = runner.invoke(
            app,
            [
                "write",
                "--theme",
                "luna",
                "--form",
                "haiku",
                "--llm",
                "stub",
                "--max-repair-attempts",
                "7",
            ],
        )

    assert result.exit_code == 0
    assert captured.get("max_repair_attempts") == 7
