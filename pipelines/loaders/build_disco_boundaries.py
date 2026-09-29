#!/usr/bin/env python3
"""
build_disco_boundaries.py — Dissolve state boundaries into DISCO franchise
polygons via geo.lga_boundary + ref.state + ref.disco.states_served.

Lagos (split Eko/Ikeja) and Kwara (partial Ibadan coverage) are approximated
at full-state resolution and flagged is_approximate=TRUE — see the extension
document (three-proxy decomposition) for why a cleaner split needs actual
DISCO franchise data we don't have yet.

Usage:
    export DATABASE_URL=postgresql://rete_admin:pass@127.0.0.1:5433/rete
    python build_disco_boundaries.py [--dry-run]
"""

import argparse
import os
import sys

import psycopg2

APPROXIMATE_DISCOS = {
    "eko": "Lagos assigned in full; actual Eko territory is southern/island Lagos only. Needs real franchise polygon.",
    "ikeja": "Lagos assigned in full; actual Ikeja territory is mainland/northern Lagos only. Needs real franchise polygon.",
    "ibadan": "Kwara coverage is partial per NERC; state assigned in full pending a better split.",
}


def main():
    parser = argparse.ArgumentParser(description="Build DISCO boundaries by dissolving states")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db_url = os.environ.get("DATABASE_URL")
    if not db_url and not args.dry_run:
        print("ERROR: DATABASE_URL not set. Export it or use --dry-run.")
        sys.exit(1)

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    cur.execute("SELECT disco_id, states_served FROM ref.disco")
    discos = cur.fetchall()
    print(f"Found {len(discos)} DISCOs to process")

    if args.dry_run:
        for disco_id, states in discos:
            note = APPROXIMATE_DISCOS.get(disco_id, "")
            flag = " [APPROXIMATE]" if note else ""
            print(f"  {disco_id:8s} <- {states}{flag}")
        cur.close()
        conn.close()
        return

    try:
        for disco_id, states in discos:
            is_approx = disco_id in APPROXIMATE_DISCOS
            note = APPROXIMATE_DISCOS.get(disco_id)

            # Dissolve: union all LGA polygons for every state in states_served
            cur.execute("""
                INSERT INTO geo.disco_boundary (disco_id, geom, is_approximate, approximation_note)
                SELECT %s,
                       ST_Multi(ST_Union(lb.geom)),
                       %s,
                       %s
                FROM geo.lga_boundary lb
                JOIN ref.lga l ON l.lga_code = lb.lga_code
                WHERE l.state_code = ANY(
                    SELECT state_code FROM ref.state WHERE name = ANY(%s)
                )
                ON CONFLICT (disco_id) DO UPDATE
                SET geom = EXCLUDED.geom,
                    is_approximate = EXCLUDED.is_approximate,
                    approximation_note = EXCLUDED.approximation_note
            """, (disco_id, is_approx, note, states))
            print(f"  Built {disco_id} ({'approximate' if is_approx else 'clean'})")

        conn.commit()
        print(f"\nDone. {len(discos)} DISCO boundaries built.")

    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()