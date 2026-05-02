"""
Import Synthea CSV fixtures into OpenEMR 7.x MariaDB.

Usage (via Fly proxy):
    # Terminal 1 — open proxy
    fly proxy 3307:3306 --app clinical-copilot-db-v2

    # Terminal 2 — run import
    python scripts/import_synthea_to_openemr.py \
        --host 127.0.0.1 --port 3307 \
        --user <MYSQL_USER> --password <MYSQL_PASS> --database openemr

    # Or use env vars (recommended — avoids typing password):
    set MYSQL_HOST=127.0.0.1
    set MYSQL_PORT=3307
    set MYSQL_USER=openemr
    set MYSQL_PASS=<value>
    set MYSQL_DATABASE=openemr
    python scripts/import_synthea_to_openemr.py

Imports: patients, medications (prescriptions), allergies (lists),
         vitals (form_vitals), lab observations (form_observation via forms).
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

try:
    import pymysql
except ImportError:
    print("pymysql not installed. Run: pip install pymysql")
    sys.exit(1)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "sample-patients"

# --- helpers -----------------------------------------------------------------

def _date(s: str) -> str | None:
    if not s:
        return None
    return s[:10]


def _dt(s: str) -> str | None:
    if not s:
        return None
    return s[:19].replace("T", " ")


def _cm_to_in(cm: str) -> float | None:
    try:
        return round(float(cm) / 2.54, 1)
    except (ValueError, TypeError):
        return None


def _kg_to_lbs(kg: str) -> float | None:
    try:
        return round(float(kg) * 2.205, 1)
    except (ValueError, TypeError):
        return None


def _sex(g: str) -> str:
    return "Male" if g.upper() in {"M", "MALE"} else "Female"


# --- importers ---------------------------------------------------------------

def _next_pid(cur: Any) -> int:
    """Get next pid using OpenEMR's sequence table, falling back to MAX(pid)+1."""
    try:
        cur.execute("SELECT id FROM sequences LIMIT 1")
        row = cur.fetchone()
        if row:
            next_id = row[0] + 1
            cur.execute("UPDATE sequences SET id = %s", (next_id,))
            return next_id
    except Exception:
        pass
    cur.execute("SELECT COALESCE(MAX(pid), 1) + 1 FROM patient_data")
    return cur.fetchone()[0]


def import_patients(cur: Any, patients_csv: Path) -> dict[str, int]:
    """Insert patients; return {uuid: pid} map."""
    pid_map: dict[str, int] = {}
    with patients_csv.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            uid = row["Id"].strip()
            if not uid:
                continue
            cur.execute(
                "SELECT pid FROM patient_data WHERE pubpid = %s LIMIT 1", (uid,)
            )
            existing = cur.fetchone()
            if existing:
                pid_map[uid] = existing[0]
                print(f"  patient {row['LAST']} already exists (pid={existing[0]})")
                continue

            pid = _next_pid(cur)
            cur.execute(
                """
                INSERT INTO patient_data
                    (pid, title, fname, mname, lname, DOB, sex, race, ethnicity,
                     street, city, state, postal_code, pubpid, date)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
                """,
                (
                    pid,
                    row.get("PREFIX", ""),
                    row.get("FIRST", ""),
                    row.get("MIDDLE", ""),
                    row.get("LAST", ""),
                    _date(row.get("BIRTHDATE", "")),
                    _sex(row.get("GENDER", "M")),
                    row.get("RACE", ""),
                    row.get("ETHNICITY", ""),
                    row.get("ADDRESS", ""),
                    row.get("CITY", ""),
                    row.get("STATE", ""),
                    row.get("ZIP", ""),
                    uid,
                ),
            )
            pid_map[uid] = pid
            print(f"  imported patient {row['FIRST']} {row['LAST']} → pid={pid}")
    return pid_map


def import_medications(cur: Any, meds_csv: Path, pid_map: dict[str, int]) -> int:
    count = 0
    with meds_csv.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pid = pid_map.get(row.get("PATIENT", "").strip())
            if not pid:
                continue
            stop = _date(row.get("STOP", ""))
            active = 1 if not stop else 0
            cur.execute(
                """
                INSERT INTO prescriptions
                    (patient_id, date_added, drug, rxnorm_drugcode, active, note,
                     txDate)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    pid,
                    _date(row.get("START", "")) or str(date.today()),
                    row.get("DESCRIPTION", "")[:255],
                    row.get("CODE", "")[:20],
                    active,
                    f"Synthea import. Stop: {stop or 'ongoing'}",
                    _date(row.get("START", "")) or str(date.today()),
                ),
            )
            count += 1
    return count


def import_allergies(cur: Any, allergies_csv: Path, pid_map: dict[str, int]) -> int:
    count = 0
    with allergies_csv.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pid = pid_map.get(row.get("PATIENT", "").strip())
            if not pid:
                continue
            atype = row.get("TYPE", "allergy")
            title = row.get("DESCRIPTION", "Unknown")[:255]
            cur.execute(
                """
                INSERT INTO lists
                    (pid, type, title, begdate, enddate, diagnosis, severity_al,
                     reaction, activity, date)
                VALUES (%s,'allergy',%s,%s,%s,%s,%s,%s,1,NOW())
                """,
                (
                    pid,
                    title,
                    _date(row.get("START", "")) or str(date.today()),
                    _date(row.get("STOP", "")) or None,
                    row.get("CODE", "")[:30],
                    row.get("SEVERITY1", "")[:30] or "mild",
                    row.get("DESCRIPTION1", "")[:255],
                ),
            )
            count += 1
    return count


def import_vitals(cur: Any, obs_csv: Path, pid_map: dict[str, int]) -> int:
    """Aggregate vital-signs observations per encounter into form_vitals rows."""
    from collections import defaultdict

    # Group by (patient, encounter, date)
    enc: dict[tuple[str, str, str], dict[str, str]] = defaultdict(dict)
    with obs_csv.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if (row.get("CATEGORY") or "").strip() != "vital-signs":
                continue
            pid_str = row.get("PATIENT", "").strip()
            if pid_str not in pid_map:
                continue
            key = (pid_str, row.get("ENCOUNTER", ""), row.get("DATE", "")[:10])
            code = row.get("CODE", "")
            val = row.get("VALUE", "")
            units = row.get("UNITS", "")
            enc[key][code] = (val, units)

    count = 0
    for (pid_str, encounter, obs_date), codes in enc.items():
        pid = pid_map[pid_str]

        def v(code: str) -> str:
            return codes.get(code, ("", ""))[0]

        height_in = _cm_to_in(v("8302-2")) if v("8302-2") else None
        weight_lbs = _kg_to_lbs(v("29463-7")) if v("29463-7") else None

        # Blood pressure: systolic 8480-6, diastolic 8462-4
        bps = v("8480-6") or None
        bpd = v("8462-4") or None
        pulse = v("8867-4") or None
        temp = v("8310-5") or None
        resp = v("9279-1") or None
        bmi = v("39156-5") or None

        cur.execute(
            """
            INSERT INTO form_vitals
                (pid, date, weight, height, bps, bpd, pulse,
                 temperature, respiration, BMI, activity)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1)
            """,
            (pid, obs_date, weight_lbs, height_in, bps, bpd, pulse, temp, resp, bmi),
        )
        # Link via forms table so OpenEMR UI shows it under patient chart
        form_id = cur.lastrowid
        cur.execute(
            """
            INSERT INTO forms
                (date, encounter, form_name, form_id, pid, user, groupname,
                 authorized, deleted, formdir)
            VALUES (%s,%s,'Vitals',%s,%s,'admin','Default',1,0,'vitals')
            """,
            (obs_date, encounter[:40] if encounter else "1", form_id, pid),
        )
        count += 1
    return count


def import_labs(cur: Any, obs_csv: Path, pid_map: dict[str, int]) -> int:
    """Import laboratory observations into form_observation / forms."""
    from collections import defaultdict

    enc: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    with obs_csv.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if (row.get("CATEGORY") or "").strip() != "laboratory":
                continue
            pid_str = row.get("PATIENT", "").strip()
            if pid_str not in pid_map:
                continue
            key = (pid_str, row.get("ENCOUNTER", ""), row.get("DATE", "")[:10])
            enc[key].append(row)

    count = 0
    for (pid_str, encounter, obs_date), rows in enc.items():
        pid = pid_map[pid_str]
        # Create a procedure_report row to anchor results
        cur.execute(
            """
            INSERT INTO procedure_report
                (procedure_order_id, date_collected, date_report,
                 report_status, review_status)
            VALUES (0,%s,%s,'final','reviewed')
            """,
            (obs_date, obs_date),
        )
        report_id = cur.lastrowid
        for row in rows:
            cur.execute(
                """
                INSERT INTO procedure_result
                    (procedure_report_id, result_code, result_text,
                     result_data_type, result, units,
                     `range`, abnormal, result_status, date)
                VALUES (%s,%s,%s,'NM',%s,%s,'','','final',%s)
                """,
                (
                    report_id,
                    row.get("CODE", "")[:31],
                    row.get("DESCRIPTION", "")[:255],
                    row.get("VALUE", "")[:255],
                    row.get("UNITS", "")[:31],
                    obs_date,
                ),
            )
            count += 1
    return count


# --- main --------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Import Synthea CSV → OpenEMR MariaDB")
    parser.add_argument("--host", default=os.environ.get("MYSQL_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("MYSQL_PORT", "3307")))
    parser.add_argument("--user", default=os.environ.get("MYSQL_USER", "openemr"))
    parser.add_argument("--password", default=os.environ.get("MYSQL_PASS", ""))
    parser.add_argument("--database", default=os.environ.get("MYSQL_DATABASE", "openemr"))
    parser.add_argument("--fixtures", default=str(FIXTURES))
    parser.add_argument("--skip-patients", action="store_true")
    parser.add_argument("--skip-medications", action="store_true")
    parser.add_argument("--skip-allergies", action="store_true")
    parser.add_argument("--skip-vitals", action="store_true")
    parser.add_argument("--skip-labs", action="store_true")
    args = parser.parse_args()

    fixtures = Path(args.fixtures)
    if not (fixtures / "patients.csv").is_file():
        print(f"ERROR: patients.csv not found under {fixtures}")
        sys.exit(1)

    print(f"Connecting to {args.host}:{args.port}/{args.database} as {args.user}...")
    conn = pymysql.connect(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database,
        charset="utf8mb4",
        autocommit=False,
    )
    cur = conn.cursor()

    try:
        # Disable strict mode so missing NOT NULL columns get defaults instead of errors
        cur.execute("SET SESSION sql_mode = 'NO_ENGINE_SUBSTITUTION'")

        print("\n[1/5] Importing patients...")
        if args.skip_patients:
            # Rebuild pid_map from existing data
            cur.execute("SELECT pubpid, pid FROM patient_data WHERE pubpid != '' AND pubpid IS NOT NULL")
            pid_map = {row[0]: row[1] for row in cur.fetchall()}
            print(f"  → skipped ({len(pid_map)} already in DB)")
        else:
            pid_map = import_patients(cur, fixtures / "patients.csv")
            print(f"  → {len(pid_map)} patients processed")

        print("\n[2/5] Importing medications...")
        if args.skip_medications:
            print("  → skipped")
        else:
            n = import_medications(cur, fixtures / "medications.csv", pid_map)
            print(f"  → {n} medication rows")

        print("\n[3/5] Importing allergies...")
        if args.skip_allergies:
            print("  → skipped")
        else:
            n = import_allergies(cur, fixtures / "allergies.csv", pid_map)
            print(f"  → {n} allergy rows")

        print("\n[4/5] Importing vitals...")
        if args.skip_vitals:
            print("  → skipped")
        else:
            n = import_vitals(cur, fixtures / "observations.csv", pid_map)
            print(f"  → {n} vitals encounters")

        print("\n[5/5] Importing lab observations...")
        if args.skip_labs:
            print("  → skipped")
        else:
            n = import_labs(cur, fixtures / "observations.csv", pid_map)
            print(f"  → {n} lab observation rows")

        conn.commit()
        print("\n✓ Import complete. All changes committed.")
        print(f"\nSeed patient UUID:  f1aa52b9-aded-3188-9386-012244805ebf")
        print(f"OpenEMR patient ID: {pid_map.get('f1aa52b9-aded-3188-9386-012244805ebf', 'not found')}")

    except Exception as e:
        conn.rollback()
        print(f"\nERROR: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
