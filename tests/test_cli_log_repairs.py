"""CLI test for --log-repairs wiring: the flag must attach a RepairDatasetHook
to the ConstrainedLoop instance, mirroring the pattern in
test_cli_max_repair_attempts.py.
"""

from __future__ import annotations

from typer.testing import CliRunner

from poesia.cli import app
from poesia.generation.constrained_loop import ConstrainedLoop
from poesia.generation.hooks import RepairDatasetHook


def test_log_repairs_flag_attaches_repair_dataset_hook() -> None:
    runner = CliRunner()
    original_add_hook = ConstrainedLoop.add_hook
    captured: list = []

    def spy_add_hook(self, hook):
        captured.append(hook)
        return original_add_hook(self, hook)

    from unittest.mock import patch

    with patch.object(ConstrainedLoop, "add_hook", spy_add_hook):
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
                "--log-repairs",
            ],
        )

    assert result.exit_code == 0
    assert any(isinstance(hook, RepairDatasetHook) for hook in captured)


def test_without_flag_no_repair_dataset_hook_is_attached() -> None:
    runner = CliRunner()
    original_add_hook = ConstrainedLoop.add_hook
    captured: list = []

    def spy_add_hook(self, hook):
        captured.append(hook)
        return original_add_hook(self, hook)

    from unittest.mock import patch

    with patch.object(ConstrainedLoop, "add_hook", spy_add_hook):
        result = runner.invoke(
            app,
            ["write", "--theme", "luna", "--form", "haiku", "--llm", "stub"],
        )

    assert result.exit_code == 0
    assert not any(isinstance(hook, RepairDatasetHook) for hook in captured)
