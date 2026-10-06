"""Safety screen for reflections and lines (docs/HACK_APERTUS_PLAN.md §6).

Before PoesIA helps shape what someone wrote, it checks the text for signs of risk to
themselves or others. Recall comes first: a phrase list per language (es, en, de, fr, it)
plus, when a model is available, one yes/no question to it. On a positive the poem pauses
and the page shows support services; the person may continue afterwards. No therapy claims.
"""

from poesia.safety.screen import RESOURCES, ScreenResult, keyword_matches, screen

__all__ = ["RESOURCES", "ScreenResult", "keyword_matches", "screen"]
