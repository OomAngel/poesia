"""Abstract LLM client interface.

Concrete backends (hosted API, llama.cpp local inference, transformers local
inference) implement this Protocol so the generation loop stays decoupled
from any single provider. This mirrors the "typed port" discipline used
elsewhere: no SDK-specific import should leak into evaluation/ or phonology/.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Protocol


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

    Reads GEMINI_API_KEY, OPENAI_API_KEY, or XAI_API_KEY from environment.
    Does not require external SDK packages, relying on standard library urllib.

    Supported providers:
      - gemini  : Google Gemini API (GEMINI_API_KEY)
      - openai  : OpenAI Chat Completions API (OPENAI_API_KEY)
      - grok    : xAI Grok API — OpenAI-compatible (XAI_API_KEY)
      - auto    : First available key wins (Gemini → Grok → OpenAI)
    """

    # xAI Grok base URL (OpenAI-compatible)
    _GROK_BASE_URL = "https://api.x.ai/v1"
    _GROK_DEFAULT_MODEL = "grok-3-mini"

    def __init__(
        self,
        provider: str = "auto",
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.provider = provider
        self.timeout = timeout

        if api_key:
            self.api_key = api_key
        elif os.environ.get("GEMINI_API_KEY"):
            self.api_key = os.environ.get("GEMINI_API_KEY", "")
            if provider == "auto":
                self.provider = "gemini"
        elif os.environ.get("XAI_API_KEY"):
            self.api_key = os.environ.get("XAI_API_KEY", "")
            if provider == "auto":
                self.provider = "grok"
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
        elif self.provider == "grok":
            self.model = self._GROK_DEFAULT_MODEL
        else:
            self.model = "gpt-4o-mini"

    def generate(self, prompt: str, n: int = 1, temperature: float = 0.9) -> list[str]:
        if not self.api_key:
            raise RuntimeError(
                "HostedLLMClient requires an API key. Set GEMINI_API_KEY, "
                "XAI_API_KEY, or OPENAI_API_KEY environment variable, or pass "
                "api_key to HostedLLMClient."
            )

        if self.provider == "gemini":
            return self._generate_gemini(prompt, n, temperature)
        elif self.provider == "grok":
            return self._generate_openai_compat(
                prompt, n, temperature,
                base_url=self._GROK_BASE_URL,
            )
        else:
            return self._generate_openai_compat(
                prompt, n, temperature,
                base_url="https://api.openai.com/v1",
            )

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
            raise RuntimeError(f"Gemini API HTTP Error {e.code}: {err_msg}") from e
        except Exception as e:
            raise RuntimeError(f"Gemini API request failed: {e}") from e

    def _generate_openai_compat(
        self, prompt: str, n: int, temperature: float, base_url: str
    ) -> list[str]:
        """OpenAI-compatible chat completions (used by OpenAI and Grok)."""
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
            },
        )
        provider_label = "Grok" if "x.ai" in base_url else "OpenAI"
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                return [c["message"]["content"].strip() for c in res.get("choices", [])]
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8")
            raise RuntimeError(f"{provider_label} API HTTP Error {e.code}: {err_msg}") from e
        except Exception as e:
            raise RuntimeError(f"{provider_label} API request failed: {e}") from e

