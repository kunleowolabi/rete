#!/usr/bin/env python3
"""
load_disco_demand_estimate.py — Load Paper 2's disequilibrium model fitted
panel into est.disco_demand_estimate.

Source: "Estimating Suppressed Electricity Demand in a Rationed Grid" —
the Fair-Jaffee/Maddala-Nelson disequilibrium model fitted on 154 DISCO-
quarters (2022Q4-2026Q1). This is a MODEL OUTPUT, not a raw observation —
values are in MWh/h to match the paper's units.

Usage:
    export DATABASE_URL=postgresql://rete_admin:pass@127.0.0.1:5433/rete
    python load_disco_demand_estimate.py [--csv path] [--dry-run]

Requires ref.disco to be populated first.
"""

import argparse
import os
import sys
from datetime import date

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

DISCO_NAME_MAP = {
    "Abuja": "abuja", "Benin": "benin", "Eko": "eko", "Enugu": "enugu",
    "Ibadan": "ibadan", "Ikeja": "ikeja", "Jos": "jos", "Kaduna": "kaduna",
    "Kano": "kano", "Port Harcourt": "ph", "Yola": "yola",
}

QUARTER_END_MONTH_DAY = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}

MODEL_VERSION = "v1_lagos_group_igr_2023_static"
MODEL_SPEC_NOTE = "Lagos-group IGR elasticity, static 2023 IGR (headline)"
SOURCE_TITLE = "Estimating Suppressed Electricity Demand in a Rationed Grid: A Disequilibrium Approach for Nigeria (Owolabi, 2026)"


def period_to_dates(year: int, quarter: int) -> tuple[date, date]:
    start_month = (quarter - 1) * 3 + 1
    period_start = date(year, start_month, 1)
    end_month, end_day = QUARTER_END_MONTH_DAY[quarter]
    period_end = date(year, end_month, end_day)
    return period_start, period_end


def main():
    parser = argparse.ArgumentParser(
        description="Load Paper 2's disequilibrium model panel into Aurora"
    )
    parser.add_argument(
        "--csv",
        default="data/sources/research/paper2_fitted_panel.csv",
        help="Path to the fitted panel CSV",
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

    df = pd.read_csv(args.csv)
    print(f"Read {len(df)} rows from {args.csv}")

    unmapped = set(df["disco"].unique()) - set(DISCO_NAME_MAP.keys())
    if unmapped:
        print(f"ERROR: Unmapped disco names: {unmapped}")
        sys.exit(1)

    df["disco_id"] = df["disco"].map(DISCO_NAME_MAP)

    rows = []
    for _, r in df.iterrows():
        period_start, period_end = period_to_dates(int(r["year"]), int(r["quarter"]))
        rows.append((
            r["disco_id"],
            period_start,
            period_end,
            float(r["Q"]),
            float(r["D_hat"]),
            float(r["S_hat"]),
            float(r["pi_demand"]),
            float(r["suppressed"]),
            MODEL_VERSION,
            MODEL_SPEC_NOTE,
        ))

    print(f"Prepared {len(rows)} rows")
    print(f"DISCOs: {df['disco_id'].nunique()}, periods: {df['period'].nunique()}")

    # Sanity check against the paper's headline aggregate figures
    avg_q = df["Q"].mean()
    avg_dhat = df["D_hat"].mean()
    avg_gap = df["suppressed"].mean()
    print(f"\nPanel averages (MWh/h): Q={avg_q:.1f}, D_hat={avg_dhat:.1f}, gap={avg_gap:.1f}")
    print(f"  Paper reports (GW): Q=3.43, D_hat=5.34, gap=1.91")
    print(f"  Panel averages (GW): Q={avg_q/1000:.2f}, D_hat={avg_dhat/1000:.2f}, gap={avg_gap/1000:.2f}")

    if args.dry_run:
        print("\n=== DRY RUN — first 5 rows ===")
        for row in rows[:5]:
            print(f"  {row[0]:8s} {row[1]}  Q={row[3]:.1f}  D_hat={row[4]:.1f}  gap={row[7]:.1f}")
        return

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    try:
        cur.execute(
            "SELECT source_document_id FROM meta.source_document WHERE title = %s",
            (SOURCE_TITLE,)
        )
        row = cur.fetchone()
        if row:
            source_doc_id = row[0]
            print(f"\nSource document already exists: {source_doc_id}")
        else:
            cur.execute("""
                INSERT INTO meta.source_document (
                    source_id, title, document_type, nature, licence,
                    extraction_status
                ) VALUES (
                    'rete_research', %s, 'csv', 'modelled', 'public', 'manual'
                )
                RETURNING source_document_id
            """, (SOURCE_TITLE,))
            source_doc_id = cur.fetchone()[0]
            print(f"\nSource document registered: {source_doc_id}")

        cur.execute("""
            INSERT INTO meta.ingestion_run (source_id, status)
            VALUES ('rete_research', 'running')
            RETURNING ingestion_run_id
        """)
        run_id = cur.fetchone()[0]

        rows_with_ids = [row + (source_doc_id, run_id) for row in rows]

        execute_values(
            cur,
            """INSERT INTO est.disco_demand_estimate (
                disco_id, period_start, period_end,
                observed_offtake_mwh_per_h, fitted_demand_mwh_per_h,
                fitted_supply_mwh_per_h, demand_regime_probability,
                suppressed_gap_mwh_per_h, model_version, model_spec_note,
                source_document_id, ingestion_run_id
            ) VALUES %s
            ON CONFLICT (disco_id, period_start, model_version) DO NOTHING""",
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