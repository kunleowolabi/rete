#!/usr/bin/env python3
"""
load_osm_plants.py — Load OSM power plant geometry into geo.osm_plant.

Source: earth-osm extraction from Geofabrik Nigeria snapshot (2026-09-26).
Applies a hand-verified crosswalk for the ~20 plants matched by name/capacity
against ref.plant during manual review. Everything else loads as unmatched —
still stored, still mappable, just not yet linked to our plant reference.

Usage:
    export DATABASE_URL=postgresql://rete_admin:pass@127.0.0.1:5433/rete
    python load_osm_plants.py [--csv path] [--dry-run]
"""

import argparse
import ast
import os
import sys

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

SNAPSHOT_DATE = "2026-09-26"
SOURCE_TITLE = f"OpenStreetMap Nigeria power infrastructure (Geofabrik snapshot {SNAPSHOT_DATE})"

# OSM tags.name -> our plant_id, hand-verified during manual review
PLANT_CROSSWALK = {
    "Afam VI Power Plant": ("afam_1", "high"),
    "Alaoji Power Plant": ("alaoji", "high"),
    "Azura-Edo IPP": ("azura_edo", "exact"),
    "Dadin Kowa Hydro Power Plant": ("dadin_kowa", "high"),
    "Egbin Thermal Power Station": ("egbin", "exact"),
    "Geregu I Power Plant": ("geregu_1", "exact"),
    "Geregu II Power Plant": ("geregu_2", "high"),
    "Ibom Power Plant": ("ibom_power", "high"),
    "Ihovbor Power Plant": ("ihovbor", "exact"),
    "Jebba Hydroelectric Power Station": ("jebba", "exact"),
    "Kainji Hydro Power Plant": ("kainji", "exact"),
    "Kashimbila Dam": ("kashimbila", "high"),
    "Maiduguri Emeregency Power Plant": ("mepp", "high"),
    "Okpai Power Plant": ("okpai", "exact"),
    "Olorunsogo I Power Plant": ("olorunsogo_1", "exact"),
    "Olorunsogo II Power Plant": ("olorunsogo_2", "high"),
    "Omoku I Power Plant": ("omoku", "exact"),
    "Omotosho I Power Plant": ("omotosho_1", "exact"),
    "Omotosho II Power Plant": ("omotosho_2", "high"),
    "Paras Energy": ("paras_energy", "exact"),
    "Sapele II Power Plant": ("sapele_nipp", "high"),
    "Shiroro Hydroelectric Power Station": ("shiroro", "exact"),
    "Zungeru Hydro Power Station": ("zungeru", "exact"),
}


def parse_geom(lonlat_str: str):
    """
    Parse the lonlat field into a WKT geometry string.
    A single [lon, lat] pair -> POINT. A list of pairs -> POLYGON (closed ring)
    or LINESTRING depending on whether first == last coordinate.
    """
    try:
        coords = ast.literal_eval(lonlat_str)
    except (ValueError, SyntaxError):
        return None

    if not coords:
        return None

    # Single point: [lon, lat]
    if isinstance(coords[0], (int, float)):
        lon, lat = coords
        return f"POINT({lon} {lat})"

    # Multiple points: list of [lon, lat] pairs
    if len(coords) == 1:
        lon, lat = coords[0]
        return f"POINT({lon} {lat})"

    pts = ", ".join(f"{lon} {lat}" for lon, lat in coords)
    if coords[0] == coords[-1]:
        return f"POLYGON(({pts}))"
    return f"LINESTRING({pts})"


def main():
    parser = argparse.ArgumentParser(description="Load OSM plant geometry into Aurora")
    parser.add_argument("--csv", default="data/sources/osm/nigeria_plant.csv")
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

    rows = []
    skipped_geom = 0
    for _, r in df.iterrows():
        wkt = parse_geom(r["lonlat"])
        if wkt is None:
            skipped_geom += 1
            continue

        name = r["tags.name"] if pd.notna(r["tags.name"]) else None
        crosswalk_entry = PLANT_CROSSWALK.get(name)
        if crosswalk_entry:
            plant_id, confidence = crosswalk_entry
        else:
            plant_id, confidence = None, "unmatched"

        rows.append((
            int(r["id"]),
            plant_id,
            name,
            r["tags.operator"] if pd.notna(r["tags.operator"]) else None,
            r["tags.plant:source"] if pd.notna(r["tags.plant:source"]) else None,
            r["tags.plant:output:electricity"] if pd.notna(r["tags.plant:output:electricity"]) else None,
            wkt,
            confidence,
        ))

    matched = sum(1 for r in rows if r[1] is not None)
    print(f"Parsed {len(rows)} rows with valid geometry ({skipped_geom} skipped — no parseable geometry)")
    print(f"Matched to ref.plant: {matched} / {len(rows)}")

    if args.dry_run:
        print("\n=== DRY RUN — matched rows ===")
        for r in rows:
            if r[1] is not None:
                print(f"  {r[1]:15s} <- {r[2]:35s} ({r[7]})")
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
        else:
            cur.execute("""
                INSERT INTO meta.source_document (
                    source_id, title, document_type, nature, licence, extraction_status
                ) VALUES ('osm', %s, 'geojson', 'crowdsourced', 'ODbL', 'complete')
                RETURNING source_document_id
            """, (SOURCE_TITLE,))
            source_doc_id = cur.fetchone()[0]
        print(f"Source document: {source_doc_id}")

        insert_rows = [
            (osm_id, plant_id, name, operator, fuel, output, wkt, confidence, source_doc_id)
            for osm_id, plant_id, name, operator, fuel, output, wkt, confidence in rows
        ]

        execute_values(
            cur,
            """INSERT INTO geo.osm_plant (
                osm_id, plant_id, name, operator, fuel_source,
                output_capacity_raw, geom, match_confidence, source_document_id
            ) VALUES %s
            ON CONFLICT (osm_id) DO NOTHING""",
            insert_rows,
            template="(%s, %s, %s, %s, %s, %s, ST_GeomFromText(%s, 4326), %s, %s)",
        )

        conn.commit()
        print(f"\nDone. {len(insert_rows)} plant geometries loaded ({matched} matched to ref.plant).")

    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()