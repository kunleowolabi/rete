#!/usr/bin/env python3
"""
load_nerc_disco_quarterly.py — Load NERC quarterly DISCO commercial data
from CSV into obs.nerc_disco_quarterly.

Source: NERC quarterly reports, extracted during Paper 2's disequilibrium
model research. Covers 2017Q3-2026Q1, 362 rows, 12 DISCOs.

Usage:
    export DATABASE_URL=postgresql://rete_admin:pass@127.0.0.1:5433/rete
    python load_nerc_disco_quarterly.py [--csv path/to/file.csv] [--dry-run]

Requires ref.disco to be populated first (load_disco_reference.py).
"""

import argparse
import os
import sys
from datetime import date

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

# CSV disco name -> our disco_id
DISCO_NAME_MAP = {
    "Aba": "aba",
    "Abuja": "abuja",
    "Benin": "benin",
    "Eko": "eko",
    "Enugu": "enugu",
    "Ibadan": "ibadan",
    "Ikeja": "ikeja",
    "Jos": "jos",
    "Kaduna": "kaduna",
    "Kano": "kano",
    "Port Harcourt": "ph",
    "Yola": "yola",
}

QUARTER_END_MONTH_DAY = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}


def period_to_dates(year: int, quarter: int) -> tuple[date, date]:
    """Convert year+quarter to period_start and period_end dates."""
    start_month = (quarter - 1) * 3 + 1
    period_start = date(year, start_month, 1)
    end_month, end_day = QUARTER_END_MONTH_DAY[quarter]
    period_end = date(year, end_month, end_day)
    return period_start, period_end


def clean_numeric(val):
    """Convert pandas NaN to None for psycopg2."""
    if pd.isna(val):
        return None
    return float(val)


def clean_int(val):
    if pd.isna(val):
        return None
    return int(val)


def main():
    parser = argparse.ArgumentParser(
        description="Load NERC quarterly DISCO data from CSV into Aurora"
    )
    parser.add_argument(
        "--csv",
        default="data/sources/nerc/nerc_disco_quarterly_clean.csv",
        help="Path to the CSV file",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db_url = os.environ.get("DATABASE_URL")
    if not db_url and not args.dry_run:
        print("ERROR: DATABASE_URL not set. Export it or use --dry-run.")
        sys.exit(1)

    if not os.path.exists(args.csv):
        print(f"ERROR: CSV not found at {args.csv}")
        sys.exit(1)

    # ── Load and validate CSV ───────────────────────────────────────────
    df = pd.read_csv(args.csv)
    print(f"Read {len(df)} rows from {args.csv}")

    unmapped = set(df["disco"].unique()) - set(DISCO_NAME_MAP.keys())
    if unmapped:
        print(f"ERROR: Unmapped disco names found: {unmapped}")
        sys.exit(1)

    df["disco_id"] = df["disco"].map(DISCO_NAME_MAP)

    # ── Build rows ───────────────────────────────────────────────────────
    rows = []
    for _, r in df.iterrows():
        period_start, period_end = period_to_dates(int(r["year"]), int(r["quarter"]))
        rows.append((
            r["disco_id"],
            period_start,
            period_end,
            clean_numeric(r["energy_offtake_mwh_h"]),
            clean_numeric(r["offtake_pct"]),
            clean_numeric(r["energy_received_gwh"]),
            clean_numeric(r["energy_billed_gwh"]),
            clean_numeric(r["billing_efficiency_pct"]),
            None,  # energy_accounting_eff_pct — not in this CSV
            None,  # revenue_billed_ngn_bn — not in this CSV
            None,  # revenue_collected_ngn_bn — not in this CSV
            None,  # collection_efficiency_pct — not in this CSV
            clean_numeric(r["myto_target_atcc_pct"]),
            clean_numeric(r["atcc_pct"]),
            clean_int(r["total_customers"]),
            clean_int(r["metered_customers"]),
            clean_numeric(r["metering_rate_pct"]),
            "csv_import_paper2_panel",  # nerc_tables_ref
        ))

    print(f"Prepared {len(rows)} rows")
    print(f"Date range: {rows[0][1]} to {rows[-1][2]}" if rows else "")

    if args.dry_run:
        print("\n=== DRY RUN — first 5 rows ===")
        for row in rows[:5]:
            print(f"  {row[0]:8s} {row[1]} to {row[2]}  offtake={row[3]}")
        return

    # ── Load into database ───────────────────────────────────────────────
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    try:
        # Register source document
        cur.execute(
            "SELECT source_document_id FROM meta.source_document WHERE title = %s",
            ("NERC Quarterly Reports 2017Q3-2026Q1 (Paper 2 panel extract)",)
        )
        row = cur.fetchone()
        if row:
            source_doc_id = row[0]
            print(f"Source document already exists: {source_doc_id}")
        else:
            cur.execute("""
                INSERT INTO meta.source_document (
                    source_id, title, document_type, nature, licence,
                    extraction_status
                ) VALUES (
                    'nerc_quarterly',
                    'NERC Quarterly Reports 2017Q3-2026Q1 (Paper 2 panel extract)',
                    'csv',
                    'compiled',
                    'public',
                    'manual'
                )
                RETURNING source_document_id
            """)
            source_doc_id = cur.fetchone()[0]
            print(f"Source document registered: {source_doc_id}")

        cur.execute("""
            INSERT INTO meta.ingestion_run (source_id, status)
            VALUES ('nerc_quarterly', 'running')
            RETURNING ingestion_run_id
        """)
        run_id = cur.fetchone()[0]

        rows_with_ids = [row + (source_doc_id, run_id) for row in rows]

        execute_values(
            cur,
            """INSERT INTO obs.nerc_disco_quarterly (
                disco_id, period_start, period_end,
                energy_offtake_mwh_per_h, offtake_performance_pct,
                energy_received_gwh, energy_billed_gwh, billing_efficiency_pct,
                energy_accounting_eff_pct, revenue_billed_ngn_bn,
                revenue_collected_ngn_bn, collection_efficiency_pct,
                myto_target_atcc_pct, actual_atcc_pct,
                customers_active, customers_metered, metering_rate_pct,
                nerc_tables_ref, source_document_id, ingestion_run_id
            ) VALUES %s
            ON CONFLICT (disco_id, period_start, source_document_id) DO NOTHING""",
            rows_with_ids,
        )

        cur.execute("""
            UPDATE meta.ingestion_run
            SET completed_at = now(), status = 'success', rows_written = %s
            WHERE ingestion_run_id = %s
        """, (len(rows), run_id))

        conn.commit()
        print(f"\nDone. Ingestion run: {run_id}")
        print(f"  {len(rows)} rows inserted (or skipped as duplicates).")

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