"""Architecture conformance tests.

Enforce the layering rules documented in ``docs/ARCHITECTURE.md`` (reconciled
2026-08-04 with the real, interface-based seams):

1. **Package dependency matrix.** Each ``poesia.*`` package may only import
   ``poesia.*`` packages listed in ``ALLOWED``. The reconciled seams:
   - ``evaluation`` → ``memoria`` (embedding *interface*, optional semantic
     scoring; falls back to deterministic metre-only without it)
   - ``generation`` → ``memoria`` (retrieval for the generation brief)
   - ``galeria`` → ``memoria`` (influence records for style anchoring)
   - ``training`` → ``phonology`` (validation during training)
2. **Lazy heavy imports.** Heavy third-party libraries (ML / audio / image
   SDKs) must never be imported at module top-level outside a ``try`` block or
   a function/class body — the package must stay importable with a bare
   ``pip install -e .`` and no extras (AGENTS.md lazy-import rule).
3. ``cli.py`` is the composition root and may import any ``poesia.*`` package.

This mirrors the AST-guardrail pattern used in ``pcb-tools``.
"""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src" / "poesia"

# Reconciled layering (docs/ARCHITECTURE.md, 2026-08-04).
ALLOWED: dict[str, set[str]] = {
    "phonology": {"phonology"},
    "evaluation": {"evaluation", "phonology", "memoria"},
    "generation": {
        "generation",
        "phonology",
        "evaluation",
        "forms",
        "memoria",
        "exceptions",
        "device",
    },
    "forms": {"forms"},
    "eufonia": {"eufonia", "phonology"},
    "galeria": {"galeria", "memoria"},
    "armonia": {"armonia", "phonology"},
    "memoria": {"memoria", "exceptions", "device"},
    "training": {"training", "phonology"},
    "config": {"config", "forms"},
}

# Top-level modules in ``src/poesia/`` (cli.py, api.py, exceptions.py,
# device.py) are entry points / leaves and are exempt from the dependency
# matrix but still subject to the heavy-import rule.

# Heavy third-party libraries that must be lazy-imported.
HEAVY_ROOTS = {
    "sentence_transformers",
    "torch",
    "transformers",
    "peft",
    "trl",
    "datasets",
    "music21",
    "pyfluidsynth",
    "audiocraft",
    "PIL",
    "weasyprint",
    "openai",
    "replicate",
    "diffusers",
    "networkx",
    "spacy",
    "outlines",
    "llama_cpp",
    "groq",
    "google",
    "datamuse",
}


def _iter_py_files() -> list[tuple[Path, str]]:
    """Return (file, package_relative_path) for every source file."""
    out = []
    for p in sorted(SRC.rglob("*.py")):
        if "__pycache__" in str(p):
            continue
        out.append((p, p.relative_to(SRC).as_posix()))
    return out


def _resolve_targets(node: ast.AST, pkg_parts: list[str]) -> list[str]:
    """Resolve an Import/ImportFrom node to a set of top-level module names."""
    if isinstance(node, ast.Import):
        out = []
        for a in node.names:
            root = a.name.split(".")[0]
            if root == "poesia":
                seg = a.name.split(".")
                out.append("poesia." + seg[1] if len(seg) > 1 else "poesia")
            else:
                out.append(root)
        return out
    if not isinstance(node, ast.ImportFrom):
        raise TypeError(f"unexpected node type: {type(node).__name__}")
    if node.level:  # relative import
        upto = len(pkg_parts) - (node.level - 1)
        base = pkg_parts[:upto] if upto >= 0 else []
        mod = (node.module or "").split(".")[0]
        parts = base + ([mod] if mod else [])
        return ["poesia." + ".".join(parts)] if parts else []
    mod = node.module or ""
    parts = mod.split(".")
    if parts[0] == "poesia":
        if len(parts) > 1:
            return ["poesia." + parts[1]]
        # `from poesia import <submodule>`
        return ["poesia." + a.name.split(".")[0] for a in node.names]
    return [parts[0]]


def _check_file(p: Path, rel: str, problems: list[str]) -> None:
    tree = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
    pkg = rel.split("/")[0]
    pkg_parts = rel.split("/")[:-1]  # package segments from the poesia root
    is_top_level = "/" not in rel  # entry points (cli.py, api.py) and leaves

    def visit(node: ast.AST, ancestors: list[ast.AST]) -> None:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            targets = _resolve_targets(node, pkg_parts)
            for t in targets:
                if t == "poesia" or not t.startswith("poesia."):
                    continue
                dep = t.split(".")[1]
                if not is_top_level:
                    allowed = ALLOWED.get(pkg, set()) | {pkg}
                    if dep not in allowed:
                        problems.append(
                            f"{rel}:{node.lineno}: {pkg} imports {dep} (allowed: {sorted(allowed)})"
                        )
            # Heavy third-party imports must be try-guarded or inside a body.
            heavy = [t for t in targets if t in HEAVY_ROOTS]
            if heavy and not any(
                isinstance(a, (ast.Try, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                for a in ancestors
            ):
                problems.append(
                    f"{rel}:{node.lineno}: top-level import of heavy module(s) "
                    f"{sorted(heavy)} — must be lazy/try-guarded"
                )
        for child in ast.iter_child_nodes(node):
            visit(child, ancestors + [node])

    visit(tree, [])


def test_architecture_layers() -> None:
    problems: list[str] = []
    for p, rel in _iter_py_files():
        _check_file(p, rel, problems)
    assert not problems, "Architecture conformance violations:\n" + "\n".join(problems)  # noqa: S101 — pytest assertion
