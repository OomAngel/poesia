"""Library of Congress calavera broadsides: build loc/items.jsonl from the search and item records that
loc_cdp_fetch.mjs saved through Angel's Chrome (loc.gov's API sits behind a Cloudflare check), then download
one 3000-px-wide IIIF JPEG per image from tile.loc.gov (no check there). Master TIFF URLs are recorded, not fetched.
Run: python -I build_loc.py <calaveritas dir>. Resumable; 1 request/second."""

import hashlib
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

root = Path(sys.argv[1]) / "loc"
rec = root / "records"
UA = {"User-Agent": "Mozilla/5.0 (PoesIA calaveritas research; private use)"}
KEEP = re.compile(r"posada|vanegas|manilla", re.I)
DROP = re.compile(
    r"big tree|calaveras county|calaveras grove|sequoia|taller de gr|highsmith|garcia, rupert|cuevas|historic american",
    re.I,
)

search = {}
for f in rec.glob("search_*.json"):
    for r in json.loads(f.read_text()).get("results", []):
        search[r["id"]] = r


def text(*parts):
    out = []
    for p in parts:
        out += p if isinstance(p, list) else [str(p or "")]
    return " ".join(out)


items = []
for f in sorted(rec.glob("item_*.json")):
    d = json.loads(f.read_text())
    it = d.get("item", {})
    lccn = f.stem.removeprefix("item_")
    s = next((v for k, v in search.items() if f"/item/{lccn}/" in k), {})
    blob = text(
        it.get("title"),
        it.get("contributor_names") or [],
        it.get("summary"),
        it.get("notes") or [],
        s.get("contributor") or [],
    )
    if DROP.search(blob) or not (KEEP.search(blob) or "broadside" in blob.lower()):
        continue
    imgs = []
    for u in s.get("image_url") or []:
        m = re.search(r"/service/pnp/(.+?)/([0-9a-z]+?)(?:_150px|t|r|v)?\.(jpg|gif)", u)
        if m:
            imgs.append((m.group(1), m.group(2)))
    # one entry per resource (cph/ppmsc ids), from the item's resources list
    res = []
    for r in d.get("resources", []):
        m = re.search(
            r"/service/pnp/(.+?)/([0-9a-z]+?)(?:_150px|t|r|v)?\.(?:jpg|gif)", r.get("image", "")
        )
        if m:
            res.append(
                {
                    "dir": m.group(1),
                    "id": m.group(2),
                    "caption": r.get("caption"),
                    "resource_url": r.get("url"),
                }
            )
    if not res:
        res = [{"dir": a, "id": b} for a, b in dict.fromkeys(imgs)]
    items.append(
        {
            "lccn": lccn,
            "url": f"https://www.loc.gov/item/{lccn}/",
            "title": it.get("title"),
            "date": it.get("date"),
            "created_published": it.get("created_published"),
            "contributors": it.get("contributor_names"),
            "summary": it.get("summary"),
            "medium": it.get("medium"),
            "notes": it.get("notes"),
            "rights_advisory": it.get("rights_advisory"),
            "call_number": it.get("call_number"),
            "images": [
                {
                    **r,
                    "iiif_3000": f"https://tile.loc.gov/image-services/iiif/service:pnp:{r['dir'].replace('/', ':')}:{r['id']}u/full/3000,/0/default.jpg",
                    "master_tif": f"https://tile.loc.gov/storage-services/master/pnp/{r['dir']}/{r['id']}u.tif",
                }
                for r in res
            ],
        }
    )

(root / "items.jsonl").write_text("".join(json.dumps(i, ensure_ascii=False) + "\n" for i in items))
print("broadside items:", len(items), "images:", sum(len(i["images"]) for i in items))

ok = fail = 0
for i in items:
    for k, im in enumerate(i["images"]):
        dest = root / "images" / i["lccn"] / f"{im['id']}.jpg"
        if dest.exists() and dest.stat().st_size > 0:
            ok += 1
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        for url in (
            im["iiif_3000"],
            im["iiif_3000"].replace("u/full", "v/full"),
            im["iiif_3000"].replace("u/full", "r/full"),
        ):
            try:
                with urllib.request.urlopen(
                    urllib.request.Request(url, headers=UA), timeout=120
                ) as r:
                    data = r.read()
                if data[:3] == b"\xff\xd8\xff":
                    dest.write_bytes(data)
                    im["fetched"] = url
                    im["sha256"] = hashlib.sha256(data).hexdigest()
                    ok += 1
                    break
            except Exception as e:
                im["error"] = str(e)[:120]
            time.sleep(1)
        else:
            fail += 1
        time.sleep(1)
(root / "items.jsonl").write_text("".join(json.dumps(i, ensure_ascii=False) + "\n" for i in items))
print("images ok:", ok, "failed:", fail)
