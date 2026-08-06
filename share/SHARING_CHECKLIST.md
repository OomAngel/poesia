# Sharing PoesIA with one contact — checklist

> Goal: deliver the repo **privately, cleanly, and with no secrets** — no 1.3 GB
> of build artifacts, no `.env_mlflow`, no API keys.

## Step 1 — Build the share bundle

```bash
bash scripts/package_share.sh
```

Produces `dist/poesia-share-YYYYMMDD.tar.gz` (**~13 MB**, tracked files only).
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
| **Email attachment** | ✅ (13 MB < 25 MB limit) | Simplest — matches "a single email" |
| **Drive / Dropbox link** | ✅ | If your mail provider is stricter |
| **git bundle** (`WITH_BUNDLE=1`) | ✅ | Recipient: `git clone poesia-share-*.bundle` — full history |
| **Private GitHub repo + invite** | ⚠️ only if you decide to | Requires your explicit instruction (AGENTS.md forbids pushing without it). If chosen: create the repo as **Private**, invite the contact as collaborator, never make it public |

## Step 3 — Pre-send checks

- [x] `git status` clean
- [x] No real `.env_mlflow` inside the bundle (script verifies; only
      `.env_mlflow.example` placeholders are tracked)
- [x] `mlruns/`, `models/`, `mlops/data/` excluded (already gitignored)
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
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest                # optional sanity check (410 tests)
poesia --help
poesia write --theme "luna" --form soneto --language es   # offline, no keys
```

## Rules of the road

- The repo must stay private — never publish it or push it to a public remote.
- The contact may share the *poems they write with PoesIA*, but the original fragments
  in `seeds/` remain © the author (see `NOTICE`) and are not to be copied or
  redistributed.
- `share/` contains your private email drafts — they ship inside the tarball,
  which is fine (they're addressed to the recipient), but exclude them from the
  bundle if you'd rather not.
