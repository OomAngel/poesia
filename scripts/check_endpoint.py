#!/usr/bin/env python3
"""Check an OpenAI-compatible endpoint the way the page uses it, without printing the key.

Reads LLM_BASE_URL and LLM_API_KEY (and optionally LLM_NAME) from the environment, lists
the models the key can see, and asks the chosen model (LLM_NAME, else the first Apertus
model listed) for one line of verse through the page's own client. Prints model ids,
timings and the line; the key never appears in the output.

    LLM_BASE_URL=https://api.inference.cscs.ch/v1 LLM_API_KEY=... python scripts/check_endpoint.py
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request


def main() -> int:
    base = os.environ.get("LLM_BASE_URL", "").rstrip("/")
    key = os.environ.get("LLM_API_KEY", "")
    if not base or not key:
        print("FAIL  LLM_BASE_URL and LLM_API_KEY must be set")
        return 2
    req = urllib.request.Request(f"{base}/models", headers={"Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            models = [m["id"] for m in json.loads(resp.read()).get("data", [])]
    except urllib.error.HTTPError as exc:
        print(f"FAIL  /models answered {exc.code} (key refused or expired?)")
        return 1
    except OSError as exc:
        print(f"FAIL  /models unreachable: {exc}")
        return 1
    print(f"PASS  key accepted; {len(models)} models:")
    for m in models:
        print(f"      {m}")
    name = os.environ.get("LLM_NAME") or next((m for m in models if "apertus" in m.lower()), "")
    if not name:
        print("FAIL  no Apertus model listed; set LLM_NAME to one of the above")
        return 1
    os.environ["LLM_NAME"] = name
    from poesia.generation.registry import get_llm

    llm = get_llm("openai_compat")
    prompt = (
        "You are writing a Spanish poem on the theme: el mar de noche. Write line 1. "
        "Exactly 11 syllables. Output ONLY the single bare poetry line."
    )
    t = time.time()
    try:
        line = llm.generate(prompt, n=1)[0]
    except Exception as exc:  # report, never raise with the request (it carries the key)
        print(f"FAIL  {name}: {type(exc).__name__}")
        return 1
    print(f"PASS  {name} answered in {time.time() - t:.1f} s: {line!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
