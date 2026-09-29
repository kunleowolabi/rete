#!/usr/bin/env python3
"""
handlers/minigrids.py — GET /minigrids
Full minigrid inventory for the map layer and dashboard table.
"""

from data_api_utils import execute_with_retry, unwrap_records, json_response

SQL = """
    SELECT
        minigrid_id,
        community,
        lga_name_raw,
        power_system,
        capacity_kw,
        status,
        condition,
        fund_type,
        project,
        owner,
        connected_to_grid,
        ST_AsGeoJSON(geom) AS geometry
    FROM ref.minigrid
    ORDER BY community
"""


def get_minigrids(event, context):
    try:
        response = execute_with_retry(SQL)
        records = unwrap_records(response)
        return json_response(200, records)
    except Exception as e:
        print(f"ERROR: {e}")
        return json_response(500, {"error": "Internal error retrieving minigrids"})