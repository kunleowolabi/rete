#!/usr/bin/env python3
"""
handlers/genco_current.py — GET /genco/current
Latest hour's generation grouped by GenCo, for the Live page's breakdown.
reporting_count is GenCos with output > 0 this hour; universe_count is every
GenCo with at least one plant on record, so "reporting" can be read as a
fraction of the whole fleet, not just of who bothered to log in.
"""

from data_api_utils import execute_with_retry, unwrap_records, json_response

SQL_BREAKDOWN = """
    SELECT g.genco_id, g.name, g.ownership, sum(h.generation_mw) AS mw
    FROM obs.niggrid_plant_hourly h
    JOIN ref.plant p ON p.plant_id = h.plant_id
    JOIN ref.genco g ON g.genco_id = p.genco_id
    WHERE h.observed_hour = (SELECT max(observed_hour) FROM obs.niggrid_plant_hourly)
    GROUP BY g.genco_id, g.name, g.ownership
    ORDER BY mw DESC
"""

SQL_UNIVERSE = """
    SELECT count(DISTINCT genco_id) AS n FROM ref.plant WHERE genco_id IS NOT NULL
"""


def get_genco_current(event, context):
    try:
        breakdown = unwrap_records(execute_with_retry(SQL_BREAKDOWN))
        universe = unwrap_records(execute_with_retry(SQL_UNIVERSE))

        reporting = sum(1 for r in breakdown if float(r["mw"] or 0) > 0)
        universe_count = universe[0]["n"] if universe else None

        return json_response(200, {
            "gencos": breakdown,
            "reporting_count": reporting,
            "universe_count": universe_count,
        })
    except Exception as e:
        print(f"ERROR: {e}")
        return json_response(500, {"error": "Internal error retrieving GenCo breakdown"})