"""Print counts for lacipi/items.jsonl (for README): items, distinct incipits, signed/unsigned,
dates, collections, files and bytes on disk. No verse text is printed (incipits are counted, not shown).

Usage: python -I scripts/summarize_lacipi.py <calaveritas folder>
"""

import collections
import json
import os
import re
import sys

root = sys.argv[1]
items = [json.loads(l) for l in open(os.path.join(root, "lacipi", "items.jsonl"), encoding="utf-8")]
c = collections.Counter()
names = collections.Counter()
coll = collections.Counter()
for r in items:
    c["items"] += 1
    c[r["signature_status"]] += 1
    if r["signature_status"] == "signed":
        names[r["names_declared"]] += 1
    coll[r["collection_consulted"]] += 1
    m = re.search(r"\b(1[89]\d\d)\b", r["year"] or "")
    y = int(m.group(1)) if m else None
    c["dated"] += y is not None
    if r["signature_status"] == "unsigned":
        if y is None:
            c["unsigned_undated"] += 1
        elif 1880 <= y <= 1928:
            c["unsigned_dated_1880_1928"] += 1
        else:
            c["unsigned_dated_other"] += 1
    c["transcription_pages"] += len(r["transcription_pages"])
    c["transcription_pages_nonempty"] += r["transcribed_pages"]
    for f in r["files"]:
        c["files_listed"] += 1
        if f["local_path"] and os.path.exists(os.path.join(root, "lacipi", f["local_path"])):
            c["files_on_disk"] += 1
            c["bytes_on_disk"] += os.path.getsize(os.path.join(root, "lacipi", f["local_path"]))
        c["bytes_listed"] += f["bytes"] or 0
        c[f"mime {f['mime']}"] += 1
c["distinct_incipits"] = len({(r["incipit"] or "").strip().lower() for r in items})
for k, v in c.items():
    print(f"{k}\t{v}")
print("signed names_declared:", dict(names))
print("collections:", dict(coll))
