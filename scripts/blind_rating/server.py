#!/usr/bin/env python3
"""Tiny rating server for the blind pair pages (standard library only, no poems in git).

Serves ``index.html`` and ``pairs.json`` from the data folder and stores ratings as JSON lines.
Meant to run in a container on the Veriton behind ``tailscale serve`` (tailnet only):

    docker run -d --name poesia-rating --restart unless-stopped --user 1000:1000 \
      -p 127.0.0.1:8095:8095 -v ~/poesia-rating:/data \
      -v ~/poesia-rating/server.py:/app/server.py:ro --entrypoint python \
      poesia-apertus-web:veriton /app/server.py

Paths are accepted with or without a leading ``/rate`` (Tailscale may or may not strip a mount
path). API: GET ``api/ratings`` (latest rating per set and id), POST ``api/rate``.
"""

from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DATA = Path(os.environ.get("RATING_DATA", "/data"))
PORT = int(os.environ.get("RATING_PORT", "8095"))
PREFIX = "/rate"
MAX_BODY = 8192
PICKS = {"A", "B", "same"}
LOCK = threading.Lock()


def _pairs() -> dict:
    return json.loads((DATA / "pairs.json").read_text(encoding="utf-8"))


def _valid_ids() -> set[tuple[str, str]]:
    return {(s["id"], p["id"]) for s in _pairs()["sets"] for p in s["pairs"]}


def _latest() -> dict:
    """Latest rating per (set, id): later lines win."""
    out: dict = {}
    path = DATA / "ratings.jsonl"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
                out.setdefault(r["set"], {})[r["id"]] = r
            except (ValueError, KeyError):
                continue
    return out


def _clean(rec: dict) -> dict | None:
    if not isinstance(rec, dict) or (rec.get("set"), rec.get("id")) not in _valid_ids():
        return None
    if rec.get("pick") not in PICKS:
        return None
    reasons = [str(x)[:40] for x in rec.get("reasons", []) if isinstance(x, str)][:12]
    return {
        "set": rec["set"],
        "id": rec["id"],
        "pick": rec["pick"],
        "reasons": reasons,
        "note": str(rec.get("note", ""))[:2000],
        "at": str(rec.get("at", ""))[:40],
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "poesia-rating"

    def _path(self) -> str:
        p = self.path.split("?", 1)[0]
        if p == PREFIX:
            return PREFIX
        return p[len(PREFIX) :] if p.startswith(PREFIX + "/") else p

    def _send(self, code: int, body: bytes, ctype: str, extra: dict | None = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        p = self._path()
        if p == PREFIX:
            self._send(301, b"", "text/plain", {"Location": PREFIX + "/"})
        elif p in ("/", "/index.html"):
            self._send(200, (DATA / "index.html").read_bytes(), "text/html; charset=utf-8")
        elif p == "/pairs.json":
            self._send(200, (DATA / "pairs.json").read_bytes(), "application/json")
        elif p == "/api/ratings":
            self._send(200, json.dumps(_latest()).encode(), "application/json")
        elif p == "/healthz":
            self._send(200, b"ok", "text/plain")
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self) -> None:  # noqa: N802
        if self._path() != "/api/rate":
            return self._send(404, b"not found", "text/plain")
        n = int(self.headers.get("Content-Length", "0") or 0)
        if n <= 0 or n > MAX_BODY:
            return self._send(413, b"bad size", "text/plain")
        try:
            rec = _clean(json.loads(self.rfile.read(n)))
        except ValueError:
            rec = None
        if rec is None:
            return self._send(400, b"bad rating", "text/plain")
        with LOCK, (DATA / "ratings.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self._send(200, b'{"ok":true}', "application/json")

    def log_message(self, fmt: str, *args) -> None:  # no poem or note text in logs
        print(self.address_string(), fmt % args, flush=True)


if __name__ == "__main__":
    # inside the container; docker publishes the port on the host's loopback only
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()  # noqa: S104
