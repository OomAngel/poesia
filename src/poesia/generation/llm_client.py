"""Abstract LLM client interface.

Concrete backends (hosted API, llama.cpp local inference, transformers local
inference) implement this Protocol so the generation loop stays decoupled
from any single provider. This mirrors the "typed port" discipline used
elsewhere: no SDK-specific import should leak into evaluation/ or phonology/.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from poesia.exceptions import LLMProviderError

# Canonical Groq generation model — the single source of truth for which Groq
# model poesia uses (referenced by both the router and the hosted client).
GROQ_MODEL = "qwen/qwen3.8-27b"


def _trace_decorator(span_type: str, name: str) -> Callable[[Any], Any]:
    """Return ``mlflow.trace(...)`` when mlflow is installed, else a no-op.

    mlflow is an optional, heavy dependency (AGENTS.md lazy-import rule) — the
    CLI must work without it. LoRALocalClient's ``generate`` tracing degrades
    to an identity decorator when mlflow is absent. Tracing is also skipped
    when ``MLFLOW_TRACING_DISABLED`` is set (the official switch), so tests
    and non-tracing deployments avoid span overhead and exporter noise.
    """
    if os.environ.get("MLFLOW_TRACING_DISABLED", "").lower() in ("1", "true"):
        return lambda fn: fn
    try:
        import mlflow

        return mlflow.trace(span_type=span_type, name=name)
    except ImportError:  # pragma: no cover - environment dependent
        return lambda fn: fn


@dataclass
class LLMUsage:
    """Token and timing metadata from an LLM generation call.

    Populated on :class:`HostedLLMClient` after each ``generate()`` call.
    """

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    latency_ms: float | None = None  # Wall-clock time for the call


class LLMClient(Protocol):
    """Minimal interface the generation loop needs from any LLM backend."""

    @_trace_decorator(span_type="LLM", name="hosted_generate")
    def generate(self, prompt: str, n: int = 1, temperature: float = 0.9) -> list[str]:
        """Return `n` candidate completions for `prompt`."""
        ...

    def repair(self, line: str, defect_description: str) -> str:
        """Ask the model to fix one explicit, named defect in a single line."""
        ...


class StubLLMClient:
    """Deterministic stub client for tests and offline development.

    Generates short plausible lines based on theme keywords instead of
    echoing the full prompt. Useful for exercising the generation loop's
    control flow without network access or API cost.
    """

    # Spanish line templates by syllable count
    _SPANISH_TEMPLATES_5 = [
        "{word} en la noche",
        "brilla la {word}",
        "{word} de plata",
        "bajo la {word}",
        "canta la {word}",
    ]

    _SPANISH_TEMPLATES_7 = [
        "{word} sobre el mar azul",
        "la {word} brilla en silencio",
        "{word} de cristal y luz",
        "susurra la {word} eterna",
        "baila la {word} callada",
    ]

    _SPANISH_TEMPLATES_11 = [
        "en el jardín florece la {word} de primavera",
        "bajo la {word} brillante caminan las sombras",
        "la {word} susurra secretos al viento callado",
        "entre las {word}s perdidas navega el recuerdo",
        "cuando la {word} desciende se enciende la aurora",
    ]

    # English line templates by syllable count
    _ENGLISH_TEMPLATES_5 = [
        "{word} in the night",
        "bright shining {word}",
        "{word} of silver",
        "beneath the {word}",
        "singing {word}",
    ]

    _ENGLISH_TEMPLATES_7 = [
        "{word} across the dark blue sea",
        "the {word} shines in silence",
        "{word} of crystal and light",
        "whispers the eternal {word}",
        "dancing {word} so quietly",
    ]

    _ENGLISH_TEMPLATES_10 = [
        "beneath the glowing {word} the shadows fall",
        "when {word} descends the morning star appears",
        "the {word} whispers secrets to the silent wind",
        "among the lost {word}s memory sails away",
        "in gardens where the {word} blooms in spring",
    ]

    # Single-syllable, sinalefa-safe padding words used to nudge a line onto
    # its exact target syllable count (see _fit_syllables). The templates
    # above are hand-authored assuming a ~2-syllable {word}; a 1- or
    # 3+-syllable theme word (or a hosted-LLM repair) throws that off, so
    # every line is snapped to the real scanner's count rather than trusted
    # as-is.
    _SPANISH_FILLERS = ["sol", "luz", "paz", "voz", "mar", "flor", "fe", "sal"]
    _ENGLISH_FILLERS = ["light", "night", "song", "dream", "sky", "star", "sea", "rain"]

    # Common function words that only ever appear in this class's own
    # Spanish templates — cheap enough to distinguish repair()'s input line
    # (which carries no language tag of its own) without a real detector.
    _SPANISH_MARKERS = {"la", "el", "en", "de", "que", "con", "del", "las", "los"}

    _phonology_cache: dict[str, Any] = {}

    @_trace_decorator(span_type="LLM", name="hosted_generate")
    def generate(self, prompt: str, n: int = 1, temperature: float = 0.9) -> list[str]:
        """Generate plausible short lines based on prompt keywords."""
        # Extract theme/language from prompt
        theme_word = self._extract_theme(prompt)
        language = self._extract_language(prompt)

        # Pick template based on context (look for syllable hints in prompt)
        templates, target = self._select_templates(prompt, language)

        # Generate n candidates by cycling through templates
        results = []
        for i in range(n):
            template = templates[i % len(templates)]
            line = template.format(word=theme_word)
            results.append(self._fit_syllables(line, target, language))

        return results

    def repair(self, line: str, defect_description: str) -> str:
        """Deterministic repair: trim/pad the line onto the syllable count
        stated in defect_description (see _repair_defect_description),
        rather than a no-op text tweak that can never satisfy the
        constrained loop's hard metre gate.
        """
        match = re.search(r"exactly (\d+)", defect_description)
        if not match:
            return f"{line} clara"
        target = int(match.group(1))
        language = self._guess_language(line)
        return self._fit_syllables(line, target, language)

    def _guess_language(self, line: str) -> str:
        """Best-effort language guess from a line this class itself produced."""
        words = {w.strip(".,;:!?\"'¡¿").lower() for w in line.split()}
        return "es" if words & self._SPANISH_MARKERS else "en"

    def _phonology_for(self, language: str) -> Any:
        """Lazily construct and cache a phonology scanner per language."""
        if language not in self._phonology_cache:
            if language == "es":
                from poesia.phonology.spanish import SpanishPhonology

                self._phonology_cache[language] = SpanishPhonology()
            else:
                from poesia.phonology.english import EnglishPhonology

                self._phonology_cache[language] = EnglishPhonology()
        return self._phonology_cache[language]

    def _fit_syllables(self, line: str, target: int, language: str) -> str:
        """Trim or pad `line` word-by-word until it scans to exactly
        `target` metrical syllables under the real phonology backend.

        The hand-authored templates above are only exactly right for the
        theme word they were eyeballed against — a different theme word
        (or a hosted LLM's own repair attempt) shifts the count. Verifying
        against the same scanner the constrained loop checks against makes
        the stub reliably metre-correct instead of only correct by luck.
        """
        phonology = self._phonology_for(language)
        fillers = self._SPANISH_FILLERS if language == "es" else self._ENGLISH_FILLERS
        words = line.split()

        # Trim from the end while too long.
        while len(words) > 1:
            actual = phonology.scan_line(" ".join(words)).metrical_syllable_count
            if actual <= target:
                break
            words.pop()

        # Pad with single-syllable fillers while too short, preferring
        # whichever filler lands exactly on target this step.
        attempts = 0
        while attempts < 20:
            actual = phonology.scan_line(" ".join(words)).metrical_syllable_count
            if actual >= target:
                break
            exact, under = None, None
            for filler in fillers:
                candidate = [*words, filler]
                candidate_count = phonology.scan_line(" ".join(candidate)).metrical_syllable_count
                if candidate_count == target:
                    exact = candidate
                    break
                if candidate_count < target and under is None:
                    under = candidate
            words = exact or under or [*words, fillers[attempts % len(fillers)]]
            attempts += 1

        return " ".join(words)

    # Human-readable language names CandidateGenerator's non-brief prompt
    # ("You are writing a {lang_name} poem...") and GenerationBrief's
    # constraint line ("You MUST write in {lang_name}.") both use.
    _LANG_NAMES = {"spanish": "es", "english": "en", "dutch": "nl"}

    def _extract_theme(self, prompt: str) -> str:
        """Extract the main theme word from prompt.

        Matches the two prompt shapes CandidateGenerator actually builds —
        the inline "...on the theme: X." sentence (no brief) and
        GenerationBrief's "## THEME\\n- X" block (with a brief) — plus the
        older colon-tagged "Theme:"/"Tema:" convention some direct-prompt
        callers/tests still use. None of these appeared verbatim in either
        real prompt shape before, so this previously always fell through to
        the "luna" fallback for every non-synthetic prompt.
        """
        for pattern in (
            r"on the theme:\s*([^\n.]+)",
            r"##\s*THEME\s*\n-\s*([^\n]+)",
            r"(?:Theme|Tema):\s*([^\n]+)",
        ):
            match = re.search(pattern, prompt, re.IGNORECASE)
            if match:
                word = match.group(1).strip().split()[0]
                return word.strip(".,;:!?\"'¡¿()")
        return "luna"  # fallback

    def _extract_language(self, prompt: str) -> str:
        """Extract language from prompt.

        Checks the older "Language: es"/"Idioma: es" tag first (still used
        by some direct-prompt callers/tests), then the real prompt shapes:
        CandidateGenerator's "writing a Spanish/English poem" sentence and
        GenerationBrief's "Language: {code}" form-metadata line (already
        covered by the first check).
        """
        if "Language: es" in prompt or "Idioma: es" in prompt:
            return "es"
        if "Language: en" in prompt or "Idioma: en" in prompt:
            return "en"
        match = re.search(r"writing an? (\w+) poem", prompt, re.IGNORECASE)
        if match:
            return self._LANG_NAMES.get(match.group(1).lower(), "es")
        return "es"  # fallback

    def _select_templates(self, prompt: str, language: str) -> tuple[list[str], int]:
        """Select templates matching the prompt's real target syllable
        count.

        CandidateGenerator renders any known target verbatim as "Exactly N
        syllables." in every real prompt (see also repair()'s "exactly N"
        parsing above) — that's authoritative regardless of poem form, so
        it's read first. Only prompts with no explicit target (forms that
        don't fix a syllable count) fall back to guessing from haiku's
        well-known 5-7-5 line-position pattern, the sole current caller
        that omits it.
        """
        match = re.search(r"[Ee]xactly (\d+) syllables", prompt)
        if match:
            target = int(match.group(1))
        else:
            poem_so_far = (
                prompt.split("Poem so far:")[-1].strip() if "Poem so far:" in prompt else ""
            )
            existing_lines = [line.strip() for line in poem_so_far.split("\n") if line.strip()]
            line_number = len(existing_lines)
            target = 7 if line_number == 1 else 5

        buckets = {
            "es": {
                5: self._SPANISH_TEMPLATES_5,
                7: self._SPANISH_TEMPLATES_7,
                11: self._SPANISH_TEMPLATES_11,
            },
            "en": {
                5: self._ENGLISH_TEMPLATES_5,
                7: self._ENGLISH_TEMPLATES_7,
                10: self._ENGLISH_TEMPLATES_10,
            },
        }[language if language in ("es", "en") else "en"]
        # The starting template only sets flavor/word choice — _fit_syllables
        # (in generate()) corrects the exact count regardless of which
        # bucket this picks, so the closest available one is good enough.
        closest = min(buckets, key=lambda n: abs(n - target))
        return buckets[closest], target


class HostedLLMClient:
    """Hosted LLM provider via standard HTTP API requests (Gemini or OpenAI format).

    Reads GEMINI_API_KEY, OPENAI_API_KEY, or GROQ_API_KEY from environment.
    Does not require external SDK packages, relying on standard library urllib.

    Supported providers:
      - gemini  : Google Gemini API (GEMINI_API_KEY)
      - openai  : OpenAI Chat Completions API (OPENAI_API_KEY)
      - groq    : Groq Cloud API — OpenAI-compatible (GROQ_API_KEY)
      - auto    : First available key wins (Gemini → Groq → OpenAI)

    Groq note: the Groq API requires n=1 per request. For n>1 candidates
    the client issues n sequential calls automatically.
    """

    # Groq Cloud base URL (OpenAI-compatible)
    _GROQ_BASE_URL = "https://api.groq.com/openai/v1"
    _GROQ_DEFAULT_MODEL = GROQ_MODEL

    def __init__(
        self,
        provider: str = "auto",
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 30.0,
        groq_pace_seconds: float = 2.1,
    ) -> None:
        self.provider = provider
        self.timeout = timeout
        self.usage: LLMUsage = LLMUsage()  # P5: populated after each generate()
        # Rate-limit pacing between sequential Groq calls (30 RPM free tier).
        # Configurable so callers/tests can disable the deliberate sleep.
        self.groq_pace_seconds = groq_pace_seconds

        if api_key is not None:
            # Explicit, even "" — an explicitly-empty key means "no key",
            # not "fall back to whatever's in the environment" (a truthy
            # check here would silently ignore api_key="" and could send a
            # different provider's real key to this one — see docs/... ).
            self.api_key = api_key
        elif os.environ.get("GEMINI_API_KEY"):
            self.api_key = os.environ.get("GEMINI_API_KEY", "")
            if provider == "auto":
                self.provider = "gemini"
        elif os.environ.get("GROQ_API_KEY"):
            self.api_key = os.environ.get("GROQ_API_KEY", "")
            if provider == "auto":
                self.provider = "groq"
        elif os.environ.get("OPENAI_API_KEY"):
            self.api_key = os.environ.get("OPENAI_API_KEY", "")
            if provider == "auto":
                self.provider = "openai"
        else:
            self.api_key = ""

        if model:
            self.model = model
        elif self.provider == "gemini":
            self.model = "gemini-2.5-flash"
        elif self.provider == "groq":
            self.model = self._GROQ_DEFAULT_MODEL
        else:
            self.model = "gpt-4o-mini"

    @_trace_decorator(span_type="LLM", name="hosted_generate")
    def generate(self, prompt: str, n: int = 1, temperature: float = 0.9) -> list[str]:
        from poesia.exceptions import LLMProviderError

        if not self.api_key:
            raise LLMProviderError(
                "HostedLLMClient requires an API key. Set GEMINI_API_KEY, "
                "GROQ_API_KEY, or OPENAI_API_KEY environment variable, or pass "
                "api_key to HostedLLMClient.",
                provider=self.provider,
            )

        self.usage = LLMUsage()  # Reset for this call
        t0 = time.time()

        try:
            if self.provider == "gemini":
                result = self._generate_gemini(prompt, n, temperature)
            elif self.provider == "groq":
                result = self._generate_groq(prompt, n, temperature)
            else:
                result = self._generate_openai_compat(
                    prompt,
                    n,
                    temperature,
                    base_url="https://api.openai.com/v1",
                )
        except LLMProviderError:
            raise  # Already structured
        except Exception as e:
            raise LLMProviderError(
                f"{self.provider} API request failed: {e}",
                provider=self.provider,
            ) from e

        self.usage.latency_ms = (time.time() - t0) * 1000
        return result

    def repair(self, line: str, defect_description: str) -> str:
        prompt = (
            f"Fix the following poetic line to resolve this defect: {defect_description}.\n"
            f'Line: "{line}"\n'
            "Output ONLY the corrected single line without quotation marks, intro, or explanation."
        )
        candidates = self.generate(prompt, n=1, temperature=0.7)
        if candidates:
            return candidates[0].strip().strip("\"'")
        return line

    def _generate_gemini(self, prompt: str, n: int, temperature: float) -> list[str]:
        """Generate using Gemini API with candidateCount for batching.

        Uses a single API call with candidateCount=n to get multiple candidates,
        reducing latency and API calls compared to n sequential requests.
        """
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            f"?key={self.api_key}"
        )

        # Use candidateCount for batched generation (max 8 for most Gemini models)
        # Falls back to sequential calls if n > max_candidates
        max_candidates = 8
        if n <= max_candidates:
            return self._generate_gemini_batched(url, prompt, n, temperature)
        else:
            # For large n, batch in chunks
            candidates: list[str] = []
            remaining = n
            while remaining > 0:
                batch_size = min(remaining, max_candidates)
                candidates.extend(
                    self._generate_gemini_batched(url, prompt, batch_size, temperature)
                )
                remaining -= batch_size
            return candidates

    def _generate_gemini_batched(
        self, url: str, prompt: str, n: int, temperature: float
    ) -> list[str]:
        """Make a single Gemini API call with candidateCount=n."""
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "candidateCount": n,
            },
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                # Extract all candidates from the response
                candidates: list[str] = []
                for cand in res.get("candidates", []):
                    content = cand.get("content", {})
                    parts = content.get("parts", [])
                    text = parts[0].get("text", "") if parts else ""
                    candidates.append(text.strip())

                # If we got fewer candidates than requested, pad with empty strings
                while len(candidates) < n:
                    candidates.append("")

                return candidates
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8")
            from poesia.exceptions import LLMProviderError

            raise LLMProviderError(
                f"Gemini API HTTP Error {e.code}: {err_msg}",
                provider="gemini",
                status_code=e.code,
                response_body=err_msg,
            ) from e
        except Exception as e:
            from poesia.exceptions import LLMProviderError

            raise LLMProviderError(
                f"Gemini API request failed: {e}",
                provider="gemini",
            ) from e

    def _generate_groq(self, prompt: str, n: int, temperature: float) -> list[str]:
        """Groq Cloud chat completions.

        Groq's API does not support n>1 per request. We issue n sequential
        calls. The free tier allows 30 RPM and 12 000 TPM. We pace at 2.1 s
        between calls (RPM budget) and honour the exact retry-after value from
        any 429 response (TPM budget) — waiting up to 65 s to let the window
        reset before retrying.
        """
        import time

        results = []
        for i in range(n):
            if i > 0 and self.groq_pace_seconds > 0:
                time.sleep(self.groq_pace_seconds)  # 30 RPM = 1 req/2 s; 2.1 s adds margin
            batch = self._generate_openai_compat(
                prompt, 1, temperature, base_url=self._GROQ_BASE_URL
            )
            results.extend(batch)
        return results

    def _generate_openai_compat(
        self, prompt: str, n: int, temperature: float, base_url: str
    ) -> list[str]:
        """OpenAI-compatible chat completions (used by OpenAI and Groq)."""
        url = f"{base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "n": n,
            "temperature": temperature,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "poesia/1.0",
            },
        )
        provider_label = "Groq" if "groq.com" in base_url else "OpenAI"
        import re
        import time as _time

        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    res = json.loads(resp.read().decode("utf-8"))
                    # P5: capture token usage from response
                    usage_data = res.get("usage", {})
                    if usage_data:
                        self.usage.prompt_tokens = usage_data.get("prompt_tokens")
                        self.usage.completion_tokens = usage_data.get("completion_tokens")
                        self.usage.total_tokens = usage_data.get("total_tokens")
                    return [c["message"]["content"].strip() for c in res.get("choices", [])]
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8")
                if e.code == 429 and attempt < 3:
                    sec_match = re.search(r"try again in ([\d.]+)s", err_body)
                    min_match = re.search(r"try again in (\d+)m([\d.]+)s", err_body)
                    if min_match:
                        wait = int(min_match.group(1)) * 60 + float(min_match.group(2)) + 1.0
                    elif sec_match:
                        raw = float(sec_match.group(1))
                        wait = raw + 1.0 if (raw > 5 or attempt == 0) else 62.0
                    else:
                        wait = 65.0
                    _time.sleep(wait)
                    continue
                raise LLMProviderError(
                    f"{provider_label} API HTTP Error {e.code}: {err_body}",
                    provider=provider_label.lower(),
                    status_code=e.code,
                    response_body=err_body,
                ) from e
            except Exception as e:
                raise LLMProviderError(
                    f"{provider_label} API request failed: {e}",
                    provider=provider_label.lower(),
                ) from e

        # Defensive: every attempt either returned or raised above (the final
        # retry re-raises rather than looping), so this is unreachable in
        # practice — but mypy needs an explicit exit for loop exhaustiveness.
        raise LLMProviderError(
            f"{provider_label} API request failed after 4 attempts",
            provider=provider_label.lower(),
        )


class OllamaClient:
    """Local LLM via Ollama (https://ollama.com).

    Calls the Ollama REST API at ``http://localhost:11434/api/chat`` (default)
    or ``OLLAMA_HOST`` env var. Uses ``OLLAMA_MODEL`` env var or a default model.

    Requires Ollama to be installed and running. No API key needed.
    Designed for offline/private generation on local hardware.

    Default model: ``gemma2:2b`` (~1.5 GB download, ~3 GB RAM during inference).
    This is the smallest viable model for poetry generation.

    Supported models (from smallest to most capable):
    - gemma2:2b (1.5 GB, 3 GB RAM) — runs on any laptop with 4 GB RAM
    - llama3.2:3b (2.0 GB, 4 GB RAM) — good balance of size and quality
    - phi3:mini (2.3 GB, 4.5 GB RAM) — strong for structured output
    - qwen2.5:7b (4.1 GB, 8 GB RAM) — best multilingual (ES+EN)
    - llama3.1:8b (4.7 GB, 8 GB RAM) — best quality offline
    """

    _DEFAULT_HOST = "http://localhost:11434"
    _DEFAULT_MODEL = "gemma2:2b"

    def __init__(
        self,
        model: str | None = None,
        host: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.host = (host or os.environ.get("OLLAMA_HOST") or self._DEFAULT_HOST).rstrip("/")
        self.model = model or os.environ.get("OLLAMA_MODEL") or self._DEFAULT_MODEL
        self.timeout = timeout
        self.usage: LLMUsage = LLMUsage()
        self.provider = "ollama"
        self._checked = False  # Lazy connectivity check

    def _check_available(self) -> None:
        """Verify Ollama is running and the model is available."""
        if self._checked:
            return

        health_url = f"{self.host}/api/tags"
        try:
            with urllib.request.urlopen(health_url, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = [m["name"] for m in data.get("models", [])]
                # Check if model is pulled (accept partial match)
                available = any(self.model in m for m in models)
                if not available:
                    # Model not pulled yet — try to pull it
                    # (This can take minutes; warn the user)
                    import warnings

                    warnings.warn(
                        f"Model '{self.model}' not found in Ollama. Run: ollama pull {self.model}",
                        stacklevel=2,
                    )
        except urllib.error.HTTPError:
            raise LLMProviderError(
                f"Ollama is not running at {self.host}. "
                "Start Ollama first (system tray or 'ollama serve').",
                provider="ollama",
            ) from None
        except (urllib.error.URLError, ConnectionError, OSError) as e:
            raise LLMProviderError(
                f"Cannot connect to Ollama at {self.host}: {e}. "
                "Is Ollama installed and running? https://ollama.com",
                provider="ollama",
            ) from e
        self._checked = True

    @_trace_decorator(span_type="LLM", name="hosted_generate")
    def generate(self, prompt: str, n: int = 1, temperature: float = 0.9) -> list[str]:
        """Generate candidate lines via Ollama.

        For n>1, issues n sequential calls (Ollama's /api/chat returns
        a single response per request).
        """
        from poesia.exceptions import LLMProviderError

        self._check_available()
        self.usage = LLMUsage()
        results: list[str] = []
        t0 = time.time()

        for i in range(n):
            if i > 0:
                time.sleep(0.1)  # Small delay between sequential calls
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {
                    "temperature": temperature,
                },
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.host}/api/chat",
                data=data,
                headers={"Content-Type": "application/json"},
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    res = json.loads(resp.read().decode("utf-8"))
                    content = res.get("message", {}).get("content", "").strip()
                    if content:
                        results.append(content)
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8")
                raise LLMProviderError(
                    f"Ollama API HTTP Error {e.code}: {err_body}",
                    provider="ollama",
                    status_code=e.code,
                    response_body=err_body,
                ) from e
            except Exception as e:
                raise LLMProviderError(
                    f"Ollama request failed: {e}",
                    provider="ollama",
                ) from e

        self.usage.latency_ms = (time.time() - t0) * 1000
        # Ollama doesn't report token counts in the response,
        # but we can estimate from response length
        self.usage.completion_tokens = sum(len(r.split()) for r in results)
        return results

    def repair(self, line: str, defect_description: str) -> str:
        """Ask Ollama to fix one explicit defect in a line."""
        prompt = (
            f"Fix the following poetic line to resolve this defect: {defect_description}.\n"
            f'Line: "{line}"\n'
            "Output ONLY the corrected single line without quotation marks, intro, or explanation."
        )
        candidates = self.generate(prompt, n=1, temperature=0.7)
        if candidates:
            return candidates[0].strip().strip("\"'")
        return line


class OutlinesClient:
    """LLMClient with grammar-constrained generation via Outlines."""

    _DEFAULT_BASE = "Qwen/Qwen2.5-1.5B-Instruct"

    # Shared adapter registry (same priority order as LoRAClient)
    _KNOWN_ADAPTERS: list[tuple[str, str | None]] = [
        ("models/poetry-lora-qwen3b/final_adapter", "Qwen/Qwen2.5-3B-Instruct"),
        ("models/poetry-lora-distilled/final_adapter", None),
        ("models/poetry-lora-multiform/final_adapter", None),
        ("models/poetry-lora-v2/final_adapter", None),
        ("models/poetry-lora-3b/final_adapter", None),
    ]

    def __init__(self, base_model=None, adapter_path=None):
        import os

        self.usage = LLMUsage()
        self.provider = "outlines"
        self.model = base_model or self._DEFAULT_BASE
        self._model_wrapper = None
        self._tokenizer: Any = None
        self._adapter_path = None

        if adapter_path is None:
            pkg_root = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            )
            for candidate_rel, candidate_base in self._KNOWN_ADAPTERS:
                candidate = os.path.join(pkg_root, candidate_rel)
                if os.path.exists(candidate):
                    self._adapter_path = candidate
                    self.model = candidate_base or self._DEFAULT_BASE
                    print(f"[Outlines] Found adapter: {candidate_rel} (base: {self.model})")
                    break
            if self._adapter_path is None:
                print("[Outlines] No adapter found — using base model only")
        else:
            self._adapter_path = adapter_path if os.path.exists(adapter_path) else None
            if base_model is None and self._adapter_path:
                pkg_root = os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                )
                for candidate_rel, candidate_base in self._KNOWN_ADAPTERS:
                    if adapter_path.endswith(candidate_rel) or adapter_path == os.path.join(
                        pkg_root, candidate_rel
                    ):
                        self.model = candidate_base or self._DEFAULT_BASE
                        print(f"[Outlines] Auto-detected base model for adapter: {self.model}")
                        break

    def _load(self):
        if self._model_wrapper is not None:
            return
        import outlines
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

        from poesia.exceptions import LLMProviderError

        bnb = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16
        )
        try:
            tokenizer = AutoTokenizer.from_pretrained(self.model)
            tokenizer.pad_token = tokenizer.eos_token
            model = AutoModelForCausalLM.from_pretrained(
                self.model, quantization_config=bnb, device_map="auto", torch_dtype=torch.bfloat16
            )
            if self._adapter_path:
                from peft import PeftModel

                model = PeftModel.from_pretrained(model, self._adapter_path)
            self._tokenizer = tokenizer
            self._model_wrapper = outlines.from_transformers(model, tokenizer)
        except Exception as e:
            raise LLMProviderError(f"Failed to load model: {e}", provider="outlines") from e

    def generate(self, prompt, n=1, temperature=0.9):
        import time

        import outlines.generator as og
        import torch

        self._load()
        self.usage = LLMUsage()
        t0 = time.time()
        results = []
        line_regex = r"[^\n]+"
        lp = og.get_regex_logits_processor(None, self._model_wrapper, line_regex)
        for i in range(n):
            if i > 0:
                time.sleep(0.1)
            try:
                text = self._model_wrapper(
                    prompt, logits_processor=lp, temperature=temperature, max_tokens=40
                )
                text = str(text).strip() if text else ""
                if text:
                    results.append(text)
            except Exception:
                inputs = self._tokenizer(prompt, return_tensors="pt").to("cuda")
                with torch.no_grad():
                    out = self._model_wrapper.model.generate(
                        **inputs, max_new_tokens=40, temperature=temperature, do_sample=True
                    )
                text = self._tokenizer.decode(
                    out[0][inputs.input_ids.shape[1] :], skip_special_tokens=True
                ).strip()
                if text:
                    text = text.split("\n")[0].strip()
                    if text:
                        results.append(text)
        self.usage.latency_ms = (time.time() - t0) * 1000
        return results if results else [""]

    def repair(self, line, defect_description):
        prompt = (
            "Fix this poetic line: "
            + defect_description
            + '\nLine: "'
            + line
            + '"\nOutput ONLY the corrected line.\n'
        )
        candidates = self.generate(prompt, n=1, temperature=0.7)
        return candidates[0].strip().strip("'\"") if candidates and candidates[0] else line


class LoRAClient:
    """Fine-tuned poetry model via QLoRA adapter.

    Loads a base 3B model in 4-bit and merges a LoRA adapter fine-tuned
    on Spanish poetry. Runs on GPU with ~4-5 GB VRAM.

    Default adapter path: ``models/poetry-lora-3b/final_adapter``
    If the adapter is not found, falls back to the base model.
    """

    _DEFAULT_BASE = "Qwen/Qwen2.5-1.5B-Instruct"

    # Known adapter paths tried in priority order (newest first)
    # Each entry: (relative_path, base_model_name)
    # If base_model_name is None, uses _DEFAULT_BASE (1.5B).
    _KNOWN_ADAPTERS: list[tuple[str, str | None]] = [
        ("models/poetry-lora-qwen3b/final_adapter", "Qwen/Qwen2.5-3B-Instruct"),
        ("models/poetry-lora-distilled/final_adapter", None),
        ("models/poetry-lora-multiform/final_adapter", None),
        ("models/poetry-lora-v2/final_adapter", None),
        ("models/poetry-lora-3b/final_adapter", None),
    ]

    def __init__(
        self,
        adapter_path: str | None = None,
        base_model: str | None = None,
    ) -> None:
        import os

        self.usage: LLMUsage = LLMUsage()
        self.provider = "lora"
        self.model = base_model or self._DEFAULT_BASE

        # Resolve adapter path: env var > explicit arg > known paths
        if adapter_path is None:
            env_path = os.environ.get("LORA_ADAPTER_PATH")
            if env_path and os.path.exists(env_path):
                adapter_path = env_path
                print(f"[LoRA] Using adapter from LORA_ADAPTER_PATH: {adapter_path}")
            else:
                # Resolve relative to repo root (4 levels up from llm_client.py)
                pkg_root = os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                )
                for candidate_rel, candidate_base in self._KNOWN_ADAPTERS:
                    candidate = os.path.join(pkg_root, candidate_rel)
                    if os.path.exists(candidate):
                        adapter_path = candidate
                        self.model = candidate_base or self._DEFAULT_BASE
                        print(f"[LoRA] Found adapter: {candidate_rel} (base: {self.model})")
                        break
                if adapter_path is None:
                    paths_only = [p for p, _ in self._KNOWN_ADAPTERS]
                    print(
                        f"[LoRA] No adapter found. Tried: {', '.join(paths_only)}. Using base model only."
                    )
        else:
            if not os.path.exists(adapter_path):
                print(f"[LoRA] Adapter path {adapter_path} not found. Using base model only.")
            # If explicit adapter_path given but no base_model, infer from known list
            if base_model is None:
                pkg_root = os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                )
                for candidate_rel, candidate_base in self._KNOWN_ADAPTERS:
                    if adapter_path.endswith(candidate_rel) or adapter_path == os.path.join(
                        pkg_root, candidate_rel
                    ):
                        self.model = candidate_base or self._DEFAULT_BASE
                        print(f"[LoRA] Auto-detected base model for adapter: {self.model}")
                        break

        self._model: Any = None
        self._tokenizer: Any = None
        self._adapter_path = adapter_path

    def _load(self) -> None:
        if self._model is not None:
            return
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

        from poesia.device import cuda_usable
        from poesia.exceptions import LLMProviderError

        # bitsandbytes 4-bit needs CUDA kernels the installed torch build
        # actually ships (torch.cuda.is_available() alone doesn't guarantee
        # that — see poesia.device.cuda_usable). Fail fast with a pointer to
        # the llama.cpp fallback instead of a mid-generate CUDA crash.
        if not cuda_usable():
            raise LLMProviderError(
                "No usable CUDA device for bitsandbytes 4-bit inference (either no GPU, "
                "or its compute capability is below what the installed torch build ships "
                "kernels for — e.g. Maxwell/Pascal cards on recent torch wheels). "
                "Use the llama.cpp fallback instead: --llm llama_cpp "
                "(see poesia/generation/llama_cpp.py for setup).",
                provider="lora",
            )

        bnb = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
        )
        try:
            self._tokenizer = AutoTokenizer.from_pretrained(self.model)
            self._tokenizer.pad_token = self._tokenizer.eos_token
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model,
                quantization_config=bnb,
                device_map="auto",
                torch_dtype=torch.bfloat16,
            )
            if self._adapter_path and os.path.exists(self._adapter_path):
                from peft import PeftModel

                self._model = PeftModel.from_pretrained(self._model, self._adapter_path)
        except Exception as e:
            raise LLMProviderError(
                f"Failed to load model '{self.model}': {e}", provider="lora"
            ) from e

    @_trace_decorator(span_type="LLM", name="hosted_generate")
    def generate(self, prompt: str, n: int = 1, temperature: float = 0.9) -> list[str]:
        import time

        import torch

        self._load()
        self.usage = LLMUsage()
        t0 = time.time()
        # A single hendecasyllable is ~7-10 words ≈ 20-30 tokens. 50 gives room.
        max_new = 50 if "Write line" in prompt or "Output ONLY" in prompt else 100

        # Batching: every line candidate shares the exact same prompt, so the n
        # samples are drawn in ONE forward pass via num_return_sequences=n instead
        # of n sequential generate() calls. This is the dominant cost of the
        # constrained loop on local GPUs (~10x wall-clock reduction for n=16).
        inputs = self._tokenizer(prompt, return_tensors="pt").to("cuda")
        with torch.no_grad():
            out = self._model.generate(
                **inputs,
                max_new_tokens=max_new,
                temperature=temperature,
                do_sample=True,
                num_return_sequences=n,
                pad_token_id=self._tokenizer.pad_token_id,
            )

        prompt_len = inputs.input_ids.shape[1]
        results = []
        for seq in out:
            text = self._tokenizer.decode(seq[prompt_len:], skip_special_tokens=True).strip()
            if text:
                # Clean up: remove instruction-echo if the model parroted the prompt
                lines = text.split("\n")
                clean = ""
                for line in lines:
                    line = line.strip().strip('"').strip("'").strip(".")
                    # Skip lines that are clearly instruction-echo
                    skip_words = [
                        "rhyme",
                        "scheme",
                        "syllable",
                        "Write line",
                        "Output ONLY",
                        "line must",
                        "Task",
                        "Poem so far",
                    ]
                    if any(sw.lower() in line.lower() for sw in skip_words):
                        continue
                    # Skip lines that are just numbers or punctuation
                    if len(line) < 3 or line.isdigit():
                        continue
                    if line and len(line) > len(clean):
                        clean = line
                if clean:
                    results.append(clean)
                else:
                    results.append(lines[-1].strip().strip('"').strip("'") if lines else text)
            if len(results) >= n:
                break
        self.usage.latency_ms = (time.time() - t0) * 1000
        return results

    def repair(self, line: str, defect_description: str) -> str:
        prompt = f'Fix this poetic line: {defect_description}\nLine: "{line}"\nOutput ONLY the corrected line.\n'
        candidates = self.generate(prompt, n=1, temperature=0.7)
        return candidates[0].strip().strip("\"'") if candidates else line


class MLflowModelClient:
    """LLMClient that loads a registered model from the MLflow Model Registry.

    Uses ``PoetryModelWrapper`` under the hood via ``mlflow.pyfunc.load_model()``,
    enabling ``mlflow models serve``-compatible serving through the CLI.

    Usage:
        client = MLflowModelClient(model_uri="models:/poesia-lora-soneto-qwen3b/1")
        client = MLflowModelClient(model_uri="runs:/<run_id>/model")
    """

    def __init__(self, model_uri: str = ""):
        import os

        self.usage = LLMUsage()
        self.provider = "mlflow"
        self.model = model_uri or os.environ.get("MLFLOW_MODEL_URI", "")
        self._model: Any = None

    def _load(self) -> None:
        if self._model is not None:
            return
        if not self.model:
            raise LLMProviderError(
                "MLflowModelClient requires a model_uri. Set MLFLOW_MODEL_URI "
                "environment variable or pass model_uri to the constructor.",
                provider="mlflow",
            )
        try:
            import mlflow.pyfunc

            self._model = mlflow.pyfunc.load_model(self.model)
        except Exception as e:
            raise LLMProviderError(
                f"Failed to load MLflow model from '{self.model}': {e}",
                provider="mlflow",
            ) from e

    def generate(self, prompt: str, n: int = 1, temperature: float = 0.8) -> list[str]:
        self._load()
        import pandas as pd

        inputs = pd.DataFrame(
            {
                "prompt": [prompt] * n,
                "temperature": [temperature] * n,
                "max_tokens": [100] * n,
            }
        )
        return self._model.predict(inputs)
