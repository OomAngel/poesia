# Calaverita source data: download and inventory scripts

These scripts built the git-ignored folder `seeds/poetry_corpus/external/calaveritas/` (2026-10-08). Its own
`README.md` and `MANIFEST.tsv` (sha256 per file) describe the data; the data is never committed (AGENTS.md: poems
and corpus data go to DVC only).

| Script | Does |
|---|---|
| `fetch_lacipi.py`, `summarize_lacipi.py` | UNAM LACIPI wiki, category "Calaveras literarias": 202 item records and scans via the MediaWiki API; signed/unsigned split |
| `loc_cdp_fetch.mjs` | Library of Congress JSON API through a real Chrome tab over CDP (loc.gov sits behind a Cloudflare check). Run on Windows with Node: `node loc_cdp_fetch.mjs urls.json outdir`, Chrome started with `--remote-debugging-port=9222` and a loc.gov tab open |
| `build_loc.py`, `loc_fallback_tif.py` | LoC item metadata to `loc/items.jsonl`; 3000-px IIIF JPEGs, or the master TIFF downscaled where IIIF 404s |
| `build_manifest.py` | `MANIFEST.tsv` (path, bytes, sha256, source URL, licence) |
| `local_corpus/` | counts in the local corpus (`corpus_master`): octosyllabic quatrains, Mexican authors, scanner validation; `make_local_ids.py` writes `local_octosyllabic/ids.tsv` (ids only, no text) |

Paths are the desktop's (`/home/angel/dev/poesia...`); adjust before running elsewhere.
