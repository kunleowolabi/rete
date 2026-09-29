#!/usr/bin/env python3
"""
loader_niggrid_disco_load.py — Load niggrid DISCO allocation data from S3
into obs.niggrid_disco_load_hourly.

Resolves niggrid's DISCO names ("Abuja Disco", "PHarcourt Disco") to our
disco_id via a fixed mapping — simpler than the plant alias table since
there are only 11 known names, no ambiguity.

Usage:
    export DATABASE_URL=postgresql://rete_admin:pass@127.0.0.1:5433/rete
    python loader_niggrid_disco_load.py [--date 2026-09-26] [--dry-run]
"""

import argparse
import json
import os
import sys
from datetime import datetime, date, timedelta

import boto3
import psycopg2
from psycopg2.extras import execute_values

S3_BUCKET = os.environ.get("S3_BUCKET", "rete-raw-270269786078")
S3_PREFIX = "niggrid/disco_load"

# niggrid name -> our disco_id
DISCO_NAME_MAP = {
    "Abuja Disco": "abuja",
    "Benin Disco": "benin",
    "Eko Disco": "eko",
    "Enugu Disco": "enugu",
    "Ibadan Disco": "ibadan",
    "Ikeja Disco": "ikeja",
    "Jos Disco": "jos",
    "Kaduna Disco": "kaduna",
    "Kano Disco": "kano",
    "PHarcourt Disco": "ph",
    "Yola Disco": "yola",
}


def list_s3_files(s3, target_date: date) -> list:
    prefix = f"{S3_PREFIX}/{target_date.strftime('%Y/%m/%d')}/"
    response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix)
    if "Contents" not in response:
        return []
    return sorted(
        obj["Key"] for obj in response["Contents"] if obj["Key"].endswith(".json")
    )


def main():
    parser = argparse.ArgumentParser(
        description="Load niggrid DISCO allocation data from S3 into Aurora"
    )
    parser.add_argument(
        "--date",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
        default=date.today() - timedelta(days=1),
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    target_date = args.date
    db_url = os.environ.get("DATABASE_URL")
    if not db_url and not args.dry_run:
        print("ERROR: DATABASE_URL not set. Export it or use --dry-run.")
        sys.exit(1)

    s3 = boto3.client("s3")
    files = list_s3_files(s3, target_date)

    print(f"Date: {target_date}")
    print(f"Files found: {len(files)}")
    if not files:
        print("No files to load.")
        return

    payloads = []
    for key in files:
        try:
            body = s3.get_object(Bucket=S3_BUCKET, Key=key)["Body"].read()
            payloads.append((key, json.loads(body)))
        except Exception as e:
            print(f"ERROR reading {key}: {e}")

    print(f"Files parsed: {len(payloads)}")

    if args.dry_run:
        total_rows = 0
        unresolved = set()
        for key, data in payloads:
            for d in data.get("discos", []):
                if d["name"] not in DISCO_NAME_MAP:
                    unresolved.add(d["name"])
            total_rows += len(data.get("discos", []))
        print(f"Would insert: {total_rows} rows")
        if unresolved:
            print(f"UNRESOLVED names: {sorted(unresolved)}")
        return

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    try:
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
            observed_hour = data.get("dashboard_timestamp")
            captured_at = data.get("captured_at")
            total_mw = data.get("total_mw")

            for d in data.get("discos", []):
                disco_id = DISCO_NAME_MAP.get(d["name"])
                if not disco_id:
                    unresolved.add(d["name"])
                    continue
                rows.append((
                    disco_id, observed_hour, d["allocation_mw"],
                    total_mw, captured_at, run_id,
                ))

        if unresolved:
            print(f"WARNING: unresolved names: {sorted(unresolved)}")

        if rows:
            execute_values(
                cur,
                """INSERT INTO obs.niggrid_disco_load_hourly (
                    disco_id, observed_hour, allocation_mw,
                    total_mw, captured_at, ingestion_run_id
                ) VALUES %s
                ON CONFLICT (disco_id, observed_hour) DO NOTHING""",
                rows,
            )

        cur.execute("""
            UPDATE meta.ingestion_run
            SET completed_at = now(), status = 'success', rows_written = %s
            WHERE ingestion_run_id = %s
        """, (len(rows), run_id))

        conn.commit()
        print(f"\nDone. Ingestion run: {run_id}")
        print(f"  Files: {len(payloads)}, Rows inserted: {len(rows)}")

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