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
