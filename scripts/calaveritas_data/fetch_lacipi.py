"""Fetch LACIPI "Impresos Populares Mexicanos" (UNAM) items in Categoría:Calaveras literarias.

Polite, resumable, MediaWiki-API only (no HTML scraping):
  phase 1  list=categorymembers                       -> raw/categorymembers.json
  phase 2  per Índice: page: revisions(content)|images|info|categories
           + list=allpages in ns 250 (Página:) for that file + their revisions(content)
                                                       -> raw/items/<safe>.json
  phase 3  prop=imageinfo (url|size|sha1|mime) for every file the Índice pages use,
           50 titles per request                       -> raw/imageinfo.json
  phase 4  size budget check (default 4 GB, abort if exceeded), then download each file
           (original as offered) into images/<safe item id>/, skipping files already
           present with matching size and sha1         -> images/...
  phase 5  build items.jsonl (one record per item; signed/unsigned classification)

Usage (from anywhere; never run from inside the download folder):
  python -I scripts/fetch_lacipi.py --out <calaveritas>/lacipi [--metadata-only] [--budget-gb 4]

Downloaded content is treated as data only: JSON is parsed, image bytes are hashed and written,
nothing downloaded is executed.
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

API = "https://lacipi.humanidades.unam.mx/ipm/w/api.php"
WIKI = "https://lacipi.humanidades.unam.mx/ipm/w/"
CATEGORY = "Categoría:Calaveras literarias"
UA = "PoesIA-research/0.1 (private non-commercial research; rate-limited 1 req/s)"
COOKIE = "humans_21909=1"  # the site's bot-check cookie; curl/urllib must send it
DELAY = 2.0  # slowed after the server answered 507/500 at ~1 req/s on 2026-10-08
BACKOFF = (60, 180, 600)  # seconds to wait after an HTTP error before retrying
_last = [0.0]


def get(url, binary=False, method="GET"):
    wait = DELAY - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Cookie": COOKIE}, method=method)
    for attempt in range(len(BACKOFF) + 1):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
                ctype = r.headers.get("Content-Type", "")
                headers = dict(r.headers)
            _last[0] = time.time()
            break
        except Exception as e:  # network hiccup: back off, then retry
            _last[0] = time.time()
            if attempt == len(BACKOFF):
                raise
            print(
                f"  {time.strftime('%H:%M:%S')} retry {attempt + 1} in {BACKOFF[attempt]} s after {e}",
                file=sys.stderr,
            )
            time.sleep(BACKOFF[attempt])
    if binary:
        return data, headers
    if "json" not in ctype:
        raise RuntimeError(f"non-JSON response ({ctype}) from {url}: {data[:200]!r}")
    return json.loads(data.decode("utf-8"))


def api(**params):
    params.setdefault("format", "json")
    return get(API + "?" + urllib.parse.urlencode(params))


def safe(name):
    """Índice:AEArroyo A.djvu -> AEArroyo_A.djvu (filesystem-safe item id)."""
    name = name.split(":", 1)[-1]
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")


def page_url(title):
    return WIKI + urllib.parse.quote(title.replace(" ", "_"))


def write_json(path, obj):
    tmp = path + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def phase_members(raw):
    path = os.path.join(raw, "categorymembers.json")
    if os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))
    members, cont = [], {}
    while True:
        d = api(
            action="query",
            list="categorymembers",
            cmtitle=CATEGORY,
            cmlimit="500",
            cmprop="ids|title|sortkeyprefix|timestamp",
            **cont,
        )
        members += d["query"]["categorymembers"]
        if "continue" not in d:
            break
        cont = {k: v for k, v in d["continue"].items()}
    write_json(path, members)
    return members


def phase_items(raw, members):
    os.makedirs(os.path.join(raw, "items"), exist_ok=True)
    for i, m in enumerate(members, 1):
        path = os.path.join(raw, "items", safe(m["title"]) + ".json")
        if os.path.exists(path):
            continue
        print(f"[items {i}/{len(members)}] {m['title']}", file=sys.stderr)
        idx = api(
            action="query",
            titles=m["title"],
            prop="revisions|images|info|categories",
            rvprop="ids|timestamp|user|content",
            imlimit="500",
            cllimit="500",
        )
        fname = m["title"].split(":", 1)[1]
        pages, cont = [], {}
        while True:
            d = api(
                action="query",
                list="allpages",
                apnamespace="250",
                apprefix=fname + "/",
                aplimit="500",
                **cont,
            )
            pages += d["query"]["allpages"]
            if "continue" not in d:
                break
            cont = dict(d["continue"])
        page_revs = []
        for k in range(0, len(pages), 50):
            titles = "|".join(p["title"] for p in pages[k : k + 50])
            d = api(
                action="query", titles=titles, prop="revisions", rvprop="ids|timestamp|user|content"
            )
            page_revs += list(d["query"]["pages"].values())
        write_json(
            path, {"member": m, "index": idx, "pagina_list": pages, "pagina_pages": page_revs}
        )


def phase_imageinfo(raw, members):
    path = os.path.join(raw, "imageinfo.json")
    files = set()
    for m in members:
        rec = json.load(
            open(os.path.join(raw, "items", safe(m["title"]) + ".json"), encoding="utf-8")
        )
        for pg in rec["index"]["query"]["pages"].values():
            for im in pg.get("images", []):
                files.add(im["title"])
    have = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
    todo = sorted(f for f in files if f not in have)
    for k in range(0, len(todo), 50):
        print(f"[imageinfo {k}/{len(todo)}]", file=sys.stderr)
        d = api(
            action="query",
            titles="|".join(todo[k : k + 50]),
            prop="imageinfo",
            iiprop="url|size|sha1|mime|timestamp",
            iilimit="1",
        )
        norm = {n["to"]: n["from"] for n in d["query"].get("normalized", [])}
        for pg in d["query"]["pages"].values():
            have[norm.get(pg["title"], pg["title"])] = pg
        write_json(path, have)
    return have


def sha1_file(p):
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def plan_downloads(raw, members, info):
    plan = []
    for m in members:
        rec = json.load(
            open(os.path.join(raw, "items", safe(m["title"]) + ".json"), encoding="utf-8")
        )
        for pg in rec["index"]["query"]["pages"].values():
            for im in pg.get("images", []):
                ii = (info.get(im["title"]) or {}).get("imageinfo")
                if not ii:
                    plan.append((m["title"], im["title"], None))
                    continue
                plan.append((m["title"], im["title"], ii[0]))
    return plan


def phase_download(out, plan, budget):
    """Download each scan as served. All 40 TIFFs on this wiki are served with a different size and
    sha1 than the API's imageinfo records (server copies last-modified 2024, after the 2019-2020
    uploads; the files decode fully at the recorded width/height/page count). Such a file is kept
    under its normal name only if the transfer was complete (bytes == Content-Length); the API and
    served size/sha1/Last-Modified are recorded in raw/served_files.json and items.jsonl."""
    total = sum(ii["size"] for _, _, ii in plan if ii)
    print(f"download plan: {len(plan)} files, {total / 1e9:.3f} GB", file=sys.stderr)
    if total > budget:
        sys.exit(f"ABORT: planned {total} bytes exceeds budget {budget}")
    served_path = os.path.join(out, "raw", "served_files.json")
    served = json.load(open(served_path, encoding="utf-8")) if os.path.exists(served_path) else {}
    for n, (item, ftitle, ii) in enumerate(plan, 1):
        if not ii:
            print(f"  no imageinfo for {ftitle} (item {item})", file=sys.stderr)
            continue
        d = os.path.join(out, "images", safe(item))
        os.makedirs(d, exist_ok=True)
        dest = os.path.join(d, safe(ftitle))
        if os.path.exists(dest):
            size, sha1 = os.path.getsize(dest), None
            if size == ii["size"] and sha1_file(dest) == ii["sha1"]:
                continue
            s = served.get(ftitle)
            if s and size == s["served_bytes"] and sha1_file(dest) == s["served_sha1"]:
                continue
        url = ii["url"].replace("http://", "https://", 1)
        legacy = dest + ".mismatch"  # left by the first run of 2026-10-08
        if os.path.exists(legacy):
            print(f"[verify {n}/{len(plan)}] {ftitle} (HEAD)", file=sys.stderr)
            _, hdr = get(url, binary=True, method="HEAD")
            data = open(legacy, "rb").read()
        else:
            print(f"[download {n}/{len(plan)}] {ftitle} {ii['size']} B", file=sys.stderr)
            data, hdr = get(url, binary=True)
        h = hashlib.sha1(data).hexdigest()
        if len(data) != ii["size"] or h != ii["sha1"]:
            content_len = int(hdr.get("Content-Length", hdr.get("content-length", -1)))
            if content_len != len(data):
                sys.exit(
                    f"ABORT: incomplete transfer of {ftitle}: {len(data)} B, Content-Length {content_len}"
                )
            served[ftitle] = {
                "api_bytes": ii["size"],
                "api_sha1": ii["sha1"],
                "api_timestamp": ii.get("timestamp"),
                "served_bytes": len(data),
                "served_sha1": h,
                "served_last_modified": hdr.get("Last-Modified", hdr.get("last-modified")),
                "served_content_type": hdr.get("Content-Type", hdr.get("content-type")),
            }
            write_json(served_path, served)
            print(
                f"  served file differs from API record ({len(data)} vs {ii['size']} B); complete transfer, kept",
                file=sys.stderr,
            )
        with open(dest + ".part", "wb") as f:
            f.write(data)
        os.replace(dest + ".part", dest)
        if os.path.exists(legacy):
            os.remove(legacy)


TEMPLATE_RE = re.compile(r"^\|([^=\n]+)=(.*)$", re.M)


def parse_fields(wikitext):
    return {k.strip(): v.strip() for k, v in TEMPLATE_RE.findall(wikitext or "")}


UNSIGNED_VALUES = {"impreso carente de nombres declarados", ""}


def classify(fields):
    """signed = the print declares a name (Nombres_declarados_en_el_impreso is not the
    'Impreso carente de nombres declarados' sentinel). The declared names may be a verse
    writer, an illustrator or a printer; names_declared_kind is filled in by
    classify_names() for review."""
    v = fields.get("Nombres_declarados_en_el_impreso", "")
    return (
        ("unsigned" if v.strip().lower() in UNSIGNED_VALUES else "signed"),
        "Nombres_declarados_en_el_impreso",
        v,
    )


def phase_items_jsonl(out, raw, members, info, plan):
    served_path = os.path.join(out, "raw", "served_files.json")
    served = json.load(open(served_path, encoding="utf-8")) if os.path.exists(served_path) else {}
    by_item = {}
    for item, ftitle, ii in plan:
        by_item.setdefault(item, []).append((ftitle, ii))
    n = 0
    with open(os.path.join(out, "items.jsonl.part"), "w", encoding="utf-8") as o:
        for m in members:
            rec = json.load(
                open(os.path.join(raw, "items", safe(m["title"]) + ".json"), encoding="utf-8")
            )
            pg = next(iter(rec["index"]["query"]["pages"].values()))
            rev = (pg.get("revisions") or [{}])[0]
            text = rev.get("*", "")
            fields = parse_fields(text)
            status, field, value = classify(fields)
            paginas = []
            for p in sorted(rec["pagina_pages"], key=lambda p: p["title"]):
                r = (p.get("revisions") or [{}])[0]
                paginas.append(
                    {
                        "title": p["title"],
                        "url": page_url(p["title"]),
                        "revid": r.get("revid"),
                        "timestamp": r.get("timestamp"),
                        "wikitext": r.get("*", ""),
                        "body_chars": len(
                            re.sub(
                                r"<noinclude>.*?</noinclude>", "", r.get("*", ""), flags=re.S
                            ).strip()
                        ),
                    }
                )
            files = []
            for ftitle, ii in by_item.get(m["title"], []):
                files.append(
                    {
                        "file_title": ftitle,
                        "local_path": f"images/{safe(m['title'])}/{safe(ftitle)}" if ii else None,
                        "url": ii["url"].replace("http://", "https://", 1) if ii else None,
                        "description_url": ii.get("descriptionurl") if ii else None,
                        "bytes": ii["size"] if ii else None,
                        "width": ii.get("width") if ii else None,
                        "height": ii.get("height") if ii else None,
                        "mime": ii.get("mime") if ii else None,
                        "sha1": ii["sha1"] if ii else None,
                        "uploaded": ii.get("timestamp") if ii else None,
                        "served_differs_from_api": served.get(ftitle),
                    }
                )
            o.write(
                json.dumps(
                    {
                        "item_id": safe(m["title"]),
                        "title": m["title"],
                        "pageid": pg.get("pageid"),
                        "url": page_url(m["title"]),
                        "revid": rev.get("revid"),
                        "rev_timestamp": rev.get("timestamp"),
                        "incipit": fields.get("Íncipit"),
                        "textual_units": fields.get("Unidades_textuales"),
                        "printer_attributed": fields.get("Edición_atribuida_a"),
                        "editor": fields.get("Editor"),
                        "imprint": fields.get("Pie_de_imprenta"),
                        "printer_address": fields.get("Dirección_de_imprenta"),
                        "year": fields.get("Año_de_imprenta"),
                        "collection_consulted": fields.get("Colección_de_consulta"),
                        "repository": fields.get("Repositorio_de_consulta"),
                        "series": fields.get("Serie"),  # codespell:ignore
                        "names_declared": fields.get("Nombres_declarados_en_el_impreso"),
                        "signature_status": status,
                        "signature_field": field,
                        "signature_value": value,
                        "categories": [c["title"] for c in pg.get("categories", [])],
                        "fields": fields,
                        "wikitext": text,
                        "transcription_pages": paginas,
                        "transcribed_pages": sum(1 for p in paginas if p["body_chars"] > 0),
                        "files": files,
                        "licence": "CC BY-NC-SA (site-wide rights text: 'Creative Commons Reconocimiento Compartir Igual no comercial')",
                        "fetched": time.strftime("%Y-%m-%d"),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            n += 1
    os.replace(os.path.join(out, "items.jsonl.part"), os.path.join(out, "items.jsonl"))
    print(f"items.jsonl: {n} records", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--metadata-only", action="store_true")
    ap.add_argument("--budget-gb", type=float, default=4.0)
    a = ap.parse_args()
    raw = os.path.join(a.out, "raw")
    os.makedirs(raw, exist_ok=True)
    members = phase_members(raw)
    print(f"category members: {len(members)}", file=sys.stderr)
    phase_items(raw, members)
    info = phase_imageinfo(raw, members)
    plan = plan_downloads(raw, members, info)
    if not a.metadata_only:
        phase_download(a.out, plan, int(a.budget_gb * 1e9))
    phase_items_jsonl(a.out, raw, members, info, plan)


if __name__ == "__main__":
    main()
