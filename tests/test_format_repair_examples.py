"""Tests for scripts/format_repair_examples.py — must match LoRAClient.repair()'s
live prompt template exactly, or a fine-tune trained on this data would still
face a prompt/task-format mismatch at inference time."""

from __future__ import annotations

from poesia.generation.llm_client import LORA_REPAIR_PROMPT_TEMPLATE
from scripts.format_repair_examples import format_record, split_train_eval


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


def test_split_train_eval_is_disjoint_and_covers_all_records() -> None:
    records = [{"i": i} for i in range(100)]

    train, eval_ = split_train_eval(records, eval_ratio=0.05, seed=42)

    assert len(train) + len(eval_) == len(records)
    assert {r["i"] for r in train}.isdisjoint({r["i"] for r in eval_})
    assert len(eval_) == 5


def test_split_train_eval_is_deterministic_for_a_given_seed() -> None:
    records = [{"i": i} for i in range(50)]

    train_a, eval_a = split_train_eval(records, eval_ratio=0.1, seed=7)
    train_b, eval_b = split_train_eval(records, eval_ratio=0.1, seed=7)

    assert train_a == train_b
    assert eval_a == eval_b


def test_split_train_eval_reserves_at_least_one_eval_record_when_nonempty() -> None:
    records = [{"i": i} for i in range(3)]

    train, eval_ = split_train_eval(records, eval_ratio=0.05, seed=0)

    assert len(eval_) == 1
    assert len(train) == 2
