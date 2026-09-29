#!/usr/bin/env python3
"""
handlers/discos.py — GET /discos
Lists all DISCOs with their latest headline metrics, for filters/selectors.
"""

from data_api_utils import execute_with_retry, unwrap_records, json_response

SQL = """
    SELECT
        d.disco_id,
        d.name,
        array_to_string(d.states_served, ', ') AS states_served,
        latest.period_start,
        latest.observed_offtake_mwh_per_h,
        latest.fitted_demand_mwh_per_h,
        latest.suppressed_gap_mwh_per_h
    FROM ref.disco d
    LEFT JOIN LATERAL (
        SELECT period_start, observed_offtake_mwh_per_h,
               fitted_demand_mwh_per_h, suppressed_gap_mwh_per_h
        FROM est.disco_demand_estimate e
        WHERE e.disco_id = d.disco_id
        ORDER BY period_start DESC
        LIMIT 1
    ) latest ON true
    ORDER BY d.name
"""


def get_discos(event, context):
    try:
        response = execute_with_retry(SQL)
        records = unwrap_records(response)
        return json_response(200, records)
    except Exception as e:
        print(f"ERROR: {e}")
        return json_response(500, {"error": "Internal error retrieving discos"})