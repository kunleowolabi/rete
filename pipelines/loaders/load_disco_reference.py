#!/usr/bin/env python3
"""
load_disco_reference.py — Load the 12 DISCO reference rows into ref.disco.

Run this BEFORE load_nerc_disco_quarterly.py, since that loader's FK
depends on ref.disco being populated first.

Usage:
    export DATABASE_URL=postgresql://rete_admin:pass@127.0.0.1:5433/rete
    python load_disco_reference.py [--dry-run]
"""

import argparse
import os
import sys

import psycopg2
from psycopg2.extras import execute_values

# disco_id, name, states_served, ring_fenced_note
DISCOS = [
    ("aba",    "Aba Power (ABEDC)",                          ["Abia"],
     "Ring-fenced: 9 LGAs in Aba metro only. Rest of Abia served by Enugu (EEDC)."),
    ("abuja",  "Abuja Electricity Distribution Co (AEDC)",    ["FCT", "Kogi", "Nasarawa", "Niger"], None),
    ("benin",  "Benin Electricity Distribution Co (BEDC)",    ["Edo", "Delta", "Ondo", "Ekiti"], None),
    ("eko",    "Eko Electricity Distribution Co (EKEDC)",     ["Lagos"],
     "Covers Lagos Island, Lekki, Victoria Island, Apapa, Festac, southern axis. Lagos split with Ikeja."),
    ("enugu",  "Enugu Electricity Distribution Co (EEDC)",    ["Enugu", "Anambra", "Ebonyi", "Imo", "Abia"],
     "Abia coverage excludes the Aba ring-fence (served by Aba Power)."),
    ("ibadan", "Ibadan Electricity Distribution Co (IBEDC)",  ["Oyo", "Ogun", "Osun", "Kwara"],
     "Kwara coverage is partial."),
    ("ikeja",  "Ikeja Electric (IE)",                         ["Lagos"],
     "Covers Lagos mainland, northern Lagos — Ikeja, Ikorodu, Shomolu. Lagos split with Eko."),
    ("jos",    "Jos Electricity Distribution Co (JED)",       ["Plateau", "Bauchi", "Benue", "Gombe"], None),
    ("kaduna", "Kaduna Electricity Distribution Co (KAEDC)",  ["Kaduna", "Kebbi", "Sokoto", "Zamfara"], None),
    ("kano",   "Kano Electricity Distribution Co (KEDCO)",    ["Kano", "Jigawa", "Katsina"], None),
    ("ph",     "Port Harcourt Electricity Distribution Co (PHED)", ["Rivers", "Bayelsa", "Cross River", "Akwa Ibom"], None),
    ("yola",   "Yola Electricity Distribution Co (YEDC)",     ["Adamawa", "Borno", "Taraba", "Yobe"], None),
]


def main():
    parser = argparse.ArgumentParser(description="Load ref.disco reference table")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db_url = os.environ.get("DATABASE_URL")
    if not db_url and not args.dry_run:
        print("ERROR: DATABASE_URL not set. Export it or use --dry-run.")
        sys.exit(1)

    if args.dry_run:
        print(f"Would insert {len(DISCOS)} DISCOs:")
        for disco_id, name, states, note in DISCOS:
            print(f"  {disco_id:8s} {name:45s} {states}")
            if note:
                print(f"           note: {note}")
        return

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    try:
        rows = [(d[0], d[1], d[2], d[3]) for d in DISCOS]
        execute_values(
            cur,
            """INSERT INTO ref.disco (disco_id, name, states_served, ring_fenced_note)
               VALUES %s
               ON CONFLICT (disco_id) DO NOTHING""",
            rows,
        )
        conn.commit()
        print(f"Done. {len(rows)} DISCOs inserted (or already present).")

    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()