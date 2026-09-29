#!/usr/bin/env python3
"""
handlers/disco_load_history.py — GET /discos/{disco_id}/load-history?range=24h
Rolling per-DISCO load allocation, for the Live page's daily profile chart.
"""

from data_api_utils import execute_with_retry, unwrap_records, json_response

RANGE_HOURS = {
    "24h": 24,
    "7d": 24 * 7,
    "30d": 24 * 30,
}

SQL_TEMPLATE = """
    SELECT observed_hour, allocation_mw
    FROM obs.niggrid_disco_load_hourly
    WHERE disco_id = :disco_id
      AND observed_hour > now() - interval '{hours} hours'
    ORDER BY observed_hour
"""


def get_disco_load_history(event, context):
    disco_id = event.get("pathParameters", {}).get("disco_id")
    if not disco_id:
        return json_response(400, {"error": "disco_id is required"})

    query_params = event.get("queryStringParameters") or {}
    range_key = query_params.get("range", "24h")
    hours = RANGE_HOURS.get(range_key)

    if hours is None:
        return json_response(400, {"error": f"Invalid range. Use one of: {list(RANGE_HOURS.keys())}"})

    sql = SQL_TEMPLATE.format(hours=hours)

    try:
        response = execute_with_retry(
            sql, parameters=[{"name": "disco_id", "value": {"stringValue": disco_id}}]
        )
        records = unwrap_records(response)
        return json_response(200, {"disco_id": disco_id, "range": range_key, "points": records})
    except Exception as e:
        print(f"ERROR: {e}")
        return json_response(500, {"error": "Internal error retrieving load history"})