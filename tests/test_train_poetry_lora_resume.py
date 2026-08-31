"""Tests for the --resume-from-checkpoint flag parsing in
scripts/train_poetry_lora.py — needed so a Colab disconnect/session-limit
kill can resume from the Trainer's last checkpoint instead of restarting.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "train_poetry_lora.py"
spec = importlib.util.spec_from_file_location("train_poetry_lora", SCRIPT_PATH)
train_poetry_lora = importlib.util.module_from_spec(spec)
sys.modules["train_poetry_lora"] = train_poetry_lora
spec.loader.exec_module(train_poetry_lora)


def test_pop_resume_flag_removes_flag_and_returns_true() -> None:
    argv = ["train_poetry_lora.py", "mlops/configs/train_v1.yaml", "--resume-from-checkpoint"]
    result = train_poetry_lora._pop_resume_flag(argv)
    assert result is True
    assert argv == ["train_poetry_lora.py", "mlops/configs/train_v1.yaml"]


def test_pop_resume_flag_absent_returns_false_and_leaves_argv_untouched() -> None:
    argv = ["train_poetry_lora.py", "mlops/configs/train_v1.yaml"]
    result = train_poetry_lora._pop_resume_flag(argv)
    assert result is False
    assert argv == ["train_poetry_lora.py", "mlops/configs/train_v1.yaml"]


def test_pop_resume_flag_works_regardless_of_position() -> None:
    argv = ["train_poetry_lora.py", "--resume-from-checkpoint", "mlops/configs/train_v1.yaml"]
    result = train_poetry_lora._pop_resume_flag(argv)
    assert result is True
    assert argv == ["train_poetry_lora.py", "mlops/configs/train_v1.yaml"]
