#!/usr/bin/env python3
"""
load_minigrids.py — Load the minigrid site inventory (66 sites, uploaded
shapefile) into ref.minigrid.

Source: user-provided shapefile, provenance/date unconfirmed. Cross-referenced
against REA public statements (900+ minigrids under construction nationally
as of 2025) — this dataset is a partial snapshot, not the full national
program. See dashboard caption.

Usage:
    export DATABASE_URL=postgresql://rete_admin:Hayorqunleh@127.0.0.1:5433/rete
    python load_minigrids.py [--shapefile path] [--dry-run]
"""

import argparse
import os
import sys

import geopandas as gpd
import psycopg2
from psycopg2.extras import execute_values

SOURCE_TITLE = "Nigeria minigrid site inventory (user-provided shapefile, provenance unconfirmed)"

# Normalize the messy condition casing to exactly two values
CONDITION_MAP = {
    "Operational": "Operational",
    "Non Operational": "Non Operational",
    "Non operational": "Non Operational",
    "Not Operational": "Non Operational",
}


def main():
    parser = argparse.ArgumentParser(description="Load minigrid inventory into Aurora")
    parser.add_argument("--shapefile", default="data/sources/minigrids/minigrids.shp")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db_url = os.environ.get("DATABASE_URL")
    if not db_url and not args.dry_run:
        print("ERROR: DATABASE_URL not set. Export it or use --dry-run.")
        sys.exit(1)

    if not os.path.exists(args.shapefile):
        print(f"ERROR: Shapefile not found at {args.shapefile}")
        sys.exit(1)

    gdf = gpd.read_file(args.shapefile).to_crs("EPSG:4326")
    print(f"Read {len(gdf)} minigrid sites")

    unmapped_conditions = set(gdf["condition"].dropna().unique()) - set(CONDITION_MAP.keys())
    if unmapped_conditions:
        print(f"ERROR: Unmapped condition values: {unmapped_conditions}")
        sys.exit(1)

    rows = []
    for _, r in gdf.iterrows():
        condition = CONDITION_MAP.get(r["condition"]) if r["condition"] else None
        rows.append((
            r.get("lga_name"),
            r["community"],
            r.get("power_syst"),
            float(r["power_kw"]) if r["power_kw"] == r["power_kw"] else None,  # NaN check
            r.get("status"),
            float(r["number_of_"]) if r["number_of_"] == r["number_of_"] else None,
            r.get("fund_type"),
            r.get("project"),
            r.get("owner"),
            condition,
            r.get("located"),
            r.geometry.wkt,
        ))

    print(f"Prepared {len(rows)} rows")
    condition_counts = gdf["condition"].map(CONDITION_MAP).value_counts()
    print(f"Condition breakdown: {condition_counts.to_dict()}")
    print(f"Total capacity: {gdf['power_kw'].sum():.1f} kW")

    if args.dry_run:
        print("\n=== DRY RUN — first 3 ===")
        for row in rows[:3]:
            print(f"  {row[1]:20s} {row[2]:15s} {row[3]} kW  {row[9]}")
        return

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    try:
        # Register source document
        cur.execute(
            "SELECT source_document_id FROM meta.source_document WHERE title = %s",
            (SOURCE_TITLE,)
        )
        row = cur.fetchone()
        if row:
            source_doc_id = row[0]
        else:
            cur.execute("""
                INSERT INTO meta.source_document (
                    source_id, title, document_type, nature, licence, extraction_status
                ) VALUES ('minigrid_inventory', %s, 'shapefile', 'compiled', 'unknown', 'complete')
                RETURNING source_document_id
            """, (SOURCE_TITLE,))
            source_doc_id = cur.fetchone()[0]
        print(f"Source document: {source_doc_id}")

        # Resolve lga_code by name where possible (best-effort, not enforced)
        cur.execute("SELECT lga_code, name FROM ref.lga")
        lga_lookup = {name.strip().lower(): code for code, name in cur.fetchall()}

        insert_rows = []
        unmatched_lgas = set()
        for row_data in rows:
            lga_name_raw = row_data[0]
            lga_code = lga_lookup.get(lga_name_raw.strip().lower()) if lga_name_raw else None
            if lga_name_raw and not lga_code:
                unmatched_lgas.add(lga_name_raw)
            insert_rows.append((lga_code, lga_name_raw) + row_data[1:] + (source_doc_id,))

        if unmatched_lgas:
            print(f"NOTE: {len(unmatched_lgas)} LGA names didn't match ref.lga exactly: {sorted(unmatched_lgas)[:10]}...")

        execute_values(
            cur,
            """INSERT INTO ref.minigrid (
                lga_code, lga_name_raw, community, power_system, capacity_kw,
                status, beneficiary_count, fund_type, project, owner,
                condition, connected_to_grid, geom, source_document_id
            ) VALUES %s""",
            insert_rows,
            template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, ST_GeomFromText(%s, 4326), %s)",
        )

        conn.commit()
        print(f"\nDone. {len(insert_rows)} minigrid sites loaded.")

    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()