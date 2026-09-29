#!/usr/bin/env python3
"""
router.py — Single Lambda entry point for all Rete API routes.
"""

import json

from handlers.summary import get_summary
from handlers.generation_current import get_generation_current
from handlers.generation_history import get_generation_history
from handlers.discos import get_discos
from handlers.discos_ranked import get_discos_ranked
from handlers.disco_live_allocation import get_disco_live_allocation
from handlers.disco_allocation_history import get_disco_allocation_history
from handlers.disco_detail import get_disco_detail
from handlers.disco_timeseries import get_disco_timeseries
from handlers.disco_load_history import get_disco_load_history
from handlers.disco_nerc_trends import get_disco_nerc_trends
from handlers.infrastructure_summary import get_infrastructure_summary
from handlers.genco_current import get_genco_current
from handlers.plants import get_plants
from handlers.substations import get_substations
from handlers.lines import get_lines
from handlers.minigrids import get_minigrids
from handlers.boundaries_discos import get_boundaries_discos
from handlers.boundaries_states import get_boundaries_states
from handlers.boundaries_country import get_boundaries_country
from handlers.genco_utilization import get_genco_utilization

ROUTES = {
    "GET /summary": get_summary,
    "GET /generation/current": get_generation_current,
    "GET /generation/history": get_generation_history,
    "GET /discos": get_discos,
    "GET /discos/ranked": get_discos_ranked,
    "GET /discos/live-allocation": get_disco_live_allocation,
    "GET /discos/allocation-history": get_disco_allocation_history,
    "GET /discos/{disco_id}": get_disco_detail,
    "GET /discos/{disco_id}/timeseries": get_disco_timeseries,
    "GET /discos/{disco_id}/load-history": get_disco_load_history,
    "GET /discos/{disco_id}/nerc-trends": get_disco_nerc_trends,
    "GET /infrastructure/summary": get_infrastructure_summary,
    "GET /genco/current": get_genco_current,
    "GET /plants": get_plants,
    "GET /substations": get_substations,
    "GET /lines": get_lines,
    "GET /minigrids": get_minigrids,
    "GET /boundaries/discos": get_boundaries_discos,
    "GET /boundaries/states": get_boundaries_states,
    "GET /boundaries/country": get_boundaries_country,
    "GET /genco/utilization": get_genco_utilization,
}


def handler(event, context):
    route_key = event.get("routeKey", "")
    print(f"Routing: {route_key}")

    fn = ROUTES.get(route_key)
    if fn is None:
        print(f"No handler registered for routeKey: {route_key}")
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": f"Route not found: {route_key}"}),
        }

    try:
        return fn(event, context)
    except Exception as e:
        print(f"UNHANDLED ERROR in {route_key}: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "Internal server error"}),
        }