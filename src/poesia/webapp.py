"""Local web page for writing a poem with PoesIA (Hack Apertus entry, docs/HACK_APERTUS_PLAN.md §2).

The person writes; the engine checks. Every line slot is the author's own text field. The
server scans a line (syllables, stress, rhyme against the form's scheme) and explains it in
plain words (``poesia.teaching``); it proposes lines only when asked, ranked by the same
deterministic scan, never by model likelihood. It keeps nothing: no database, no logs of
what is written. Saving is the browser downloading the poem to the author's own disk.

Run (binds to this machine only):

    poesia-web                     # or: python -m poesia.webapp
    OLLAMA_MODEL=apertus-v1.5-8b-text:q4km POESIA_WEB_LLM=ollama poesia-web
    poesia-web --with-ollama --link-index data/linking --open   # native: Ollama app only

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
    ("de", "sonett"),
    ("fr", "sonnet"),
    # Free verse: no metre or rhyme checks; scanning still shows syllables, and safety,
    # suggestions, read-back and linking all work.
    ("es", "free"),
    ("en", "free"),
    ("it", "free"),
    ("de", "free"),
    ("fr", "free"),
]
FREE = "free"
FREE_START_LINES = 8


_voice_cache: dict[str, Any] = {}


def read_aloud(text: str, language: str) -> bytes:
    """WAV bytes of ``text`` in a stock synthetic voice (Piper, offline). Raises on no voice."""
    import io
    import wave

    from piper import PiperVoice

    from poesia.voices import VOICES, voice_dir

    if language not in _voice_cache:
        path = voice_dir() / VOICES[language]
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
    if language == "de":
        from poesia.phonology.german import GermanPhonology

        return GermanPhonology()
    if language == "fr":
        from poesia.phonology.french import FrenchPhonology

        return FrenchPhonology()
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


# Function words per language, for spotting a line written in another language than the
# form's (U5). Shared words ("la", "in", "no", "con") count for each language they belong to.
_FUNCTION_WORDS = {
    "es": set(
        "el la los las que de y en con por para del una un como mi su sus sin se lo al más pero es no muy".split()
    ),
    "en": set(
        "the and of to in a is my with on for that it as his her your from by at not are was i you we".split()
    ),
    "it": set(
        "il lo la gli le che di e in con per del della una un come mio mia sua non si nel nella al ma è ed dei".split()
    ),
    "de": set(
        "der die das und ist nicht ich du er sie es wir ein eine mit von zu auf dem den des im mein dein sich auch wie".split()
    ),
    "fr": set(
        "le la les et est un une des du de que qui dans pour pas ne je tu il elle nous vous mon ma mes sur au aux".split()
    ),
}
_LANG_NAME = {
    "es": {"es": "español", "en": "inglés", "it": "italiano", "de": "alemán", "fr": "francés"},
    "en": {"es": "Spanish", "en": "English", "it": "Italian", "de": "German", "fr": "French"},
    "it": {"es": "spagnolo", "en": "inglese", "it": "italiano", "de": "tedesco", "fr": "francese"},
    "de": {
        "es": "Spanisch",
        "en": "Englisch",
        "it": "Italienisch",
        "de": "Deutsch",
        "fr": "Französisch",
    },
    "fr": {"es": "espagnol", "en": "anglais", "it": "italien", "de": "allemand", "fr": "français"},
}
_MISMATCH = {
    "es": "Este verso parece estar en {other}; esta forma cuenta las sílabas en {own}.",
    "en": "This line looks {other}; this form counts syllables in {own}.",
    "it": "Questo verso sembra in {other}; questa forma conta le sillabe in {own}.",
    "de": "Dieser Vers sieht nach {other} aus; diese Form zählt die Silben auf {own}.",
    "fr": "Ce vers semble être en {other} ; cette forme compte les syllabes en {own}.",
}


def guess_language(line: str) -> str | None:
    """The language the function words point to clearly, else None."""
    words = [w.strip(".,;:!?¡¿«»\"'()").lower() for w in line.replace("’", "'").split()]
    words = [w.split("'")[-1] if "'" in w else w for w in words]
    scores = {lang: sum(w in fw for w in words) for lang, fw in _FUNCTION_WORDS.items()}
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    (best, top), (_, second) = ranked[0], ranked[1]
    return best if top >= 2 and top - second >= 2 else None


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
    looks_like = guess_language(line)
    mismatch = looks_like is not None and looks_like != language
    if looks_like is not None and mismatch:
        names = _LANG_NAME[language]
        messages.insert(0, _MISMATCH[language].format(other=names[looks_like], own=names[language]))
    if rhymes is False and partner is not None:
        messages.append(
            {
                "en": f"Rhyme {letter}: this line should rhyme with line {partner + 1} "
                f"(“{partner_line}”). Change the last word.",
                "es": f"Rima {letter}: este verso debe rimar con el verso {partner + 1} "
                f"(«{partner_line}»). Cambia la última palabra.",
                "it": f"Rima {letter}: questo verso deve rimare con il verso {partner + 1} "
                f"(«{partner_line}»). Cambia l'ultima parola.",
                "de": f"Reim {letter}: dieser Vers soll sich auf Vers {partner + 1} reimen "
                f"(„{partner_line}“). Ändere das letzte Wort.",
                "fr": f"Rime {letter} : ce vers doit rimer avec le vers {partner + 1} "
                f"(« {partner_line} »). Change le dernier mot.",
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
        "other_language": looks_like if mismatch else None,
        # A line in another language is shown in that language's syllables, as the hint says.
        "view": _view(line, looks_like if looks_like is not None and mismatch else language),
    }


def _view(line: str, language: str) -> list[dict[str, Any]]:
    """Syllables for display (poesia.scansion_view); never fails the scan."""
    try:
        from poesia.scansion_view import syllable_view

        return syllable_view(line, language)
    except Exception:
        return []


_PUNCT_OPEN = ".,;:!?¡¿«»\"'()—–-…“”‘’„"


def _raw_proposals(
    llm: Any, language: str, form_name: str, index: int, lines: list[str], anchor: str, n: int
) -> tuple[list[str], str | None]:
    """Model candidates for one line, and the partner's rhyme word (or None)."""
    from poesia.generation.candidate_generator import CandidateGenerator

    form = _form(language, form_name)
    partner = _partner_index(form, index)
    example = None
    if partner is not None and partner < len(lines) and lines[partner].split():
        example = lines[partner].split()[-1].strip(".,;:!?¡¿«»\"'")
    if form is None:  # free verse: no metre or rhyme to repair
        prior = [ln for ln in lines[:index] if ln.strip()]
        raw = CandidateGenerator(llm).generate_lines(
            theme=anchor, language=language, n_candidates=max(n * 2, 4), prior_lines=prior
        )
        return raw, None
    # The engine's own line machinery (docs/GENERATION_QUALITY_PLAN.md): 8 candidates, the
    # best repaired for metre and rhyme with the rhyme word named, the same word refused.
    from poesia.generation.constrained_loop import ConstrainedLoop

    loop = ConstrainedLoop(language=language, form=form_name, llm=llm)
    raw = loop.propose_line(anchor, index, lines, n_candidates=max(n * 2, 8), max_repair_attempts=2)
    return raw, example


def _proposal_rank(
    text: str, result: dict[str, Any], target: int | None, openings: set[str]
) -> tuple[bool, int, bool, bool]:
    """Sort key: right language, metre, rhyme, a new opening word (in that order).

    A line in another language comes last: Apertus slipped into English in 10-22% of benchmark
    lines in it/de/fr (2026-10-09), and the target language's counter would happily count it.
    The prompt asks for a new opening word, yet seven of fourteen French lines began "Sous le".
    """
    off = abs(result["syllables"] - target) if target else 0  # free verse: no metre rank
    repeats_opening = text.split()[0].lower().strip(_PUNCT_OPEN) in openings
    return (result["other_language"] is not None, off, result["rhymes"] is False, repeats_opening)


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
    from poesia.word_ideas import last_word

    anchor = theme.strip() or "what the author felt"
    if reflection.strip():
        anchor += f". What the author wrote about it: {reflection.strip()[:400]}"
    raw, example = _raw_proposals(llm, language, form_name, index, lines, anchor, n)
    target = _target(_form(language, form_name), index)
    prior = [ln for ln in lines[:index] if ln.strip()]
    openings = {ln.split()[0].lower().strip(_PUNCT_OPEN) for ln in prior if ln.split()}
    seen: set[str] = set()
    ranked = []
    for cand in raw:
        text = cand.strip().strip("\"'«»").strip()
        if not text or text.lower() in seen or len(text.split()) < 3:
            continue
        seen.add(text.lower())
        if example and last_word(text) == example.lower():
            continue  # the partner's own word is not a rhyme
        result = scan_line(text, language, form_name, index, [*lines[:index], text])
        ranked.append((_proposal_rank(text, result, target, openings), text, result))
    ranked.sort(key=lambda r: r[0])
    return [{"text": t, "check": res} for _, t, res in ranked[:n]]


def create_app(llm: Any | None = None, setup: Any | None = None) -> Any:
    """FastAPI app. ``llm`` defaults to ``POESIA_WEB_LLM`` (a registry name); without it, an
    OpenAI-compatible endpoint when ``LLM_BASE_URL`` is set, else Ollama (``OLLAMA_MODEL``).

    ``setup`` (or ``POESIA_SETUP_OLLAMA``, an Ollama URL) prepares the models in the
    background on first run (``poesia.model_setup``); ``/api/status`` reports its progress.
    """
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import FileResponse
    from pydantic import BaseModel, Field

    if setup is None and os.environ.get("POESIA_SETUP_OLLAMA", "off") not in ("", "off", "none"):
        from poesia.model_setup import OllamaSetup

        setup = OllamaSetup(os.environ["POESIA_SETUP_OLLAMA"])
        setup.start()

    if llm is None:
        from poesia.generation.registry import get_llm

        default = "openai_compat" if os.environ.get("LLM_BASE_URL") else "ollama"
        llm = get_llm(os.environ.get("POESIA_WEB_LLM", default))

    app = FastAPI(title="PoesIA", docs_url=None, redoc_url=None)

    class LineRequest(BaseModel):
        language: str = Field(pattern="^(es|en|it|de|fr)$")
        form: str
        index: int = Field(ge=0, le=200)  # free verse grows line by line
        lines: list[str] = Field(default_factory=list, max_length=200)

    class SafetyRequest(BaseModel):
        text: str = Field(default="", max_length=8000)
        language: str = Field(default="en", pattern="^(es|en|it|de|fr)$")  # of the pause's text

    class ReadRequest(BaseModel):
        language: str = Field(pattern="^(es|en|it|de|fr)$")
        text: str = Field(min_length=1, max_length=4000)

    class LinkRequest(BaseModel):
        language: str = Field(pattern="^(es|en|it|de|fr)$")
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

    @app.get("/api/status")
    def status() -> dict[str, Any]:
        """Model readiness: 'ready' unless a first-run setup is still working (or failed)."""
        if setup is None:
            return {"phase": "ready"}
        out = dict(setup.status.as_dict())
        if out["phase"] == "ready":
            out["gpu_fraction"] = (
                setup.gpu_fraction()
            )  # P6: say when the model runs (partly) on CPU
        return out

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
        from poesia.safety.screen import resources_for

        result = screen(req.text, llm=llm)
        return {
            "flagged": result.flagged,
            "resources": resources_for(req.language) if result.flagged else [],
        }

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

    @app.post("/api/words")
    def words(req: LineRequest) -> dict[str, Any]:
        """Rhyme words for line ``index`` (U6: small suggestions first, offline)."""
        from poesia.word_ideas import last_word, rhyme_words

        _check(req)
        form = _form(req.language, req.form)
        partner = _partner_index(form, req.index)
        if partner is None:
            # The first line of its rhyme (or free verse): any last word works.
            return {"words": [], "partner": None, "reason": "free" if form is None else "first"}
        partner_line = req.lines[partner] if partner < len(req.lines) else ""
        if not partner_line.strip():
            return {"words": [], "partner": partner, "reason": "partner_empty"}
        avoid = {last_word(ln) for j, ln in enumerate(req.lines) if j != req.index and ln.strip()}
        return {
            "words": rhyme_words(req.language, partner_line, avoid=avoid),
            "partner": partner,
            "partner_word": last_word(partner_line),
            "reason": "",
        }

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


def _use_local_ollama(url: str) -> None:
    """Point the page at an Ollama app on this machine (native install, no Docker)."""
    import json
    import urllib.request

    try:
        with urllib.request.urlopen(f"{url}/api/version", timeout=5) as resp:
            json.loads(resp.read())
    except OSError:
        raise SystemExit(
            f"No Ollama at {url}. Install the Ollama app (https://ollama.com/download), "
            "start it, and run this again."
        ) from None
    os.environ.setdefault("LLM_BASE_URL", f"{url}/v1")
    os.environ.setdefault("LLM_NAME", "poesia-apertus")
    os.environ.setdefault("EMBED_NAME", "poesia-embed")
    os.environ.setdefault("POESIA_SETUP_OLLAMA", url)  # the page prepares the models


def _ensure_voices() -> None:
    from poesia import voices

    if "POESIA_PIPER_VOICES" not in os.environ:
        os.environ["POESIA_PIPER_VOICES"] = str(voices.user_voice_dir())
    root = voices.voice_dir()
    if voices.missing(root):
        try:
            voices.fetch(root)
        except OSError as exc:  # read-back is optional; the page still works without it
            print(f"Could not download the read-back voices ({exc}); continuing without.")


def main(argv: list[str] | None = None) -> None:
    """``poesia-web``; ``poesia-web --with-ollama --link-index DIR --open`` for a native install.

    With ``--with-ollama`` the page uses the Ollama app on this machine and prepares the models
    there on first run (progress on the page), and the read-back voices are fetched once into
    the user's data folder. Settings already in the environment win over these defaults.
    """
    import argparse

    ap = argparse.ArgumentParser(prog="poesia-web", description="PoesIA writing page")
    ap.add_argument(
        "--with-ollama",
        nargs="?",
        const="http://localhost:11434",
        metavar="URL",
        help="use the Ollama app on this machine (default URL http://localhost:11434)",
    )
    ap.add_argument("--link-index", metavar="DIR", help="linking index folder (data/linking)")
    ap.add_argument("--open", action="store_true", help="open the page in the browser")
    args = ap.parse_args(argv)

    import uvicorn

    if args.with_ollama:
        _use_local_ollama(args.with_ollama.rstrip("/"))
        _ensure_voices()
    if args.link_index:
        os.environ["POESIA_LINK_INDEX"] = args.link_index
    host = os.environ.get("POESIA_WEB_HOST", "127.0.0.1")
    port = int(os.environ.get("POESIA_WEB_PORT", "8000"))
    app = create_app()
    if args.open:
        import threading
        import webbrowser

        threading.Timer(1.5, webbrowser.open, [f"http://localhost:{port}"]).start()
    print(f"PoesIA: http://localhost:{port}  (stop with Ctrl+C)")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
