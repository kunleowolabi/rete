#!/usr/bin/env python3
"""
handlers/boundaries_country.py — GET /boundaries/country
Nigeria's national outline as a single GeoJSON feature, precomputed from
the dissolved state boundaries (geo.country_boundary).
"""

import json

from data_api_utils import execute_with_retry, unwrap_records, json_response

SIMPLIFY_TOLERANCE = 0.01

SQL = f"""
    SELECT ST_AsGeoJSON(ST_SimplifyPreserveTopology(geom, {SIMPLIFY_TOLERANCE})) AS geometry
    FROM geo.country_boundary
    WHERE country_code = 'NG'
"""


def get_boundaries_country(event, context):
    try:
        records = unwrap_records(execute_with_retry(SQL))
        if not records:
            return json_response(404, {"error": "No country boundary available"})

        feature = {
            "type": "Feature",
            "properties": {"country_code": "NG", "name": "Nigeria"},
            "geometry": json.loads(records[0]["geometry"]),
        }
        return json_response(200, {"type": "FeatureCollection", "features": [feature]})
    except Exception as e:
        print(f"ERROR: {e}")
        return json_response(500, {"error": "Internal error retrieving country boundary"})