#!/usr/bin/env python3
"""
scraper_niggrid_plant_hourly.py — Capture niggrid.org generation data to S3.

Runs as a Lambda function (triggered by EventBridge at :55 each hour)
or locally for testing (python scraper_niggrid_plant_hourly.py [--local]).

Flow:
    1. GET https://niggrid.org/
    2. Parse HTML spans for time, total MW, reporting count, per-plant MW
    3. Write timestamped JSON to s3://rete-raw-270269786078/niggrid/hourly/YYYY/MM/DD/HH55.json

The raw JSON preserves niggrid names exactly as displayed. Plant name resolution
happens at load time (loader_niggrid_plant_hourly.py), not here.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta

import boto3
import requests
from bs4 import BeautifulSoup

S3_BUCKET = os.environ.get("S3_BUCKET", "rete-raw-270269786078")
S3_PREFIX = "niggrid/hourly"
NIGGRID_URL = "https://niggrid.org/"
TIMEOUT = 30

# WAT = UTC+1
WAT = timezone(timedelta(hours=1))


def scrape_niggrid() -> dict:
    """
    GET niggrid.org and parse the realtime generation HTML.

    Returns a dict with:
        dashboard_timestamp: ISO 8601 string (WAT, what niggrid says the data is for)
        captured_at:         ISO 8601 string (UTC, when we actually scraped)
        dashboard_total_mw:  float
        reporting_gencos:    int
        gencos:              list of {name: str, generation_mw: float}
    """
    captured_at = datetime.now(timezone.utc)

    resp = requests.get(NIGGRID_URL, timeout=TIMEOUT)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # ── Header fields ────────────────────────────────────────────────
    time_span = soup.find(id="MainContent_lblTime")
    total_span = soup.find(id="MainContent_lblRealtimeGeneration")
    count_span = soup.find(id="MainContent_lblNumberOfGencos")

    if not time_span or not total_span or not count_span:
        raise ValueError("Could not find realtime generation spans in HTML")

    dashboard_time = time_span.get_text(strip=True)          # "10:00"
    dashboard_total = total_span.get_text(strip=True)        # "3,230.32 MW"
    reporting_count = count_span.get_text(strip=True)        # "15"

    # Build timestamp: combine today's WAT date with the dashboard time
    now_wat = captured_at.astimezone(WAT)
    try:
        hour, minute = dashboard_time.split(":")
        dashboard_dt = now_wat.replace(
            hour=int(hour), minute=int(minute), second=0, microsecond=0
        )
    except (ValueError, TypeError):
        dashboard_dt = now_wat

    # ── Per-plant data ───────────────────────────────────────────────
    # ── Per-plant data ───────────────────────────────────────────────
    gencos = []
    datalist = soup.find(id="MainContent_dlstRealtimeGen")

    if datalist:
        for td in datalist.find_all("td"):
            # Name is inside the div with class col-md-7
            name_div = td.find("div", class_=lambda c: c and "col-md-7" in c)
            # MW is inside the div with class col-md-3
            mw_div = td.find("div", class_=lambda c: c and "col-md-3" in c)

            if name_div and mw_div:
                name_font = name_div.find("font")
                mw_font = mw_div.find("font")
                if name_font and mw_font:
                    gencos.append({
                        "name": name_font.get_text(strip=True),
                        "generation_mw": _safe_float(mw_font.get_text(strip=True)),
                    })

    return {
        "dashboard_timestamp": dashboard_dt.isoformat(),
        "captured_at": captured_at.isoformat(),
        "dashboard_total_mw": _safe_float(dashboard_total.replace("MW", "")),
        "reporting_gencos": _safe_int(reporting_count),
        "gencos": gencos,
        "raw_time_string": dashboard_time,
    }


def write_to_s3(payload: dict, s3_client=None) -> str:
    """Write the payload to S3 and return the key."""
    if s3_client is None:
        s3_client = boto3.client("s3")

    captured = datetime.fromisoformat(payload["captured_at"])
    key = (
        f"{S3_PREFIX}/"
        f"{captured.strftime('%Y/%m/%d')}/"
        f"{captured.strftime('%H%M')}.json"
    )

    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=json.dumps(payload, indent=2),
        ContentType="application/json",
    )
    return key


# ── Helpers ──────────────────────────────────────────────────────────────────

def _safe_float(val) -> float:
    if isinstance(val, (int, float)):
        return float(val)
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0.0


def _safe_int(val) -> int:
    try:
        return int(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0


# ── Entry points ─────────────────────────────────────────────────────────────

def lambda_handler(event, context):
    """AWS Lambda entry point."""
    try:
        payload = scrape_niggrid()
        key = write_to_s3(payload)
        print(
            f"OK: {payload['reporting_gencos']} gencos, "
            f"{payload['dashboard_total_mw']} MW, "
            f"→ s3://{S3_BUCKET}/{key}"
        )
        return {"statusCode": 200, "key": key}
    except Exception as e:
        print(f"ERROR: {e}")
        raise


def main():
    """Local testing entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Scrape niggrid.org generation data")
    parser.add_argument(
        "--local", action="store_true",
        help="Print to stdout instead of writing to S3",
    )
    args = parser.parse_args()

    print("Scraping niggrid.org...")
    payload = scrape_niggrid()

    print(f"  Timestamp:   {payload['dashboard_timestamp']}")
    print(f"  Captured at: {payload['captured_at']}")
    print(f"  Total MW:    {payload['dashboard_total_mw']}")
    print(f"  Reporting:   {payload['reporting_gencos']} gencos")
    print(f"  Plants:      {len(payload['gencos'])}")

    if payload["gencos"]:
        active = [g for g in payload["gencos"] if g["generation_mw"] > 0]
        print(f"  Active:      {len(active)} generating")
        for g in sorted(active, key=lambda x: -x["generation_mw"])[:5]:
            print(f"    {g['name']:30s} {g['generation_mw']:>8.2f} MW")

    if args.local:
        print(f"\n{json.dumps(payload, indent=2)}")
    else:
        key = write_to_s3(payload)
        print(f"\n  Written to s3://{S3_BUCKET}/{key}")


if __name__ == "__main__":
    main()