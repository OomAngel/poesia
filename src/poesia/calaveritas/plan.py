"""A plan for the whole calaverita before any verse: the idea, one scene per stanza, the punchline.

Without a plan every stanza saw every trait, so the most concrete one (the phone) took over every
stanza, and every stanza restaged Death's arrival (audit 2026-10-09). Here each trait or the detail
goes to one stanza only, and one model call turns it into a concrete scene. If that call fails or
answers in the wrong shape, the stanzas still get their own material and a default role.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .options import TRAITS, Request


@dataclass
class Plan:
    idea: str
    scenes: list[str]  # one per stanza, may be empty strings
    punchline: str
    materials: list[str]  # the trait(s) or detail each stanza is about


def materials(request: Request) -> list[str]:
    """Split the detail and the traits across the stanzas, the detail first, one item per stanza
    while there are enough stanzas; extra items join the stanzas round-robin."""
    items = ([request.detail] if request.detail else []) + [
        TRAITS[t][request.language] for t in request.traits
    ]
    n = request.stanzas
    out: list[list[str]] = [[] for _ in range(n)]
    for i, item in enumerate(items):
        out[i % n].append(item)
    return ["; ".join(x) for x in out]


_NUM = re.compile(r"^\s*(?:estrofa|stanza)?\s*(\d)\s*[:.)-]\s*(.+)$", re.I)
_IDEA = re.compile(r"^\s*(?:idea|premisa|premise)\s*[:.-]\s*(.+)$", re.I)
_PUNCH = re.compile(r"^\s*(?:remate|punchline|final|ending)\s*[:.-]\s*(.+)$", re.I)


def parse(text: str, request: Request) -> Plan:
    """Read the model's plan; whatever is missing stays empty (the prompts then fall back to roles)."""
    mats = materials(request)
    idea, punch = "", ""
    scenes = [""] * request.stanzas
    for raw in (text or "").splitlines():
        line = raw.strip().strip("*").strip()
        if m := _IDEA.match(line):
            idea = m.group(1).strip()
        elif m := _PUNCH.match(line):
            punch = m.group(1).strip()
        elif (m := _NUM.match(line)) and 1 <= int(m.group(1)) <= request.stanzas:
            scenes[int(m.group(1)) - 1] = m.group(2).strip()
    return Plan(idea[:300], [s[:300] for s in scenes], punch[:300], mats)


def empty(request: Request) -> Plan:
    return Plan("", [""] * request.stanzas, "", materials(request))
