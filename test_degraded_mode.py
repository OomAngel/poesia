#!/usr/bin/env python3
"""Test degraded mode messaging when embeddings aren't available."""

import sys
from unittest.mock import patch

# Mock sentence_transformers to simulate it not being installed
with patch.dict('sys.modules', {'sentence_transformers': None}):
    from typer.testing import CliRunner
    from poesia.cli import app
    
    runner = CliRunner()
    
    print("=== Testing degraded mode with --brief ===\n")
    result = runner.invoke(app, [
        "write",
        "--theme", "luna",
        "--form", "haiku", 
        "--brief"
    ])
    
    print(result.output)
    print(f"\nExit code: {result.exit_code}")
