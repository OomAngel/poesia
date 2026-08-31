"""Tests for scripts/format_repair_examples.py — must match LoRAClient.repair()'s
live prompt template exactly, or a fine-tune trained on this data would still
face a prompt/task-format mismatch at inference time."""

from __future__ import annotations

from poesia.generation.llm_client import LORA_REPAIR_PROMPT_TEMPLATE
from scripts.format_repair_examples import format_record


def test_matches_lora_client_repair_prompt_format() -> None:
    record = {
        "before": "una linea con demasiadas silabas hoy",
        "defect_description": "actual=12 target=11",
        "after": "una linea con silabas correctas",
        "resolved": True,
    }

    out = format_record(record)

    expected_prompt = LORA_REPAIR_PROMPT_TEMPLATE.format(
        defect_description=record["defect_description"], line=record["before"]
    )
    assert out == {"prompt": expected_prompt, "completion": record["after"]}


def test_unresolved_attempts_are_dropped() -> None:
    record = {
        "before": "x",
        "after": "y",
        "defect_description": "d",
        "resolved": False,
    }
    assert format_record(record) is None


def test_missing_fields_are_dropped() -> None:
    assert format_record({"resolved": True}) is None
