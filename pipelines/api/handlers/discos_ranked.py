#!/usr/bin/env python3
"""
handlers/discos_ranked.py — GET /discos/ranked
Latest NERC quarter's ATC&C loss and billing efficiency per DISCO, for the
Infrastructure page's distribution-section bar charts.
"""

from data_api_utils import execute_with_retry, unwrap_records, json_response

SQL = """
    SELECT d.disco_id, d.name, q.period_start, q.period_end,
           q.actual_atcc_pct, q.billing_efficiency_pct, q.metering_rate_pct
    FROM ref.disco d
    JOIN LATERAL (
        SELECT * FROM obs.nerc_disco_quarterly nq
        WHERE nq.disco_id = d.disco_id
        ORDER BY period_start DESC LIMIT 1
    ) q ON true
    ORDER BY q.actual_atcc_pct DESC NULLS LAST
"""


def get_discos_ranked(event, context):
    try:
        records = unwrap_records(execute_with_retry(SQL))
        return json_response(200, records)
    except Exception as e:
        print(f"ERROR: {e}")
        return json_response(500, {"error": "Internal error retrieving ranked discos"})