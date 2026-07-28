"""Abstract LLM client interface.

Concrete backends (hosted API, llama.cpp local inference, transformers local
inference) implement this Protocol so the generation loop stays decoupled
from any single provider. This mirrors the "typed port" discipline used
elsewhere: no SDK-specific import should leak into evaluation/ or phonology/.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Protocol


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

    def generate(self, prompt: str, n: int = 1, temperature: float = 0.9) -> list[str]:
        """Generate plausible short lines based on prompt keywords."""
        # Extract theme/language from prompt
        theme_word = self._extract_theme(prompt)
        language = self._extract_language(prompt)
        
        # Pick template based on context (look for syllable hints in prompt)
        templates = self._select_templates(prompt, language)
        
        # Generate n candidates by cycling through templates
        results = []
        for i in range(n):
            template = templates[i % len(templates)]
            line = template.format(word=theme_word)
            results.append(line)
        
        return results

    def repair(self, line: str, defect_description: str) -> str:
        """Simple repair: slightly modify the line."""
        # For now, just add a word to try to fix syllable count
        return f"{line} clara"

    def _extract_theme(self, prompt: str) -> str:
        """Extract the main theme word from prompt."""
        # Look for "Theme: <word>" pattern
        if "Theme:" in prompt or "Tema:" in prompt:
            for line in prompt.split("\n"):
                if "Theme:" in line or "Tema:" in line or "theme:" in line:
                    parts = line.split(":", 1)
                    if len(parts) > 1:
                        theme = parts[1].strip().split()[0]  # First word of theme
                        return theme
        return "luna"  # fallback

    def _extract_language(self, prompt: str) -> str:
        """Extract language from prompt."""
        if "Language: es" in prompt or "Idioma: es" in prompt:
            return "es"
        if "Language: en" in prompt:
            return "en"
        return "es"  # fallback

    def _select_templates(self, prompt: str, language: str) -> list[str]:
        """Select appropriate templates based on prompt context."""
        # Without form info in prompt, default to short lines (5-7 syllables)
        # Real LLMs would get this from the brief or learn from examples
        prompt_lower = prompt.lower()
        
        # Count existing lines to handle haiku's 5-7-5 pattern
        poem_so_far = prompt.split("Poem so far:")[-1].strip() if "Poem so far:" in prompt else ""
        existing_lines = [l.strip() for l in poem_so_far.split("\n") if l.strip()]
        line_number = len(existing_lines)
        
        if language == "es":
            # For haiku pattern: line 0 -> 5, line 1 -> 7, line 2 -> 5
            if line_number == 1 or "7" in prompt:
                return self._SPANISH_TEMPLATES_7
            elif "haiku" in prompt_lower or line_number in [0, 2] or "5" in prompt:
                return self._SPANISH_TEMPLATES_5
            else:
                return self._SPANISH_TEMPLATES_11  # Sonnet default
        else:  # English
            if line_number == 1 or "7" in prompt:
                return self._ENGLISH_TEMPLATES_7
            elif "haiku" in prompt_lower or line_number in [0, 2] or "5" in prompt:
                return self._ENGLISH_TEMPLATES_5
            else:
                return self._ENGLISH_TEMPLATES_10  # Sonnet default


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
    _GROQ_DEFAULT_MODEL = "llama-3.3-70b-versatile"

    def __init__(
        self,
        provider: str = "auto",
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.provider = provider
        self.timeout = timeout
        self.usage: LLMUsage = LLMUsage()  # P5: populated after each generate()

        if api_key:
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
                    prompt, n, temperature,
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
            f"Line: \"{line}\"\n"
            "Output ONLY the corrected single line without quotation marks, intro, or explanation."
        )
        candidates = self.generate(prompt, n=1, temperature=0.7)
        if candidates:
            return candidates[0].strip().strip('"\'')
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
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}
        )
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
            if i > 0:
                time.sleep(2.1)  # 30 RPM = 1 req/2 s; 2.1 s adds margin
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
        last_err_msg = ""
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
                from poesia.exceptions import LLMProviderError
                raise LLMProviderError(
                    f"{provider_label} API HTTP Error {e.code}: {err_body}",
                    provider=provider_label.lower(),
                    status_code=e.code,
                    response_body=err_body,
                ) from e
            except Exception as e:
                from poesia.exceptions import LLMProviderError
                raise LLMProviderError(
                    f"{provider_label} API request failed: {e}",
                    provider=provider_label.lower(),
                ) from e

