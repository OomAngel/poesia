"""Generate a data version manifest for the current training data.

Usage:
    python mlops/data_manifest.py --data seeds/poetry_corpus/training_data_structured/sonetos_train.jsonl

Output: prints a JSON manifest with SHA256 hash, record count, sources, etc.
This manifest should be saved alongside the adapter for traceability.
"""

import argparse
import hashlib
import json
from pathlib import Path


def compute_manifest(data_path: str) -> dict:
    path = Path(data_path)
    if not path.exists():
        raise FileNotFoundError(f"{data_path} not found")

    # Read all records
    records = []
    with open(path) as f:
        for line in f:
            records.append(json.loads(line))

    # Compute hash over concatenated sorted JSON
    hasher = hashlib.sha256()
    for rec in records:
        hasher.update(json.dumps(rec, sort_keys=True).encode())

    # Extract sources and forms
    sources = set()
    forms = set()
    for rec in records:
        if "source" in rec:
            sources.add(rec["source"])
        if "form" in rec:
            forms.add(rec["form"])

    # Sample syllable counts
    avg_syllables = []
    for rec in records:
        if "avg_syllables" in rec and rec["avg_syllables"]:
            avg_syllables.append(rec["avg_syllables"])

    manifest = {
        "data_path": str(data_path),
        "sha256": hasher.hexdigest(),
        "record_count": len(records),
        "sources": sorted(sources),
        "forms": sorted(forms),
        "avg_syllables_mean": round(sum(avg_syllables) / len(avg_syllables), 1)
        if avg_syllables
        else None,
        "file_size_bytes": path.stat().st_size,
    }
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Path to training data JSONL")
    args = parser.parse_args()
    manifest = compute_manifest(args.data)
    print(json.dumps(manifest, indent=2))
