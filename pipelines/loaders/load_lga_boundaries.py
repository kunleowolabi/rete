#!/usr/bin/env python3
"""
load_lga_boundaries.py — Load LGA polygon geometry into geo.lga_boundary.

Source: the same GRID3 shapefile used for the Phase 1.1 attribute load
(data/sources/grid3/). That load only took lgacode/name/state/area —
geometry was deferred to Stage D. This is Stage D.

Usage:
    export DATABASE_URL=postgresql://rete_admin:pass@127.0.0.1:5433/rete
    python load_lga_boundaries.py [--shapefile path] [--dry-run]
"""

import argparse
import os
import sys

import geopandas as gpd
import psycopg2
from psycopg2.extras import execute_values


def main():
    parser = argparse.ArgumentParser(description="Load LGA boundary geometry into Aurora")
    parser.add_argument(
        "--shapefile",
        default="data/sources/grid3/grid3_nga_boundary_vacclgas.shp",
    )
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
    print(f"Read {len(gdf)} LGA polygons")

    # Force everything to MultiPolygon (some are Polygon, some already MultiPolygon)
    gdf["geometry"] = gdf["geometry"].apply(
        lambda g: g if g.geom_type == "MultiPolygon" else gpd.GeoSeries([g]).unary_union
    )

    rows = [(row["lgacode"], row["geometry"].wkt) for _, row in gdf.iterrows()]
    print(f"Prepared {len(rows)} rows")

    if args.dry_run:
        print("\n=== DRY RUN — first 3 ===")
        for lga_code, wkt in rows[:3]:
            print(f"  {lga_code}: {wkt[:60]}...")
        return

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    try:
        execute_values(
            cur,
            """INSERT INTO geo.lga_boundary (lga_code, geom)
               VALUES %s
               ON CONFLICT (lga_code) DO NOTHING""",
            rows,
            template="(%s, ST_Multi(ST_GeomFromText(%s, 4326)))",
        )
        conn.commit()
        print(f"\nDone. {len(rows)} LGA boundaries loaded.")

    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()