#!/usr/bin/env python3
"""
handlers/lines.py — GET /lines
Transmission line geometry for the map. Simplified to fit Data API's 1MB cap
— unsimplified was 1019.7 KB, right at the ceiling (see map features review list).
"""

from data_api_utils import execute_with_retry, unwrap_records, json_response

SIMPLIFY_TOLERANCE = 0.005

SQL = f"""
    SELECT
        osm_id,
        voltage_tier,
        length_km,
        ST_AsGeoJSON(ST_SimplifyPreserveTopology(geom, {SIMPLIFY_TOLERANCE})) AS geometry
    FROM geo.osm_line
    ORDER BY voltage_tier
"""


def get_lines(event, context):
    try:
        response = execute_with_retry(SQL)
        records = unwrap_records(response)
        return json_response(200, records)
    except Exception as e:
        print(f"ERROR: {e}")
        return json_response(500, {"error": "Internal error retrieving lines"})