# Email 2 — Setup + 15-minute tour

> Send after Email 1, or include both. Only the recipient's `[name]` remains to
> fill in — everything else is ready to send.

**To:** [contact's email]
**Subject:** Re: PoesIA — here's how to run it (15 minutes)

Hi [name],

Following up on the tarball — here's the fastest way in.

## Install (about 5 minutes)

Prerequisites: Python 3.11, ~2 GB of free disk. Git is optional.

```bash
# from the folder where you unpacked poesia-share-20260804.tar.gz
cd poesia
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

That installs the CLI plus the test suite. Everything below works offline,
no API keys:

```bash
poesia --help
poesia scan "En el principio era el Verbo y el Verbo" --language es
poesia write --theme "lluvia sobre piedra" --form soneto --language es
```

The default `stub` backend is a rule-based stand-in. To use a real LLM you'd
need an API key (Groq / Gemini / OpenAI) or a local Ollama:

```bash
poesia write --theme "luna" --form soneto --llm groq --brief
```

## A 15-minute tour of the repo

1. **README.md** — the whole idea + the -IA family table (2 min)
2. **USAGE_GUIDE.md** — every command, poetic forms, the library (3 min)
3. **docs/ARCHITECTURE.md** — how the generate → validate → repair loop works (3 min)
4. **seeds/angel_fragments/** — the personal fragments that ground generation (2 min)
5. **Write something of your own** (3 min):

   ```bash
   poesia write --theme "tu tema" --form soneto --show-alternatives 3 --save
   ```

   Saved poems land in `~/.poesia/poems/` — `poesia memoria list` to see them.

## Things worth knowing

- Heavy features (illustration, music, embeddings, fine-tuning) install behind
  extras: `pip install -e ".[all]"`. The core works without them.
- Sanity check: `pytest` runs the full suite (**477 tests**).
- The training/MLOps side (LoRA adapters, MLflow) is real but resource-heavy —
  happy to walk you through it separately if you're curious.

Any snag, just reply — I'll help you through it.

Angel

---

## Versión en español (opcional)

**Asunto:** Re: PoesIA — así se ejecuta (15 minutos)

Instala con `python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"`
y prueba `poesia scan "En el principio era el Verbo y el Verbo" --language es`.
Luego `poesia write --theme "tu tema" --form soneto`. El recorrido completo
está en el README y en `USAGE_GUIDE.md`. ¿Cualquier duda? Escríbeme.
