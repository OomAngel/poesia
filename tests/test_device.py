"""Tests for the shared CUDA-usability probe (poesia.device.cuda_usable).

Mirrors the mocking pattern from test_memoria_embeddings.py's _safe_device
tests, which now delegate to this same function.
"""

from __future__ import annotations

import sys
import types

import pytest


def test_cuda_usable_no_cuda(monkeypatch: pytest.MonkeyPatch) -> None:
    """No CUDA available at all -> False, no op attempted."""
    from poesia.device import cuda_usable

    fake_torch = types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: False))
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    assert cuda_usable() is False


def test_cuda_usable_present_but_unsupported(monkeypatch: pytest.MonkeyPatch) -> None:
    """CUDA visible, but a trivial op on it raises -> False.

    This is the exact failure mode this probe exists to catch: an old
    compute-capability GPU that `is_available()` sees, but the installed
    torch build has no compiled kernel for (cudaErrorNoKernelImageForDevice).
    """
    from poesia.device import cuda_usable

    def _boom(*args, **kwargs):
        raise RuntimeError("CUDA error: no kernel image is available for execution")

    fake_torch = types.SimpleNamespace(
        cuda=types.SimpleNamespace(is_available=lambda: True),
        zeros=_boom,
    )
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    assert cuda_usable() is False


def test_cuda_usable_present_and_working(monkeypatch: pytest.MonkeyPatch) -> None:
    """CUDA visible and the trivial op succeeds -> True."""
    from poesia.device import cuda_usable

    class _FakeTensor:
        def __add__(self, other):
            return self

        def cpu(self):
            return self

    fake_torch = types.SimpleNamespace(
        cuda=types.SimpleNamespace(is_available=lambda: True),
        zeros=lambda *a, **k: _FakeTensor(),
    )
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    assert cuda_usable() is True


# ---------------------------------------------------------------------------
# bnb_4bit_usable: what LoRAClient and evaluate_adapter_mlflow.py dispatch on.
# ---------------------------------------------------------------------------


class _FakeTensor:
    def __add__(self, other):
        return self

    def cpu(self):
        return self


def _working_cuda_torch() -> types.SimpleNamespace:
    return types.SimpleNamespace(
        cuda=types.SimpleNamespace(is_available=lambda: True),
        zeros=lambda *a, **k: _FakeTensor(),
        ones=lambda *a, **k: _FakeTensor(),
        float16="float16",
    )


def _fake_bnb(monkeypatch: pytest.MonkeyPatch, quantize_4bit) -> None:
    functional = types.SimpleNamespace(quantize_4bit=quantize_4bit)
    monkeypatch.setitem(sys.modules, "bitsandbytes", types.SimpleNamespace(functional=functional))
    monkeypatch.setitem(sys.modules, "bitsandbytes.functional", functional)


def test_bnb_4bit_usable_no_cuda(monkeypatch: pytest.MonkeyPatch) -> None:
    """No usable CUDA -> False, bitsandbytes never touched."""
    from poesia.device import bnb_4bit_usable

    fake_torch = types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: False))
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    _fake_bnb(monkeypatch, lambda *a, **k: pytest.fail("bitsandbytes must not be called"))
    assert bnb_4bit_usable() is False


def test_bnb_4bit_usable_torch_works_but_no_bitsandbytes(monkeypatch: pytest.MonkeyPatch) -> None:
    """The laptop case: torch cu126 runs on sm_50, bitsandbytes is not installed -> False."""
    from poesia.device import bnb_4bit_usable, cuda_usable

    monkeypatch.setitem(sys.modules, "torch", _working_cuda_torch())
    monkeypatch.setitem(sys.modules, "bitsandbytes", None)  # import raises ImportError
    monkeypatch.setitem(sys.modules, "bitsandbytes.functional", None)
    assert cuda_usable() is True
    assert bnb_4bit_usable() is False


def test_bnb_4bit_usable_no_bitsandbytes_kernel(monkeypatch: pytest.MonkeyPatch) -> None:
    """bitsandbytes installed but without kernels for this GPU -> False."""
    from poesia.device import bnb_4bit_usable

    def _boom(*args, **kwargs):
        raise RuntimeError("CUDA error: no kernel image is available for execution")

    monkeypatch.setitem(sys.modules, "torch", _working_cuda_torch())
    _fake_bnb(monkeypatch, _boom)
    assert bnb_4bit_usable() is False


def test_bnb_4bit_usable_working(monkeypatch: pytest.MonkeyPatch) -> None:
    """The desktop case: torch and bitsandbytes both run on the GPU -> True."""
    from poesia.device import bnb_4bit_usable

    calls = []
    monkeypatch.setitem(sys.modules, "torch", _working_cuda_torch())
    _fake_bnb(monkeypatch, lambda *a, **k: calls.append(k))
    assert bnb_4bit_usable() is True
    assert calls == [{"quant_type": "nf4"}]
