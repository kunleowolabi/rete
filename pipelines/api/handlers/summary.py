#!/usr/bin/env python3
"""
handlers/summary.py — GET /summary
National headline numbers as of the latest fitted period, plus the
system-level figures (available capacity, wheeling capacity, population,
record peak) from ref.system_figure.
"""

from data_api_utils import execute_with_retry, unwrap_records, json_response

SQL_SUMMARY = """
    SELECT
        e.period_start,
        e.period_end,
        round(sum(e.observed_offtake_mwh_per_h) / 1000.0, 2) AS total_observed_gw,
        round(sum(e.fitted_demand_mwh_per_h) / 1000.0, 2) AS total_demand_gw,
        round(sum(e.suppressed_gap_mwh_per_h) / 1000.0, 2) AS total_gap_gw,
        count(DISTINCT e.disco_id) AS disco_count
    FROM est.disco_demand_estimate e
    WHERE e.period_start = (SELECT max(period_start) FROM est.disco_demand_estimate)
    GROUP BY e.period_start, e.period_end
"""

SQL_FIGURES = """
    SELECT figure_key, value, unit, as_of
    FROM ref.system_figure
"""


def get_summary(event, context):
    try:
        records = unwrap_records(execute_with_retry(SQL_SUMMARY))
        if not records:
            return json_response(404, {"error": "No data available"})

        figures = {
            r["figure_key"]: {"value": r["value"], "unit": r["unit"], "as_of": r["as_of"]}
            for r in unwrap_records(execute_with_retry(SQL_FIGURES))
        }

        return json_response(200, {**records[0], "figures": figures})
    except Exception as e:
        print(f"ERROR: {e}")
        return json_response(500, {"error": "Internal error retrieving summary"})