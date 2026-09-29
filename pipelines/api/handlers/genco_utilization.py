#!/usr/bin/env python3
"""
handlers/genco_utilization.py — GET /genco/utilization
Every GenCo with installed capacity on record, current output, and the
resulting utilization ratio — for the Infrastructure page's full GenCo view.
Distinct from /genco/current (Live page), which is a top-output ranking,
not a capacity-relative one.
"""

from data_api_utils import execute_with_retry, unwrap_records, json_response

SQL = """
    WITH plant_installed AS (
        SELECT DISTINCT ON (plant_id) plant_id, installed_mw
        FROM ref.plant_capacity
        ORDER BY plant_id, as_of_date DESC NULLS LAST
    ),
    latest_hour AS (
        SELECT max(observed_hour) AS h FROM obs.niggrid_plant_hourly
    ),
    plant_current AS (
        SELECT plant_id, generation_mw
        FROM obs.niggrid_plant_hourly, latest_hour
        WHERE observed_hour = latest_hour.h
    )
    SELECT
        g.genco_id,
        g.name,
        g.ownership,
        round(sum(coalesce(pc.generation_mw, 0)), 2) AS current_mw,
        round(sum(pi.installed_mw), 2) AS installed_mw,
        round(
            sum(coalesce(pc.generation_mw, 0)) / NULLIF(sum(pi.installed_mw), 0) * 100,
            1
        ) AS utilization_pct
    FROM ref.genco g
    JOIN ref.plant p ON p.genco_id = g.genco_id
    JOIN plant_installed pi ON pi.plant_id = p.plant_id
    LEFT JOIN plant_current pc ON pc.plant_id = p.plant_id
    GROUP BY g.genco_id, g.name, g.ownership
    ORDER BY utilization_pct DESC NULLS LAST
"""


def get_genco_utilization(event, context):
    try:
        records = unwrap_records(execute_with_retry(SQL))
        return json_response(200, records)
    except Exception as e:
        print(f"ERROR: {e}")
        return json_response(500, {"error": "Internal error retrieving GenCo utilization"})