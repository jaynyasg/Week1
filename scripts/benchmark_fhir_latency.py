#!/usr/bin/env python3
"""
Measure OpenEMR FHIR round-trips for AUD-005 / pre-visit summary budgeting.

Requires the same secrets as the agent:
  OPENEMR_BASE_URL, OPENEMR_FHIR_CLIENT_ID, OPENEMR_FHIR_CLIENT_SECRET

Optional:
  BENCHMARK_PATIENT_UUID — Synthea-style id in ``patient_data.pubpid`` (default: seed fixture id)

Run from repository root:

  python scripts/benchmark_fhir_latency.py
"""

from __future__ import annotations

import os
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import time


def main() -> int:
    from agent.http.env import load_dotenv_if_present

    load_dotenv_if_present()
    pid = (
        os.environ.get("BENCHMARK_PATIENT_UUID", "").strip()
        or "f1aa52b9-aded-3188-9386-012244805ebf"
    )
    try:
        from agent.tools.openemr_fhir import (
            OpenEMRNotConfigured,
            fhir_observations,
            fhir_patient_by_identifier,
        )
    except ImportError as e:
        print(f"Import error (run from repo root): {e}", file=sys.stderr)
        return 2

    try:
        t0 = time.perf_counter()
        p = fhir_patient_by_identifier(pid)
        t_p = (time.perf_counter() - t0) * 1000.0
        if "error" in p:
            print(f"patient_lookup_ms={t_p:.1f} error={p}")
            return 1
        print(f"patient_lookup_ms={t_p:.1f} fhir_id={p.get('fhir_id')}")

        for cat, label in (("laboratory", "labs"), ("vital-signs", "vitals")):
            t0 = time.perf_counter()
            obs = fhir_observations(pid, cat)
            t_o = (time.perf_counter() - t0) * 1000.0
            skipped = obs.get("skipped_not_matching_category", 0)
            cnt = obs.get("count", 0)
            print(f"observation_{label}_ms={t_o:.1f} count={cnt} skipped_category_mismatch={skipped}")
    except OpenEMRNotConfigured as e:
        print(str(e), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
