#!/usr/bin/env python3
"""
handlers/disco_detail.py — GET /discos/{disco_id}
Single DISCO detail: boundary geometry + latest quarter's full metrics.
"""

from data_api_utils import execute_with_retry, unwrap_records, json_response

SQL = """
    SELECT
        d.disco_id,
        d.name,
        array_to_string(d.states_served, ', ') AS states_served,
        ST_AsGeoJSON(b.geom) AS boundary_geojson,
        b.is_approximate,
        q.period_start,
        q.period_end,
        q.energy_offtake_mwh_per_h,
        q.energy_received_gwh,
        q.energy_billed_gwh,
        q.billing_efficiency_pct,
        q.actual_atcc_pct,
        q.myto_target_atcc_pct,
        e.fitted_demand_mwh_per_h,
        e.suppressed_gap_mwh_per_h
    FROM ref.disco d
    LEFT JOIN geo.disco_boundary b ON b.disco_id = d.disco_id
    LEFT JOIN LATERAL (
        SELECT * FROM obs.nerc_disco_quarterly nq
        WHERE nq.disco_id = d.disco_id
        ORDER BY period_start DESC LIMIT 1
    ) q ON true
    LEFT JOIN LATERAL (
        SELECT * FROM est.disco_demand_estimate de
        WHERE de.disco_id = d.disco_id
        ORDER BY period_start DESC LIMIT 1
    ) e ON true
    WHERE d.disco_id = :disco_id
"""


def get_disco_detail(event, context):
    disco_id = event.get("pathParameters", {}).get("disco_id")
    if not disco_id:
        return json_response(400, {"error": "disco_id is required"})

    try:
        response = execute_with_retry(
            SQL, parameters=[{"name": "disco_id", "value": {"stringValue": disco_id}}]
        )
        records = unwrap_records(response)
        if not records:
            return json_response(404, {"error": f"DISCO '{disco_id}' not found"})
        return json_response(200, records[0])
    except Exception as e:
        print(f"ERROR: {e}")
        return json_response(500, {"error": "Internal error retrieving disco detail"})