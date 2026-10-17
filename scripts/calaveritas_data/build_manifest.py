"""Write MANIFEST.tsv (path, bytes, sha256, source_url, licence) for every data file under the
calaveritas folder (scripts/, README.md and MANIFEST.tsv itself excluded).

Usage: python -I scripts/build_manifest.py <calaveritas folder>
"""

import hashlib
import json
import os
import sys

root = sys.argv[1]
API = "https://lacipi.humanidades.unam.mx/ipm/w/api.php"
LACIPI_LIC = "CC BY-NC-SA (LACIPI/UNAM site rights); private use, credit LACIPI, no redistribution of photographs"

src = {}
items_path = os.path.join(root, "lacipi", "items.jsonl")
if os.path.exists(items_path):
    for line in open(items_path, encoding="utf-8"):
        r = json.loads(line)
        src[f"lacipi/raw/items/{r['item_id']}.json"] = (
            r["url"] + f" (via {API}, revid {r['revid']})"
        )
        for f in r["files"]:
            if f["local_path"]:
                src["lacipi/" + f["local_path"]] = f["url"]

fixed = {
    "lacipi/items.jsonl": (f"derived from {API} responses in lacipi/raw/", LACIPI_LIC),
    "lacipi/raw/categorymembers.json": (
        f"{API}?action=query&list=categorymembers&cmtitle=Categoría:Calaveras_literarias",
        LACIPI_LIC,
    ),
    "lacipi/raw/imageinfo.json": (
        f"{API}?action=query&prop=imageinfo&iiprop=url|size|sha1|mime|timestamp",
        LACIPI_LIC,
    ),
    "lacipi/raw/served_files.json": (
        "HTTP response headers of the image URLs vs API imageinfo (see README)",
        LACIPI_LIC,
    ),
    "loc/BLOCKED.txt": ("local note (no download)", "n/a"),
    "hf_vpalma/STATUS.txt": ("local note (no download)", "n/a"),
    "hf_vpalma/dataset_card_README.md": (
        "https://huggingface.co/datasets/vpalma/CalaveritasVsPOEMs/blob/68b070f51529ef98feefbddf9cdca9241e996532/README.md",
        "dataset card; dataset tagged CC BY 4.0 but gated 'I agree to not redistribute this data'",
    ),
    "local_octosyllabic/ids.tsv": (
        "derived from /home/angel/dev/poesia/seeds/poetry_corpus/corpus_master/poems.jsonl (sha256 41c6a60d...) via scripts/local_corpus/",
        "metadata only (ids, authors, titles); underlying poems carry their own corpus_master licences",
    ),
}

rows = []
for dp, dns, fns in os.walk(root):
    rel_dir = os.path.relpath(dp, root)
    if rel_dir.split(os.sep)[0] == "scripts":
        continue
    for fn in fns:
        rel = os.path.normpath(os.path.join(rel_dir, fn))
        if rel in ("README.md", "MANIFEST.tsv") or fn.endswith(".part"):
            continue
        p = os.path.join(dp, fn)
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""):
                h.update(b)
        if rel in fixed:
            url, lic = fixed[rel]
        elif rel in src:
            url, lic = src[rel], LACIPI_LIC
        else:
            url, lic = "UNKNOWN", "UNKNOWN"
        rows.append((rel, os.path.getsize(p), h.hexdigest(), url, lic))

rows.sort()
with open(os.path.join(root, "MANIFEST.tsv"), "w", encoding="utf-8") as o:
    o.write("path\tbytes\tsha256\tsource_url\tlicence\n")
    for r in rows:
        o.write("\t".join(map(str, r)) + "\n")
unknown = [r[0] for r in rows if r[3] == "UNKNOWN"]
print(f"{len(rows)} files, {sum(r[1] for r in rows)} bytes; unknown source: {unknown[:10]}")
