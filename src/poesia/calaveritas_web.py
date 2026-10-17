"""Public Calaveritas page (PoesIA's first section): FastAPI app served behind a reverse proxy.

Routes: ``/`` -> ``/es/``; ``/es/`` and ``/en/`` (the page, same file, language set server-side);
``/static/*``; ``POST /api/calaverita`` (validate, rate-limit, write, check); ``POST /api/report``
(forward to a private GitHub issue, count toward the scoped auto-pause); ``/healthz`` (the app);
``/healthz/model`` (503 while the model is unreachable, for the probe's alert).

Nothing is stored and no names or poems are logged: stdout gets one line per request with the
status, the time taken and the model. Decisions: docs/calaveritas/DECISIONS.md.

Run locally: ``poesia-calaveritas`` (127.0.0.1:8080), or in the container with
``POESIA_CALAV_HOST=0.0.0.0``. FastAPI is imported lazily (``pip install -e '.[web]'``); no
``from __future__ import annotations`` so FastAPI can resolve the request models.
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from poesia.calaveritas import generator
from poesia.calaveritas.guard import MESSAGES, Rejection, validate_request
from poesia.calaveritas.service import ModelWatch, RateLimiter, ReportGuard, send_github_issue

STATIC = Path(__file__).parent / "calaveritas" / "static"
MAX_BODY = 4096
MAX_REPORT = 4000

ERRORS = {
    "rate_client": (
        "Ya pediste varias seguidas. Espera unos minutos.",
        "You asked for several in a row. Wait a few minutes.",
    ),
    "rate_global": (
        "Por hoy se acabaron las calaveritas. Vuelve mañana.",
        "That is all the calaveritas for today. Come back tomorrow.",
    ),
    "paused": (
        "Por ahora solo se escriben calaveritas para mascotas y para ti, sin detalle libre.",
        "For now only calaveritas for pets and for yourself are written, without free detail.",
    ),
    "unavailable": (
        "La Catrina descansa: el modelo no responde. Intenta más tarde.",
        "La Catrina is resting: the model is not answering. Try again later.",
    ),
    "quality": (
        "Esta vez no salió una calaverita con la métrica y la rima en su lugar. Intenta de nuevo o cambia los rasgos.",
        "This time no calaverita came out with its metre and rhyme in place. Try again or change the traits.",
    ),
    "floor": (
        "Con esos datos no se puede escribir una calaverita aquí. Prueba con otros rasgos.",
        "A calaverita cannot be written here with those details. Try other traits.",
    ),
    "too_large": ("La petición es demasiado grande.", "The request is too large."),
    "report_unavailable": (
        "Los reportes no están disponibles ahora. Escribe al contacto del aviso.",
        "Reports are not available right now. Use the contact in the notice.",
    ),
}


def _msg(code: str, lang: str) -> str:
    pair = ERRORS.get(code) or MESSAGES.get(code) or MESSAGES["invalid"]
    return pair[0 if lang == "es" else 1]


def _client(request: Any) -> str:
    peer = request.client.host if request.client else ""
    if peer in ("127.0.0.1", "::1") or peer.startswith(("172.", "10.")):
        fwd = request.headers.get("x-forwarded-for", "")
        if fwd:
            return fwd.split(",")[0].strip()
    return peer


def _log(event: str, **fields: Any) -> None:
    sys.stdout.write(json.dumps({"t": round(time.time()), "event": event, **fields}) + "\n")
    sys.stdout.flush()


def create_app(providers: list[generator.Provider] | None = None) -> Any:
    from fastapi import FastAPI, Request
    from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
    from fastapi.staticfiles import StaticFiles

    app = FastAPI(title="PoesIA Calaveritas", docs_url=None, redoc_url=None, openapi_url=None)
    providers = generator.providers_from_env() if providers is None else providers
    limiter = RateLimiter()
    reports = ReportGuard()
    model = ModelWatch(providers)
    page = (STATIC / "index.html").read_text(encoding="utf-8")

    @app.middleware("http")
    async def headers(request: Request, call_next):  # type: ignore[no-untyped-def]
        if int(request.headers.get("content-length") or 0) > MAX_REPORT + 1024:
            return JSONResponse({"ok": False, "code": "too_large"}, status_code=413)
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data: blob:; style-src 'self'; font-src 'self'; "
            "script-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cache-Control"] = (
            "no-store" if request.url.path.startswith("/api") else "public, max-age=600"
        )
        return response

    @app.get("/")
    def root() -> Any:
        return RedirectResponse("/es/", status_code=302)

    @app.get("/es/")
    def page_es() -> Any:
        return HTMLResponse(page.replace("{{LANG}}", "es"))

    @app.get("/en/")
    def page_en() -> Any:
        return HTMLResponse(page.replace("{{LANG}}", "en"))

    @app.get("/healthz")
    def healthz() -> dict[str, Any]:
        return {
            "status": "ok",
            "app": "calaveritas",
            "providers": len(providers),
            "risky_paused": reports.paused,
        }

    @app.get("/healthz/model")
    def healthz_model() -> Any:
        """503 while the model is unreachable, so the probe alerts (Telegram, email)."""
        ok, detail = model.status()
        return JSONResponse(
            {"model": "ok" if ok else "down", "detail": detail}, status_code=200 if ok else 503
        )

    @app.post("/api/calaverita")
    async def calaverita(request: Request) -> Any:
        t0 = time.monotonic()
        body = await request.body()
        lang = "es"
        if len(body) > MAX_BODY:
            return JSONResponse(
                {"ok": False, "code": "too_large", "message": _msg("too_large", lang)},
                status_code=413,
            )
        try:
            raw = json.loads(body or b"{}")
            lang = raw.get("language") if raw.get("language") in ("es", "en") else "es"
            req = validate_request(raw)
        except (ValueError, AttributeError):
            return JSONResponse(
                {"ok": False, "code": "invalid", "message": _msg("invalid", lang)}, status_code=400
            )
        except Rejection as r:
            _log("rejected", code=r.code)
            return JSONResponse(
                {"ok": False, "code": r.code, "message": r.message(lang)}, status_code=400
            )
        if reports.blocks(req):
            return JSONResponse(
                {"ok": False, "code": "paused", "message": _msg("paused", lang)}, status_code=503
            )
        over = limiter.check(_client(request))
        if over:
            code = "rate_client" if over == "client" else "rate_global"
            return JSONResponse(
                {"ok": False, "code": code, "message": _msg(code, lang)}, status_code=429
            )
        from starlette.concurrency import run_in_threadpool

        try:
            poem = await run_in_threadpool(generator.write, req, providers)
        except generator.GenerationError as e:
            _log("failed", code=e.code, s=round(time.monotonic() - t0, 1))
            if e.code == "unavailable":
                model.record(False, "a request found no provider answering")
            status = 503 if e.code == "unavailable" else 422
            return JSONResponse(
                {"ok": False, "code": e.code, "message": _msg(e.code, lang)}, status_code=status
            )
        _log("written", model=poem.model, stanzas=len(poem.stanzas), s=round(poem.elapsed_s, 1))
        model.record(True, "a request was answered")
        return {"ok": True, "poem": poem.as_dict(), "name": req.name, "tone": req.tone.value}

    @app.post("/api/report")
    async def report(request: Request) -> Any:
        body = await request.body()
        try:
            raw = json.loads(body or b"{}")
        except ValueError:
            raw = {}
        lang = raw.get("language") if raw.get("language") in ("es", "en") else "es"
        text = str(raw.get("poem", ""))[:MAX_REPORT]
        reason = str(raw.get("reason", ""))[:500]
        if not text.strip():
            return JSONResponse(
                {"ok": False, "code": "invalid", "message": _msg("invalid", lang)}, status_code=400
            )
        if limiter.check("report:" + _client(request)):
            return JSONResponse(
                {"ok": False, "code": "rate_client", "message": _msg("rate_client", lang)},
                status_code=429,
            )
        started = reports.add()
        sent = send_github_issue(
            "Reporte de calaverita",
            f"Motivo: {reason or '(sin motivo)'}\n\n```\n{text}\n```",
            ["report"],
        )
        if started:
            send_github_issue(
                "AUTO-PAUSE: rutas de riesgo pausadas",
                "Tres reportes en una hora. Pausado: detalle libre, personas privadas, figuras públicas y "
                "famosos fallecidos. Para reanudar: reiniciar el contenedor tras revisar.",
                ["auto-pause"],
            )
        _log("report", delivered=sent, paused=reports.paused)
        if not sent:
            return JSONResponse(
                {
                    "ok": False,
                    "code": "report_unavailable",
                    "message": _msg("report_unavailable", lang),
                },
                status_code=503,
            )
        return {"ok": True}

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app


def main() -> None:
    import uvicorn

    host = os.environ.get("POESIA_CALAV_HOST", "127.0.0.1")
    port = int(os.environ.get("POESIA_CALAV_PORT", "8080"))
    uvicorn.run(
        create_app(),
        host=host,
        port=port,
        proxy_headers=False,
        access_log=False,
        server_header=False,
    )


if __name__ == "__main__":
    main()
