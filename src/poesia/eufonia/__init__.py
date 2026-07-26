"""EufonIA — sound/euphony analysis.

*Eufonía* (euphony): the pleasantness of sound itself. This module judges how
a poem *sounds* — rhyme quality, assonance/consonance density, cacophonous
clusters, repeated phoneme patterns — as distinct from ArmonIA, which turns a
poem into music. EufonIA consumes the `phonology/` layer's scan results; it
does not do its own phoneme extraction.

Phase 0 status: interface only, no scoring implementation yet.
"""
