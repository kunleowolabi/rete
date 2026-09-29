#!/usr/bin/env python3
"""
handlers/generation_history.py — GET /generation/history?range=24h
Rolling national generation total, for the Overview page chart.
"""

from data_api_utils import execute_with_retry, unwrap_records, json_response

RANGE_HOURS = {
    "24h": 24,
    "7d": 24 * 7,
    "30d": 24 * 30,
}


def get_generation_history(event, context):
    query_params = event.get("queryStringParameters") or {}
    range_key = query_params.get("range", "24h")
    hours = RANGE_HOURS.get(range_key)

    if hours is None:
        return json_response(400, {"error": f"Invalid range. Use one of: {list(RANGE_HOURS.keys())}"})

    sql = f"""
        SELECT DISTINCT observed_hour, dashboard_total_mw, reporting_gencos
        FROM obs.niggrid_plant_hourly
        WHERE observed_hour > now() - interval '{hours} hours'
        ORDER BY observed_hour
    """

    try:
        response = execute_with_retry(sql)
        records = unwrap_records(response)
        return json_response(200, {"range": range_key, "points": records})
    except Exception as e:
        print(f"ERROR: {e}")
        return json_response(500, {"error": "Internal error retrieving generation history"})