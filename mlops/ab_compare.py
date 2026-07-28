"""A/B comparison of two trained adapters.

Usage:
    python mlops/ab_compare.py --adapter-a models/poetry-lora-v1/final_adapter --adapter-b models/poetry-lora-v2/final_adapter -n 3

Generates the same poem themes with both adapters, scores each,
and shows a side-by-side comparison table.
"""

import argparse, json, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from poesia.generation.llm_client import OutlinesClient
from poesia.phonology.spanish import SpanishPhonology

TEST_THEMES = [
    ("la luna", 11, "ABBA ABBA CDC DCD"),
    ("el mar", 11, "ABBA ABBA CDC DCD"),
    ("la noche", 11, "ABBA ABBA CDC DCD"),
]

phonology = SpanishPhonology()


def evaluate_adapter(adapter_path: str, name: str, num_poems: int) -> dict:
    """Generate N poems with an adapter and return aggregate metrics."""
    client = OutlinesClient(adapter_path=adapter_path)
    client._load()

    results = {"name": name, "poems": []}
    all_line_counts = []
    all_syllable_devs = []
    total_attempts = 0

    for theme_name, target_syll, rhyme in TEST_THEMES[:num_poems]:
        prompt = (
            f"Write a soneto in Spanish.\n"
            f"Syllables per line: {target_syll}.\n"
            f"Rhyme scheme: {rhyme}.\n"
            f"Theme: {theme_name}.\n\n"
        )
        lines = []
        for i in range(14):
            line_prompt = f"{prompt}\nWrite line {i+1} of 14.\n"
            result = client.generate(line_prompt, n=1, temperature=0.8)
            if result and result[0]:
                lines.append(result[0])
            total_attempts += 1

        line_count = len(lines)
        all_line_counts.append(line_count)

        syll_devs = []
        for l in lines:
            scan = phonology.scan_line(l)
            syll_devs.append(abs(scan.metrical_syllable_count - target_syll))
        avg_dev = sum(syll_devs) / len(syll_devs) if syll_devs else 0
        all_syllable_devs.extend(syll_devs)

        results["poems"].append({
            "theme": theme_name,
            "lines": line_count,
            "target_lines": 14,
            "avg_syllable_deviation": round(avg_dev, 2),
            "sample_first": lines[0] if lines else "(empty)",
            "sample_last": lines[-1] if len(lines) >= 14 else "(short)",
        })

    results["summary"] = {
        "avg_line_count": round(sum(all_line_counts) / len(all_line_counts), 1),
        "line_count_accuracy": round(sum(1 for c in all_line_counts if c == 14) / len(all_line_counts), 3),
        "avg_syllable_deviation": round(sum(all_syllable_devs) / len(all_syllable_devs), 2),
    }
    return results


def print_comparison(a: dict, b: dict):
    """Print side-by-side comparison table."""
    print(f"\n{'='*70}")
    print(f"A/B COMPARISON: {a['name']} vs {b['name']}")
    print(f"{'='*70}")

    # Summary header
    print(f"\n{'Metric':<30} {a['name'][:22]:<22} {b['name'][:22]:<22}")
    print(f"{'-'*30} {'-':-<22} {'-':-<22}")
    print(f"{'Avg line count':<30} {a['summary']['avg_line_count']:<22} {b['summary']['avg_line_count']:<22}")
    print(f"{'Line count accuracy (14/14)':<30} {a['summary']['line_count_accuracy']:.1%}{'':>19} {b['summary']['line_count_accuracy']:.1%}{'':>19}")
    print(f"{'Avg syllable deviation':<30} {a['summary']['avg_syllable_deviation']:<22} {b['summary']['avg_syllable_deviation']:<22}")
    
    # Winner
    acc_a = a['summary']['line_count_accuracy']
    acc_b = b['summary']['line_count_accuracy']
    dev_a = a['summary']['avg_syllable_deviation']
    dev_b = b['summary']['avg_syllable_deviation']
    
    print(f"\n{'─'*70}")
    if acc_a > acc_b:
        print(f"  🏆 {a['name']} wins (better line count accuracy)")
    elif acc_b > acc_a:
        print(f"  🏆 {b['name']} wins (better line count accuracy)")
    else:
        if dev_a < dev_b:
            print(f"  🏆 {a['name']} wins (lower syllable deviation)")
        elif dev_b < dev_a:
            print(f"  🏆 {b['name']} wins (lower syllable deviation)")
        else:
            print(f"  🤝 Tie")
    
    # Per-theme detail
    print(f"\n{'─'*70}")
    print(f"Per-theme detail:")
    for pa, pb in zip(a['poems'], b['poems']):
        print(f"\n  Theme: {pa['theme']}")
        print(f"    {a['name'][:22]:<22} {b['name'][:22]:<22}")
        print(f"    {pa['lines']} lines{'':<15} {pb['lines']} lines")
        print(f"    {pa['avg_syllable_deviation']} syll dev{'':<13} {pb['avg_syllable_deviation']} syll dev")
        print(f"    {pa['sample_first'][:40]:<40} {pb['sample_first'][:40]:<40}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter-a", required=True, help="First adapter path")
    parser.add_argument("--adapter-b", required=True, help="Second adapter path")
    parser.add_argument("--name-a", default="Adapter A", help="Display name for A")
    parser.add_argument("--name-b", default="Adapter B", help="Display name for B")
    parser.add_argument("-n", type=int, default=3, help="Number of poems per adapter (max 3)")
    args = parser.parse_args()

    print(f"Evaluating {args.name_a}...")
    results_a = evaluate_adapter(args.adapter_a, args.name_a, args.n)
    
    print(f"Evaluating {args.name_b}...")
    results_b = evaluate_adapter(args.adapter_b, args.name_b, args.n)
    
    print_comparison(results_a, results_b)
    
    # Save comparison result
    output = {
        "a": results_a,
        "b": results_b,
        "winner": "A" if results_a['summary']['line_count_accuracy'] > results_b['summary']['line_count_accuracy']
                  else "B" if results_b['summary']['line_count_accuracy'] > results_a['summary']['line_count_accuracy']
                  else "tie",
    }
    out_path = "mlops/runs/ab_comparison.json"
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\nComparison saved to {out_path}")


if __name__ == "__main__":
    main()
