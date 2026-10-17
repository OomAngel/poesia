"""Kaggle kernel: the calaveritas engine on gpt-oss-20b, for the blind model A/B (2026-10-09).

Runs on a private Kaggle notebook with 2 x T4 and Internet on, no secrets (gpt-oss-20b is not gated,
so an API-pushed run works). Steps:
1. Python 3.13 through uv (the project pins 3.13) and the scanner libraries from pip.
2. The engine from the private dataset `calaveritas-engine` (engine.tar.gz: the calaveritas and
   phonology modules, word lists, generate_batch.py, the few-shot file; poems never public).
3. Ollama, one server per T4, model gpt-oss:20b.
4. Preflight: the engine's own Provider asks for one quatrain and one editor-style number with each
   candidate reasoning setting; the first setting that answers 3 of 3 calls is used. If none does,
   the run stops here.
5. The first 40 requests of the review batch (seed 20261009, the same requests Apertus answered),
   split across the two GPUs; one JSONL per GPU in /kaggle/working, plus run.log.
Names in the batch are invented first names, generic roles and famous people who have died.
"""

from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request

# Kaggle defaults; the AB_* variables let the same file run as a local smoke test (against CSCS,
# without Ollama) before any remote GPU time is spent.
WORK = os.environ.get("AB_WORK", "/kaggle/working")
INPUT = os.environ.get("AB_INPUT", "/kaggle/input")
ENGINE = os.environ.get("AB_ENGINE", "/tmp/engine")
VENV = os.environ.get("AB_VENV", "/tmp/venv")
NLTK = os.environ.get(
    "AB_NLTK", os.path.expanduser("~/nltk_data")
)  # NLTK refuses world-writable dirs
MODELS = "/tmp/ollama-models"
MODEL = os.environ.get("AB_MODEL", "gpt-oss:20b")
N_ONLY = int(os.environ.get("AB_N", "40"))
PORTS = (11434, 11435)
URLS = os.environ.get("AB_URLS", ",".join(f"http://127.0.0.1:{p}/v1" for p in PORTS)).split(",")
TAG = os.environ.get("AB_TAG", "go20lite-20261009")
# lite engine (generator.py): the full engine needs ~250 calls per poem, which a T4 cannot serve
PROFILE = os.environ.get("AB_PROFILE", "lite")
LOG = open(f"{WORK}/run.log", "a", buffering=1)  # noqa: SIM115 - one log for the whole run
T0 = time.time()


def log(msg: str) -> None:
    line = f"{time.time() - T0:7.0f}s {msg}"
    print(line, flush=True)
    LOG.write(line + "\n")


def sh(cmd: str, check: bool = True, env: dict | None = None) -> str:
    log(f"$ {cmd}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=env)  # noqa: S602
    out = (r.stdout + r.stderr).strip()
    if out:
        log(out[-1500:])
    if check and r.returncode != 0:
        log(f"FAILED ({r.returncode}): {cmd}")
        sys.exit(1)
    return r.stdout


def setup_python() -> str:
    sh("pip install -q uv")
    sh(f"uv venv --clear {VENV} --python 3.13")
    py = f"{VENV}/bin/python"
    sh(f"uv pip install --python {py} -q fonemas silabeador pronouncing g2p_en nltk")
    os.makedirs(NLTK, mode=0o700, exist_ok=True)
    os.chmod(NLTK, 0o700)
    # Kaggle's egress goes through its own proxy, which NLTK >= 3.10 refuses unless told to trust it.
    env = dict(os.environ, NLTK_ALLOW_PROXIED_URLOPEN="1", NLTK_DATA=NLTK)
    sh(f"{py} -m nltk.downloader -q -d {NLTK} averaged_perceptron_tagger_eng cmudict", env=env)
    sh(  # the downloader exits 0 even when it failed, so prove the data loads
        f"{py} -c \"import nltk; nltk.data.find('corpora/cmudict'); "
        f"nltk.data.find('taggers/averaged_perceptron_tagger_eng'); print('nltk data ok')\"",
        env=env,
    )
    return py


def unpack_engine() -> None:
    tars = glob.glob(f"{INPUT}/**/engine.tar.gz", recursive=True)
    if tars:
        os.makedirs(ENGINE, exist_ok=True)
        with tarfile.open(tars[0]) as tf:
            tf.extractall(ENGINE, filter="data")
    else:  # Kaggle may have unpacked the archive itself
        found = glob.glob(f"{INPUT}/**/generate_batch.py", recursive=True)
        if not found:
            log(f"FAILED: engine.tar.gz not found in {INPUT}")
            sys.exit(1)
        # generate_batch.py sits at the archive's root, next to src/, fewshot.json and COMMIT
        shutil.copytree(os.path.dirname(found[0]), ENGINE, dirs_exist_ok=True)
    log("engine commit: " + open(f"{ENGINE}/COMMIT").read().strip())


def wait_up(port: int, seconds: int = 120) -> None:
    for _ in range(seconds):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/version", timeout=2)  # noqa: S310
            return
        except OSError:
            time.sleep(1)
    log(f"FAILED: ollama on {port} did not start")
    sys.exit(1)


def setup_ollama() -> None:
    sh("nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv")
    sh("apt-get -qq update && apt-get -qq install -y zstd", check=False)
    sh("curl -fsSL https://ollama.com/install.sh | sh")
    os.makedirs(MODELS, exist_ok=True)
    for gpu, port in enumerate(PORTS):
        env = dict(
            os.environ,
            CUDA_VISIBLE_DEVICES=str(gpu),
            OLLAMA_HOST=f"127.0.0.1:{port}",
            OLLAMA_MODELS=MODELS,
            OLLAMA_NUM_PARALLEL="4",
            OLLAMA_CONTEXT_LENGTH="6144",
            OLLAMA_KEEP_ALIVE="-1",
        )
        subprocess.Popen(  # noqa: S603
            ["ollama", "serve"],
            env=env,
            stdout=open(f"{WORK}/ollama-{port}.log", "w"),  # noqa: SIM115
            stderr=subprocess.STDOUT,
        )
        wait_up(port)
    sh(f"OLLAMA_HOST=127.0.0.1:{PORTS[0]} ollama pull {MODEL}")
    sh("ollama --version", check=False)


PREFLIGHT = r"""
import json, sys, time
sys.path.insert(0, sys.argv[5] + "/src")
from poesia.calaveritas.generator import Provider
url, extra, floor, model = sys.argv[1], json.loads(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
p = Provider(model, url, model, "", True, extra, floor)
asks = [
    [{"role": "user", "content": "Escribe una cuarteta octosílaba de calaverita sobre Lupita, que siempre llega tarde. Solo los cuatro versos."}],
    [{"role": "system", "content": "Responde SOLO con un número."}, {"role": "user", "content": "¿Cuál es mejor, 1 o 2? 1) Andaba la Calavera 2) La calavera andaba"}],
    [{"role": "user", "content": "Escribe UN verso octosílabo que rime con «escalera». Solo el verso."}],
]
# one raw call first: the engine's Provider returns only the text, this shows tokens and speed
import urllib.request
body = {"model": model, "messages": asks[0], "temperature": 0.7, "max_tokens": max(160, floor), **extra}
t = time.time()
try:
    req = urllib.request.Request(url.rstrip("/") + "/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=300).read())
    dt = time.time() - t
    msg = r["choices"][0]["message"]
    reasoning = msg.get("reasoning") or msg.get("reasoning_content") or ""
    out_tokens = (r.get("usage") or {}).get("completion_tokens", 0)
    print(json.dumps({"speed": round(out_tokens / dt, 1), "s": round(dt, 1), "out_tokens": out_tokens,
                      "reasoning_chars": len(reasoning), "content": (msg.get("content") or "")[:200]}, ensure_ascii=False))
except Exception as e:  # noqa: BLE001
    print("RAW CALL FAILED", type(e).__name__, e)
ok = 0
for msgs in asks:
    t = time.time()
    try:
        out = p.chat(msgs, 0.7)
    except Exception as e:  # noqa: BLE001
        out = f"ERROR {type(e).__name__}: {e}"
    good = bool(out.strip()) and not out.startswith("ERROR")
    ok += good
    print(json.dumps({"ok": good, "s": round(time.time() - t, 1), "out": out[:300]}, ensure_ascii=False))
print("SCORE", ok)
"""


def preflight(py: str) -> tuple[dict, int]:
    path = "/tmp/preflight.py"
    open(path, "w").write(PREFLIGHT)
    # the same call limit as the batch: a T4 answers a verse call with reasoning in well over 25 s
    env = dict(os.environ, CALAVERITAS_CALL_TIMEOUT="180", NLTK_DATA=NLTK)
    for extra, floor in (
        ({"reasoning_effort": "low"}, 1000),
        ({"reasoning_effort": "low"}, 2500),
        ({}, 2500),
    ):
        for url in URLS:  # warm every server (the first call loads the model onto the GPU)
            out = sh(
                f"{py} {path} {url} '{json.dumps(extra)}' {floor} {MODEL} {ENGINE}",
                check=False,
                env=env,
            )
            if "SCORE 3" not in out:
                break
        else:
            log(f"preflight passed with extra={extra} min_tokens={floor}")
            return extra, floor
        log(f"preflight failed with extra={extra} min_tokens={floor}")
    log("FAILED: no reasoning setting gave non-empty answers; stopping before the batch")
    sys.exit(1)


def run_batch(py: str, extra: dict, floor: int) -> None:
    env = dict(
        os.environ,
        PYTHONPATH=f"{ENGINE}/src",
        CALAVERITAS_FEWSHOT=f"{ENGINE}/fewshot.json",
        CALAVERITAS_CALL_TIMEOUT="180",
        CALAVERITAS_TOTAL_BUDGET="2400",
        CALAVERITAS_PROFILE=PROFILE,
        NLTK_DATA=NLTK,
    )
    procs = []
    for shard, url in enumerate(URLS):
        cmd = [
            py, f"{ENGINE}/generate_batch.py", f"{WORK}/batch-{TAG}-s{shard}.jsonl",
            "--url", url, "--model", MODEL,
            "--n", "200", "--n-only", str(N_ONLY), "--workers", "1",
            "--tag", TAG, "--extra", json.dumps(extra),
            "--min-tokens", str(floor), "--shard", f"{shard}/{len(URLS)}",
        ]  # fmt: skip
        log("$ " + " ".join(cmd))
        procs.append(
            subprocess.Popen(cmd, env=env, stdout=LOG, stderr=subprocess.STDOUT)  # noqa: S603
        )
    deadline = T0 + 11 * 3600  # Kaggle stops a session at 12 h
    while any(p.poll() is None for p in procs):
        if time.time() > deadline:
            log("time limit: stopping the batch (rows written so far are kept)")
            for p in procs:
                p.kill()
            break
        time.sleep(60)
        # count poems, not rows: on 2026-10-09 "19/40" hid that every row so far had failed
        rows = [json.loads(x) for f in glob.glob(f"{WORK}/batch-{TAG}-s*.jsonl") for x in open(f)]
        ok = sum("poem" in r for r in rows)
        log(f"progress: {len(rows)}/{N_ONLY} done, {ok} poems, {len(rows) - ok} failed")
    log("exit codes: " + ", ".join(str(p.returncode) for p in procs))


def main() -> None:
    py = setup_python()
    unpack_engine()
    if not os.environ.get("AB_SKIP_OLLAMA"):
        setup_ollama()
    extra, floor = preflight(py)
    run_batch(py, extra, floor)
    sh("nvidia-smi --query-gpu=memory.used --format=csv", check=False)
    log("done")


if __name__ == "__main__":
    main()
