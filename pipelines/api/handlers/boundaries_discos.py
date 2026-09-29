#!/usr/bin/env python3
"""
handlers/boundaries_discos.py — GET /boundaries/discos
All DISCO franchise polygons as a GeoJSON FeatureCollection. Simplified to
fit Data API's 1MB cap — unsimplified was 1007.2 KB, right at the ceiling.
"""

from data_api_utils import execute_with_retry, unwrap_records, json_response

SIMPLIFY_TOLERANCE = 0.01

SQL = f"""
    SELECT
        d.disco_id,
        d.name,
        b.is_approximate,
        ST_AsGeoJSON(ST_SimplifyPreserveTopology(b.geom, {SIMPLIFY_TOLERANCE})) AS geometry
    FROM geo.disco_boundary b
    JOIN ref.disco d ON d.disco_id = b.disco_id
    ORDER BY d.name
"""


def get_boundaries_discos(event, context):
    import json as json_lib
    try:
        response = execute_with_retry(SQL)
        records = unwrap_records(response)

        features = [
            {
                "type": "Feature",
                "properties": {
                    "disco_id": r["disco_id"],
                    "name": r["name"],
                    "is_approximate": r["is_approximate"],
                },
                "geometry": json_lib.loads(r["geometry"]),
            }
            for r in records
        ]
        return json_response(200, {"type": "FeatureCollection", "features": features})
    except Exception as e:
        print(f"ERROR: {e}")
        return json_response(500, {"error": "Internal error retrieving disco boundaries"})