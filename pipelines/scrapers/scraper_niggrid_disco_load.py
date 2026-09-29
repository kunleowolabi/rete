#!/usr/bin/env python3
"""
scraper_niggrid_disco_load.py — Capture niggrid.org DISCO load allocation to S3.

Runs as a Lambda function (triggered by EventBridge, same :55 hourly cadence
as the plant scraper) or locally for testing (--local flag).

Source: https://niggrid.org/DisCoLoadProfile — plain HTML, no POST/viewstate
needed (confirmed via curl and DevTools, 2026-09-27). Table id
MainContent_gvDiscoLoadProfiles, rows are <font size="5"> pairs of
company name and MW allocation, ending with a Total row.
"""

import json
import os
import re
from datetime import datetime, timezone, timedelta

import boto3
import requests
from bs4 import BeautifulSoup

S3_BUCKET = os.environ.get("S3_BUCKET", "rete-raw-270269786078")
S3_PREFIX = "niggrid/disco_load"
NIGGRID_URL = "https://niggrid.org/DisCoLoadProfile"
TIMEOUT = 30

WAT = timezone(timedelta(hours=1))


def scrape_disco_load() -> dict:
    """
    GET niggrid.org/DisCoLoadProfile and parse the DISCO allocation table.

    Returns a dict with:
        dashboard_timestamp: ISO 8601 string (WAT, "Data as at" from the page)
        captured_at:         ISO 8601 string (UTC, when we scraped)
        total_mw:            float (the Total row)
        discos:              list of {name: str, allocation_mw: float}
    """
    captured_at = datetime.now(timezone.utc)

    resp = requests.get(NIGGRID_URL, timeout=TIMEOUT)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # ── Parse "Data as at DD/MM/YYYY HH:MM:SS" from the card footer ────
    dashboard_timestamp = None
    footer_text = soup.get_text()
    match = re.search(
        r"Data as at\s*(\d{2}/\d{2}/\d{4})\s*(\d{2}:\d{2}:\d{2})",
        footer_text,
    )
    if match:
        date_str, time_str = match.groups()
        try:
            dt = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M:%S")
            dashboard_timestamp = dt.replace(tzinfo=WAT).isoformat()
        except ValueError:
            dashboard_timestamp = f"{date_str} {time_str}"

    # ── Parse the table ─────────────────────────────────────────────────
    table = soup.find(id="MainContent_gvDiscoLoadProfiles")
    if not table:
        raise ValueError("Could not find DISCO load profile table in HTML")

    discos = []
    total_mw = None

    rows = table.find_all("tr")
    for row in rows[1:]:  # skip header row
        cells = row.find_all("td")
        if len(cells) != 2:
            continue

        name = cells[0].get_text(strip=True)
        value_text = cells[1].get_text(strip=True)
        value = _safe_float(value_text)

        if name.strip().lower().startswith("total"):
            total_mw = value
        else:
            discos.append({"name": name, "allocation_mw": value})

    if not discos:
        raise ValueError("Parsed table but found no DISCO rows")

    return {
        "dashboard_timestamp": dashboard_timestamp,
        "captured_at": captured_at.isoformat(),
        "total_mw": total_mw,
        "discos": discos,
    }


def write_to_s3(payload: dict, s3_client=None) -> str:
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


def _safe_float(val) -> float:
    if isinstance(val, (int, float)):
        return float(val)
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0.0


def lambda_handler(event, context):
    try:
        payload = scrape_disco_load()
        key = write_to_s3(payload)
        print(
            f"OK: {len(payload['discos'])} DISCOs, "
            f"{payload['total_mw']} MW total, "
            f"→ s3://{S3_BUCKET}/{key}"
        )
        return {"statusCode": 200, "key": key}
    except Exception as e:
        print(f"ERROR: {e}")
        raise


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Scrape niggrid.org DISCO load allocation")
    parser.add_argument("--local", action="store_true", help="Print to stdout instead of writing to S3")
    args = parser.parse_args()

    print("Scraping niggrid.org/DisCoLoadProfile...")
    payload = scrape_disco_load()

    print(f"  Timestamp:   {payload['dashboard_timestamp']}")
    print(f"  Captured at: {payload['captured_at']}")
    print(f"  Total MW:    {payload['total_mw']}")
    print(f"  DISCOs:      {len(payload['discos'])}")
    for d in payload["discos"]:
        print(f"    {d['name']:20s} {d['allocation_mw']:>8.2f} MW")

    if args.local:
        print(f"\n{json.dumps(payload, indent=2)}")
    else:
        key = write_to_s3(payload)
        print(f"\n  Written to s3://{S3_BUCKET}/{key}")


if __name__ == "__main__":
    main()