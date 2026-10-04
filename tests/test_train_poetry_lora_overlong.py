"""train_poetry_lora drops examples that don't fit max_length instead of truncating them.

Right-side truncation removed the completion and EOS of long line examples, so those
examples trained the model to continue the prompt (docs/RETRAINING_PLAN_2026-10.md §5).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

# The script imports its training stack at module level.
for _dep in ("mlflow", "torch", "yaml", "datasets", "peft", "transformers"):
    pytest.importorskip(_dep)

from datasets import Dataset  # noqa: E402

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "train_poetry_lora.py"
spec = importlib.util.spec_from_file_location("train_poetry_lora", SCRIPT_PATH)
train_poetry_lora = importlib.util.module_from_spec(spec)
sys.modules["train_poetry_lora"] = train_poetry_lora
spec.loader.exec_module(train_poetry_lora)


def _ds(lengths: list[int]) -> Dataset:
    return Dataset.from_dict(
        {"input_ids": [[1] * n for n in lengths], "quality_weight": [1.0] * len(lengths)}
    )


def test_keeps_examples_up_to_and_including_max_length() -> None:
    kept, dropped = train_poetry_lora._drop_overlong(_ds([3, 4, 5, 9]), 4, "train")
    assert [len(x) for x in kept["input_ids"]] == [3, 4]
    assert dropped == 2


def test_kept_examples_are_untouched_not_truncated() -> None:
    kept, _ = train_poetry_lora._drop_overlong(_ds([4]), 4, "train")
    assert kept["input_ids"] == [[1, 1, 1, 1]]


def test_every_example_too_long_raises() -> None:
    with pytest.raises(ValueError, match="every example is longer"):
        train_poetry_lora._drop_overlong(_ds([5, 6]), 4, "train")


def test_empty_split_is_allowed() -> None:
    kept, dropped = train_poetry_lora._drop_overlong(_ds([]), 4, "eval")
    assert len(kept) == 0 and dropped == 0
