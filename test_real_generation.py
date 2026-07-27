#!/usr/bin/env python3
"""Quick test of real generation flow to see what's working."""

from poesia.generation.constrained_loop import ConstrainedLoop
from poesia.generation.llm_client import StubLLMClient

# Generate a haiku with stub client
loop = ConstrainedLoop(
    language="es",
    form="haiku",
    llm=StubLLMClient(),
)

print("=== Haiku Pattern ===")
print(f"Line 1 target: {loop.form_spec.syllables_for_line(0)} syllables")
print(f"Line 2 target: {loop.form_spec.syllables_for_line(1)} syllables")
print(f"Line 3 target: {loop.form_spec.syllables_for_line(2)} syllables")
print()

result = loop.run(theme="luna", n_candidates=3)

print("=== Generated Poem ===")
for line in result.lines:
    print(f"  {line}")

print("\n=== Scored History (Top 3 per line) ===")
for i, scored_candidates in enumerate(result.scored_history):
    print(f"\nLine {i+1}:")
    for j, candidate in enumerate(scored_candidates[:3]):
        print(f"  {j+1}. [{candidate.score:.3f}] {candidate.line}")
        print(f"      syllables={candidate.scan.metrical_syllable_count}, "
              f"valid={candidate.scan.is_valid}")
        print(f"      metre={candidate.breakdown['metre']:.2f}, "
              f"theme={candidate.breakdown['theme']:.2f}, "
              f"novelty={candidate.breakdown['novelty']:.2f}")
