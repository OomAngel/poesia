"""Limits, reports and the scoped auto-pause for the public Calaveritas page. All in memory.

Nothing about a visitor is stored: the rate limiter keeps counters under a salted hash of the
client address (the salt changes daily and lives only in this process), and forgets them after a
day. Reports are forwarded to a private GitHub issue (``CALAVERITAS_GITHUB_REPO`` and
``CALAVERITAS_GITHUB_TOKEN``, a fine-grained token with issue write access to that repo only) and
not kept here. Three reports within an hour pause the risky paths (free-text detail, private
recipients, public figures, the late famous) until the operator resumes them; pets and "myself"
with chips keep working, so a few hostile reports cannot take the whole page down.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import secrets
import threading
import time
import urllib.error
import urllib.request
from collections import deque
from dataclasses import dataclass, field

from .options import PRIVATE, Recipient, Request

RISKY = PRIVATE | {Recipient.PUBLICA, Recipient.FALLECIDA}


@dataclass
class Limits:
    per_client_window: int = 5  # requests per client per 10 minutes
    per_client_day: int = 25
    global_day: int = 2000
    window_s: int = 600


class RateLimiter:
    def __init__(self, limits: Limits | None = None) -> None:
        self.limits = limits or Limits()
        self._lock = threading.Lock()
        self._salt = secrets.token_bytes(16)
        self._day = dt.date.today()
        self._recent: dict[str, deque[float]] = {}
        self._daily: dict[str, int] = {}
        self._global = 0

    def _key(self, client: str) -> str:
        return hashlib.sha256(self._salt + client.encode()).hexdigest()[:20]

    def _roll(self) -> None:
        today = dt.date.today()
        if today != self._day:
            self._day, self._salt = today, secrets.token_bytes(16)
            self._recent.clear()
            self._daily.clear()
            self._global = 0

    def check(self, client: str, now: float | None = None) -> str | None:
        """Count one request; return "client" or "global" when over a limit, else None."""
        now = time.monotonic() if now is None else now
        with self._lock:
            self._roll()
            if self._global >= self.limits.global_day:
                return "global"
            key = self._key(client)
            q = self._recent.setdefault(key, deque())
            while q and now - q[0] > self.limits.window_s:
                q.popleft()
            if (
                len(q) >= self.limits.per_client_window
                or self._daily.get(key, 0) >= self.limits.per_client_day
            ):
                return "client"
            q.append(now)
            self._daily[key] = self._daily.get(key, 0) + 1
            self._global += 1
            return None


@dataclass
class ReportGuard:
    threshold: int = 3
    window_s: int = 3600
    times: deque = field(default_factory=deque)
    paused_since: float | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def add(self, now: float | None = None) -> bool:
        """Record a report; return True if this report started a pause."""
        now = time.monotonic() if now is None else now
        with self._lock:
            self.times.append(now)
            while self.times and now - self.times[0] > self.window_s:
                self.times.popleft()
            if self.paused_since is None and len(self.times) >= self.threshold:
                self.paused_since = now
                return True
            return False

    @property
    def paused(self) -> bool:
        return self.paused_since is not None or os.environ.get("CALAVERITAS_PAUSE_RISKY") == "1"

    def resume(self) -> None:
        with self._lock:
            self.paused_since = None
            self.times.clear()

    def blocks(self, request: Request) -> bool:
        return self.paused and (request.recipient in RISKY or bool(request.detail))


def send_github_issue(title: str, body: str, labels: list[str]) -> bool:
    repo = os.environ.get("CALAVERITAS_GITHUB_REPO", "")
    token = os.environ.get("CALAVERITAS_GITHUB_TOKEN", "")
    if not repo or not token:
        return False
    req = urllib.request.Request(  # noqa: S310 - fixed GitHub API host
        f"https://api.github.com/repos/{repo}/issues",
        data=json.dumps({"title": title[:200], "body": body[:60000], "labels": labels}).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "poesia-calaveritas",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
            return 200 <= resp.status < 300
    except OSError:
        return False


class ModelWatch:
    """Is the model reachable? So the probe can alert when the CSCS key or service dies.

    ``/healthz`` stayed "ok" while every request failed (it only checks the app). This asks the
    primary provider for its model list (authenticated, no tokens spent) at most every
    ``ttl`` seconds; real requests update it in between (a success marks it up, an
    "unavailable" failure marks it down). Visitors already get "La Catrina descansa".
    """

    def __init__(self, providers: list, ttl: float = 600.0) -> None:
        self._providers = providers
        self._ttl = ttl
        self._lock = threading.Lock()
        self._ok: bool | None = None
        self._detail = "not checked yet"
        self._at = 0.0

    def record(self, ok: bool, detail: str) -> None:
        with self._lock:
            self._ok, self._detail, self._at = ok, detail, time.monotonic()

    def _probe(self) -> tuple[bool, str]:
        if not self._providers:
            return False, "no provider configured"
        p = self._providers[0]
        req = urllib.request.Request(  # noqa: S310 - URL comes from the operator's configuration
            f"{p.url.rstrip('/')}/models",
            headers={"Authorization": f"Bearer {p.key}", "User-Agent": "poesia-calaveritas/1.0"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
                return 200 <= resp.status < 300, f"models HTTP {resp.status}"
        except urllib.error.HTTPError as e:
            return False, f"models HTTP {e.code}"
        except OSError as e:
            return False, f"models unreachable ({type(e).__name__})"

    def status(self) -> tuple[bool, str]:
        with self._lock:
            fresh = self._ok is not None and time.monotonic() - self._at < self._ttl
            if fresh:
                return bool(self._ok), self._detail
        ok, detail = self._probe()
        self.record(ok, detail)
        return ok, detail
