"""Vulture whitelist — names intentionally kept for external API contracts.

Each name is flagged by vulture as "unused", but is required by a method
signature:

- ``score_bytes`` — parameter of ``AudioSynthBackend.render`` (a ``Protocol``
  method with no body).
- ``return_outputs`` / ``num_items_in_batch`` — parameters of ``compute_loss``
  matching the HuggingFace ``Trainer.compute_loss`` callback contract (a
  subclass may receive either).

This file is passed to vulture as a whitelist and excluded from ruff.
"""

score_bytes  # Protocol method parameter
return_outputs  # HF Trainer.compute_loss callback parameter
num_items_in_batch  # HF Trainer.compute_loss callback parameter
