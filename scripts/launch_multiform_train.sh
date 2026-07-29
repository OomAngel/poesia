#!/bin/bash
# Launches multi-form training in background
cd /home/angel/dev/poesia
source /home/angel/miniconda3/etc/profile.d/conda.sh
conda activate poesia
exec python scripts/train_poetry_lora.py mlops/configs/train_multiform.yaml > /tmp/multiform_training.log 2>&1
