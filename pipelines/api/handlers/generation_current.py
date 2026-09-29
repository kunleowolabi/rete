#!/usr/bin/env python3
"""
handlers/generation_current.py — GET /generation/current
Live national supply vs. modelled demand ceiling.
"""

from data_api_utils import execute_with_retry, unwrap_records, json_response

SQL = """
    WITH latest_scrape AS (
        SELECT DISTINCT observed_hour, dashboard_total_mw, reporting_gencos
        FROM obs.niggrid_plant_hourly
        ORDER BY observed_hour DESC
        LIMIT 1
    ),
    latest_demand AS (
        SELECT period_start, period_end,
               sum(fitted_demand_mwh_per_h) AS total_demand_mwh_per_h
        FROM est.disco_demand_estimate
        WHERE period_start = (SELECT max(period_start) FROM est.disco_demand_estimate)
        GROUP BY period_start, period_end
    )
    SELECT
        s.observed_hour,
        s.dashboard_total_mw,
        s.reporting_gencos,
        d.period_start AS demand_model_period_start,
        d.period_end AS demand_model_period_end,
        round(d.total_demand_mwh_per_h, 2) AS demand_ceiling_mwh_per_h,
        round(d.total_demand_mwh_per_h - s.dashboard_total_mw, 2) AS live_gap_mwh_per_h
    FROM latest_scrape s, latest_demand d
"""


def get_generation_current(event, context):
    try:
        response = execute_with_retry(SQL)
        records = unwrap_records(response)
        if not records:
            return json_response(404, {"error": "No generation data available"})
        return json_response(200, records[0])
    except Exception as e:
        print(f"ERROR: {e}")
        return json_response(500, {"error": "Internal error retrieving current generation"})