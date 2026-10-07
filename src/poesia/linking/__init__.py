"""Linking: poems from the person's tradition on the same feeling (docs/HACK_APERTUS_PLAN.md §2).

After writing, the person may ask for two or three public-domain (or openly licensed) poems
close in feeling to what they wrote. The reflection is embedded by a local model through an
OpenAI-compatible ``/embeddings`` endpoint; the poems' vectors are precomputed
(``scripts/build_linking_index.py``). Only texts whose licence allows showing them are in the
index; each result carries its source and licence for the credit line.
"""

from poesia.linking.index import EmbeddingClient, LinkIndex

__all__ = ["EmbeddingClient", "LinkIndex"]
