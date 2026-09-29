#!/usr/bin/env python3
"""
load_osm_lines.py — Load OSM transmission line geometry into geo.osm_line.
"""

import argparse
import ast
import os
import sys
from math import radians, sin, cos, sqrt, atan2

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

SOURCE_TITLE = "OpenStreetMap Nigeria power infrastructure (Geofabrik snapshot 2026-09-26)"

VOLTAGE_TIER_MAP = {
    "330000": "330kV",
    "132000": "132kV",
    "33000": "33kV",
    "11000": "11kV",
}


def parse_linestring(lonlat_str: str):
    try:
        coords = ast.literal_eval(lonlat_str)
    except (ValueError, SyntaxError):
        return None, 0.0
    if not coords or len(coords) < 2:
        return None, 0.0

    pts = ", ".join(f"{lon} {lat}" for lon, lat in coords)
    wkt = f"LINESTRING({pts})"

    total_km = 0.0
    R = 6371
    for i in range(len(coords) - 1):
        lon1, lat1 = coords[i]
        lon2, lat2 = coords[i + 1]
        dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
        a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
        total_km += R * 2 * atan2(sqrt(a), sqrt(1 - a))

    return wkt, total_km


def normalize_tier(voltage_raw):
    if pd.isna(voltage_raw):
        return "unknown"
    v = str(voltage_raw)
    if ";" in v:
        tiers = [VOLTAGE_TIER_MAP.get(part, part) for part in v.split(";")]
        return "+".join(tiers)
    return VOLTAGE_TIER_MAP.get(v, "unknown")


def main():
    parser = argparse.ArgumentParser(description="Load OSM line geometry into Aurora")
    parser.add_argument("--csv", default="data/sources/osm/nigeria_line.csv")
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
        wkt, length_km = parse_linestring(r["lonlat"])
        if wkt is None:
            skipped += 1
            continue
        tier = normalize_tier(r["tags.voltage"])
        rows.append((
            int(r["id"]),
            r["tags.operator"] if pd.notna(r["tags.operator"]) else None,
            str(r["tags.voltage"]) if pd.notna(r["tags.voltage"]) else None,
            tier,
            round(length_km, 2),
            wkt,
        ))

    print(f"Parsed {len(rows)} rows ({skipped} skipped)")
    total_km = sum(r[4] for r in rows)
    print(f"Total length: {total_km:.0f} km")
    for tier in ["330kV", "132kV", "33kV", "11kV", "unknown"]:
        tier_km = sum(r[4] for r in rows if r[3] == tier)
        print(f"  {tier}: {tier_km:.0f} km")

    if args.dry_run:
        print("\n=== DRY RUN — first 5 ===")
        for r in rows[:5]:
            print(f"  tier={r[3]:8s} length={r[4]:.1f}km")
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

        insert_rows = [(osm_id, op, volt, tier, length_km, wkt, source_doc_id)
                        for osm_id, op, volt, tier, length_km, wkt in rows]

        execute_values(
            cur,
            """INSERT INTO geo.osm_line (
                osm_id, operator, voltage_raw, voltage_tier, length_km, geom, source_document_id
            ) VALUES %s
            ON CONFLICT (osm_id) DO NOTHING""",
            insert_rows,
            template="(%s, %s, %s, %s, %s, ST_GeomFromText(%s, 4326), %s)",
        )

        conn.commit()
        print(f"\nDone. {len(insert_rows)} lines loaded.")

    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()