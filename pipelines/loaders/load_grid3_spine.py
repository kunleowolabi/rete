#!/usr/bin/env python3
"""
load_grid3_spine.py — Load GRID3 LGA boundaries into ref.state and ref.lga.

This is the root load — every subsequent table depends on these codes.

Source: GRID3 Nigeria "NGA Operational LGA Boundaries" shapefile
        https://data.grid3.org
        Licence: CC-BY-4.0

Usage:
    export DATABASE_URL=postgresql://user:pass@host:5432/rete
    python load_grid3_spine.py [--shapefile path/to/shapefile.shp] [--dry-run]

Expects the shapefile at data/sources/grid3/grid3_nga_boundary_vacclgas.shp
relative to the project root, unless overridden with --shapefile.

Idempotent: uses ON CONFLICT DO NOTHING. Safe to re-run.
"""

import argparse
import hashlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import psycopg2
from psycopg2.extras import execute_values

# ── Geopolitical zone mapping ────────────────────────────────────────────────
# 37 states (36 + FCT) → 6 zones. Keyed on statecode from the shapefile.

ZONE_MAP = {
    # North Central
    "BE": "North Central",  # Benue
    "KO": "North Central",  # Kogi
    "KW": "North Central",  # Kwara
    "NA": "North Central",  # Nasarawa
    "NI": "North Central",  # Niger
    "PL": "North Central",  # Plateau
    "FC": "North Central",  # FCT
    # North East
    "AD": "North East",     # Adamawa
    "BA": "North East",     # Bauchi
    "BR": "North East",     # Borno
    "GO": "North East",     # Gombe
    "TA": "North East",     # Taraba
    "YO": "North East",     # Yobe
    # North West
    "JI": "North West",     # Jigawa
    "KD": "North West",     # Kaduna
    "KN": "North West",     # Kano
    "KT": "North West",     # Katsina
    "KB": "North West",     # Kebbi
    "SO": "North West",     # Sokoto
    "ZA": "North West",     # Zamfara
    # South East
    "AB": "South East",     # Abia
    "AN": "South East",     # Anambra
    "EB": "South East",     # Ebonyi
    "EN": "South East",     # Enugu
    "IM": "South East",     # Imo
    # South South
    "AK": "South South",    # Akwa Ibom
    "BY": "South South",    # Bayelsa
    "CR": "South South",    # Cross River
    "DE": "South South",    # Delta
    "ED": "South South",    # Edo
    "RI": "South South",    # Rivers
    # South West
    "EK": "South West",     # Ekiti
    "LA": "South West",     # Lagos
    "OG": "South West",     # Ogun
    "ON": "South West",     # Ondo
    "OS": "South West",     # Osun
    "OY": "South West",     # Oyo
}


def compute_checksum(filepath: str) -> str:
    """SHA-256 of the .shp file for source_document deduplication."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def load_shapefile(shapefile_path: str) -> gpd.GeoDataFrame:
    """Read and validate the GRID3 LGA shapefile."""
    gdf = gpd.read_file(shapefile_path)

    # Validate expectations from eval 01 inspection
    assert len(gdf) == 774, f"Expected 774 LGAs, got {len(gdf)}"
    assert gdf["lgacode"].is_unique, "lgacode is not unique"
    assert gdf["statename"].nunique() == 37, f"Expected 37 states, got {gdf['statename'].nunique()}"
    assert gdf.crs.to_epsg() == 4326, f"Expected EPSG:4326, got {gdf.crs}"
    assert gdf.geometry.is_valid.all(), "Invalid geometries found"

    # Compute area in km² using UTM zone 32N (covers Nigeria)
    gdf_proj = gdf.to_crs(epsg=32632)
    gdf["area_km2"] = (gdf_proj.geometry.area / 1e6).round(3)

    # Verify all statecodes have a zone mapping
    unmapped = set(gdf["statecode"].unique()) - set(ZONE_MAP.keys())
    assert not unmapped, f"States missing zone mapping: {unmapped}"

    return gdf


def main():
    parser = argparse.ArgumentParser(description="Load GRID3 LGA spine into Rete database")
    parser.add_argument(
        "--shapefile",
        default="data/sources/grid3/grid3_nga_boundary_vacclgas.shp",
        help="Path to the GRID3 LGA shapefile",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate and print without writing to DB")
    args = parser.parse_args()

    db_url = os.environ.get("DATABASE_URL")
    if not db_url and not args.dry_run:
        print("ERROR: DATABASE_URL not set. Export it or use --dry-run.")
        sys.exit(1)

    shapefile_path = args.shapefile
    if not Path(shapefile_path).exists():
        print(f"ERROR: Shapefile not found at {shapefile_path}")
        print("Place the GRID3 shapefile there, or use --shapefile to specify the path.")
        sys.exit(1)

    # ── Load and validate ────────────────────────────────────────────────
    print(f"Reading {shapefile_path}...")
    gdf = load_shapefile(shapefile_path)
    checksum = compute_checksum(shapefile_path)
    print(f"  774 LGAs, 37 states — validated")
    print(f"  Checksum: {checksum[:30]}...")

    # ── Build state rows ─────────────────────────────────────────────────
    states = (
        gdf[["statecode", "statename"]]
        .drop_duplicates()
        .sort_values("statecode")
    )
    states["zone"] = states["statecode"].map(ZONE_MAP)

    state_rows = [
        (row["statecode"], row["statename"], row["zone"])
        for _, row in states.iterrows()
    ]

    # ── Build LGA rows ───────────────────────────────────────────────────
    lga_rows = [
        (row["lgacode"], row["lganame"], row["statecode"], row["area_km2"])
        for _, row in gdf.iterrows()
    ]

    if args.dry_run:
        print(f"\n=== DRY RUN ===")
        print(f"Would insert {len(state_rows)} states:")
        for code, name, zone in state_rows:
            print(f"  {code:3s}  {name:20s}  {zone}")
        print(f"\nWould insert {len(lga_rows)} LGAs (first 10):")
        for code, name, state, area in lga_rows[:10]:
            print(f"  {code:6s}  {name:25s}  {state}  {area:,.1f} km²")
        print(f"  ... and {len(lga_rows) - 10} more")
        print(f"\nTotal area: {sum(r[3] for r in lga_rows):,.0f} km²")
        return

    # ── Write to database ────────────────────────────────────────────────
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    now = datetime.now(timezone.utc)

    try:
        # 1. Register source document (check-then-insert; partial unique index
        #    on checksum doesn't support ON CONFLICT directly)
        cur.execute(
            "SELECT source_document_id FROM meta.source_document WHERE checksum = %s",
            (checksum,)
        )
        row = cur.fetchone()
        if row:
            source_doc_id = row[0]
            print(f"  Source document already exists: {source_doc_id}")
        else:
            cur.execute("""
                INSERT INTO meta.source_document (
                    source_id, title, document_type, nature, licence,
                    published_at, s3_uri, checksum, extraction_status
                ) VALUES (
                    'grid3',
                    'NGA Operational LGA Boundaries (GRID3 v2.0)',
                    'shapefile',
                    'compiled',
                    'CC-BY-4.0',
                    '2021-01-01',
                    NULL,
                    %s,
                    'complete'
                )
                RETURNING source_document_id
            """, (checksum,))
            source_doc_id = cur.fetchone()[0]
            print(f"  Source document registered: {source_doc_id}")

        # 2. Create ingestion run
        cur.execute("""
            INSERT INTO meta.ingestion_run (source_id, status)
            VALUES ('grid3', 'running')
            RETURNING ingestion_run_id
        """)
        run_id = cur.fetchone()[0]

        # 3. Insert states
        execute_values(
            cur,
            """
            INSERT INTO ref.state (state_code, name, zone)
            VALUES %s
            ON CONFLICT (state_code) DO NOTHING
            """,
            state_rows,
        )
        print(f"  ref.state: {len(state_rows)} rows inserted")

        # 4. Insert LGAs (with source_document_id)
        lga_rows_full = [
            (code, name, state, area, source_doc_id)
            for code, name, state, area in lga_rows
        ]
        execute_values(
            cur,
            """
            INSERT INTO ref.lga (lga_code, name, state_code, area_km2, source_document_id)
            VALUES %s
            ON CONFLICT (lga_code) DO NOTHING
            """,
            lga_rows_full,
        )
        print(f"  ref.lga:   {len(lga_rows)} rows inserted")

        # 5. Complete the ingestion run
        cur.execute("""
            UPDATE meta.ingestion_run
            SET completed_at = now(),
                status = 'success',
                rows_written = %s
            WHERE ingestion_run_id = %s
        """, (len(state_rows) + len(lga_rows), run_id))

        conn.commit()
        print(f"\nDone. Ingestion run: {run_id}")
        print(f"  {len(state_rows)} states, {len(lga_rows)} LGAs loaded.")

    except Exception as e:
        conn.rollback()
        # Mark the run as failed
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
