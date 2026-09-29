#!/usr/bin/env python3
"""
handlers/disco_timeseries.py — GET /discos/{disco_id}/timeseries
Historical trend: offtake, fitted demand, gap, ATC&C, billing efficiency.
"""

from data_api_utils import execute_with_retry, unwrap_records, json_response

SQL = """
    SELECT
        q.period_start,
        q.period_end,
        q.energy_offtake_mwh_per_h,
        q.actual_atcc_pct,
        q.billing_efficiency_pct,
        e.fitted_demand_mwh_per_h,
        e.suppressed_gap_mwh_per_h
    FROM obs.nerc_disco_quarterly q
    LEFT JOIN est.disco_demand_estimate e
        ON e.disco_id = q.disco_id AND e.period_start = q.period_start
    WHERE q.disco_id = :disco_id
    ORDER BY q.period_start
"""


def get_disco_timeseries(event, context):
    disco_id = event.get("pathParameters", {}).get("disco_id")
    if not disco_id:
        return json_response(400, {"error": "disco_id is required"})

    try:
        response = execute_with_retry(
            SQL, parameters=[{"name": "disco_id", "value": {"stringValue": disco_id}}]
        )
        records = unwrap_records(response)
        return json_response(200, records)
    except Exception as e:
        print(f"ERROR: {e}")
        return json_response(500, {"error": "Internal error retrieving timeseries"})