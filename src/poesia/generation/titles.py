"""LLM-backed poem title suggestion (fail-open).

After a poem is generated and validated, the write pipeline can ask the LLM
for a short title. This module builds the prompt, cleans the model's answer,
and degrades gracefully: any failure falls back to a safe theme/line-derived
title instead of aborting the save. It works with any backend that implements
the ``LLMClient.generate`` contract (stub, hosted, ollama, lora, cloudflare…).
"""

from __future__ import annotations

from poesia.generation.llm_client import LLMClient

_MAX_TITLE_LENGTH = 80

_PREFIXES = (
    "Title:",
    "Título:",
    "Titulo:",
    "Suggested title:",
    "Título sugerido:",
    "Titulo sugerido:",
)


def build_title_prompt(
    lines: list[str],
    language: str,
    form: str,
    theme: str,
) -> str:
    """Build the title-suggestion prompt for a finished poem."""
    body = "\n".join(lines)
    return (
        f"Write a title for this {form} poem written in {language}, about: {theme}.\n"
        f"Poem:\n{body}\n\n"
        "Output ONLY the title — no quotes, no explanation, no 'Title:' prefix."
    )


def _clean_title(raw: str, max_len: int = _MAX_TITLE_LENGTH) -> str:
    """Normalize the model's answer into a single-line title string."""
    text = raw.strip()
    if not text:
        return ""
    # Models sometimes append reasoning on a second line — keep only the first.
    title = text.splitlines()[0].strip()
    title = title.strip("\"'«»“”‘’")
    # Drop common labels the model may insist on adding.
    lowered = title.lower()
    for prefix in _PREFIXES:
        if lowered.startswith(prefix.lower()):
            title = title[len(prefix) :].strip()
            break
    title = title.strip("\"'«»“”‘’")
    # Collapse internal whitespace.
    title = " ".join(title.split())
    if not title:
        return ""
    # A model that ends "cleanly" often leaves a trailing period/colon.
    title = title.rstrip(".:;")
    if len(title) > max_len:
        head = title[:max_len]
        cut = head.rsplit(" ", 1)[0] if " " in head else head
        title = cut.rstrip(".,;:").strip()
    return title


def _fallback_title(theme: str, lines: list[str], max_len: int = _MAX_TITLE_LENGTH) -> str:
    """Safe, deterministic title when the LLM is unavailable or returns nothing.

    Prefers a theme that is already short and usable; otherwise falls back to
    the poem's first line, which is usually a better title than a mangled
    truncation of a long theme.
    """
    theme_clean = _clean_title(theme, max_len=max_len) if theme else ""
    if theme_clean and len(theme) <= max_len:
        return theme_clean
    first_line = lines[0] if lines else ""
    line_clean = _clean_title(first_line, max_len=max_len) if first_line else ""
    if line_clean:
        return line_clean
    return theme_clean if theme_clean else "Poema"


def suggest_title(
    lines: list[str],
    language: str,
    form: str,
    theme: str,
    llm_client: LLMClient,
    max_len: int = _MAX_TITLE_LENGTH,
) -> str:
    """Ask ``llm_client`` for a poem title; fail-open on any error.

    Args:
        lines: The poem's lines (already generated/validated).
        language: Language code (es, en, nl).
        form: Poetic form name.
        theme: The thematic anchor used to generate the poem.
        llm_client: Any backend implementing ``generate(prompt, n, temperature)``.
        max_len: Maximum title length in characters.

    Returns:
        A cleaned, single-line title. Never raises — on any failure it
        returns a theme- or first-line-derived fallback.
    """
    prompt = build_title_prompt(lines, language, form, theme)
    try:
        raw = llm_client.generate(prompt, n=1, temperature=0.7)
    except Exception:
        return _fallback_title(theme, lines, max_len=max_len)
    if not raw or not raw[0].strip():
        return _fallback_title(theme, lines, max_len=max_len)
    title = _clean_title(raw[0], max_len=max_len)
    return title if title else _fallback_title(theme, lines, max_len=max_len)
