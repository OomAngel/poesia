#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
# Post-Training Pipeline
#   Runs after training: evaluate adapter → log metrics → migrate to PG
#
# Usage:
#   bash scripts/post_training_pipeline.sh                  # last run
#   bash scripts/post_training_pipeline.sh <run_id>         # specific run
#   bash scripts/post_training_pipeline.sh --dry-run        # preview
# ═══════════════════════════════════════════════════════════════════════

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
POESIA_PYTHON="/home/angel/miniconda3/envs/poesia/bin/python3"
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }
info() { echo -e "  ${CYAN}→${NC} $1"; }

source "$SCRIPT_DIR/poesia_env.sh" --source 2>/dev/null || true

# ── Find last finished training run ──────────────────────────────────
find_last_run() {
    $POESIA_PYTHON -c "
import mlflow, json, sys
mlflow.set_tracking_uri('${MLFLOW_TRACKING_URI:-sqlite:///mlruns/mlflow.db}')
from mlflow.tracking import MlflowClient; c = MlflowClient()
runs = []
for e in c.search_experiments():
    if e.name in ('Default','test'): continue
    for r in c.search_runs([e.experiment_id], order_by=['attributes.start_time DESC']):
        if r.info.status == 'FINISHED' and r.data.params.get('adapter_path',''):
            runs.append((r.info.start_time, r.info.run_id, e.name, r.data.params.get('adapter_path',''), r.data.params.get('model','')))
runs.sort(reverse=True)
if not runs: print('NO_RUNS'); sys.exit(0)
b = runs[0]
print(f'RUN_ID={b[1]} EXP={b[2]} ADAPTER={b[3]} MODEL={b[4]}')
" 2>/dev/null
}


# ── Evaluate adapter across 5 themes ────────────────────────────────
evaluate_adapter() {
    local run_id="$1" adapter="$2" model="$3"
    $POESIA_PYTHON -c "
import mlflow, json, sys, os, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, '$PROJECT_ROOT')
from poesia.generation.llm_client import LoRAClient
from poesia.generation.constrained_loop import ConstrainedLoop
from poesia.phonology.spanish import SpanishPhonology

mlflow.set_tracking_uri('${MLFLOW_TRACKING_URI:-sqlite:///mlruns/mlflow.db}')
client = LoRAClient(base_model='$model', adapter_path='$adapter')
phon = SpanishPhonology()
themes = ['luna sobre el mar','amor eterno','noche estrellada','sol naciente','viento del sur']
results = {}
for theme in themes:
    loop = ConstrainedLoop(language='es', form='soneto', llm=client)
    r = loop.run(theme=theme, n_candidates=4)
    correct = 0; total_dev = 0.0
    for line in r.lines:
        s = phon.scan_line(line)
        dev = abs(s.metrical_syllable_count - 11)
        total_dev += dev
        correct += 1 if dev <= 1 else 0
    results[theme] = {'lines': len(r.lines), 'correct': correct, 'dev': round(total_dev/max(len(r.lines),1),2)}
with mlflow.start_run(run_id='$run_id') as ar:
    for t, r in results.items():
        mlflow.log_metric(f'{t}_lines', r['lines'])
        mlflow.log_metric(f'{t}_correct', r['correct'])
        mlflow.log_metric(f'{t}_deviation', r['dev'])
    total = sum(r['lines'] for r in results.values())
    correct = sum(r['correct'] for r in results.values())
    acc = round(correct/total, 4) if total else 0
    dev = round(sum(r['dev'] for r in results.values())/len(results), 2)
    mlflow.log_metric('eval_total_lines', total)
    mlflow.log_metric('eval_correct_lines', correct)
    mlflow.log_metric('eval_accuracy', acc)
    mlflow.log_metric('eval_avg_deviation', dev)
    print(json.dumps({'accuracy': acc, 'deviation': dev, 'total': total, 'correct': correct}))
" 2>/dev/null
}

# ── Migrate SQLite → PostgreSQL ────────────────────────────────────
migrate_if_sqlite() {
    if [[ "${MLFLOW_TRACKING_URI:-}" == sqlite://* ]]; then
        info "Migrating SQLite to PostgreSQL..."
        [ -f /tmp/migrate_mlflow.py ] && $POESIA_PYTHON /tmp/migrate_mlflow.py 2>/dev/null | grep -v WARNING
        ok "Migration done"
    else
        ok "Already on PostgreSQL"
    fi
}

# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════
RUN_ID="${1:-}"
if [ "$RUN_ID" == "--dry-run" ]; then
    result=$(find_last_run)
    [[ "$result" == "NO_RUNS" ]] && { warn "No runs"; exit 0; }
    eval "$result"
    info "Dry-run: would process RUN_ID=${RUN_ID:0:8}"
    info "Would evaluate adapter: ${ADAPTER}"
    info "Would migrate to PostgreSQL"
    exit 0
fi

if [ -z "$RUN_ID" ]; then
    result=$(find_last_run)
    [[ "$result" == "NO_RUNS" ]] && { warn "No finished training runs"; exit 1; }
    eval "$result"
fi

echo -e "\n${CYAN}═══ Post-Training Pipeline ═══${NC}"
echo "  Run:    ${RUN_ID:0:8}  (${EXP:-?})"
echo "  Model:  ${MODEL:-?}"
echo "  Adapter: ${ADAPTER:-?}"
echo ""

evaluate_adapter "$RUN_ID" "$ADAPTER" "$MODEL"
echo ""
migrate_if_sqlite
echo ""
echo -e "${GREEN}✓${NC} Pipeline complete. View at: http://localhost:5000"
