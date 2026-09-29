#!/usr/bin/env python3
"""
handlers/disco_live_allocation.py — GET /discos/live-allocation
Latest per-DISCO load allocation from niggrid, for the Live page.
"""

from data_api_utils import execute_with_retry, unwrap_records, json_response

SQL = """
    WITH latest AS (
        SELECT max(observed_hour) AS observed_hour
        FROM obs.niggrid_disco_load_hourly
    )
    SELECT
        d.disco_id,
        d.name,
        l.allocation_mw,
        l.total_mw,
        l.observed_hour
    FROM obs.niggrid_disco_load_hourly l
    JOIN ref.disco d ON d.disco_id = l.disco_id
    JOIN latest ON l.observed_hour = latest.observed_hour
    ORDER BY l.allocation_mw DESC
"""


def get_disco_live_allocation(event, context):
    try:
        response = execute_with_retry(SQL)
        records = unwrap_records(response)
        return json_response(200, records)
    except Exception as e:
        print(f"ERROR: {e}")
        return json_response(500, {"error": "Internal error retrieving live allocation"})