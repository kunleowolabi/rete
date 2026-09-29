#!/usr/bin/env python3
"""
handlers/infrastructure_summary.py — GET /infrastructure/summary
Aggregated infrastructure figures: installed/available capacity, fuel mix,
HV/MV line totals. One payload instead of the client stitching several calls.
"""

from data_api_utils import execute_with_retry, unwrap_records, json_response

SQL_CAPACITY = """
    SELECT
        p.fuel_type,
        count(*) AS plant_count,
        sum(pc.installed_mw) AS installed_mw
    FROM ref.plant p
    LEFT JOIN ref.plant_capacity pc ON pc.plant_id = p.plant_id
    GROUP BY p.fuel_type
    ORDER BY installed_mw DESC NULLS LAST
"""

SQL_TOTALS = """
    SELECT
        sum(pc.installed_mw) AS total_installed_mw,
        count(*) FILTER (WHERE p.reporting_status = 'active') AS active_plants,
        count(*) AS total_plants
    FROM ref.plant p
    LEFT JOIN ref.plant_capacity pc ON pc.plant_id = p.plant_id
"""

SQL_LATEST_AVAILABLE = """
    SELECT DISTINCT observed_hour, dashboard_total_mw
    FROM obs.niggrid_plant_hourly
    ORDER BY observed_hour DESC
    LIMIT 1
"""

SQL_LINES = """
    SELECT
        voltage_tier,
        count(*) AS segment_count,
        round(sum(length_km)::numeric, 1) AS total_length_km
    FROM geo.osm_line
    GROUP BY voltage_tier
    ORDER BY total_length_km DESC
"""

SQL_SUBSTATIONS = """
    SELECT
        substation_type,
        count(*) AS count
    FROM geo.osm_substation
    WHERE substation_type IS NOT NULL
    GROUP BY substation_type
    ORDER BY count DESC
"""


def get_infrastructure_summary(event, context):
    try:
        fuel_mix = unwrap_records(execute_with_retry(SQL_CAPACITY))
        totals = unwrap_records(execute_with_retry(SQL_TOTALS))
        latest_available = unwrap_records(execute_with_retry(SQL_LATEST_AVAILABLE))
        lines = unwrap_records(execute_with_retry(SQL_LINES))
        substations = unwrap_records(execute_with_retry(SQL_SUBSTATIONS))

        return json_response(200, {
            "totals": totals[0] if totals else None,
            "latest_available": latest_available[0] if latest_available else None,
            "fuel_mix": fuel_mix,
            "lines_by_voltage": lines,
            "substations_by_type": substations,
            "note": "MV (33kV) and LV (11kV) line coverage in OSM is sparse — see data page for known limitations.",
        })
    except Exception as e:
        print(f"ERROR: {e}")
        return json_response(500, {"error": "Internal error retrieving infrastructure summary"})