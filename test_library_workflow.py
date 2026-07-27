#!/usr/bin/env python3
"""Test complete library workflow end-to-end."""

from poesia.memoria.library import Library

# Load the library
library = Library()

# List all poems
poems = library.list_all()
print(f"Total poems in library: {len(poems)}")
print()

for i, poem in enumerate(poems, 1):
    print(f"=== Poem {i}: {poem.id} ===")
    print(f"Theme: {poem.theme}")
    print(f"Form: {poem.form}")
    print(f"Tags: {', '.join(poem.tags)}")
    if poem.provenance:
        print(f"Provenance:")
        if poem.provenance.model:
            print(f"  Model: {poem.provenance.model}")
        if poem.provenance.embedding_model:
            print(f"  Embedding: {poem.provenance.embedding_model}")
        if poem.provenance.brief_level:
            print(f"  Brief level: {poem.provenance.brief_level}")
        if poem.provenance.fragments_used:
            print(f"  Fragments used ({len(poem.provenance.fragments_used)}): {poem.provenance.fragments_used[:3]}...")
    print("Lines:")
    for line in poem.lines:
        print(f"  {line}")
    print()
