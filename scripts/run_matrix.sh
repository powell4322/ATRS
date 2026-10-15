#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
PYTHON_BIN="${PYTHON_BIN:-python}"
CONFIG="${CONFIG:-experiments/ml1m_sasrec.json}"
DEVICE="${DEVICE:-cuda}"

if [[ "$DEVICE" == cuda* ]]; then
  "$PYTHON_BIN" -c 'import torch; assert torch.cuda.is_available(), "CUDA is unavailable to PyTorch"'
fi

"$PYTHON_BIN" -m atrs.cli preprocess --config "$CONFIG"
"$PYTHON_BIN" -m atrs.cli train-teacher --config "$CONFIG" --defense none --device "$DEVICE"
"$PYTHON_BIN" -m atrs.cli train-teacher --config "$CONFIG" --defense gro --device "$DEVICE"
"$PYTHON_BIN" -m atrs.cli train-teacher --config "$CONFIG" --defense continued-clean --device "$DEVICE"
for defense in none gro continued-clean; do
  for attack in dfme become; do
    "$PYTHON_BIN" -m atrs.cli run-attack --config "$CONFIG" --defense "$defense" --attack "$attack" --device "$DEVICE"
  done
done
