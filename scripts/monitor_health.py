#!/usr/bin/env python3
"""Monitoring & drift detection for PoesIA models.

Periodically evaluates the latest production model against a held-back
evaluation corpus and compares metrics to historical baselines.
Logs results to an MLflow monitoring experiment.

Designed to run on a schedule (cron, GitHub Actions scheduled workflow)
or manually to check model health.

Usage:
    python scripts/monitor_health.py
    python scripts/monitor_health.py --model-uri "models:/poesia-lora-soneto-structured/latest"
    python scripts/monitor_health.py --dry-run
    python scripts/monitor_health.py --max-syllable-deviation 2.0 --min-line-accuracy 0.8
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

import mlflow
from mlflow.tracking import MlflowClient


_TRACKING_URI = os.environ.get("DATABASE_URL", "sqlite:///mlruns/mlflow.db")
_DEFAULT_THRESHOLDS = {
    "max_syllable_deviation": 2.0,
    "min_line_accuracy": 0.8,
}


def _client():
    mlflow.set_tracking_uri(_TRACKING_URI)
    return MlflowClient(_TRACKING_URI)


def _resolve_model_uri(model_arg):
    if model_arg:
        return model_arg
    client = _client()
    for reg_model in client.search_registered_models():
        for version in reg_model.latest_versions:
            if version.current_stage == "Production":
                return f"models:/{reg_model.name}/{version.version}"
    for reg_model in client.search_registered_models():
        for version in reg_model.latest_versions:
            if version.current_stage == "Staging":
                return f"models:/{reg_model.name}/{version.version}"
    experiments = client.search_experiments()
    for exp in experiments:
        runs = client.search_runs(
            experiment_ids=[exp.experiment_id],
            filter_string='attributes.status = "FINISHED"',
            order_by=["attributes.start_time DESC"], max_results=1,
        )
        if runs:
            return f"runs:/{runs[0].info.run_id}/model"
    raise RuntimeError("No models found")


def _compute_baseline(client, lookback_days=30):
    baseline = {
        "eval_syllable_deviation": {"mean": None, "std": None, "count": 0, "values": []},
        "eval_line_count_accuracy": {"mean": None, "std": None, "count": 0, "values": []},
    }
    try:
        exp = client.get_experiment_by_name("poesia-monitoring")
        if not exp:
            return baseline
        cutoff = time.time() - lookback_days * 86400
        runs = client.search_runs(
            experiment_ids=[exp.experiment_id],
            filter_string=f'attributes.start_time > {int(cutoff * 1000)}',
            order_by=["attributes.start_time DESC"],
        )
        for r in runs:
            for mk in ("eval_syllable_deviation", "eval_line_count_accuracy"):
                val = r.data.metrics.get(mk)
                if val is not None:
                    baseline[mk]["values"].append(val)
        for key, data in baseline.items():
            vals = data["values"]
            if vals:
                n = len(vals)
                mean = sum(vals) / n
                var = sum((x - mean) ** 2 for x in vals) / n
                data["mean"] = round(mean, 4)
                data["std"] = round(var ** 0.5, 4)
                data["count"] = n
    except Exception as e:
        print(f"  [WARN] Baseline error: {e}")
    return baseline


def _check_drift(current, baseline, thresholds):
    alerts = []
    sd = current.get("eval_syllable_deviation")
    if sd is not None:
        if sd > thresholds["max_syllable_deviation"]:
            alerts.append({
                "metric": "eval_syllable_deviation", "current": sd,
                "threshold": thresholds["max_syllable_deviation"],
                "severity": "alert",
                "message": f"Syllable dev {sd:.2f} > threshold {thresholds['max_syllable_deviation']:.2f}",
            })
        elif baseline["eval_syllable_deviation"]["mean"] is not None:
            bm = baseline["eval_syllable_deviation"]["mean"]
            bs = baseline["eval_syllable_deviation"]["std"] or 0.01
            z = (sd - bm) / bs
            if abs(z) > 2:
                alerts.append({
                    "metric": "eval_syllable_deviation", "current": sd,
                    "baseline_mean": bm, "z_score": round(z, 2),
                    "severity": "warning",
                    "message": f"Syllable dev {sd:.2f} is {z:.1f}σ from baseline {bm:.2f}",
                })
    la = current.get("eval_line_count_accuracy")
    if la is not None:
        if la < thresholds["min_line_accuracy"]:
            alerts.append({
                "metric": "eval_line_count_accuracy", "current": la,
                "threshold": thresholds["min_line_accuracy"],
                "severity": "alert",
                "message": f"Line acc {la:.1%} < threshold {thresholds['min_line_accuracy']:.0%}",
            })
        elif baseline["eval_line_count_accuracy"]["mean"] is not None:
            bm = baseline["eval_line_count_accuracy"]["mean"]
            bs = baseline["eval_line_count_accuracy"]["std"] or 0.01
            z = (la - bm) / bs
            if abs(z) > 2:
                alerts.append({
                    "metric": "eval_line_count_accuracy", "current": la,
                    "baseline_mean": bm, "z_score": round(z, 2),
                    "severity": "warning",
                    "message": f"Line acc {la:.1%} is {z:.1f}σ from baseline {bm:.1%}",
                })
    return alerts


def evaluate_model(model_uri):
    try:
        model = mlflow.pyfunc.load_model(model_uri)
        print(f"  Model loaded from {model_uri}")
    except Exception as e:
        print(f"  pyfunc load failed: {e}, trying fallback...")
        return _evaluate_fallback(model_uri)

    import pandas as pd
    from poesia.phonology.spanish import SpanishPhonology
    phonology = SpanishPhonology()
    test_prompts = [
        {"prompt": "Write line 1 of a sonnet about the sea. Exactly 11 syllables.\n", "temperature": 0.8},
        {"prompt": "Write line 2 of a sonnet about the sea. Exactly 11 syllables.\n", "temperature": 0.8},
        {"prompt": "Write line 1 of a sonnet about the moon. Exactly 11 syllables.\n", "temperature": 0.8},
    ]
    syll_devs, line_accs = [], []
    for p in test_prompts:
        try:
            outputs = model.predict(pd.DataFrame([p]))
            text = outputs[0] if outputs else ""
            if text:
                scan = phonology.scan_line(text)
                dev = abs(scan.metrical_syllable_count - 11)
                syll_devs.append(dev)
                line_accs.append(1.0 if dev <= 1 else 0.0)
        except Exception as e:
            print(f"  [WARN] Eval prompt failed: {e}")
    return {
        "eval_syllable_deviation": round(sum(syll_devs) / len(syll_devs), 2) if syll_devs else None,
        "eval_line_count_accuracy": round(sum(line_accs) / len(line_accs), 3) if line_accs else None,
        "n_samples": len(syll_devs),
    }


def _evaluate_fallback(model_uri):
    sys.path.insert(0, "mlops")
    from evaluate_adapter import evaluate as eval_adapter
    adapter_path = None
    if model_uri.startswith("models:/"):
        parts = model_uri.split("/")
        if len(parts) >= 4:
            client = _client()
            try:
                mv = client.get_model_version(parts[1], parts[2])
                run = client.get_run(mv.run_id)
                adapter_path = run.data.params.get("adapter_path")
            except Exception:
                pass
    elif model_uri.startswith("runs:/"):
        client = _client()
        try:
            run = client.get_run(model_uri.split("/")[1])
            adapter_path = run.data.params.get("adapter_path")
        except Exception:
            pass
    if adapter_path and os.path.exists(adapter_path):
        results = eval_adapter(adapter_path)
        return results.get("summary", {})
    print("  [WARN] No adapter path — returning empty metrics")
    return {"eval_syllable_deviation": None, "eval_line_count_accuracy": None}



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-uri", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-syllable-deviation", type=float, default=None)
    parser.add_argument("--min-line-accuracy", type=float, default=None)
    parser.add_argument("--lookback-days", type=int, default=30)
    args = parser.parse_args()

    thresholds = dict(_DEFAULT_THRESHOLDS)
    if args.max_syllable_deviation is not None:
        thresholds["max_syllable_deviation"] = args.max_syllable_deviation
    if args.min_line_accuracy is not None:
        thresholds["min_line_accuracy"] = args.min_line_accuracy

    mlflow.set_tracking_uri(_TRACKING_URI)
    client = _client()
    try:
        mlflow.create_experiment("poesia-monitoring", artifact_location="./mlruns/poesia-monitoring")
    except Exception:
        pass
    mlflow.set_experiment("poesia-monitoring")

    print(f"PoesIA Model Health Monitor")
    print(f"{'=' * 50}")
    model_uri = _resolve_model_uri(args.model_uri)
    print(f"  Model: {model_uri}")

    baseline = _compute_baseline(client, args.lookback_days)
    if baseline["eval_syllable_deviation"]["mean"] is not None:
        print(f"  Baseline ({args.lookback_days}d, {baseline['eval_syllable_deviation']['count']} runs):")
        print(f"    Syllable dev: μ={baseline['eval_syllable_deviation']['mean']:.3f} σ={baseline['eval_syllable_deviation']['std']:.3f}")
        print(f"    Line accuracy: μ={baseline['eval_line_count_accuracy']['mean']:.3f} σ={baseline['eval_line_count_accuracy']['std']:.3f}")
    else:
        print("  No baseline — first monitoring run")

    current = evaluate_model(model_uri)
    print(f"  Current: syll_dev={current.get('eval_syllable_deviation', 'N/A')}, "
          f"line_acc={current.get('eval_line_count_accuracy', 'N/A')}")

    with mlflow.start_run(run_name=f"monitor-{datetime.now().strftime('%Y%m%d_%H%M%S')}") as run:
        mlflow.log_param("model_uri", model_uri)
        mlflow.log_param("thresholds", json.dumps(thresholds))
        for k, v in current.items():
            if v is not None:
                mlflow.log_metric(k, v)
        for mk, data in baseline.items():
            if data["mean"] is not None:
                mlflow.log_metric(f"baseline_{mk}_mean", data["mean"])
                mlflow.log_metric(f"baseline_{mk}_std", data["std"])
        alerts = _check_drift(current, baseline, thresholds)
        mlflow.log_param("n_alerts", len(alerts))
        threshold_breach = any(a["severity"] == "alert" for a in alerts)
        mlflow.set_tag("model_health", "unhealthy" if threshold_breach else "healthy")
        if alerts:
            print(f"\n  {'⚠️ ' + str(len(alerts)) + ' drift signal(s):'}")
            for a in alerts:
                print(f"    {'🔴' if a['severity'] == 'alert' else '🟡'} {a['message']}")
        else:
            print(f"\n  ✅ No drift detected")

    print(f"\n  Run ID: {run.info.run_id}")
    print(f"  Health: {'🔴 UNHEALTHY' if threshold_breach else '✅ HEALTHY'}")
    if threshold_breach and not args.dry_run:
        sys.exit(1)


if __name__ == "__main__":
    main()
