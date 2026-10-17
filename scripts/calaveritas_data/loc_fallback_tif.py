"""For LoC images whose IIIF derivative 404s: fetch the master TIFF, keep a 3000-px-wide JPEG (quality 90)
next to the others, and record source + sha256 in items.jsonl. The TIFF itself is not kept.
Run with the poesia env (Pillow): python -I loc_fallback_tif.py <calaveritas dir>"""

import hashlib
import io
import json
import sys
import time
import urllib.request
from pathlib import Path

from PIL import Image

Image.MAX_IMAGE_PIXELS = None
root = Path(sys.argv[1]) / "loc"
items = [json.loads(l) for l in open(root / "items.jsonl")]
UA = {"User-Agent": "Mozilla/5.0 (PoesIA calaveritas research; private use)"}
for it in items:
    for im in it["images"]:
        dest = root / "images" / it["lccn"] / f"{im['id']}.jpg"
        if dest.exists() and dest.stat().st_size > 0:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            with urllib.request.urlopen(
                urllib.request.Request(im["master_tif"], headers=UA), timeout=300
            ) as r:
                raw = r.read()
            img = Image.open(io.BytesIO(raw))
            img.load()
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            if img.width > 3000:
                img = img.resize((3000, round(img.height * 3000 / img.width)), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=90)
            data = buf.getvalue()
            dest.write_bytes(data)
            im.update(
                fetched=im["master_tif"] + " (downscaled to 3000 px JPEG)",
                sha256=hashlib.sha256(data).hexdigest(),
                master_bytes=len(raw),
            )
            im.pop("error", None)
            print("ok", it["lccn"], im["id"], len(raw), "->", len(data))
        except Exception as e:
            im["error"] = str(e)[:160]
            print("FAIL", it["lccn"], im["id"], e)
        time.sleep(1)
(root / "items.jsonl").write_text("".join(json.dumps(i, ensure_ascii=False) + "\n" for i in items))
