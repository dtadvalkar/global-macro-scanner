from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
SCANNER_ROOT = REPO_ROOT / "global-macro-scanner"
SCANNER_MAIN = SCANNER_ROOT / "main.py"


def main() -> int:
    if not SCANNER_MAIN.exists():
        print(
            "The scanner entrypoint was not found at "
            f"{SCANNER_MAIN}. Open {SCANNER_ROOT} and verify the checkout."
        )
        return 1

    cmd = [sys.executable, str(SCANNER_MAIN), *sys.argv[1:]]
    return subprocess.call(cmd, cwd=str(SCANNER_ROOT))


if __name__ == "__main__":
    raise SystemExit(main())
