#!/usr/bin/env python3
"""
load_plant_reference.py — Load plant crosswalk into ref.genco, ref.plant,
ref.plant_capacity, and ref.plant_alias.

Master list: niggrid (33 plants).
Capacity source: NERC Q1 2026 quarterly report (28 grid-connected plants).
Alias sources: niggrid + nerc_quarterly.

Usage:
    export DATABASE_URL=postgresql://rete_admin:pass@127.0.0.1:5433/rete
    python load_plant_reference.py [--dry-run]

Idempotent: uses ON CONFLICT DO NOTHING. Safe to re-run.
"""

import argparse
import os
import sys
from datetime import datetime, timezone

import psycopg2
from psycopg2.extras import execute_values

# =============================================================================
# DATA
# =============================================================================

# ── Generation companies ─────────────────────────────────────────────────────
# genco_id, name, ownership ('private'|'ndphc'|'ipp'|'state')
GENCOS = [
    ("transafam",       "TransAfam Power Ltd",                "private"),
    ("mainstream",      "Mainstream Energy Solutions Ltd",     "private"),
    ("egbin_power",     "Egbin Power Plc",                    "private"),
    ("transcorp_power", "Transcorp Power Ltd",                "private"),
    ("amperion",        "Amperion Power Distribution Co Ltd", "private"),
    ("ndphc",           "Niger Delta Power Holding Co",       "ndphc"),
    ("north_south",     "North South Power Co Ltd",           "private"),
    ("zungeru_hydro",   "Zungeru Hydroelectric Power Plc",    "private"),
    ("azura_edo",       "Azura Power West Africa Ltd",        "ipp"),
    ("paras_energy",    "Paras Energy & Natural Resources",   "ipp"),
    ("naoc",            "Nigerian Agip Oil Co (NAOC)",        "ipp"),
    ("ibom_power",      "Ibom Power Co Ltd",                  "state"),
    ("rivers_ipp",      "Rivers State IPP",                   "ipp"),
    ("sapele_power",    "Sapele Power Plc",                   "private"),
    ("gpal",            "Geometric Power Aba Ltd",            "ipp"),
    ("kashimbila",      "Kashimbila Hydroelectric Co",        "private"),
    ("mepp_ipp",        "MEPP IPP Ltd",                       "ipp"),
    ("taopex",          "Taopex Energy Services Co",          "ipp"),
    ("olorunsogo_pwr",  "Olorunsogo Power Co Ltd",            "private"),
    ("omotosho_pwr",    "Omotosho Power Co Ltd",              "private"),
    ("trans_amadi",     "Trans Amadi Power Ltd",              "ipp"),
    ("dadin_kowa",      "Dadin Kowa Hydro",                   "private"),
]

# ── Plants ───────────────────────────────────────────────────────────────────
# plant_id, name, genco_id, fuel_type, plant_type, reporting_status,
# is_grid_connected, niggrid_name, nerc_name, installed_mw (from NERC Q1 2026)
#
# niggrid_name and nerc_name go into ref.plant_alias
# installed_mw goes into ref.plant_capacity

PLANTS = [
    # ── 28 NERC-mapped plants ────────────────────────────────────────────
    ("afam_1",        "Afam VI",              "transafam",       "gas_steam", "genco", "active",           True,  "AFAM VI (GAS/STEAM)",    "Afam_1",         726),
    ("afam_2",        "Afam III Fast Power",  "transafam",       "gas",       "genco", "active",           True,  "AFAM III FAST P",        "Afam_2",         650),
    ("alaoji",        "Alaoji",               "ndphc",           "gas",       "nipp",  "non_operational",  True,  "ALAOJI NIPP (GAS)",      "Alaoji_1",       500),
    ("azura_edo",     "Azura-Edo",            "azura_edo",       "gas",       "ipp",   "active",           True,  "AZURA-EDO IPP (GAS)",    "Ihovbor_2",      461),
    ("dadin_kowa",    "Dadin Kowa",           "dadin_kowa",      "hydro",     "genco", "active",           True,  "DADINKOWA G.S",          "Dadin-Kowa_1",    40),
    ("delta",         "Delta (Ughelli)",      "transcorp_power", "gas",       "genco", "active",           True,  "DELTA (GAS)",            "Delta_1",        900),
    ("egbin",         "Egbin",                "egbin_power",     "steam",     "genco", "active",           True,  "EGBIN (STEAM)",          "Egbin_1",       1320),
    ("geregu_1",      "Geregu Phase 1",       "amperion",        "gas",       "genco", "active",           True,  "GEREGU (GAS)",           "Geregu_1",       435),
    ("geregu_2",      "Geregu Phase 2",       "ndphc",           "gas",       "nipp",  "active",           True,  "GEREGU NIPP (GAS)",      "Geregu_2",       435),
    ("ibom_power",    "Ibom Power",           "ibom_power",      "gas",       "genco", "active",           True,  "IBOM POWER (GAS)",       "Ibom power_1",   190),
    ("igbafo",        "Igbafo (Trans Afam)",  "transafam",       "gas",       "genco", "active",           True,  "TRANS AFAM POWE",        "Igbafo_1",        45),
    ("ihovbor",       "Ihovbor",              "ndphc",           "gas",       "nipp",  "active",           True,  "IHOVBOR NIPP (GAS)",     "Ihovbor_1",      500),
    ("jebba",         "Jebba",                "mainstream",      "hydro",     "genco", "active",           True,  "JEBBA (HYDRO)",          "Jebba_1",        578),
    ("kainji",        "Kainji",               "mainstream",      "hydro",     "genco", "active",           True,  "KAINJI (HYDRO)",         "Kainji_1",       760),
    ("odukpani",      "Odukpani",             "ndphc",           "gas",       "nipp",  "active",           True,  "ODUKPANI NIPP",          "Odukpani_1",     625),
    ("okpai",         "Okpai",                "naoc",            "gas_steam", "ipp",   "active",           True,  "OKPAI (GAS/STEAM)",      "Okpai_1",        480),
    ("olorunsogo_1",  "Olorunsogo Phase 1",   "olorunsogo_pwr",  "gas",       "genco", "active",           True,  "OLORUNSOGO (GAS)",       "Olorunsogo_1",   335),
    ("olorunsogo_2",  "Olorunsogo Phase 2",   "ndphc",           "gas",       "nipp",  "active",           True,  "OLORUNSOGO NIPP",        "Olorunsogo_2",   750),
    ("omoku",         "Omoku",                "ndphc",           "gas",       "nipp",  "active",           True,  "OMOKU (GAS)",            "Omoku_1",        150),
    ("omotosho_1",    "Omotosho Phase 1",     "omotosho_pwr",    "gas",       "genco", "active",           True,  "OMOTOSHO (GAS)",         "Omotosho_1",     335),
    ("omotosho_2",    "Omotosho Phase 2",     "ndphc",           "gas",       "nipp",  "active",           True,  "OMOTOSHO NIPP (GAS)",    "Omotosho_2",     500),
    ("paras_energy",  "Paras Energy",         "paras_energy",    "gas",       "ipp",   "active",           True,  "PARAS ENERGY (GAS)",     "Ikeja_1",        110),
    ("rivers_ipp",    "Rivers IPP",           "rivers_ipp",      "gas",       "ipp",   "active",           True,  "RIVERS IPP (GAS)",       "Rivers_1",       180),
    ("sapele_steam",  "Sapele Steam",         "sapele_power",    "steam",     "genco", "active",           True,  "SAPELE (STEAM)",         "Sapele Steam_1", 720),
    ("sapele_nipp",   "Sapele NIPP",          "ndphc",           "gas",       "nipp",  "active",           True,  "SAPELE NIPP (GAS)",      "Sapele_2",       500),
    ("shiroro",       "Shiroro",              "north_south",     "hydro",     "genco", "active",           True,  "SHIRORO (HYDRO)",        "Shiroro_1",      600),
    ("trans_amadi",   "Trans Amadi",          "trans_amadi",     "gas",       "ipp",   "active",           True,  "TRANS-AMADI (GAS)",      "Trans Amadi_1",  100),
    ("zungeru",       "Zungeru",              "zungeru_hydro",   "hydro",     "genco", "active",           True,  "ZUNGERU",                "Zungeru_1",      700),

    # ── 5 niggrid-only (not in NERC 28) ──────────────────────────────────
    ("gbarain",       "Gbarain",              "ndphc",           "gas",       "nipp",  "non_operational",  True,  "GBARAIN NIPP (GAS)",     None,             None),
    ("gpal",          "GPAL (Aba)",           "gpal",            "gas",       "ipp",   "non_operational",  False, "GPAL (GAS)",             None,             None),
    ("kashimbila",    "Kashimbila",           "kashimbila",      "hydro",     "genco", "non_operational",  False, "KASHIMBILA GS",          None,             None),
    ("mepp",          "MEPP (Maiduguri)",     "mepp_ipp",        "gas",       "ipp",   "island_mode",      False, "MEPP",                   None,             None),
    ("taopex",        "Taopex",               "taopex",          "gas",       "ipp",   "non_operational",  False, "TAOPEX (GAS)",           None,             None),
]


def main():
    parser = argparse.ArgumentParser(description="Load plant reference into Rete database")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print without writing to DB")
    args = parser.parse_args()

    db_url = os.environ.get("DATABASE_URL")
    if not db_url and not args.dry_run:
        print("ERROR: DATABASE_URL not set. Export it or use --dry-run.")
        sys.exit(1)

    # ── Validate data ────────────────────────────────────────────────────
    genco_ids = {g[0] for g in GENCOS}
    for p in PLANTS:
        assert p[2] in genco_ids, f"Plant {p[0]} references unknown genco {p[2]}"
    print(f"Validated: {len(GENCOS)} gencos, {len(PLANTS)} plants")

    if args.dry_run:
        print(f"\n=== DRY RUN ===")
        print(f"\nGenCos ({len(GENCOS)}):")
        for gid, name, own in GENCOS:
            print(f"  {gid:20s} {name:45s} {own}")
        print(f"\nPlants ({len(PLANTS)}):")
        active = [p for p in PLANTS if p[5] == "active"]
        inactive = [p for p in PLANTS if p[5] != "active"]
        print(f"  Active: {len(active)}, Inactive/excluded: {len(inactive)}")
        for p in PLANTS:
            mw = f"{p[9]:,} MW" if p[9] else "—"
            print(f"  {p[0]:18s} {p[1]:25s} {p[3]:10s} {p[5]:18s} {mw:>10s}")
        print(f"\nAliases: {sum(1 for p in PLANTS if p[7])} niggrid + {sum(1 for p in PLANTS if p[8])} NERC")
        return

    # ── Write to database ────────────────────────────────────────────────
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    try:
        # 1. Register NERC Q1 2026 as a source document
        cur.execute(
            "SELECT source_document_id FROM meta.source_document WHERE title = %s",
            ("NERC Quarterly Report Q1 2026",)
        )
        row = cur.fetchone()
        if row:
            nerc_doc_id = row[0]
            print(f"  NERC Q1 2026 doc already exists: {nerc_doc_id}")
        else:
            cur.execute("""
                INSERT INTO meta.source_document (
                    source_id, title, document_type, nature, licence,
                    published_at, extraction_status
                ) VALUES (
                    'nerc_quarterly',
                    'NERC Quarterly Report Q1 2026',
                    'pdf',
                    'compiled',
                    'public',
                    '2026-06-01',
                    'manual'
                )
                RETURNING source_document_id
            """)
            nerc_doc_id = cur.fetchone()[0]
            print(f"  NERC Q1 2026 doc registered: {nerc_doc_id}")

        # 2. Create ingestion run
        cur.execute("""
            INSERT INTO meta.ingestion_run (source_id, status)
            VALUES ('nerc_quarterly', 'running')
            RETURNING ingestion_run_id
        """)
        run_id = cur.fetchone()[0]

        # 3. Insert gencos
        genco_rows = [(gid, name, own) for gid, name, own in GENCOS]
        execute_values(
            cur,
            "INSERT INTO ref.genco (genco_id, name, ownership) VALUES %s ON CONFLICT (genco_id) DO NOTHING",
            genco_rows,
        )
        print(f"  ref.genco: {len(genco_rows)} rows")

        # 4. Insert plants
        plant_rows = [
            (p[0], p[1], p[2], None, p[3], p[4], p[5], None, p[6], None, nerc_doc_id)
            for p in PLANTS
        ]
        execute_values(
            cur,
            """INSERT INTO ref.plant (
                plant_id, name, genco_id, lga_code, fuel_type, plant_type,
                reporting_status, commissioned_on, is_grid_connected,
                location, source_document_id
            ) VALUES %s ON CONFLICT (plant_id) DO NOTHING""",
            plant_rows,
        )
        print(f"  ref.plant: {len(plant_rows)} rows")

        # 5. Insert plant capacities (NERC-mapped plants only)
        capacity_rows = [
            (p[0], nerc_doc_id, p[9], None, "nameplate", "2026-03-31")
            for p in PLANTS if p[9] is not None
        ]
        execute_values(
            cur,
            """INSERT INTO ref.plant_capacity (
                plant_id, source_document_id, installed_mw, available_mw,
                capacity_type, as_of_date
            ) VALUES %s ON CONFLICT (plant_id, source_document_id) DO NOTHING""",
            capacity_rows,
        )
        print(f"  ref.plant_capacity: {len(capacity_rows)} rows")

        # 6. Insert aliases
        alias_rows = []
        for p in PLANTS:
            plant_id, _, _, _, _, _, _, niggrid_name, nerc_name, _ = p
            if niggrid_name:
                alias_rows.append((plant_id, "niggrid", niggrid_name))
            if nerc_name:
                alias_rows.append((plant_id, "nerc_quarterly", nerc_name))
        execute_values(
            cur,
            """INSERT INTO ref.plant_alias (plant_id, source_id, alias)
               VALUES %s ON CONFLICT (source_id, alias) DO NOTHING""",
            alias_rows,
        )
        print(f"  ref.plant_alias: {len(alias_rows)} rows ({sum(1 for p in PLANTS if p[7])} niggrid + {sum(1 for p in PLANTS if p[8])} nerc)")

        # 7. Complete the ingestion run
        total_rows = len(genco_rows) + len(plant_rows) + len(capacity_rows) + len(alias_rows)
        cur.execute("""
            UPDATE meta.ingestion_run
            SET completed_at = now(), status = 'success', rows_written = %s
            WHERE ingestion_run_id = %s
        """, (total_rows, run_id))

        conn.commit()
        print(f"\nDone. Ingestion run: {run_id}")
        print(f"  {len(genco_rows)} gencos, {len(plant_rows)} plants, "
              f"{len(capacity_rows)} capacities, {len(alias_rows)} aliases")

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
