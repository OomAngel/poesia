"""Kaggle notebook: QLoRA adapter for Apertus v1.5 8B on teacher-written poem lines.

Data: the private Kaggle dataset made from ``scripts/distill_line_data.py`` output (chat
messages: the page's one-line system message, the line or repair prompt, the accepted line).
Runs on Kaggle's 2 x T4 with DDP (270 tokens/s measured 2026-10-08,
career-assets hack-apertus-kaggle-bench). Lessons applied (docs/RETRAINING_PLAN_2026-10.md):

- Loss on the answer only, and the answer's end-of-turn token keeps its label: from July to
  6 Oct no adapter learned to stop, because padding equal to EOS masked the real end token.
- Examples have the exact shape the page sends; whole-poem training failed on line prompts.
- ``model.train()`` after loading (checkpointing needs training mode) and no fp32 upcast of the
  131k-word embeddings (3 GB, no gain); one sequence per GPU.

Needs the Kaggle secret ``HF_TOKEN`` (gated model) and Internet on; secrets reach only runs
started in the editor (Save Version -> Save & Run All), not ``kaggle kernels push`` runs.
Writes /kaggle/working/adapter/ (PEFT) and train_log.json.
"""

import json
import os
import subprocess
import sys

OUT = "/kaggle/working"
WORKER = r"""
import json, math, os, random, sys, time
import torch, torch.distributed as dist
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

MODEL, DATA, OUT = os.environ["MODEL"], os.environ["DATA"], os.environ["OUT"]
EPOCHS, LR, ACCUM, MAXLEN = float(os.environ["EPOCHS"]), float(os.environ["LR"]), int(os.environ["ACCUM"]), int(os.environ["MAXLEN"])
# bf16 where the GPU has it (L4, A100): Apertus overflows fp16 (NaN loss from step 1 on an L4,
# 2026-10-09, as the f16 KL base did on 10-08). T4 (Kaggle) has no bf16: fp16 with the scaler.
DT = torch.bfloat16 if os.environ.get("DTYPE", "fp16") == "bf16" else torch.float16
ddp = int(os.environ.get("WORLD_SIZE", "1")) > 1
rank = int(os.environ.get("LOCAL_RANK", "0"))
if ddp:
    dist.init_process_group("nccl")
torch.cuda.set_device(rank)
world = dist.get_world_size() if ddp else 1

tok = AutoTokenizer.from_pretrained(MODEL)
rows = [json.loads(l) for l in open(DATA, encoding="utf-8") if l.strip()]
examples = []
for r in rows:
    msgs = r["messages"]
    # Render to text, then tokenise: apply_chat_template(tokenize=True) returns a BatchEncoding
    # in transformers 5, and comparing that against ids kept 0 of 1,160 examples (2026-10-09).
    prompt_text = tok.apply_chat_template(msgs[:-1], add_generation_prompt=True, tokenize=False)
    full_text = tok.apply_chat_template(msgs, tokenize=False)
    prompt_ids = tok(prompt_text, add_special_tokens=False)["input_ids"]
    full_ids = tok(full_text, add_special_tokens=False)["input_ids"]
    if full_ids[: len(prompt_ids)] != prompt_ids or len(full_ids) > MAXLEN:
        continue  # template mismatch or too long: skip rather than train on a shifted mask
    labels = [-100] * len(prompt_ids) + full_ids[len(prompt_ids):]  # the answer and its end token
    examples.append((full_ids, labels, r.get("language", "")))
random.Random(0).shuffle(examples)
n_eval = max(20, len(examples) // 20)
evals, train = examples[:n_eval], examples[n_eval:]
if rank == 0:
    print(f"examples {len(examples)} (skipped {len(rows) - len(examples)}), train {len(train)}, eval {len(evals)}", flush=True)

bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True,
                         bnb_4bit_compute_dtype=DT)
model = AutoModelForCausalLM.from_pretrained(MODEL, quantization_config=bnb, dtype=DT,
                                             device_map={"": rank})
model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True,
                                        gradient_checkpointing_kwargs={"use_reentrant": False})
for p in model.parameters():  # no fp32 upcast of the embeddings (3 GB, no gain)
    if p.dtype == torch.float32 and p.ndim == 2 and p.shape[0] > 100000:
        p.data = p.data.to(DT)
model = get_peft_model(model, LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, bias="none", task_type="CAUSAL_LM",
                                         target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "up_proj", "down_proj"]))
model.train()
core = model
if ddp:
    model = torch.nn.parallel.DistributedDataParallel(model, device_ids=[rank])
opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=LR, weight_decay=0.0)
mine = train[rank::world]
steps = math.ceil(len(mine) * EPOCHS / ACCUM)
sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, (s + 1) / 20) * max(0.0, 1 - s / max(steps, 1)))
scaler = torch.amp.GradScaler("cuda", enabled=DT == torch.float16)

def loss_of(ids, labels):
    x = torch.tensor([ids], device=rank); y = torch.tensor([labels], device=rank)
    with torch.autocast("cuda", dtype=DT):
        return model(input_ids=x, labels=y).loss

def evaluate():
    model.eval(); tot = 0.0
    with torch.no_grad():
        for ids, labels, _ in evals[rank::world]:
            tot += loss_of(ids, labels).item()
    model.train()
    t = torch.tensor([tot, len(evals[rank::world])], device=rank)
    if ddp: dist.all_reduce(t)
    return (t[0] / t[1]).item()

log = {"examples": len(examples), "train": len(train), "eval": len(evals), "epochs": EPOCHS, "lr": LR,
       "accum": ACCUM, "world": world, "eval_loss": [], "train_loss": []}
log["eval_loss"].append((0, evaluate()))
if not math.isfinite(log["eval_loss"][0][1]):
    raise SystemExit(f"eval loss {log['eval_loss'][0][1]} before training: numeric overflow, stopping")
if rank == 0:
    print(f"eval loss before training {log['eval_loss'][0][1]:.3f}", flush=True)
bad = 0
t0 = time.time(); step = 0; seen = 0; run = 0.0
order = [i for _ in range(math.ceil(EPOCHS)) for i in random.Random(1).sample(range(len(mine)), len(mine))]
order = order[: int(len(mine) * EPOCHS)]
for k, i in enumerate(order):
    ids, labels, _ = mine[i]
    loss = loss_of(ids, labels) / ACCUM
    scaler.scale(loss).backward(); run += loss.item(); seen += len(ids)
    if (k + 1) % ACCUM == 0 or k + 1 == len(order):
        scaler.unscale_(opt); torch.nn.utils.clip_grad_norm_(core.parameters(), 1.0)
        scaler.step(opt); scaler.update(); opt.zero_grad(set_to_none=True); sched.step(); step += 1
        log["train_loss"].append((step, run))
        bad = bad + 1 if not math.isfinite(run) else 0
        if bad >= 3:
            raise SystemExit(f"loss not finite for 3 optimiser steps (step {step}): stopping")
        run = 0.0
        if rank == 0 and step % 10 == 0:
            print(f"step {step}/{steps} loss {log['train_loss'][-1][1]:.3f} tok/s/gpu {seen / (time.time() - t0):.0f}", flush=True)
        if step % 100 == 0 or step == steps:
            ev = evaluate(); log["eval_loss"].append((step, ev))
            if rank == 0: print(f"eval loss {ev:.3f}", flush=True)
log["seconds"] = time.time() - t0
if rank == 0:
    core.save_pretrained(f"{OUT}/adapter")
    tok.save_pretrained(f"{OUT}/adapter")
    json.dump(log, open(f"{OUT}/train_log.json", "w"), indent=1)
    print("saved adapter", flush=True)
if ddp:
    dist.destroy_process_group()
"""


def sh(cmd, env=None):
    print("$", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, env={**os.environ, **(env or {})})


if __name__ == "__main__":
    from kaggle_secrets import UserSecretsClient  # type: ignore[import-not-found]

    os.environ["HF_TOKEN"] = UserSecretsClient().get_secret("HF_TOKEN")
    sh(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-q",
            "-U",
            "transformers",
            "peft",
            "accelerate",
            "bitsandbytes",
        ]
    )
    from huggingface_hub import snapshot_download

    model_dir = snapshot_download(
        "andreasmartin/apertus-v1.5-8b-text", local_dir="/kaggle/tmp/model"
    )
    data = next(
        os.path.join(root, f)
        for root, _d, files in os.walk("/kaggle/input")
        for f in files
        if f.endswith(".jsonl")
    )
    with open(f"{OUT}/worker.py", "w") as fh:
        fh.write(WORKER)
    env = {
        "MODEL": model_dir,
        "DATA": data,
        "OUT": OUT,
        "EPOCHS": "2",
        "LR": "1e-4",
        "ACCUM": "8",
        "MAXLEN": "1024",
    }
    sh(["torchrun", "--nproc_per_node", "2", f"{OUT}/worker.py"], env)
    print(json.dumps(json.load(open(f"{OUT}/train_log.json"))["eval_loss"]), flush=True)
