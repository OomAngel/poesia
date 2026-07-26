"""LLM orchestration and the constrained generation/revision loop.

This package is the only place that talks to an LLM (local via llama.cpp /
transformers, or a hosted API). It owns no phonological knowledge itself —
it calls into `poesia.phonology` and `poesia.evaluation` to validate and
rank what the LLM proposes, then asks the LLM to repair one explicit defect
at a time rather than regenerating from scratch.
"""
