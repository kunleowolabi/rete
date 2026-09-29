#!/usr/bin/env python3
"""
load_osm_substations.py — Load OSM substation geometry into geo.osm_substation.
"""

import argparse
import ast
import os
import sys

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

SOURCE_TITLE = "OpenStreetMap Nigeria power infrastructure (Geofabrik snapshot 2026-09-26)"


def parse_point(lonlat_str: str):
    try:
        coords = ast.literal_eval(lonlat_str)
    except (ValueError, SyntaxError):
        return None
    if not coords:
        return None
    if isinstance(coords[0], (int, float)):
        lon, lat = coords
        return f"POINT({lon} {lat})"
    # Polygon/area substation — use centroid of the ring
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return f"POINT({sum(lons)/len(lons)} {sum(lats)/len(lats)})"


def main():
    parser = argparse.ArgumentParser(description="Load OSM substation geometry into Aurora")
    parser.add_argument("--csv", default="data/sources/osm/nigeria_substation.csv")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db_url = os.environ.get("DATABASE_URL")
    if not db_url and not args.dry_run:
        print("ERROR: DATABASE_URL not set. Export it or use --dry-run.")
        sys.exit(1)

    df = pd.read_csv(args.csv)
    print(f"Read {len(df)} rows from {args.csv}")

    rows = []
    skipped = 0
    for _, r in df.iterrows():
        wkt = parse_point(r["lonlat"])
        if wkt is None:
            skipped += 1
            continue
        rows.append((
            int(r["id"]),
            r["tags.name"] if pd.notna(r["tags.name"]) else None,
            r["tags.operator"] if pd.notna(r["tags.operator"]) else None,
            str(r["tags.voltage"]) if pd.notna(r["tags.voltage"]) else None,
            r["tags.substation"] if pd.notna(r["tags.substation"]) else None,
            wkt,
        ))

    voltage_tagged = sum(1 for r in rows if r[3] is not None)
    print(f"Parsed {len(rows)} rows ({skipped} skipped)")
    print(f"Voltage-tagged: {voltage_tagged} / {len(rows)} ({voltage_tagged/len(rows)*100:.1f}%)")

    if args.dry_run:
        print("\n=== DRY RUN — first 10 ===")
        for r in rows[:10]:
            print(f"  {r[1] or '(unnamed)':30s} voltage={r[3]}  type={r[4]}")
        return

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    try:
        cur.execute(
            "SELECT source_document_id FROM meta.source_document WHERE title = %s",
            (SOURCE_TITLE,)
        )
        row = cur.fetchone()
        source_doc_id = row[0] if row else None
        if not source_doc_id:
            cur.execute("""
                INSERT INTO meta.source_document (
                    source_id, title, document_type, nature, licence, extraction_status
                ) VALUES ('osm', %s, 'geojson', 'crowdsourced', 'ODbL', 'complete')
                RETURNING source_document_id
            """, (SOURCE_TITLE,))
            source_doc_id = cur.fetchone()[0]

        insert_rows = [(osm_id, name, op, volt, sub_type, wkt, source_doc_id)
                        for osm_id, name, op, volt, sub_type, wkt in rows]

        execute_values(
            cur,
            """INSERT INTO geo.osm_substation (
                osm_id, name, operator, voltage_raw, substation_type, geom, source_document_id
            ) VALUES %s
            ON CONFLICT (osm_id) DO NOTHING""",
            insert_rows,
            template="(%s, %s, %s, %s, %s, ST_GeomFromText(%s, 4326), %s)",
        )

        conn.commit()
        print(f"\nDone. {len(insert_rows)} substations loaded.")

    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()