#!/usr/bin/env python3
"""
build_state_boundaries.py — Dissolve LGA polygons into state boundaries,
precomputed once so the API never runs ST_Union at request time.

Usage:
    export DATABASE_URL=postgresql://rete_admin:pass@127.0.0.1:5433/rete
    python build_state_boundaries.py [--dry-run]
"""

import argparse
import os
import sys

import psycopg2


def main():
    parser = argparse.ArgumentParser(description="Build state boundaries by dissolving LGAs")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db_url = os.environ.get("DATABASE_URL")
    if not db_url and not args.dry_run:
        print("ERROR: DATABASE_URL not set. Export it or use --dry-run.")
        sys.exit(1)

    if args.dry_run:
        print("Would dissolve geo.lga_boundary -> geo.state_boundary for all 37 states")
        return

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO geo.state_boundary (state_code, geom)
            SELECT l.state_code, ST_Multi(ST_Union(lb.geom))
            FROM geo.lga_boundary lb
            JOIN ref.lga l ON l.lga_code = lb.lga_code
            GROUP BY l.state_code
            ON CONFLICT (state_code) DO UPDATE SET geom = EXCLUDED.geom
        """)
        conn.commit()
        cur.execute("SELECT count(*) FROM geo.state_boundary")
        count = cur.fetchone()[0]
        print(f"Done. {count} state boundaries built.")

    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()