"""Observer hooks for the generation loop.

Usage:
    from poesia.generation.hooks import GenerationHook, LoggingHook

    loop = ConstrainedLoop(...)
    loop.add_hook(LoggingHook())  # auto logs every step
    loop.run(...)
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class HookEvent:
    """Context data passed to hook callbacks."""

    line_index: int
    phase: str  # "before_generate", "after_score", "on_line_selected"
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class GenerationHook(ABC):
    """Abstract hook that can be attached to the generation loop."""

    @abstractmethod
    def on_event(self, event: HookEvent) -> None:
        """Called when an event occurs during generation."""
        ...


class CompositeHook(GenerationHook):
    """Combines multiple hooks into one."""

    def __init__(self, hooks: list[GenerationHook] | None = None) -> None:
        self._hooks = hooks or []

    def add(self, hook: GenerationHook) -> None:
        self._hooks.append(hook)

    def on_event(self, event: HookEvent) -> None:
        for hook in self._hooks:
            try:
                hook.on_event(event)
            except Exception:
                pass  # Never let a hook crash the generation


class LoggingHook(GenerationHook):
    """Logs each generation step (timing, tokens, etc.)."""

    def __init__(self) -> None:
        self._start_time: datetime | None = None
        self._step_times: list[float] = []

    def on_event(self, event: HookEvent) -> None:
        if event.phase == "before_generate":
            self._start_time = datetime.now()
        elif event.phase == "after_score" and self._start_time:
            elapsed = (datetime.now() - self._start_time).total_seconds()
            self._step_times.append(elapsed)
            n = event.data.get("n_candidates", 0)
            best = event.data.get("best_score", 0)
            # Log quietly — in production this would go to MLflow
            print(
                f"  [hook] line {event.line_index + 1}: {n} candidates in {elapsed:.2f}s, best={best:.3f}"
            )


class RepairDatasetHook(GenerationHook):
    """Harvests real repair attempts (before/defect/after/resolved) into a JSONL
    file, formatted for a future repair-specific fine-tune — training-format
    data collected for free from ordinary generation runs, rather than
    authored or synthesized separately.
    """

    DEFAULT_PATH = "seeds/poetry_corpus/repair_examples/repair_log.jsonl"

    def __init__(self, path: str = DEFAULT_PATH) -> None:
        self._path = path

    def on_event(self, event: HookEvent) -> None:
        if event.phase != "after_repair":
            return
        os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
        record = {
            "timestamp": event.timestamp.isoformat(),
            "line_index": event.line_index,
            **event.data,
        }
        with open(self._path, "a") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
