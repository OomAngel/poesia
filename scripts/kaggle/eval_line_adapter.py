"""Kaggle notebook: the seeded sonnet benchmark with and without the line adapter.

No secrets, so ``kaggle kernels push`` starts it with no clicks: the base is the public 4-bit
file the page ships (Colby/apertus-v1.5-8b-text-Q4_K_M-GGUF), the engine comes from the public
PoesIA repository at ``POESIA_REF``, and the adapter (GGUF LoRA, converted from the PEFT
adapter on a CPU) is the private Kaggle dataset ``poesia-line-adapter-gguf``. One T4 serves the
plain file, the other the same file with ``--lora``; both run the same benchmark.

Positive controls before any score: both servers answer, and at temperature 0 the adapter
server answers a fixed prompt differently from the plain one (otherwise the adapter is not
applied and the run stops). Results: /kaggle/working/results/{plain,lora}-s{seed}-{lang}.json.
"""

import glob
import json
import os
import subprocess
import sys
import time
import urllib.request

POESIA_REF = "POESIA_REF_PLACEHOLDER"
LLAMA_CPP_REF = "f498f864f"
LANGS = ["es", "it", "de", "fr"]
SEEDS = [0, 3]
W = "/kaggle/working"


def sh(cmd, **kw):
    print("$", cmd if isinstance(cmd, str) else " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, shell=isinstance(cmd, str), **kw)


def chat(port, prompt):
    body = {
        "model": "poesia-apertus",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 40,
    }
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)["choices"][0]["message"]["content"]


def wait_ready(port):
    for _ in range(240):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=3) as r:
                if b'"ok"' in r.read():
                    return
        except OSError:
            pass
        time.sleep(5)
    raise SystemExit(f"server on {port} did not start")


def main():
    t0 = time.time()
    sh(
        f"git clone -q https://github.com/ggml-org/llama.cpp {W}/llama.cpp && "
        f"git -C {W}/llama.cpp checkout -q {LLAMA_CPP_REF}"
    )
    sh(
        f"cmake -S {W}/llama.cpp -B {W}/llama.cpp/build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=75 "
        "-DLLAMA_CURL=OFF -DLLAMA_BUILD_TESTS=OFF > /dev/null"
    )
    sh(f"cmake --build {W}/llama.cpp/build -j8 --target llama-server > /dev/null")
    print(f"built in {time.time() - t0:.0f} s", flush=True)
    sh(
        f"curl -fsSL https://github.com/OomAngel/poesia/archive/{POESIA_REF}.tar.gz | tar -xz -C {W}"
    )
    repo = glob.glob(f"{W}/poesia-*")[0]
    sh([sys.executable, "-m", "pip", "install", "-q", "-e", f"{repo}[spanish,english-scan,mlops]"])
    from huggingface_hub import hf_hub_download

    base = hf_hub_download(
        "Colby/apertus-v1.5-8b-text-Q4_K_M-GGUF",
        "apertus-v1.5-8b-text-q4_k_m.gguf",
        local_dir=f"{W}/model",
    )
    lora = glob.glob("/kaggle/input/**/line-v1.gguf", recursive=True)[0]
    server = f"{W}/llama.cpp/build/bin/llama-server"
    common = [
        "--alias",
        "poesia-apertus",
        "--jinja",
        "-ngl",
        "99",
        "-c",
        "4096",
        "-np",
        "3",
        "--host",
        "127.0.0.1",
    ]
    procs = {}
    for name, port, gpu, extra in (("plain", 8080, "0", []), ("lora", 8081, "1", ["--lora", lora])):
        log = open(f"{W}/server-{name}.log", "w")
        procs[name] = subprocess.Popen(
            [server, "-m", base, *extra, *common, "--port", str(port)],
            stdout=log,
            stderr=subprocess.STDOUT,
            env={**os.environ, "CUDA_VISIBLE_DEVICES": gpu},
        )
    for port in (8080, 8081):
        wait_ready(port)
    probe = (
        "You are writing a German poem on the theme: der Herbst.\nWrite line 1. Exactly 10 syllables. "
        "Write the line in German only, no English words. Output ONLY the single bare poetry line."
    )
    a, b = chat(8080, probe), chat(8081, probe)
    print(f"control plain: {a!r}\ncontrol lora:  {b!r}", flush=True)
    if a.strip() == b.strip():
        raise SystemExit(
            "the adapter server answers exactly like the plain one: adapter not applied"
        )
    os.makedirs(f"{W}/results", exist_ok=True)
    os.chdir(repo)
    jobs = []
    for name, port in (("plain", 8080), ("lora", 8081)):
        for lang in LANGS:
            for seed in SEEDS:
                env = {
                    **os.environ,
                    "LLM_BASE_URL": f"http://127.0.0.1:{port}/v1",
                    "LLM_NAME": "poesia-apertus",
                    "LLM_API_KEY": "x",
                    "MLFLOW_TRACKING_URI": f"sqlite:///{W}/mlflow-{name}-{lang}-{seed}.db",
                    "MLFLOW_DISABLE_AGENT_HINT": "1",
                }
                out = f"{W}/results/{name}-s{seed}-{lang}.json"
                log = open(f"{W}/results/{name}-s{seed}-{lang}.log", "w")
                jobs.append(
                    subprocess.Popen(
                        [
                            sys.executable,
                            "scripts/evaluate_adapter_mlflow.py",
                            "--openai-compat",
                            "--languages",
                            lang,
                            "--samples",
                            "3",
                            "--seed",
                            str(seed),
                            "--out",
                            out,
                        ],
                        env=env,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                    )
                )
    failed = sum(p.wait() != 0 for p in jobs)
    for p in procs.values():
        p.terminate()
    done = sorted(os.path.basename(f) for f in glob.glob(f"{W}/results/*.json"))
    print(
        f"runs {len(jobs)}, failed {failed}, results {len(done)}, {time.time() - t0:.0f} s total",
        flush=True,
    )


if __name__ == "__main__":
    main()
