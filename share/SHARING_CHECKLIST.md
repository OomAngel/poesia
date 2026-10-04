# Sharing PoesIA with one contact — checklist

> Goal: deliver the repo **cleanly and with no secrets** — no 1.3 GB
> of build artifacts, no `.env_mlflow`, no API keys.

## Step 1 — Build the share bundle

```bash
bash scripts/package_share.sh
```

Produces `dist/poesia-share-YYYYMMDD.tar.gz` (**~1.3 MB** on 2026-10-04, tracked files
only; the corpus is in DVC, not git).
The script verifies no secret file (`.env_mlflow`, `.key`, …) sneaks in and
aborts if one does.

Want the recipient to get the full git history (they can `git clone` and see
every commit)?

```bash
WITH_BUNDLE=1 bash scripts/package_share.sh
```

## Step 2 — Choose a delivery channel

| Channel | Fits your case? | Notes |
|---|---|---|
| **Email attachment** | ✅ (≈1.3 MB < 25 MB limit) | Simplest — matches "a single email" |
| **Drive / Dropbox link** | ✅ | If your mail provider is stricter |
| **git bundle** (`WITH_BUNDLE=1`) | ✅ | Recipient: `git clone poesia-share-*.bundle` — full history |
| **GitHub link** | ✅ | The repository is public: `git clone https://github.com/OomAngel/poesia.git` (no corpus, no model weights) |

## Step 3 — Pre-send checks

- [x] `git status` clean
- [x] No real `.env_mlflow` inside the bundle (script verifies; only
      `.env_mlflow.example` placeholders are tracked)
- [x] `mlruns/`, `models/`, `mlops/data/`, the corpus excluded (gitignored or DVC-tracked)
- [x] Email drafts filled (`share/EMAIL_01_COVER.md`, `share/EMAIL_02_SETUP_TOUR.md`) —
      only the recipient's `[name]` / `[contact's email]` remain
- [ ] Choose English or Spanish body (both are provided)
- [x] LICENSE + NOTICE travel inside the tarball automatically — no extra step
- [x] README showcase includes a live Cloudflare example
      (`docs/examples/auca_cloudflare_la_luna.png`, downscaled)

## Step 4 — Recipient quick start (paste into the email if useful)

```bash
tar -xzf poesia-share-20260804.tar.gz
cd poesia
python3.13 -m venv .venv && source .venv/bin/activate   # requires Python 3.13
pip install -e ".[dev]"
pytest                # optional sanity check (519 pass in the full conda env, 2026-10-04)
poesia --help
poesia write --theme "luna" --form soneto --language es   # offline, no keys
```

## Rules of the road

- The repository is public on GitHub. The poetry corpus is never in it (DVC only) and must
  never be shared.
- The contact may share the *poems they write with PoesIA*, but the original fragments
  in `seeds/` remain © the author (see `NOTICE`) and are not to be copied or
  redistributed.
- `share/` contains your email drafts — they ship inside the tarball and are also
  public in the GitHub repository (they're addressed to the recipient).
