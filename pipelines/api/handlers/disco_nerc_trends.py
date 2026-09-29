#!/usr/bin/env python3
"""
handlers/disco_nerc_trends.py — GET /discos/{disco_id}/nerc-trends
ATC&C, billing efficiency, metering rate over time — separate from the
demand/gap trend so the frontend can chart them independently.
"""

from data_api_utils import execute_with_retry, unwrap_records, json_response

SQL = """
    SELECT
        period_start,
        period_end,
        actual_atcc_pct,
        myto_target_atcc_pct,
        billing_efficiency_pct,
        energy_accounting_eff_pct,
        collection_efficiency_pct,
        metering_rate_pct,
        customers_active,
        customers_metered
    FROM obs.nerc_disco_quarterly
    WHERE disco_id = :disco_id
    ORDER BY period_start
"""


def get_disco_nerc_trends(event, context):
    disco_id = event.get("pathParameters", {}).get("disco_id")
    if not disco_id:
        return json_response(400, {"error": "disco_id is required"})

    try:
        response = execute_with_retry(
            SQL, parameters=[{"name": "disco_id", "value": {"stringValue": disco_id}}]
        )
        records = unwrap_records(response)
        return json_response(200, {"disco_id": disco_id, "points": records})
    except Exception as e:
        print(f"ERROR: {e}")
        return json_response(500, {"error": "Internal error retrieving NERC trends"})