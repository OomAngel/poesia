"""MLflow pyfunc wrapper for PoesIA LoRA adapter models.

Usage (after training saves adapter):
    from poesia.training.model_wrapper import PoetryModelWrapper
    import mlflow

    mlflow.pyfunc.log_model(
        artifact_path="model",
        python_model=PoetryModelWrapper(),
        artifacts={"adapter": "models/poetry-lora-ruli/final_adapter"},
    )
    mlflow.register_model("runs:/<run_id>/model", "poesia-lora")
"""

from __future__ import annotations

import os

import mlflow
import pandas as pd


class PoetryModelWrapper(mlflow.pyfunc.PythonModel):
    """MLflow pyfunc wrapper for PoesIA's LoRA-tuned poetry models.

    Loads the base model + LoRA adapter at inference time and exposes a
    ``predict()`` method that accepts prompts and returns generated text.

    The base model ID is stored as a model config so any supported HuggingFace
    model can be swapped without code changes.
    """

    def __init__(self, base_model: str = "Qwen/Qwen2.5-1.5B-Instruct"):
        self._base_model = base_model
        self._model = None
        self._tokenizer = None

    def load_context(self, context: mlflow.pyfunc.PythonModelContext) -> None:
        """Load model + tokenizer from MLflow artifact path.

        Expects the adapter weights at the "adapter" artifact key.
        """
        import torch
        from peft import PeftModel
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            BitsAndBytesConfig,
        )

        adapter_path = context.artifacts.get("adapter")

        bnb = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
        )

        # Allow override via model_config if stored
        model_id = (
            context.model_config.get("base_model") if context.model_config else self._base_model
        ) or self._base_model

        self._tokenizer = AutoTokenizer.from_pretrained(model_id)
        self._tokenizer.pad_token = self._tokenizer.eos_token

        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            quantization_config=bnb,
            device_map="auto",
            torch_dtype=torch.bfloat16,
        )

        if adapter_path and os.path.exists(adapter_path):
            model = PeftModel.from_pretrained(model, adapter_path)

        self._model = model

    def predict(
        self,
        context: mlflow.pyfunc.PythonModelContext,
        inputs: pd.DataFrame,
    ) -> list[str]:
        """Generate poem lines from prompts.

        Args:
            inputs: DataFrame with a 'prompt' column. Optional 'temperature'
                    and 'max_tokens' columns.

        Returns:
            List of generated text strings.
        """
        if self._model is None or self._tokenizer is None:
            raise RuntimeError("Model not loaded. Call load_context() first.")

        import torch

        results = []
        for _, row in inputs.iterrows():
            prompt = str(row.get("prompt", ""))
            temperature = float(row.get("temperature", 0.8))
            max_tokens = int(row.get("max_tokens", 100))

            input_ids = self._tokenizer(prompt, return_tensors="pt").to(self._model.device)
            with torch.no_grad():
                out = self._model.generate(
                    **input_ids,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    do_sample=True,
                )
            text = self._tokenizer.decode(
                out[0][input_ids.input_ids.shape[1] :],
                skip_special_tokens=True,
            ).strip()
            results.append(text)

        return results
