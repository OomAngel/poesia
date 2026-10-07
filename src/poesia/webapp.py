"""Local web page for writing a poem with PoesIA (Hack Apertus entry, docs/HACK_APERTUS_PLAN.md §2).

The person writes; the engine checks. Every line slot is the author's own text field. The
server scans a line (syllables, stress, rhyme against the form's scheme) and explains it in
plain words (``poesia.teaching``); it proposes lines only when asked, ranked by the same
deterministic scan, never by model likelihood. It keeps nothing: no database, no logs of
what is written. Saving is the browser downloading the poem to the author's own disk.

Run (binds to this machine only):

    poesia-web                     # or: python -m poesia.webapp
    OLLAMA_MODEL=apertus-v1.5-8b-text:q4km POESIA_WEB_LLM=ollama poesia-web

Like ``cli.py`` this module is a composition root, so it may import any poesia package.
FastAPI and uvicorn are imported lazily (``pip install -e '.[web]'``). No
``from __future__ import annotations`` here: FastAPI has to resolve the request models defined
inside ``create_app`` at runtime.
"""

import os
from pathlib import Path
from typing import Any

WEBUI = Path(__file__).with_name("webui")

# Forms offered on the page: (language, form name).
FORMS: list[tuple[str, str]] = [
    ("es", "soneto"),
    ("en", "sonnet_shakespearean"),
    ("es", "haiku"),
    ("en", "haiku"),
    ("it", "sonetto"),
    # Free verse: no metre or rhyme checks; scanning still shows syllables, and safety,
    # suggestions, read-back and linking all work.
    ("es", "free"),
    ("en", "free"),
    ("it", "free"),
]
FREE = "free"
FREE_START_LINES = 8


# Read-back voices (clear licences, docs/CORPUS_SOURCES.md): es CC0, en public domain,
# it CC BY 4.0 (credit in the README).
VOICES = {
    "es": "es/es_ES/davefx/medium/es_ES-davefx-medium.onnx",
    "en": "en/en_US/ljspeech/medium/en_US-ljspeech-medium.onnx",
    "it": "it/it_IT/serena/medium/it_IT-serena-medium.onnx",
}
_voice_cache: dict[str, Any] = {}


def read_aloud(text: str, language: str) -> bytes:
    """WAV bytes of ``text`` in a stock synthetic voice (Piper, offline). Raises on no voice."""
    import io
    import wave

    from piper import PiperVoice

    if language not in _voice_cache:
        root = Path(os.environ.get("POESIA_PIPER_VOICES", "models/piper"))
        path = root / VOICES[language]
        if not path.exists():
            raise FileNotFoundError(f"voice not installed: {path}")
        _voice_cache[language] = PiperVoice.load(str(path))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        _voice_cache[language].synthesize_wav(text, wav)
    return buf.getvalue()


_link_index: Any = None


def link_poems(text: str, language: str, k: int = 3) -> list[dict[str, Any]]:
    """Public-domain or openly licensed poems near ``text`` in feeling (``poesia.linking``)."""
    global _link_index
    from poesia.linking import EmbeddingClient, LinkIndex

    if _link_index is None:
        _link_index = LinkIndex.load(os.environ.get("POESIA_LINK_INDEX", "data/linking"))
    vec = EmbeddingClient().embed([text[:2000]])[0]
    return _link_index.nearest(vec, language, k)


def _phonology(language: str) -> Any:
    if language == "es":
        from poesia.phonology.spanish import SpanishPhonology

        return SpanishPhonology()
    if language == "en":
        from poesia.phonology.english import EnglishPhonology

        return EnglishPhonology()
    if language == "it":
        from poesia.phonology.italian import ItalianPhonology

        return ItalianPhonology()
    raise ValueError(f"no phonology for language '{language}'")


def _form(language: str, name: str) -> Any:
    """The FormSpec, or None for free verse."""
    if name == FREE:
        return None
    from poesia.forms.definitions import get_form

    return get_form(name, language)


def _target(form: Any, index: int) -> int | None:
    if form is None:
        return None
    return (
        form.syllables_for_line(index) if index < form.total_lines or not form.total_lines else None
    )


def _letter(form: Any, index: int) -> str:
    if form is None:
        return ""
    scheme = form.rhyme_scheme.replace(" ", "")
    return scheme[index] if index < len(scheme) else ""


def _partner_index(form: Any, index: int) -> int | None:
    """First earlier line in the same rhyme group, or None (first of its group / unrhymed)."""
    if form is None:
        return None
    letter = _letter(form, index)
    if not letter.isalpha():
        return None
    scheme = form.rhyme_scheme.replace(" ", "")
    for j in range(index):
        if scheme[j] == letter:
            return j
    return None


def scan_line(
    line: str, language: str, form_name: str, index: int, lines: list[str]
) -> dict[str, Any]:
    """Deterministic check of one line in its place in the poem, with the lesson."""
    from poesia.teaching import teach_scan

    form = _form(language, form_name)
    phon = _phonology(language)
    target = _target(form, index)
    scan = phon.scan_line(line)
    lesson = teach_scan(
        scan, target, language=language, form_name=getattr(form, "name", None), ui_language=language
    )
    letter = _letter(form, index)
    partner = _partner_index(form, index)
    rhymes: bool | None = None
    partner_line = None
    key = phon.rhyme_key(line).consonant if line.strip() else ""
    if partner is not None and partner < len(lines) and lines[partner].strip():
        partner_line = lines[partner]
        rhymes = bool(key) and key == phon.rhyme_key(partner_line).consonant
    messages = list(lesson.messages)
    if rhymes is False and partner is not None:
        messages.append(
            {
                "en": f"Rhyme {letter}: this line should rhyme with line {partner + 1} "
                f"(“{partner_line}”). Change the last word.",
                "es": f"Rima {letter}: este verso debe rimar con el verso {partner + 1} "
                f"(«{partner_line}»). Cambia la última palabra.",
                "it": f"Rima {letter}: questo verso deve rimare con il verso {partner + 1} "
                f"(«{partner_line}»). Cambia l'ultima parola.",
            }[language]
        )
    return {
        "index": index,
        "syllables": scan.metrical_syllable_count,
        "target": target,
        "status": lesson.status,
        "stress": lesson.stress,
        "rhyme_letter": letter,
        "rhyme_key": key,
        "rhyme_partner": partner,
        "rhymes": rhymes,
        "messages": messages,
    }


def propose_lines(
    llm: Any,
    language: str,
    form_name: str,
    index: int,
    lines: list[str],
    theme: str,
    reflection: str,
    n: int = 3,
) -> list[dict[str, Any]]:
    """Ask the model for candidate lines and rank them by the deterministic scan."""
    from poesia.generation.candidate_generator import CandidateGenerator

    form = _form(language, form_name)
    phon = _phonology(language)
    target = _target(form, index)
    partner = _partner_index(form, index)
    prior = [ln for ln in lines[:index] if ln.strip()]
    rhyme_key = example = None
    if partner is not None and partner < len(lines) and lines[partner].strip():
        rhyme_key = phon.rhyme_key(lines[partner]).consonant or None
        example = (
            lines[partner].split()[-1].strip(".,;:!?¡¿«»\"'") if lines[partner].split() else None
        )
    anchor = theme.strip() or "what the author felt"
    if reflection.strip():
        anchor += f". What the author wrote about it: {reflection.strip()[:400]}"
    raw = CandidateGenerator(llm).generate_lines(
        theme=anchor,
        language=language,
        n_candidates=max(n * 2, 4),
        prior_lines=prior,
        target_syllables=target,
        target_rhyme_key=rhyme_key,
        example_rhyme_word=example,
    )
    seen: set[str] = set()
    ranked = []
    for cand in raw:
        text = cand.strip().strip("\"'«»").strip()
        if not text or text.lower() in seen or len(text.split()) < 3:
            continue
        seen.add(text.lower())
        result = scan_line(text, language, form_name, index, [*lines[:index], text])
        off = abs(result["syllables"] - target) if target else 0  # free verse: no metre rank
        ranked.append((off, result["rhymes"] is False, text, result))
    ranked.sort(key=lambda r: (r[0], r[1]))
    return [{"text": t, "check": res} for _, _, t, res in ranked[:n]]


def create_app(llm: Any | None = None) -> Any:
    """FastAPI app. ``llm`` defaults to ``POESIA_WEB_LLM`` (a registry name); without it, an
    OpenAI-compatible endpoint when ``LLM_BASE_URL`` is set, else Ollama (``OLLAMA_MODEL``)."""
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import FileResponse
    from pydantic import BaseModel, Field

    if llm is None:
        from poesia.generation.registry import get_llm

        default = "openai_compat" if os.environ.get("LLM_BASE_URL") else "ollama"
        llm = get_llm(os.environ.get("POESIA_WEB_LLM", default))

    app = FastAPI(title="PoesIA", docs_url=None, redoc_url=None)

    class LineRequest(BaseModel):
        language: str = Field(pattern="^(es|en|it)$")
        form: str
        index: int = Field(ge=0, le=200)  # free verse grows line by line
        lines: list[str] = Field(default_factory=list, max_length=200)

    class SafetyRequest(BaseModel):
        text: str = Field(default="", max_length=8000)

    class ReadRequest(BaseModel):
        language: str = Field(pattern="^(es|en|it)$")
        text: str = Field(min_length=1, max_length=4000)

    class LinkRequest(BaseModel):
        language: str = Field(pattern="^(es|en|it)$")
        text: str = Field(min_length=1, max_length=8000)

    class ProposeRequest(LineRequest):
        theme: str = Field(default="", max_length=200)
        reflection: str = Field(default="", max_length=4000)
        n: int = Field(default=3, ge=1, le=5)

    def _check(req: LineRequest) -> None:
        if (req.language, req.form) not in FORMS:
            raise HTTPException(status_code=400, detail="unknown form for this language")

    @app.get("/")
    def index() -> Any:
        return FileResponse(WEBUI / "index.html")

    @app.get("/api/forms")
    def forms() -> list[dict[str, Any]]:
        out = []
        for lang, name in FORMS:
            f = _form(lang, name)
            if f is None:
                out.append(
                    {
                        "language": lang,
                        "form": name,
                        "free": True,
                        "lines": FREE_START_LINES,
                        "scheme": "",
                        "syllables": [],
                        "stanzas": [],
                    }
                )
                continue
            out.append(
                {
                    "language": lang,
                    "form": name,
                    "free": False,
                    "lines": f.total_lines,
                    "scheme": f.rhyme_scheme.replace(" ", ""),
                    "syllables": [f.syllables_for_line(i) for i in range(f.total_lines)],
                    "stanzas": list(f.lines_per_stanza),
                }
            )
        return out

    @app.post("/api/scan")
    def scan(req: LineRequest) -> dict[str, Any]:
        _check(req)
        line = req.lines[req.index] if req.index < len(req.lines) else ""
        return scan_line(line, req.language, req.form, req.index, req.lines)

    @app.post("/api/safety")
    def safety(req: SafetyRequest) -> dict[str, Any]:
        """Screen a reflection or line; nothing is stored or logged."""
        from poesia.safety import screen

        result = screen(req.text, llm=llm)
        return {"flagged": result.flagged, "resources": result.resources}

    @app.post("/api/readback")
    def readback(req: ReadRequest) -> Any:
        """The poem read by a labelled synthetic voice; no cloning, nothing stored."""
        from fastapi.responses import Response

        try:
            audio = read_aloud(req.text, req.language)
        except (ImportError, FileNotFoundError) as exc:
            raise HTTPException(status_code=503, detail=f"read-back unavailable: {exc}") from exc
        return Response(content=audio, media_type="audio/wav")

    @app.post("/api/link")
    def link(req: LinkRequest) -> dict[str, Any]:
        """Two or three poems from the person's tradition on the same feeling."""
        try:
            poems = link_poems(req.text, req.language)
        except Exception as exc:  # no index or no embedding endpoint: the page works without
            raise HTTPException(status_code=503, detail=f"linking unavailable: {exc}") from exc
        return {"poems": poems}

    @app.post("/api/propose")
    def propose(req: ProposeRequest) -> dict[str, Any]:
        _check(req)
        try:
            props = propose_lines(
                llm, req.language, req.form, req.index, req.lines, req.theme, req.reflection, req.n
            )
        except Exception as exc:  # model offline etc.: the page keeps working without it
            raise HTTPException(status_code=503, detail=f"model unavailable: {exc}") from exc
        return {"proposals": props, "model": getattr(llm, "model", "")}

    return app


def main() -> None:
    import uvicorn

    host = os.environ.get("POESIA_WEB_HOST", "127.0.0.1")
    port = int(os.environ.get("POESIA_WEB_PORT", "8000"))
    uvicorn.run(create_app(), host=host, port=port)


if __name__ == "__main__":
    main()
