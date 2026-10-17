No commit or PR body names Claude or Anthropic as author or committer or carries a `Co-Authored-By: Claude`, `Claude-Session:` or "Generated with Claude Code" line (Angel, 2026-10-06). The `no-ai-attribution` commit-msg hook rejects such a commit; install it once per clone with `pre-commit install -t commit-msg`, and never bypass it with `--no-verify` or `SKIP=`.

Start here for model work (branch `hack-apertus`): `docs/TUNING_ROUNDS_2026-10.md`, section "Continue here (retired 2026-10-17)".
