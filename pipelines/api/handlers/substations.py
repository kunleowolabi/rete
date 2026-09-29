#!/usr/bin/env python3
"""
handlers/substations.py — GET /substations
Substation markers for the transmission layer.
"""

from data_api_utils import execute_with_retry, unwrap_records, json_response

SQL = """
    SELECT
        osm_id,
        name,
        voltage_raw,
        substation_type,
        ST_AsGeoJSON(geom) AS geometry
    FROM geo.osm_substation
    ORDER BY name NULLS LAST
"""


def get_substations(event, context):
    try:
        response = execute_with_retry(SQL)
        records = unwrap_records(response)
        return json_response(200, records)
    except Exception as e:
        print(f"ERROR: {e}")
        return json_response(500, {"error": "Internal error retrieving substations"})