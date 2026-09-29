#!/usr/bin/env python3
"""
handlers/boundaries_states.py — GET /boundaries/states
State polygons, precomputed via build_state_boundaries.py, simplified
to fit within the Data API's 1MB response limit.
"""

from data_api_utils import execute_with_retry, unwrap_records, json_response

SIMPLIFY_TOLERANCE = 0.01

SQL = f"""
    SELECT
        s.state_code,
        s.name,
        s.zone,
        ST_AsGeoJSON(ST_SimplifyPreserveTopology(b.geom, {SIMPLIFY_TOLERANCE})) AS geometry
    FROM geo.state_boundary b
    JOIN ref.state s ON s.state_code = b.state_code
    ORDER BY s.name
"""


def get_boundaries_states(event, context):
    import json as json_lib
    try:
        response = execute_with_retry(SQL)
        records = unwrap_records(response)

        features = [
            {
                "type": "Feature",
                "properties": {
                    "state_code": r["state_code"],
                    "name": r["name"],
                    "zone": r["zone"],
                },
                "geometry": json_lib.loads(r["geometry"]),
            }
            for r in records
        ]
        return json_response(200, {"type": "FeatureCollection", "features": features})
    except Exception as e:
        print(f"ERROR: {e}")
        return json_response(500, {"error": "Internal error retrieving state boundaries"})