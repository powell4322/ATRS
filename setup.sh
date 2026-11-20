#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

python - <<'PY'
import sys

if sys.version_info < (3, 10):
    raise SystemExit("Python >=3.10 is required. Activate the image's supported Python environment.")

try:
    import torch
except ImportError:
    raise SystemExit("PyTorch is missing from this Python. Activate the image's CUDA PyTorch environment.")

version = tuple(int(part) for part in torch.__version__.split(".")[:2])
if not (2, 3) <= version < (3, 0):
    raise SystemExit(f"Expected PyTorch >=2.3,<3.0, found {torch.__version__}.")
if not torch.cuda.is_available():
    raise SystemExit("CUDA is unavailable to this Python. Check the selected image/environment and instance GPU.")

print(f"Python: {sys.executable}")
print(f"PyTorch: {torch.__version__}; CUDA runtime: {torch.version.cuda}")
print(f"GPU: {torch.cuda.get_device_name(0)}")
PY

python -m pip install --no-deps -e .
python -m atrs.cli preprocess
