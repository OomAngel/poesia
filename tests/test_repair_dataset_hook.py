"""Tests for RepairDatasetHook — harvests real repair attempts (before/defect/
after/resolved) into JSONL for a future repair-specific fine-tune. See
docs/GENERATION_QUALITY_PLAN.md for the root-cause gap this data is meant to
close (fine-tune only ever trained on full-poem generation, never on the
defect->fix task shape).
"""

from __future__ import annotations

import json

from poesia.generation.hooks import HookEvent, RepairDatasetHook


def test_ignores_non_repair_phases(tmp_path) -> None:
    path = tmp_path / "repair_log.jsonl"
    hook = RepairDatasetHook(path=str(path))

    hook.on_event(HookEvent(line_index=0, phase="before_generate"))
    hook.on_event(HookEvent(line_index=0, phase="after_score"))

    assert not path.exists()


def test_writes_one_jsonl_record_per_after_repair_event(tmp_path) -> None:
    path = tmp_path / "nested" / "repair_log.jsonl"
    hook = RepairDatasetHook(path=str(path))

    hook.on_event(
        HookEvent(
            line_index=2,
            phase="after_repair",
            data={
                "before": "una linea con demasiadas silabas hoy",
                "defect_description": "actual=12 target=11",
                "after": "una linea con silabas correctas",
                "resolved": True,
                "target_syllables": 11,
                "target_rhyme_key": "ado",
                "attempt": 1,
            },
        )
    )
    hook.on_event(
        HookEvent(
            line_index=3,
            phase="after_repair",
            data={"before": "x", "after": "y", "resolved": False},
        )
    )

    lines = path.read_text().splitlines()
    assert len(lines) == 2

    first = json.loads(lines[0])
    assert first["line_index"] == 2
    assert first["before"] == "una linea con demasiadas silabas hoy"
    assert first["after"] == "una linea con silabas correctas"
    assert first["resolved"] is True
    assert "timestamp" in first

    second = json.loads(lines[1])
    assert second["line_index"] == 3
    assert second["resolved"] is False
