"""GalerIA — illustration for poems.

*Galería* (gallery). Generates imagery to accompany a poem, in the spirit of
the Spanish "auca"/"aleluya" tradition: a sheet of illustrations paired with
rhymed verses. Owns image generation (pluggable backend), text+image
composition, and export (PNG/SVG/PDF).

Backends are injected via the `ImageBackend` Protocol (see `backends.py`) so
no specific SDK (openai, replicate, diffusers) is a hard dependency of this
package.

Phase 0 status: interfaces + stub backend only.
"""
