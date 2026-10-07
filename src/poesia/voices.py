"""Read-back voices for the page: which ones, where they live, and fetching them.

Piper voices from ``rhasspy/piper-voices`` at a fixed revision, one per language, chosen for
clear licences (docs/CORPUS_SOURCES.md): es_ES-davefx-medium (CC0), en_US-ljspeech-medium
(public domain), it_IT-serena-medium (CC BY 4.0, credited in the entry README). The Docker
image bakes them in with ``python -m poesia.voices /opt/piper``; a native install fetches
them once into the user's data folder (``poesia-web --with-ollama`` does it).
"""

from __future__ import annotations

import os
import sys
import urllib.request
from collections.abc import Callable
from pathlib import Path

VOICES_REV = "c10ece1aade47bb51c153c893d14e5bf8e5b7117"
VOICES = {
    "es": "es/es_ES/davefx/medium/es_ES-davefx-medium.onnx",
    "en": "en/en_US/ljspeech/medium/en_US-ljspeech-medium.onnx",
    "it": "it/it_IT/serena/medium/it_IT-serena-medium.onnx",
}


def user_voice_dir() -> Path:
    """Per-user data folder: %LOCALAPPDATA%, ~/Library/Application Support or XDG data."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "poesia" / "piper"


def voice_dir() -> Path:
    """Where the page looks: POESIA_PIPER_VOICES, else models/piper (a source checkout)."""
    return Path(os.environ.get("POESIA_PIPER_VOICES", "models/piper"))


def missing(root: Path) -> list[str]:
    return [rel for rel in VOICES.values() if not (root / rel).exists()]


def fetch(root: Path, rev: str = VOICES_REV, say: Callable[[str], None] = print) -> None:
    """Download the voices (model + config) that ``root`` lacks; ~60 MB each."""
    for rel in VOICES.values():
        for suffix in (".json", ""):  # config first: a model without it is unusable
            dest = root / f"{rel}{suffix}"
            if dest.exists():
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            say(f"Downloading voice {Path(rel).stem}{suffix or ' (model)'}...")
            url = f"https://huggingface.co/rhasspy/piper-voices/resolve/{rev}/{rel}{suffix}"
            part = dest.with_name(dest.name + ".part")
            urllib.request.urlretrieve(url, part)
            part.replace(dest)  # never leave a half-written file under the final name


if __name__ == "__main__":
    fetch(Path(sys.argv[1]) if len(sys.argv) > 1 else user_voice_dir())
