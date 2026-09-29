#!/usr/bin/env python3
"""
loader_niggrid_plant_hourly.py — Load niggrid hourly data from S3 into Aurora.

Reads JSON files written by scraper_niggrid_plant_hourly.py from the S3 raw
bucket and inserts into obs.niggrid_plant_hourly. Resolves plant names via
ref.plant_alias at load time.

Usage:
    export DATABASE_URL=postgresql://rete_admin:pass@127.0.0.1:5433/rete
    python loader_niggrid_plant_hourly.py [--date 2026-08-28] [--dry-run]

    --date    Date to load (YYYY-MM-DD). Defaults to yesterday.
    --dry-run Show what would be loaded without writing to DB.

Idempotent: uses ON CONFLICT DO NOTHING on (plant_id, observed_hour).
"""

import argparse
import json
import os
import sys
from datetime import datetime, date, timedelta, timezone

import boto3
import psycopg2
from psycopg2.extras import execute_values

S3_BUCKET = os.environ.get("S3_BUCKET", "rete-raw-270269786078")
S3_PREFIX = "niggrid/hourly"


def load_alias_map(cur) -> dict:
    """Build a niggrid_name → plant_id lookup from ref.plant_alias."""
    cur.execute(
        "SELECT alias, plant_id FROM ref.plant_alias WHERE source_id = 'niggrid'"
    )
    return {row[0]: row[1] for row in cur.fetchall()}


def list_s3_files(s3, target_date: date) -> list:
    """List all JSON files in S3 for a given date."""
    prefix = f"{S3_PREFIX}/{target_date.strftime('%Y/%m/%d')}/"
    response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix)

    if "Contents" not in response:
        return []

    files = [
        obj["Key"]
        for obj in response["Contents"]
        if obj["Key"].endswith(".json")
    ]
    return sorted(files)


def read_s3_json(s3, key: str) -> dict:
    """Read and parse a single JSON file from S3."""
    body = s3.get_object(Bucket=S3_BUCKET, Key=key)["Body"].read()
    return json.loads(body)


def main():
    parser = argparse.ArgumentParser(
        description="Load niggrid hourly data from S3 into Aurora"
    )
    parser.add_argument(
        "--date",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
        default=date.today() - timedelta(days=1),
        help="Date to load (YYYY-MM-DD). Defaults to yesterday.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be loaded without writing to DB",
    )
    args = parser.parse_args()

    target_date = args.date
    db_url = os.environ.get("DATABASE_URL")
    if not db_url and not args.dry_run:
        print("ERROR: DATABASE_URL not set. Export it or use --dry-run.")
        sys.exit(1)

    # ── List files from S3 ───────────────────────────────────────────────
    s3 = boto3.client("s3")
    files = list_s3_files(s3, target_date)

    print(f"Date: {target_date}")
    print(f"S3 prefix: {S3_PREFIX}/{target_date.strftime('%Y/%m/%d')}/")
    print(f"Files found: {len(files)}")

    if not files:
        print("No files to load.")
        return

    # ── Gap detection ────────────────────────────────────────────────────
    hours_captured = set()
    for f in files:
        # Key format: niggrid/hourly/2026/08/28/1355.json → extract "13"
        basename = f.rsplit("/", 1)[-1].replace(".json", "")
        if len(basename) == 4 and basename.isdigit():
            hours_captured.add(int(basename[:2]))

    expected_hours = set(range(24))
    missing_hours = expected_hours - hours_captured
    if missing_hours:
        print(f"WARNING: Missing hours: {sorted(missing_hours)}")
    else:
        print("All 24 hours present.")

    # ── Read all files ───────────────────────────────────────────────────
    payloads = []
    for key in files:
        try:
            data = read_s3_json(s3, key)
            payloads.append((key, data))
        except Exception as e:
            print(f"ERROR reading {key}: {e}")

    print(f"Files parsed: {len(payloads)}")

    if args.dry_run:
        # Connect to DB just to resolve aliases
        if db_url:
            conn = psycopg2.connect(db_url)
            alias_map = load_alias_map(conn.cursor())
            conn.close()
        else:
            alias_map = {}
            print("(No DB connection — alias resolution skipped)")

        total_rows = 0
        unresolved = set()
        for key, data in payloads:
            ts = data.get("dashboard_timestamp", "?")
            n_gencos = len(data.get("gencos", []))
            total_mw = data.get("dashboard_total_mw", 0)
            reporting = data.get("reporting_gencos", 0)
            print(f"  {key.rsplit('/', 1)[-1]:12s}  {ts}  "
                  f"{reporting:>2d} reporting  {total_mw:>8.2f} MW  "
                  f"{n_gencos} plants")
            for g in data.get("gencos", []):
                if alias_map and g["name"] not in alias_map:
                    unresolved.add(g["name"])
            total_rows += n_gencos

        print(f"\nWould insert: {total_rows} rows")
        if unresolved:
            print(f"UNRESOLVED aliases ({len(unresolved)}):")
            for name in sorted(unresolved):
                print(f"  - {name}")
        return

    # ── Load into database ───────────────────────────────────────────────
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    try:
        alias_map = load_alias_map(cur)
        print(f"Alias map: {len(alias_map)} entries")

        # Create ingestion run — one per batch (day), not per file
        s3_uri = f"s3://{S3_BUCKET}/{S3_PREFIX}/{target_date.strftime('%Y/%m/%d')}/"
        cur.execute("""
            INSERT INTO meta.ingestion_run (source_id, status, s3_raw_uri)
            VALUES ('niggrid', 'running', %s)
            RETURNING ingestion_run_id
        """, (s3_uri,))
        run_id = cur.fetchone()[0]

        rows = []
        unresolved = set()

        for key, data in payloads:
            dashboard_ts = data.get("dashboard_timestamp")
            captured_at = data.get("captured_at")
            dashboard_total_mw = data.get("dashboard_total_mw")
            reporting_gencos = data.get("reporting_gencos")

            for g in data.get("gencos", []):
                name = g["name"]
                plant_id = alias_map.get(name)

                if not plant_id:
                    unresolved.add(name)
                    continue

                rows.append((
                    plant_id,
                    dashboard_ts,       # observed_hour
                    g["generation_mw"],  # generation_mw
                    reporting_gencos,
                    dashboard_total_mw,
                    captured_at,
                    run_id,
                ))

        if unresolved:
            print(f"WARNING: {len(unresolved)} unresolved aliases:")
            for name in sorted(unresolved):
                print(f"  - {name}")

        # Batch insert with conflict handling
        if rows:
            execute_values(
                cur,
                """INSERT INTO obs.niggrid_plant_hourly (
                    plant_id, observed_hour, generation_mw,
                    reporting_gencos, dashboard_total_mw,
                    captured_at, ingestion_run_id
                ) VALUES %s
                ON CONFLICT (plant_id, observed_hour) DO NOTHING""",
                rows,
            )

        # Complete the ingestion run
        cur.execute("""
            UPDATE meta.ingestion_run
            SET completed_at = now(),
                status = 'success',
                rows_written = %s
            WHERE ingestion_run_id = %s
        """, (len(rows), run_id))

        conn.commit()
        print(f"\nDone. Ingestion run: {run_id}")
        print(f"  Files: {len(payloads)}, Rows inserted: {len(rows)}")
        if missing_hours:
            print(f"  Missing hours: {sorted(missing_hours)}")

    except Exception as e:
        conn.rollback()
        try:
            cur.execute("""
                UPDATE meta.ingestion_run
                SET completed_at = now(), status = 'failed', error_detail = %s
                WHERE ingestion_run_id = %s
            """, (str(e), run_id))
            conn.commit()
        except Exception:
            pass
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()