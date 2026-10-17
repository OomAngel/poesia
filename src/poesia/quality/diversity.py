"""Drift measures over a batch of poems or a stream of lines.

Fine-tuning on lines the engine had passed lifted metre and rhyme but cut distinct openings
from 129 to 21 (line adapter v1, 2026-10); the first Calaveritas batch ended 96% of its rhyme
lines on six words. These measures make such collapse visible in every A/B. They are
descriptive, not scores: report them next to form and sense, never fold them into one number.
"""

from __future__ import annotations

import threading
from collections import Counter, deque
from collections.abc import Iterable
from dataclasses import dataclass

from poesia.quality.gates import end_word, opening


@dataclass(frozen=True)
class Diversity:
    lines: int
    distinct_openings: int
    top_opening_share: float  # share of lines opening like the commonest opening
    distinct_end_words: int
    top10_end_share: float  # share of lines ending on the ten commonest end words

    def as_dict(self) -> dict[str, float | int]:
        return self.__dict__.copy()


def measure(lines: Iterable[str]) -> Diversity:
    lines = [ln for ln in lines if ln.strip()]
    n = len(lines)
    if not n:
        return Diversity(0, 0, 0.0, 0, 0.0)
    opens = Counter(opening(ln) for ln in lines)
    ends = Counter(end_word(ln) for ln in lines)
    return Diversity(
        lines=n,
        distinct_openings=len(opens),
        top_opening_share=opens.most_common(1)[0][1] / n,
        distinct_end_words=len(ends),
        top10_end_share=sum(c for _, c in ends.most_common(10)) / n,
    )


class RecentEndings:
    """End words of recently written lines across requests, so a ranker can spread rhymes."""

    def __init__(self, size: int = 600) -> None:
        self._q: deque[str] = deque(maxlen=size)
        self._lock = threading.Lock()

    def add(self, lines: Iterable[str]) -> None:
        with self._lock:
            self._q.extend(end_word(ln) for ln in lines)

    def counts(self) -> Counter[str]:
        with self._lock:
            return Counter(self._q)
