"""
Quick smoke-check: confirms Synthea data was imported into OpenEMR's MariaDB.

Usage (requires fly proxy running on 3307):
    fly proxy 3307:3306 --app clinical-copilot-db-v2
    python scripts/verify_import.py

Optional args:
    --host 127.0.0.1  --port 3307  --user openemr  --password <pw>
    --seed-uuid f1aa52b9-aded-3188-9386-012244805ebf
"""

from __future__ import annotations

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify Synthea→OpenEMR import.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3307)
    parser.add_argument("--user", default="openemr")
    parser.add_argument("--password", default="")
    parser.add_argument("--db", default="openemr")
    parser.add_argument(
        "--seed-uuid",
        default="f1aa52b9-aded-3188-9386-012244805ebf",
        help="Synthea UUID of the demo seed patient (Maurice742 Brekke496)",
    )
    args = parser.parse_args()

    try:
        import pymysql
    except ImportError:
        print("ERROR: pymysql not installed.  pip install pymysql", file=sys.stderr)
        sys.exit(1)

    print(f"Connecting to {args.host}:{args.port}/{args.db} as {args.user}…")
    conn = pymysql.connect(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.db,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )

    passed = 0
    failed = 0

    def check(label: str, sql: str, params: tuple = (), *, expect_gt: int = 0) -> None:
        nonlocal passed, failed
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            count = list(row.values())[0] if row else 0
        ok = count > expect_gt
        status = "✓ PASS" if ok else "✗ FAIL"
        if ok:
            passed += 1
        else:
            failed += 1
        print(f"  {status}  {label}: {count}")

    print("\n── Patients ────────────────────────────────")
    check("Total patients in patient_data", "SELECT COUNT(*) FROM patient_data")
    check(
        "Seed patient by pubpid",
        "SELECT COUNT(*) FROM patient_data WHERE pubpid = %s",
        (args.seed_uuid,),
    )

    print("\n── Medications ─────────────────────────────")
    check("Total prescriptions", "SELECT COUNT(*) FROM prescriptions")

    # Link to seed patient
    with conn.cursor() as cur:
        cur.execute(
            "SELECT pid FROM patient_data WHERE pubpid = %s LIMIT 1", (args.seed_uuid,)
        )
        row = cur.fetchone()
        seed_pid = row["pid"] if row else None

    if seed_pid:
        print(f"  (seed patient OpenEMR pid = {seed_pid})")
        check(
            "Seed patient prescriptions",
            "SELECT COUNT(*) FROM prescriptions WHERE patient_id = %s",
            (seed_pid,),
        )
    else:
        print("  ✗ FAIL  Seed patient not found — medications cannot be verified")
        failed += 1

    print("\n── Allergies ───────────────────────────────")
    check(
        "Allergy rows in lists",
        "SELECT COUNT(*) FROM lists WHERE type = 'allergy'",
    )

    print("\n── Vitals ──────────────────────────────────")
    check(
        "Vitals in form_vitals",
        "SELECT COUNT(*) FROM form_vitals",
    )

    print("\n── Labs ────────────────────────────────────")
    check("procedure_report rows", "SELECT COUNT(*) FROM procedure_report")
    check("procedure_result rows", "SELECT COUNT(*) FROM procedure_result")

    conn.close()

    print(f"\n{'─'*45}")
    print(f"  {passed} checks passed, {failed} failed")

    if failed:
        print("\n  Some data may be missing. Re-run the full import:")
        print("    python scripts/import_synthea_to_openemr.py")
        sys.exit(1)
    else:
        print("\n  All data verified. OpenEMR import looks good.")
        print(f"\n  Seed patient UUID : {args.seed_uuid}")
        print(f"  OpenEMR pid       : {seed_pid}")
        print("\n  Agent FHIR activation (next step):")
        print("    Register an API client in OpenEMR:")
        print("      Administration → Config → API Clients → Register New Client")
        print("      grant_type: client_credentials")
        print("      scopes: patient/Patient.read patient/MedicationRequest.read")
        print("              patient/Observation.read patient/AllergyIntolerance.read")
        print("    Then:")
        print("      fly secrets set OPENEMR_FHIR_CLIENT_ID=<id> \\")
        print("                      OPENEMR_FHIR_CLIENT_SECRET=<secret> \\")
        print("                      --app clinical-agent-scaffold")
        print("      fly deploy --config fly.agent.toml")


if __name__ == "__main__":
    main()
