#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"
python_bin="$project_root/.venv/bin/python"

# cuBLAS/cuDNN wheels stay inside this project's virtual environment.
cuda_lib_dirs="$("$python_bin" - <<'PY'
from pathlib import Path
import sysconfig

nvidia = Path(sysconfig.get_path('purelib')) / 'nvidia'
paths = [nvidia / name / 'lib' for name in ('cublas', 'cudnn', 'cuda_nvrtc')]
print(':'.join(str(path) for path in paths if path.is_dir()))
PY
)"
if [[ -n "$cuda_lib_dirs" ]]; then
  export LD_LIBRARY_PATH="$cuda_lib_dirs${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi

exec "$python_bin" "$@"
