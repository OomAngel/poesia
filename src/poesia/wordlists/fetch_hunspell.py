"""Fetch the es_MX Hunspell dictionary into wordlists/hunspell/ (not kept in git: 0.9 MB).

Pinned to a LibreOffice dictionaries commit and checked by SHA-256; the Calaveritas image runs
this before installing the package. Licence and source: wordlists/hunspell/README.md.

Usage: python src/poesia/wordlists/fetch_hunspell.py
"""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

COMMIT = "762abe74008b94b2ff06db6f4024b59a8254c467"
FILES = {
    "es_MX.dic": "44ce35af220962c68f97962776639bef271f7d90a85ba924b539a36e33315f82",
    "es_MX.aff": "d966cb748e4a688ed75ec84b50c0835ac438e5325ee4fce703a093794f9cba7e",
}
URL = "https://raw.githubusercontent.com/LibreOffice/dictionaries/{commit}/es/{name}"
DEST = Path(__file__).resolve().parent / "hunspell"


def main() -> int:
    for name, sha in FILES.items():
        path = DEST / name
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == sha:
            continue
        with urllib.request.urlopen(URL.format(commit=COMMIT, name=name), timeout=60) as r:  # noqa: S310 - fixed https URL
            data = r.read()
        got = hashlib.sha256(data).hexdigest()
        if got != sha:
            print(f"{name}: checksum {got} != {sha}", file=sys.stderr)
            return 1
        path.write_bytes(data)
        print(f"{name}: {len(data)} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
