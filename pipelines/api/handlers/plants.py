#!/usr/bin/env python3
"""
handlers/plants.py — GET /plants
Plant markers for the map.
"""

from data_api_utils import execute_with_retry, unwrap_records, json_response

SQL = """
    SELECT
        p.osm_id,
        p.plant_id,
        coalesce(rp.name, p.name) AS name,
        p.fuel_source,
        pc.installed_mw,
        p.match_confidence,
        ST_AsGeoJSON(ST_Centroid(p.geom)) AS geometry
    FROM geo.osm_plant p
    LEFT JOIN ref.plant rp ON rp.plant_id = p.plant_id
    LEFT JOIN ref.plant_capacity pc ON pc.plant_id = p.plant_id
    WHERE p.name IS NOT NULL
    ORDER BY name
"""


def get_plants(event, context):
    try:
        response = execute_with_retry(SQL)
        records = unwrap_records(response)
        return json_response(200, records)
    except Exception as e:
        print(f"ERROR: {e}")
        return json_response(500, {"error": "Internal error retrieving plants"})