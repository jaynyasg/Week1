"""Quick sanity check for fixtures/sample-patients (does not run full FK scan)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_validate_sample_patient_fixtures_quick() -> None:
    root = Path(__file__).resolve().parents[3]
    script = root / "scripts" / "validate_sample_patient_fixtures.py"
    r = subprocess.run(
        [sys.executable, str(script), "--quick"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr + r.stdout
