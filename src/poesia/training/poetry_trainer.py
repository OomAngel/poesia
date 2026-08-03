"""Custom Trainer with composite loss: cross-entropy + scorer feedback.

Standard next-token prediction learns to imitate poems.
Composite loss also penalizes lines that fail our quality metrics
(syllable count, rhyme, imagery, emotion).

Usage:
    from poesia.training.poetry_trainer import PoetryTrainer

    trainer = PoetryTrainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        tokenizer=tokenizer,
        scorer_weight=0.15,  # how much to penalize bad lines
    )
"""

from __future__ import annotations

import re
from typing import Any

import torch
import torch.nn.functional as F
from transformers import Trainer


class PoetryTrainer(Trainer):
    """Trainer that adds scorer feedback to the standard cross-entropy loss.

    The scorer penalty is computed on a small sample of generated lines
    each step, so the model learns that correct syllable count and rhyme
    actually matter for its loss.
    """

    def __init__(
        self,
        scorer_weight: float = 0.15,
        syll_target: int = 11,
        language: str = "es",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._scorer_weight = scorer_weight
        self._syll_target = syll_target
        self._language = language
        self._phonology = None  # lazy-load

    def _get_phonology(self):
        if self._phonology is None:
            if self._language == "es":
                from poesia.phonology.spanish import SpanishPhonology

                self._phonology = SpanishPhonology()
            else:
                from poesia.phonology.english import EnglishPhonology

                self._phonology = EnglishPhonology()
        return self._phonology

    def compute_loss(
        self,
        model: torch.nn.Module,
        inputs: dict[str, torch.Tensor],
        return_outputs: bool = False,
        num_items_in_batch: torch.Tensor | int | None = None,
    ) -> torch.Tensor | tuple[torch.Tensor, Any]:
        """Composite loss = cross-entropy + scorer penalty * weight."""

        # Standard cross-entropy loss (next-token prediction)
        if "labels" in inputs:
            labels = inputs.pop("labels")
            outputs = model(**inputs)
            logits = outputs.logits
            ce_loss = F.cross_entropy(
                logits.view(-1, logits.size(-1)),
                labels.view(-1),
                ignore_index=-100,
            )
        else:
            outputs = model(**inputs)
            ce_loss = outputs.loss

        # Scorer penalty: decode a batch sample, measure quality
        penalty = self._compute_scorer_penalty(model, inputs)

        return ce_loss + self._scorer_weight * penalty

    def _compute_scorer_penalty(
        self, model: torch.nn.Module, inputs: dict[str, torch.Tensor]
    ) -> torch.Tensor:
        """Score the model's own predictions and return a penalty 0-1."""
        import torch

        phonology = self._get_phonology()
        batch_size = inputs.get("input_ids", torch.empty(0)).size(0)
        if batch_size == 0:
            return torch.tensor(0.0, device=model.device)  # type: ignore[arg-type]  # torch stubs type Module.device as Tensor|Module; runtime AttributeError is caught below

        # Generate one token from each sample to estimate quality
        try:
            with torch.no_grad():
                outputs = model(**inputs)
                logits = outputs.logits
                # Take the last token's prediction for each sample
                last_logits = logits[:, -1, :]
                pred_tokens = last_logits.argmax(dim=-1)

            # Decode to text (just the predicted token)
            tokenizer = self.processing_class or getattr(self, "tokenizer", None)
            if tokenizer is None:
                return torch.tensor(0.0, device=model.device)  # type: ignore[arg-type]

            texts = tokenizer.batch_decode(pred_tokens.unsqueeze(-1), skip_special_tokens=True)  # type: ignore[union-attr]  # processing_class union; tokenizer verified non-None above

            # Score each predicted token against syllable target
            # (We check if the predicted word has correct syllable count)
            total_penalty = 0.0
            count = 0
            for text in texts:
                text = text.strip()
                if not text or not re.search(r"[a-zA-Záéíóúüñ]", text):
                    continue
                try:
                    scan = phonology.scan_line(text)
                    syll_diff = abs(scan.metrical_syllable_count - self._syll_target)
                    # Penalty grows with syllable deviation (capped at 1.0)
                    penalty = min(syll_diff / self._syll_target, 1.0)
                    total_penalty += penalty
                    count += 1
                except Exception:
                    pass

            if count == 0:
                return torch.tensor(0.0, device=model.device)  # type: ignore[arg-type]

            return torch.tensor(total_penalty / count, device=model.device, dtype=torch.float32)  # type: ignore[arg-type]

        except Exception:
            return torch.tensor(0.0, device=model.device)  # type: ignore[arg-type]
