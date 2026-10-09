# Kaggle: the line adapter

`train_line_adapter.py` trains a QLoRA adapter for Apertus v1.5 8B on Kaggle's 2 × T4 from the
teacher-written lines of `scripts/distill_line_data.py` (see its docstring for the filters).

1. Data as a **private** Kaggle dataset `angelmarquezaguilar/poesia-distill-lines`
   (`kaggle datasets create -p <folder>` with a `dataset-metadata.json`; new versions with
   `kaggle datasets version`). Lines written by Apertus 70B on CSCS, not the poetry corpus.
2. Push the notebook (`kaggle kernels push -p scripts/kaggle`), then **start it from the
   editor** (Save Version → Save & Run All): Kaggle gives secrets (`HF_TOKEN`, for the gated
   model) only to runs started there, and needs Internet on (both set on the account,
   2026-10-08; career-assets `hack-apertus-kaggle-bench/README.md`).
3. Output: `adapter/` (PEFT) and `train_log.json`; `kaggle kernels output
   angelmarquezaguilar/poesia-line-adapter -p <dir>`.

The adapter is used only if it beats plain Apertus on the seeded benchmark (metre, rhyme,
lines in another language), run online (Hugging Face Jobs), never on the desktop GPU.
