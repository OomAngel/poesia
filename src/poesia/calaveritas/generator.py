"""Write a calaverita: the story first, then the verse, with minimal repair.

One plan call tells the story (the gist, what happens in each stanza, the punchline: one storyline,
not one trait per stanza). English: POEM_DRAFTS whole-poem drafts, ranked by an editor call on story
and sense, the best mended. Spanish: per stanza, DRAFTS drafts on the story's beat plus a shortened
version of the long ones, the JUDGED closest to the form ranked by the editor, the best mended.
Mending keeps the draft's lines and repairs only real defects (metre beyond RELAXED_TOLERANCE, a
missing required rhyme, a copied, unsafe or broken line); a repeated word is tried once. Only if
the story path cannot deliver a stanza does the earlier engine run (full gates, line by line), so
the form never fails where it did not before. Every stanza rhymes at least lines 2 and 4 (``abcb``,
the commonest scheme in the transcribed broadsides, 21 of 49); a draft in ABAB or ABBA keeps it.

Why (2026-10-15, 12 + 12 traced requests): the full gates rewrote most lines one at a time (Spanish:
1-3 of 12 final lines were the model's own) and the joke was lost; PoesIA's poems that held up came
from one whole-poem draft and repair of only what failed.

Providers are OpenAI-compatible chat endpoints configured by environment variables:
``CALAVERITAS_LLM_URL`` / ``_MODEL`` / ``_KEY`` (primary: CSCS, Switzerland, receives the name) and
``CALAVERITAS_FALLBACK_URL`` / ``_MODEL`` / ``_KEY`` (used only when the primary fails; never receives
the name, see prompt.PLACEHOLDER). Nothing is stored; the request lives only for the call.
"""

from __future__ import annotations

import json
import os
import random
import re
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from poesia.phonology.base import ScanResult
from poesia.quality import gates

from . import plan as planmod
from . import quality
from .guard import check_output
from .options import Request, Tone
from .prompt import PLACEHOLDER

TARGET = 8
# Metre gate: the target must be among the counts the licences allow (synalepha/dialefa,
# syneresis/dieresis; phonology.spanish_metre, 92% exact on broadside octosyllables), within
# this slack. English has one count per line, so it keeps a window.
METRE_TOLERANCE = {"es": 0, "en": 2}
# When no candidate hits the target exactly, the best one within this slack is kept rather
# than failing the poem: strict-only failed 11 of 33 Spanish requests (2026-10-10, 40-request
# batch), while lines at exactly 8 rose from 37% to 86%.
RELAXED_TOLERANCE = {"es": 1, "en": 2}
# Sense (POETICS #4): a line whose mean token log-probability is below this is broken Spanish and
# goes to repair. Real verse lines: median -4.6, 4% below -6.5; flagged bad lines: half below.
# English, measured the same way with its own header (scripts/quality/sense_floor_calibrate.py,
# 2026-10-15): real lines median -3.6, 1% below -6.5; broken copies 42% below. On 40 English
# requests -6.5 failed no more often than no floor (34/40 each), while -6.0 failed 6 of 20 against 1.
# Its gain is small: ranking by sense already drops most weak lines (3 -> 1 of ~366 below -6.5).
# (A Spanish header had made 5 of 7 English requests fail.)
SENSE_FLOOR = {"es": -6.5, "en": -6.5}
SENSE_WEIGHT = 1.0  # per nat above the median of the candidates for the same slot
SENSE_PREFIX = {
    "es": "Calaverita (poema mexicano en verso):\n",
    "en": "Calaverita (Mexican Day of the Dead verse):\n",
}
# Seconds per model call and per poem; the environment may raise them for slow hosts (a Kaggle T4).
CALL_TIMEOUT = float(os.environ.get("CALAVERITAS_CALL_TIMEOUT") or 25.0)
TOTAL_BUDGET = float(os.environ.get("CALAVERITAS_TOTAL_BUDGET") or 90.0)


class GenerationError(Exception):
    """``code``: "unavailable" (no provider answered), "quality" (form not met), "floor"."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass
class Provider:
    label: str
    url: str
    model: str
    key: str
    sends_names: bool
    # Reasoning models (gpt-oss, Qwen3) spend output tokens on hidden reasoning that count against
    # max_tokens: ``extra`` carries e.g. {"reasoning_effort": "low"}, ``min_tokens`` raises the cap.
    extra: dict = field(default_factory=dict)
    min_tokens: int = 0
    # Sense signal: the endpoint scores a line's token log-probabilities (/completions with echo;
    # CSCS serves it). Off unless the operator turns it on, so tests and other hosts make no call.
    sense: bool = False
    # An optional second model that writes drafts and repair candidates (never the story, the
    # editor's choices or the checks), always with the name masked; any error falls back to self.
    drafter: Provider | None = None
    draft_langs: tuple[str, ...] = ("es",)

    def line_logprob(self, context: list[str], line: str, language: str = "es") -> float | None:
        """Mean token log-probability of ``line`` after ``context`` (None if not available).

        Measured 2026-10-14 (scripts/quality/sense_instrument_eval.py): it ranks a real verse line
        above a broken copy of it 90% of the time; broken Spanish scores far below real lines
        (-6.5 and lower vs a median of -4.6); fluent nonsense is not caught."""
        if not self.sense:
            return None
        prefix = SENSE_PREFIX.get(language, SENSE_PREFIX["en"]) + "".join(c + "\n" for c in context)
        payload = {
            "model": self.model,
            "prompt": prefix + line,
            "max_tokens": 1,
            "echo": True,
            "logprobs": 1,
            "temperature": 0,
        }
        headers = {"Content-Type": "application/json", "User-Agent": "poesia-calaveritas/1.0"}
        if self.key:
            headers["Authorization"] = f"Bearer {self.key}"
        req = urllib.request.Request(  # noqa: S310 - URL comes from the operator's configuration
            f"{self.url.rstrip('/')}/completions",
            data=json.dumps(payload).encode(),
            headers=headers,
        )
        try:
            with urllib.request.urlopen(req, timeout=CALL_TIMEOUT) as resp:  # noqa: S310
                lp = json.loads(resp.read().decode())["choices"][0]["logprobs"]
            values = [
                v
                for o, v in zip(lp["text_offset"], lp["token_logprobs"], strict=False)
                if o >= len(prefix) and v is not None
            ]
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError, TypeError):
            return None
        return sum(values) / len(values) if values else None

    def chat(
        self, msgs: list[dict[str, str]], temperature: float = 0.9, max_tokens: int = 160
    ) -> str:
        payload = {
            "model": self.model,
            "messages": msgs,
            "temperature": temperature,
            "max_tokens": max(max_tokens, self.min_tokens),
            "seed": random.randrange(2**31),  # noqa: S311 - sampling seed, not security
            **self.extra,
        }
        headers = {"Content-Type": "application/json", "User-Agent": "poesia-calaveritas/1.0"}
        if self.key:
            headers["Authorization"] = f"Bearer {self.key}"
        req = urllib.request.Request(  # noqa: S310 - URL comes from the operator's configuration
            f"{self.url.rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode(),
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=CALL_TIMEOUT) as resp:  # noqa: S310
            res = json.loads(resp.read().decode())
        choices = res.get("choices") or [{}]
        return (choices[0].get("message", {}).get("content") or "").strip()


class _NameMask(Provider):
    """Wraps a provider that must not receive names: every message has the name replaced by the
    placeholder before it leaves, whatever prompt produced it (drafts, repairs, the editor's pass)."""

    def __init__(self, inner: Provider, name: str) -> None:
        super().__init__(inner.label, inner.url, inner.model, inner.key, False)
        self.inner = inner
        self._pattern = re.compile(rf"(?<!\w){re.escape(name)}(?!\w)") if name.strip() else None

    def line_logprob(self, context: list[str], line: str, language: str = "es") -> float | None:
        if self._pattern is None:
            return self.inner.line_logprob(context, line, language)
        return self.inner.line_logprob(
            [self._pattern.sub(PLACEHOLDER, c) for c in context],
            self._pattern.sub(PLACEHOLDER, line),
            language,
        )

    def chat(
        self, msgs: list[dict[str, str]], temperature: float = 0.9, max_tokens: int = 160
    ) -> str:
        if self._pattern is not None:
            msgs = [{**m, "content": self._pattern.sub(PLACEHOLDER, m["content"])} for m in msgs]
        return self.inner.chat(msgs, temperature, max_tokens)


def providers_from_env(env: dict[str, str] | None = None) -> list[Provider]:
    """``CALAVERITAS_LLM_*`` (receives names) then ``CALAVERITAS_FALLBACK_*`` (masked names);
    each may add ``_EXTRA`` (JSON merged into the request) and ``_MIN_TOKENS``."""
    env = dict(os.environ if env is None else env)
    out = []
    for prefix, label, sends_names in (
        ("CALAVERITAS_LLM", "Apertus · CSCS", True),
        ("CALAVERITAS_FALLBACK", "Apertus · fallback", False),
    ):
        if env.get(f"{prefix}_URL") and env.get(f"{prefix}_MODEL"):
            out.append(
                Provider(
                    env.get(f"{prefix}_LABEL", label),
                    env[f"{prefix}_URL"],
                    env[f"{prefix}_MODEL"],
                    env.get(f"{prefix}_KEY", ""),
                    sends_names,
                    json.loads(env.get(f"{prefix}_EXTRA") or "{}"),
                    int(env.get(f"{prefix}_MIN_TOKENS") or 0),
                    env.get(f"{prefix}_SENSE", "logprob") == "logprob",
                )
            )
    if out and env.get("CALAVERITAS_DRAFT_URL") and env.get("CALAVERITAS_DRAFT_MODEL"):
        out[0].drafter = Provider(
            env.get("CALAVERITAS_DRAFT_LABEL", "drafts"),
            env["CALAVERITAS_DRAFT_URL"],
            env["CALAVERITAS_DRAFT_MODEL"],
            env.get("CALAVERITAS_DRAFT_KEY", ""),
            False,
            json.loads(env.get("CALAVERITAS_DRAFT_EXTRA") or "{}"),
            int(env.get("CALAVERITAS_DRAFT_MIN_TOKENS") or 0),
        )
        out[0].draft_langs = tuple(
            x.strip() for x in env.get("CALAVERITAS_DRAFT_LANGS", "es").split(",") if x.strip()
        )
    return out


_PHON: dict[str, object] = {}
_PHON_LOCK = threading.Lock()


def _phonology(language: str) -> object:
    with _PHON_LOCK:
        if language not in _PHON:
            if language == "es":
                from poesia.phonology.spanish import SpanishPhonology

                _PHON[language] = SpanishPhonology()
            else:
                from poesia.phonology.english import EnglishPhonology

                _PHON[language] = EnglishPhonology()
        return _PHON[language]


def scan(line: str, language: str) -> ScanResult:
    """The language's scan of ``line``: best count and, in Spanish, the licensed counts."""
    return _phonology(language).scan_line(line)  # type: ignore[attr-defined]


def syllables(line: str, language: str) -> int:
    return scan(line, language).metrical_syllable_count


_NUMBERING = re.compile(r"^\s*(?:\d+[.)]|[-*•])\s*")


def parse_quatrain(text: str) -> list[str] | None:
    lines = []
    for raw in text.splitlines():
        line = _NUMBERING.sub("", raw).strip().strip("\"“”«»'").strip()
        if not line or line.lower().startswith(
            ("estrofa", "stanza", "calaverita", "aquí tienes", "here is")
        ):
            continue
        lines.append(line)
    return lines if len(lines) == 4 else None


def _rhymes(a: str, b: str, language: str, loose: bool) -> bool:
    """Phonetic rhyme (shared key; Spanish with seseo), the same word never rhymes with itself."""
    return gates.rhyme(b, a, _phonology(language), loose) is None  # type: ignore[arg-type]


def scheme(lines: list[str], language: str) -> str | None:
    """ "ABAB" / "ABBA" (full rhyme), "abcb" (lines 2 and 4 rhyme, assonance allowed), or None."""
    if _rhymes(lines[0], lines[2], language, False) and _rhymes(
        lines[1], lines[3], language, False
    ):
        return "ABAB"
    if _rhymes(lines[0], lines[3], language, False) and _rhymes(
        lines[1], lines[2], language, False
    ):
        return "ABBA"
    if _rhymes(lines[1], lines[3], language, True):
        return "abcb"
    return None


@dataclass
class Stanza:
    lines: list[str]
    counts: list[int]
    scheme: str


@dataclass
class Poem:
    language: str
    stanzas: list[Stanza]
    model: str
    elapsed_s: float
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "language": self.language,
            "stanzas": [
                {"lines": s.lines, "syllables": s.counts, "scheme": s.scheme} for s in self.stanzas
            ],
            "model": self.model,
            "elapsed_s": round(self.elapsed_s, 1),
            "target_syllables": TARGET,
        }


def _restore(lines: list[str], name: str) -> list[str]:
    return [re.sub(rf"\b{PLACEHOLDER}\b", name, line, flags=re.I) for line in lines]


def _norm(line: str) -> str:
    return re.sub(r"[^\w]+", " ", line.lower()).strip()


def write(request: Request, providers: list[Provider], rng: random.Random | None = None) -> Poem:
    """Write ``request.stanzas`` stanzas or raise GenerationError."""
    if not providers:
        raise GenerationError("unavailable")
    t0 = time.monotonic()
    rng = rng or random.Random()  # noqa: S311 - sampling, not security
    last_error = "unavailable"
    for provider in providers:
        if not provider.sends_names:
            provider = _NameMask(provider, request.name)
        try:
            stanzas = _write_with(provider, request, rng, t0)
            return Poem(request.language, stanzas, provider.label, time.monotonic() - t0)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            last_error = "unavailable"
            continue
        except GenerationError as e:
            last_error = e.code
            if e.code != "unavailable":
                break  # the form or the floor failed: another provider would not be safer
    raise GenerationError(last_error)


def _parse_line(text: str) -> str | None:
    for raw in text.splitlines():
        line = _NUMBERING.sub("", raw).strip()
        line = (
            re.sub(r"^(verso|line)\s*\d+\s*[:.-]\s*", "", line, flags=re.I).strip("\"“”«»'").strip()
        )
        if line:
            return line if 2 < len(line.split()) <= 12 else None
    return None


def _end_word(line: str) -> str:
    words = re.findall(r"[A-Za-zÀ-ÿ'’]+", line)
    return words[-1].lower() if words else ""


def _ask_many(
    provider: Provider, batches: list[list[dict[str, str]]], temperature: float
) -> list[str]:
    """One call per message list, in parallel; raises a connection error only if every call failed."""
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=len(batches)) as pool:
        futures = [pool.submit(provider.chat, msgs, temperature) for msgs in batches]
    out, errors = [], []
    for f in futures:
        try:
            out.append(f.result())
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
            errors.append(e)
    if not out and errors:
        raise errors[0]
    return out


def _drafter(ctx: _Ctx) -> Provider | None:
    d = getattr(ctx.provider, "drafter", None)
    return d if d is not None and ctx.lang in ctx.provider.draft_langs else None


def _write_many(ctx: _Ctx, batches: list[list[dict[str, str]]], temperature: float) -> list[str]:
    """Draft or repair calls: the drafter (name masked) if one is set for the language, else the
    provider; if the drafter fails or is rate-limited, the provider answers instead."""
    d = _drafter(ctx)
    if d is not None:
        try:
            got = _ask_many(_NameMask(d, ctx.request.name), batches, temperature)
            if got:
                return got
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            pass
    return _ask_many(ctx.provider, batches, temperature)


def _start(line: str) -> str:
    return gates.opening(line)


def _clashes(line: str, others: list[str], language: str) -> bool:
    """Same two opening words as another line, or the same opening content word ("Memo..., Memo...")."""
    return gates.opening_clash(line, tuple(others), language) is not None


def _dangling(line: str, language: str) -> bool:
    return gates.dangling(line, language) is not None


def _allowed_words(request: Request) -> frozenset[str]:
    """Words the vocabulary check accepts besides the word list: name, traits, detail, genre."""
    from .options import TRAITS
    from .rhymebank import GENRE_WORDS

    text = " ".join(
        [request.name, request.detail, *(TRAITS[t][request.language] for t in request.traits)]
    )
    own = {w.lower() for w in re.findall(r"[A-Za-zÀ-ÿ]+", text)} | {PLACEHOLDER.lower()}
    return frozenset(own | GENRE_WORDS[request.language])


def _may_repeat(request: Request) -> frozenset[str]:
    """Words a poem may repeat (POETICS #3 otherwise forbids it): the name, and the genre's
    words, which the broadsides repeat like a refrain ("calaveras ... calaveras")."""
    from .rhymebank import GENRE_WORDS

    name = {w.lower() for w in re.findall(r"[A-Za-zÀ-ÿ]+", request.name)}
    return frozenset(name | {PLACEHOLDER.lower()} | GENRE_WORDS[request.language])


def _gibberish(line: str, request: Request) -> bool:
    return bool(gates.unknown_words(line, request.language, _allowed_words(request)))


def _polish(lines: list[str]) -> list[str]:
    """Capital letter at the start of each line, closing punctuation at the end of the stanza."""
    out = []
    for line in lines:
        m = re.search(r"[A-Za-zÀ-ÿ]", line)
        out.append(
            line[: m.start()] + line[m.start()].upper() + line[m.start() + 1 :] if m else line
        )
    if out and not re.search(r"[.!?…»”]$", out[-1]):
        out[-1] = out[-1].rstrip(",;:") + "."
    return out


LINE_CANDIDATES = 8  # repair calls per line, in parallel
SHOWN = 4  # best-ranked candidates the fluency check sees
BANK = 4  # rhyme words offered per repair call (each call gets its own sample)
DRAFTS = 6
REPAIR_DRAFTS = 4  # drafts repaired in parallel; every one that passes becomes a candidate
DRAFT_ROUNDS = 2  # a new round when the editor rejects every candidate
POEM_DRAFTS = 4  # whole-poem drafts per round (English)
# With a drafter on a free tier (Groq: 8,000 tokens a minute), fewer calls per poem: whole-poem
# drafts in Spanish too (Qwen 27B keeps the octosyllable over a whole poem: 86% of lines at 7-9,
# Apertus 70B 34% on single stanzas; 2026-10-16) and fewer repair candidates.
POEM_DRAFTS_DRAFTER = 3
LINE_CANDIDATES_DRAFTER = 4
JUDGED = (
    5  # stanza drafts (with their shortened versions) the editor ranks, closest to the form first
)
# CALAVERITAS_PROFILE=lite: about 2-3x fewer calls, for comparing models on slow hosts (a Kaggle T4
# served ~1 call per 3 s, too slow for the full engine; 2026-10-09). The live site uses the default.
# A first lite profile (3 drafts, 2 repaired, 3 candidates, 1 round) failed 29 of 40 requests on
# Apertus 70B (2026-10-10): too few line candidates leave the fallback without usable lines.
if os.environ.get("CALAVERITAS_PROFILE") == "lite":
    DRAFTS, REPAIR_DRAFTS, LINE_CANDIDATES, DRAFT_ROUNDS = 4, 2, 6, 2
FALLBACK_TRIES = 2  # per line; the last try keeps the best-ranked line even if the check says none
# 0.9 drafts made less sense; at 0.6-0.7 Apertus 70B keeps the thread (2026-10-09)
DRAFT_TEMPERATURE = 0.7
REPAIR_TEMPERATURE = 0.7


@dataclass
class _Ctx:
    """One stanza being written: the request, the plan and what earlier stanzas used."""

    provider: Provider
    request: Request
    index: int
    done: list[Stanza]
    plan: planmod.Plan
    rng: random.Random
    t0: float
    lps: dict = field(default_factory=dict)  # (context, line) -> mean log-probability
    # Minimal repair (the story-first path): only real defects send a line to repair; repeats and
    # reused end words are tried once and kept if no repair passes (see _mend_stanza).
    minimal: bool = False
    exact: bool = False  # tightening: the metre gate at the exact target again

    def logprob(self, context: list[str], line: str) -> float | None:
        key = (tuple(context), line)
        if key not in self.lps:
            self.lps[key] = self.provider.line_logprob(list(context), line, self.request.language)
        return self.lps[key]

    @property
    def lang(self) -> str:
        return self.request.language

    @property
    def escolar(self) -> bool:
        return self.request.tone is Tone.ESCOLAR

    @property
    def phon(self) -> object | None:
        return _phonology(self.lang) if self.lang == "en" else None

    @property
    def previous(self) -> list[list[str]]:
        return [s.lines for s in self.done]

    @property
    def scene(self) -> str:
        return self.plan.scenes[self.index] if self.index < len(self.plan.scenes) else ""

    @property
    def material(self) -> str:
        return self.plan.materials[self.index] if self.index < len(self.plan.materials) else ""

    def seen(self) -> set[str]:
        return {_norm(x) for st in self.done for x in st.lines}

    def used(self) -> set[str]:
        return {_end_word(x) for st in self.done for x in st.lines}

    def over_budget(self) -> bool:
        return time.monotonic() - self.t0 > TOTAL_BUDGET


def _hard_problem(line: str, ctx: _Ctx, others: list[str]) -> str:
    """Minimal repair: only what no reader would accept (a copied line, unsafe text, a broken end)."""
    if (
        _norm(line) in ctx.seen() | {_norm(x) for x in others}
        or check_output([line], ctx.request)
        or _dangling(line, ctx.lang)
    ):
        return "other"
    return "tacked" if gates.tacked_on(line) else ""


def _surface_problem(line: str, ctx: _Ctx, li: int, others: list[str]) -> str:
    """The first surface defect of ``line`` ("" if none): clashes, repeats, endings, openings."""
    lang = ctx.lang
    if ctx.minimal:
        return _hard_problem(line, ctx, others)
    if (
        _clashes(line, others, lang)
        or _norm(line) in ctx.seen() | {_norm(x) for x in others}
        or check_output([line], ctx.request)
        or _dangling(line, lang)
        or _gibberish(line, ctx.request)
        or _end_word(line) in ctx.used()  # no end word twice in a poem
    ):
        return "other"
    if gates.tacked_on(line):
        return "tacked"
    if li == 0 and ctx.index > 0 and quality.death_opening(line, lang):
        return "opening"
    earlier = tuple(x for st in ctx.done for x in st.lines) + tuple(others)
    if gates.repeated_words(line, earlier, lang, _may_repeat(ctx.request)):
        return "repeated_word"  # POETICS #3: no repeated words in a poem
    return ""


def _check(
    line: str,
    ctx: _Ctx,
    li: int,
    others: list[str],
    partner: str | None,
    loose: bool,
    tolerance: int | None = None,
) -> tuple[int | None, str]:
    """(syllable count, "") if the line can stay, else (None, the problem for the repair prompt)."""
    lang = ctx.lang
    problem = _surface_problem(line, ctx, li, others)
    if problem:
        return None, problem
    if partner is not None and not _rhymes(partner, line, lang, loose):
        return None, "rhyme"
    scanned = scan(line, lang)
    if tolerance is None:
        tolerance = (RELAXED_TOLERANCE if ctx.minimal and not ctx.exact else METRE_TOLERANCE)[lang]
    if gates.metre(scanned, TARGET, tolerance):
        return None, "metre"
    lp = ctx.logprob(others, line)
    floor = SENSE_FLOOR.get(lang)
    if lp is not None and floor is not None and lp < floor:
        return None, "stiff"  # POETICS #4: broken Spanish (far below real verse lines)
    return scanned.metrical_syllable_count, ""


def _candidates(texts: list[str], ctx: _Ctx, others: list[str]) -> list[str]:
    """Distinct parsed lines (names restored), with their sense scored in parallel once."""
    lines = [_parse_line(raw) for text in texts for raw in text.splitlines()]
    lines = [_restore([x], ctx.request.name)[0] for x in dict.fromkeys(lines) if x is not None]
    if ctx.provider.sense and lines:
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=min(8, len(lines))) as pool:
            list(pool.map(lambda x: ctx.logprob(others, x), lines))
    return lines


def _with_sense(out: list[tuple[float, str, int]], ctx: _Ctx, others: list[str]) -> list:
    """Add each candidate's log-probability relative to the slot's median (shared style/context)."""
    lps = {line: ctx.logprob(others, line) for _, line, _ in out}
    known = sorted(v for v in lps.values() if v is not None)
    if not known:
        return out
    mid = known[len(known) // 2]
    return [
        (sc + SENSE_WEIGHT * ((lps[ln] if lps[ln] is not None else mid) - mid), ln, c)
        for sc, ln, c in out
    ]


def _rank(
    texts: list[str], ctx: _Ctx, li: int, others: list[str], partner: str | None, loose: bool
) -> list[tuple[float, str, int]]:
    """Candidate lines that pass every check, best first (quality.score_line plus sense)."""
    from .rhymebank import common

    recent = quality.RECENT.counts()
    prior = [x for st in ctx.done for x in st.lines] + others
    lines = _candidates(texts, ctx, others)
    checked = [(x, _check(x, ctx, li, others, partner, loose)[0]) for x in lines]
    if not any(c is not None for _, c in checked):  # nothing exact: keep the near ones
        relaxed = RELAXED_TOLERANCE[ctx.lang]
        checked = [(x, _check(x, ctx, li, others, partner, loose, relaxed)[0]) for x in lines]
    out = []
    for line, count in checked:
        if count is None:
            continue
        end = _end_word(line)
        score = quality.score_line(
            line,
            ctx.lang,
            syllables=count,
            target=TARGET,
            end_word=end,
            common_ends=common(end, ctx.lang, ctx.phon) if partner else set(),
            scene=ctx.scene,
            material=ctx.material,
            prior=prior,
            opening=li == 0 and ctx.index > 0,
            recent=recent,
        )
        if ctx.minimal:  # repeats are not rejected here, only ranked down
            score -= len(_repeats(line, ctx, others)) + (end in ctx.used())
        out.append((score, line, count))
    return sorted(_with_sense(out, ctx, others), key=lambda t: -t[0])


def _numbers(text: str, n: int) -> list[int] | None:
    """1-based numbers in an editor's answer, as 0-based indexes; [] for "0"; None if unreadable."""
    nums = [int(x) for x in re.findall(r"\d+", text or "")]
    if not nums:
        return None
    if nums == [0]:
        return []
    return [k - 1 for k in dict.fromkeys(nums) if 1 <= k <= n]


def _choose(
    ctx: _Ctx,
    current: list[str],
    ranked: list[tuple[float, str, int]],
    original: str | None = None,
    must: bool = False,
) -> tuple[str, int] | None:
    """The fluency gate on candidate lines: the editor keeps the natural ones, best first.
    An unreadable answer or a failed call keeps the ranking's choice (fail open, as in PoesIA);
    with ``must`` (the last try of the fallback) a "none" answer also keeps it."""
    from .prompt import choose_messages

    top = ranked[:SHOWN]
    if not top:
        return None
    try:
        answer = ctx.provider.chat(
            choose_messages(ctx.request, current, [t[1] for t in top], original), temperature=0.1
        )
        picked = _numbers(answer, len(top))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        picked = None
    if picked is None:
        return top[0][1], top[0][2]
    if not picked:
        return (top[0][1], top[0][2]) if must else None
    return top[picked[0]][1], top[picked[0]][2]


def _rewrite(
    ctx: _Ctx,
    li: int,
    others: list[str],
    current: list[str],
    line: str | None,
    problem: str,
    partner: str | None,
    loose: bool,
    must: bool = False,
) -> tuple[str, int] | None:
    """Ask LINE_CANDIDATES calls for line ``li`` (a repair of ``line``, or a fresh line if None)."""
    from .prompt import line_messages, repair_messages
    from .rhymebank import partners

    rhyme_with = _end_word(partner) if partner else None
    pool = (
        partners(
            rhyme_with, ctx.lang, ctx.escolar, ctx.used(), k=24, phonology=ctx.phon, rng=ctx.rng
        )
        if rhyme_with
        else []
    )
    count = syllables(line, ctx.lang) if line and problem == "metre" else None
    batches = []
    for _ in range(LINE_CANDIDATES_DRAFTER if _drafter(ctx) else LINE_CANDIDATES):
        bank = ctx.rng.sample(pool, min(BANK, len(pool)))
        kw = {"plan": ctx.plan, "send_name": ctx.provider.sends_names, "rng": ctx.rng}
        if line is None:
            msgs = line_messages(
                ctx.request, ctx.index, li, current, ctx.previous, rhyme_with, bank, **kw
            )
        else:
            msgs = repair_messages(
                ctx.request,
                ctx.index,
                current,
                ctx.previous,
                line,
                problem,
                rhyme_with,
                bank,
                count=count,
                **kw,
            )
        batches.append(msgs)
    texts = _write_many(ctx, batches, REPAIR_TEMPERATURE)
    return _choose(ctx, current, _rank(texts, ctx, li, others, partner, loose), line, must)


def _pairs(draft: list[str], lang: str) -> dict[int, tuple[int, bool, bool]]:
    """Rhyme partner of each line: index -> (partner index, loose, required).

    Lines 2 and 4 must rhyme (loose: assonance counts). A draft whose lines 1 and 3 already rhyme
    keeps that rhyme if a repair can (not required). A draft in ABBA keeps ABBA (required)."""
    if _rhymes(draft[0], draft[3], lang, False) and _rhymes(draft[1], draft[2], lang, False):
        return {2: (1, False, True), 3: (0, False, True)}
    pairs = {3: (1, True, True)}
    if _rhymes(draft[0], draft[2], lang, False):
        pairs[2] = (0, False, False)
    return pairs


def _fix_line(
    ctx: _Ctx, lines: list[str], li: int, line: str, pairs: dict[int, tuple[int, bool, bool]]
) -> tuple[str, int] | None:
    pair = pairs.get(li)
    partner = lines[pair[0]] if pair else None
    loose = pair[1] if pair else False
    count, problem = _check(line, ctx, li, lines, partner, loose)
    if count is not None:
        return line, count
    got = _rewrite(ctx, li, lines, lines, line, problem, partner, loose)
    if got is None and pair and not pair[2]:  # a rhyme kept from the draft, not required
        pairs.pop(li)
        got = _rewrite(ctx, li, lines, lines, line, problem, None, False)
    if got is None and problem == "metre":  # no exact repair: the draft line may still be near
        near, _ = _check(line, ctx, li, lines, partner, loose, RELAXED_TOLERANCE[ctx.lang])
        if near is not None:
            return line, near
    return got


def _polish_stiff(
    ctx: _Ctx, lines: list[str], counts: list[int], pairs: dict[int, tuple[int, bool, bool]]
) -> tuple[list[str], list[int]] | None:
    """PoesIA's stiffness gate on the whole stanza: rewrite the lines the editor finds forced,
    keeping every rhyme already in place; drop the stanza if a forced line cannot be fixed."""
    from .prompt import fluency_messages

    try:
        answer = ctx.provider.chat(fluency_messages(ctx.request, lines), temperature=0.1)
        stiff = _numbers(answer, 4)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        stiff = None
    if not stiff:
        return lines, counts
    links = {li: (p, loose) for li, (p, loose, _) in pairs.items()}
    links |= {p: (li, loose) for li, (p, loose, _) in pairs.items()}
    lines, counts = list(lines), list(counts)
    for li in stiff:
        others = lines[:li] + lines[li + 1 :]
        link = links.get(li)
        partner = lines[link[0]] if link else None
        got = _rewrite(
            ctx, li, others, lines, lines[li], "stiff", partner, link[1] if link else False
        )
        if got is None:
            return None
        lines[li], counts[li] = got
    return lines, counts


def _repair_draft(ctx: _Ctx, draft: list[str]) -> Stanza | None:
    pairs = _pairs(draft, ctx.lang)
    lines: list[str] = []
    counts: list[int] = []
    for li, line in enumerate(draft):
        got = _fix_line(ctx, lines, li, line, pairs)
        if got is None:
            return None
        lines.append(got[0])
        counts.append(got[1])
    polished = _polish_stiff(ctx, lines, counts, pairs)
    if polished is None:
        return None
    lines, counts = polished
    sch = scheme(lines, ctx.lang)
    return Stanza(lines, counts, sch) if sch else None


def _judge(text: str, n: int) -> int | None:
    """The editor's pick as a 0-based index; -1 for "none is good"; None if unreadable."""
    nums = _numbers(text, n)
    if nums is None:
        return None
    return nums[0] if nums else -1


def _form_score(st: Stanza) -> float:
    return -sum(abs(c - TARGET) for c in st.counts) + (0.5 if st.scheme in ("ABAB", "ABBA") else 0)


def _pick_stanza(ctx: _Ctx, cands: list[Stanza]) -> Stanza | None:
    """The editor's choice among candidate stanzas, or None if it rejects them all; if the call
    fails or the answer is unreadable, the best form wins."""
    from .prompt import judge_messages

    try:
        msgs = judge_messages(
            ctx.request, ctx.index, ctx.previous, [c.lines for c in cands], ctx.plan
        )
        k = _judge(ctx.provider.chat(msgs, temperature=0.2), len(cands))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        k = None
    if k is None:
        return max(cands, key=_form_score)
    return cands[k] if k >= 0 else None


def _distinct(draft: list[str], ctx: _Ctx) -> bool:
    """Four different lines, none repeated from an earlier stanza, and no copy of a whole stanza."""
    norms = [_norm(x) for x in draft]
    return len(set(norms)) == 4 and not set(norms) & ctx.seen()


def _draft_stanza(ctx: _Ctx, rejected: list[Stanza]) -> Stanza | None:
    """The editor's pick of repaired drafts; candidates it rejects are kept in ``rejected``."""
    from concurrent.futures import ThreadPoolExecutor

    from .prompt import messages

    msgs = messages(
        ctx.request,
        ctx.index,
        ctx.previous,
        ctx.plan,
        send_name=ctx.provider.sends_names,
        rng=ctx.rng,
    )
    for _ in range(DRAFT_ROUNDS):
        if ctx.over_budget():
            return None
        drafts = []
        for text in _ask_many(ctx.provider, [msgs] * DRAFTS, DRAFT_TEMPERATURE):
            draft = parse_quatrain(text)
            if draft is None:
                continue
            if not ctx.provider.sends_names:
                draft = _restore(draft, ctx.request.name)
            if _distinct(draft, ctx) and not check_output(draft, ctx.request):
                drafts.append(draft)
        drafts = drafts[:REPAIR_DRAFTS]
        if not drafts:
            continue
        subs = [
            _Ctx(
                ctx.provider,
                ctx.request,
                ctx.index,
                ctx.done,
                ctx.plan,
                random.Random(ctx.rng.randrange(2**31)),
                ctx.t0,
            )  # noqa: S311
            for _ in drafts
        ]
        with ThreadPoolExecutor(max_workers=len(drafts)) as pool:
            futures = [pool.submit(_repair_draft, c, d) for c, d in zip(subs, drafts, strict=True)]
        cands = [st for f in futures if (st := f.result()) is not None]
        if not cands:
            continue
        best = _pick_stanza(ctx, cands)
        if best is not None:
            return best
        rejected.extend(cands)
    return None


def _write_stanza(ctx: _Ctx) -> Stanza:
    """Fallback when no draft survives: write the stanza line by line (lines 2 and 4 rhyme)."""
    lines: list[str] = []
    counts: list[int] = []
    for li in range(4):
        partner = lines[1] if li == 3 else None
        got = None
        for attempt in range(FALLBACK_TRIES):
            if ctx.over_budget():
                raise GenerationError("quality")
            last = attempt == FALLBACK_TRIES - 1
            got = _rewrite(ctx, li, lines, lines, None, "other", partner, True, must=last)
            if got is not None:
                break
        if got is None:
            raise GenerationError("quality")
        lines.append(got[0])
        counts.append(got[1])
    return Stanza(lines, counts, scheme(lines, ctx.lang) or "abcb")


def _repeats(line: str, ctx: _Ctx, others: list[str]) -> tuple[str, ...]:
    earlier = tuple(x for st in ctx.done for x in st.lines) + tuple(others)
    return gates.repeated_words(line, earlier, ctx.lang, _may_repeat(ctx.request))


def _mend_stanza(ctx: _Ctx, draft: list[str]) -> Stanza | None:
    """Keep the draft's lines; repair only real defects (POETICS #4 before #1: the meaning of a
    draft line is worth more than an exact count). A line goes to repair if its metre is off by more
    than RELAXED_TOLERANCE, its required rhyme is missing, it copies a line, it is unsafe, or it ends
    broken. A repeated word or a reused end word (POETICS #3) is tried once and the line stays if no
    repair passes. None if a defect cannot be repaired.

    Measured 2026-10-15 (12 + 12 requests): the full gates rewrote most lines one by one (Spanish:
    254 replaced, 86 kept; 1-3 of 12 final lines were the model's own) and the joke was lost."""
    pairs = _pairs(draft, ctx.lang)
    lines: list[str] = []
    counts: list[int] = []
    for li, line in enumerate(draft):
        others = lines + draft[li + 1 :]
        pair = pairs.get(li)
        partner = lines[pair[0]] if pair else None
        loose = pair[1] if pair else False
        current = lines + draft[li:]
        count, problem = _check(line, ctx, li, others, partner, loose)
        if count is None:
            got = _rewrite(ctx, li, others, current, line, problem, partner, loose)
            if got is None and pair and not pair[2]:  # a rhyme kept from the draft, not required
                pairs.pop(li)
                got = _rewrite(ctx, li, others, current, line, problem, None, False)
            if got is None:
                return None
            line, count = got
        if _repeats(line, ctx, others) or _end_word(line) in ctx.used():
            got = _rewrite(ctx, li, others, current, line, "repeated_word", partner, loose)
            if got is not None and not _repeats(got[0], ctx, others):
                line, count = got
        lines.append(line)
        counts.append(count)
    if ctx.lang == "es":
        lines, counts = _tighten(ctx, lines, counts)
    sch = scheme(lines, ctx.lang)
    return Stanza(lines, counts, sch) if sch else None


def _tighten(ctx: _Ctx, lines: list[str], counts: list[int]) -> tuple[list[str], list[int]]:
    """One try to bring each line one syllable off to exactly TARGET, keeping its end word (so the
    rhyme and the sense stay); the line is kept as it is if no candidate lands. Lines run in parallel."""
    from concurrent.futures import ThreadPoolExecutor

    near = [i for i, c in enumerate(counts) if c != TARGET]
    if not near or ctx.over_budget():
        return lines, counts
    tight = _Ctx(
        ctx.provider, ctx.request, ctx.index, ctx.done, ctx.plan, ctx.rng, ctx.t0,
        minimal=True, exact=True,
    )  # fmt: skip

    def one(i: int) -> tuple[str, int] | None:
        others = lines[:i] + lines[i + 1 :]
        got = _rewrite(tight, i, others, lines, lines[i], "metre", None, False)
        if got and got[1] == TARGET and _end_word(got[0]) == _end_word(lines[i]):
            return got
        return None

    with ThreadPoolExecutor(max_workers=len(near)) as pool:
        results = list(pool.map(one, near))
    lines, counts = list(lines), list(counts)
    for i, got in zip(near, results, strict=True):
        if got:
            lines[i], counts[i] = got
    return lines, counts


def _order(answer: str, n: int) -> list[int]:
    """The editor's ranking as indexes ([] = none is good); unreadable = the given order."""
    nums = _numbers(answer, n)
    if nums is None:
        return list(range(n))
    return nums + [k for k in range(n) if nums and k not in nums]


def _ranked(ctx_provider: Provider, msgs: list[dict[str, str]], n: int) -> list[int]:
    if n == 1:
        return [0]
    try:
        return _order(ctx_provider.chat(msgs, temperature=0.2), n)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return list(range(n))


def _sub(ctx: _Ctx, index: int | None = None, done: list[Stanza] | None = None) -> _Ctx:
    return _Ctx(
        ctx.provider,
        ctx.request,
        ctx.index if index is None else index,
        ctx.done if done is None else done,
        ctx.plan,
        random.Random(ctx.rng.randrange(2**31)),  # noqa: S311
        ctx.t0,
        minimal=True,
    )


def _off(ctx: _Ctx, draft: list[str]) -> float:
    """How far a draft is from the form: syllables beyond the slack, plus 3 if lines 2 and 4 do not
    rhyme (a missing rhyme costs a repair that rarely keeps the sense)."""
    slack = RELAXED_TOLERANCE[ctx.lang]
    off = sum(max(0, abs(syllables(x, ctx.lang) - TARGET) - slack) for x in draft)
    reps = sum(len(_repeats(x, ctx, draft[:i])) for i, x in enumerate(draft))
    return off + reps + (0 if _rhymes(draft[1], draft[3], ctx.lang, True) else 3)


def _condensed(ctx: _Ctx, drafts: list[list[str]]) -> list[list[str]]:
    """One whole-stanza shortening of each draft whose lines run long (see prompt.condense_messages)."""
    from .prompt import condense_messages

    slack = RELAXED_TOLERANCE[ctx.lang]
    long = [d for d in drafts if any(syllables(x, ctx.lang) > TARGET + slack for x in d)]
    if not long or ctx.over_budget():
        return []
    batches = [condense_messages(ctx.request, d, [syllables(x, ctx.lang) for x in d]) for d in long]
    out = []
    try:
        texts = _write_many(ctx, batches, 0.5)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return []
    for text in texts:
        d = parse_quatrain(text)
        if d is not None:
            d = _restore(d, ctx.request.name)
        if d is not None and _distinct(d, ctx) and not check_output(d, ctx.request):
            out.append(d)
    return out


def _closest(ctx: _Ctx, drafts: list[list[str]]) -> list[list[str]]:
    return sorted(drafts, key=lambda d: _off(ctx, d))


def _story_stanza(ctx: _Ctx) -> Stanza | None:
    """Stanza drafts that follow the story's beat; the editor ranks them as drafts (story and
    sense), then the best ones are mended (minimal repair), two at a time; the first in the
    editor's order that survives is kept."""
    from concurrent.futures import ThreadPoolExecutor

    from .prompt import judge_messages, messages

    msgs = messages(
        ctx.request,
        ctx.index,
        ctx.previous,
        ctx.plan,
        send_name=ctx.provider.sends_names,
        rng=ctx.rng,
    )
    for _ in range(DRAFT_ROUNDS):
        if ctx.over_budget():
            return None
        drafts = []
        for text in _write_many(ctx, [msgs] * DRAFTS, DRAFT_TEMPERATURE):
            draft = parse_quatrain(text)
            if draft is None:
                continue
            draft = _restore(draft, ctx.request.name)
            if _distinct(draft, ctx) and not check_output(draft, ctx.request):
                drafts.append(draft)
        if not drafts:
            continue
        drafts = _closest(ctx, drafts + _condensed(ctx, drafts))[:JUDGED]
        order = _ranked(
            ctx.provider,
            judge_messages(ctx.request, ctx.index, ctx.previous, drafts, ctx.plan),
            len(drafts),
        )[:REPAIR_DRAFTS]
        for i in range(0, len(order), 2):
            if ctx.over_budget():
                return None
            batch = order[i : i + 2]
            with ThreadPoolExecutor(max_workers=len(batch)) as pool:
                got = list(
                    pool.map(lambda d: _mend_stanza(_sub(ctx), d), [drafts[k] for k in batch])
                )
            for st in got:
                if st is not None:
                    return st
    return None


def parse_poem(text: str, n: int) -> list[list[str]] | None:
    """``n`` quatrains from a whole-poem answer (blank lines between stanzas, or 4n lines), or None."""
    blocks: list[list[str]] = []
    cur: list[str] = []
    for raw in (text or "").splitlines():
        line = _NUMBERING.sub("", raw.strip().strip("*#").strip()).strip().strip("\"“”«»'").strip()
        if not line:
            if cur:
                blocks.append(cur)
                cur = []
            continue
        if line.lower().startswith(("estrofa", "stanza", "calaverita", "aquí tienes", "here is")):
            continue
        cur.append(line)
    if cur:
        blocks.append(cur)
    if len(blocks) == n and all(len(b) == 4 for b in blocks):
        return blocks
    flat = [x for b in blocks for x in b]
    if len(flat) == 4 * n and len(blocks) <= 1:
        return [flat[i : i + 4] for i in range(0, 4 * n, 4)]
    return None


def _poem_repeats(ctx: _Ctx, poem: list[list[str]]) -> int:
    flat = [x for st in poem for x in st]
    allowed = _may_repeat(ctx.request)
    return sum(
        len(gates.repeated_words(x, tuple(flat[:i]), ctx.lang, allowed)) for i, x in enumerate(flat)
    )


def _mend_poem(ctx: _Ctx, poem: list[list[str]]) -> list[Stanza] | None:
    done: list[Stanza] = []
    for i, draft in enumerate(poem):
        if ctx.over_budget():
            return None
        st = _mend_stanza(_sub(ctx, index=i, done=done), draft)
        if st is None:
            return None
        done.append(st)
    return done


def _story_poem(ctx: _Ctx) -> list[Stanza] | None:
    """The whole calaverita in one answer, POEM_DRAFTS times; the editor ranks the drafts (one story,
    the habit as an image, a punchline on it, sense in every line), then the best are mended.
    Used for English: Apertus 70B keeps the story and about eight syllables over a whole English
    poem, but not Spanish octosyllables (10-17 syllables a line, 2026-10-15)."""
    from .prompt import poem_judge_messages, poem_messages

    n = ctx.request.stanzas
    msgs = poem_messages(ctx.request, ctx.plan, send_name=ctx.provider.sends_names, rng=ctx.rng)
    for _ in range(DRAFT_ROUNDS):
        if ctx.over_budget():
            return None
        poems = []
        k = POEM_DRAFTS_DRAFTER if _drafter(ctx) else POEM_DRAFTS
        for text in _write_many(ctx, [msgs] * k, DRAFT_TEMPERATURE):
            poem = parse_poem(text, n)
            if poem is None:
                continue
            poem = [_restore(st, ctx.request.name) for st in poem]
            flat = [x for st in poem for x in st]
            if len({_norm(x) for x in flat}) == len(flat) and not check_output(flat, ctx.request):
                poems.append(poem)
        if not poems:
            continue
        order = _ranked(ctx.provider, poem_judge_messages(ctx.request, ctx.plan, poems), len(poems))
        order = sorted(order[:3], key=lambda k: min(2, _poem_repeats(ctx, poems[k]))) + order[3:]
        for k in order[:2]:
            got = _mend_poem(ctx, poems[k])
            if got is not None:
                return got
    return None


def _plan(provider: Provider, request: Request) -> planmod.Plan:
    from .prompt import plan_messages

    text = provider.chat(
        plan_messages(request, send_name=provider.sends_names), temperature=0.8, max_tokens=500
    )
    return planmod.parse(text, request)


def _write_with(
    provider: Provider, request: Request, rng: random.Random, t0: float
) -> list[Stanza]:
    """Story first (one plan call), then the verse: whole-poem drafts for English, stanza drafts on
    the story's beats for Spanish, each with minimal repair. The earlier engine (full gates, line by
    line) is kept only as the fallback for a stanza the story path cannot deliver."""
    plan = _plan(provider, request)
    whole = request.language == "en" or (
        provider.drafter is not None and request.language in provider.draft_langs
    )
    if whole:
        poem = _story_poem(_Ctx(provider, request, 0, [], plan, rng, t0, minimal=True))
        if poem is not None:
            poem = [Stanza(_polish(st.lines), st.counts, st.scheme) for st in poem]
            quality.RECENT.add([_end_word(x) for st in poem for x in st.lines])
            return poem
    done: list[Stanza] = []
    for index in range(request.stanzas):
        stanza = _story_stanza(_Ctx(provider, request, index, done, plan, rng, t0, minimal=True))
        if stanza is not None:
            done.append(Stanza(_polish(stanza.lines), stanza.counts, stanza.scheme))
            continue
        ctx = _Ctx(provider, request, index, done, plan, rng, t0)
        rejected: list[Stanza] = []
        stanza = _draft_stanza(ctx, rejected)
        if stanza is None:
            try:
                stanza = _write_stanza(ctx)
            except GenerationError:
                # a stanza the editor turned down is still better than no calaverita at all
                if not rejected:
                    raise
                stanza = max(rejected, key=_form_score)
        done.append(Stanza(_polish(stanza.lines), stanza.counts, stanza.scheme))
    quality.RECENT.add([_end_word(x) for st in done for x in st.lines])
    return done
