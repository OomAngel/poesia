"""Small helpers in the training scripts: device placement and the eval-file path."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_eval_path_never_equals_the_train_path() -> None:
    bfd = _load("build_fixed_dataset")
    assert bfd.eval_path_for("mlops/data/train_fixed.jsonl") == "mlops/data/eval_fixed.jsonl"
    assert bfd.eval_path_for("mlops/data/smoke_8b.jsonl") == "mlops/data/smoke_8b.eval.jsonl"
    for p in ("a/train_fixed.jsonl", "a/run.jsonl", "a/run"):
        assert bfd.eval_path_for(p) != p


class TestDeviceMap:
    @pytest.fixture(scope="class")
    def tpl(self):
        for dep in ("mlflow", "torch", "yaml", "datasets", "peft", "transformers"):
            pytest.importorskip(dep)
        return _load("train_poetry_lora")

    def test_default_layout_is_auto_and_leaves_bnb_untouched(self, tpl) -> None:
        kwargs: dict = {}
        assert tpl._device_map({}, kwargs) == "auto"
        assert kwargs == {}

    def test_low_vram_quantizes_lm_head_and_loads_on_gpu0(self, tpl) -> None:
        kwargs: dict = {}
        dm = tpl._device_map({"memory_layout": "low_vram"}, kwargs)
        assert dm == {"": 0}
        assert kwargs["llm_int8_skip_modules"] == []

    def test_unknown_layout_raises(self, tpl) -> None:
        with pytest.raises(ValueError):
            tpl._device_map({"memory_layout": "tiny"}, {})


def test_lora_client_reads_the_base_model_from_adapter_config(tmp_path) -> None:
    import json

    from poesia.generation.llm_client import LoRAClient, _adapter_base

    adapter = tmp_path / "final_adapter"
    adapter.mkdir()
    (adapter / "adapter_config.json").write_text(
        json.dumps({"base_model_name_or_path": "Qwen/Qwen3-8B"})
    )
    assert _adapter_base(str(adapter)) == "Qwen/Qwen3-8B"
    assert LoRAClient(adapter_path=str(adapter)).model == "Qwen/Qwen3-8B"  # was Qwen2.5-1.5B
    assert _adapter_base(str(tmp_path / "missing")) is None


def test_four_bit_placement_layouts() -> None:
    from poesia.device import four_bit_placement

    assert four_bit_placement("default") == ({}, "auto")
    extra, dm = four_bit_placement("low_vram")
    assert extra == {"llm_int8_skip_modules": []} and dm == {"": 0}
    with pytest.raises(ValueError):
        four_bit_placement("tiny")


def test_explicit_base_model_without_adapter_skips_adapter_discovery(monkeypatch, tmp_path) -> None:
    from poesia.generation.llm_client import LoRAClient

    monkeypatch.setenv("LORA_ADAPTER_PATH", str(tmp_path))  # would be picked up otherwise
    client = LoRAClient(base_model="Qwen/Qwen3-4B-Instruct-2507")
    assert client.model == "Qwen/Qwen3-4B-Instruct-2507"
    assert client._adapter_path is None


def test_offload_input_embeddings_routes_ids_to_cpu_and_output_back() -> None:
    torch = pytest.importorskip("torch")
    from poesia.device import offload_input_embeddings

    class Tiny(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.emb = torch.nn.Embedding(10, 4)

        def get_input_embeddings(self):
            return self.emb

    model = offload_input_embeddings(Tiny(), compute_device="cpu")  # CI has no GPU
    out = model.get_input_embeddings()(torch.tensor([[1, 2, 3]]))
    assert model.emb.weight.device.type == "cpu"
    assert out.shape == (1, 3, 4) and out.device.type == "cpu"


def test_offload_refuses_tied_embeddings() -> None:
    torch = pytest.importorskip("torch")
    from poesia.device import offload_input_embeddings

    class Tied(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.emb = torch.nn.Embedding(10, 4)
            self.head = torch.nn.Linear(4, 10, bias=False)
            self.head.weight = self.emb.weight

        def get_input_embeddings(self):
            return self.emb

        def get_output_embeddings(self):
            return self.head

    with pytest.raises(ValueError, match="tied"):
        offload_input_embeddings(Tied(), compute_device="cpu")
