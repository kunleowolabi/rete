#!/usr/bin/env python3
"""
backfill.py — Replay raw niggrid files from S3 through the loader Lambda.

Use it once to load history, or any time to repair a gap (for example after
an Aurora outage). Safe to re-run: the loader skips rows that already exist.

Usage:
    python3 pipelines/loader/backfill.py --from 2026-08-28 [--to 2026-09-28] [--dry-run]
"""

import argparse
import json
from datetime import date, datetime, timedelta, timezone

import boto3
from botocore.config import Config

FUNCTION_NAME = "rete-niggrid-loader"


def main():
    today = datetime.now(timezone.utc).date()
    parser = argparse.ArgumentParser(description="Replay raw niggrid files through the loader Lambda")
    parser.add_argument("--from", dest="start", required=True, type=date.fromisoformat)
    parser.add_argument("--to", dest="end", default=today, type=date.fromisoformat)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    lam = boto3.client(
        "lambda",
        region_name="eu-west-1",
        config=Config(read_timeout=330, retries={"max_attempts": 0}),
    )

    day = args.start
    while day <= args.end:
        payload = {"backfill_date": day.isoformat(), "dry_run": args.dry_run}
        resp = lam.invoke(FunctionName=FUNCTION_NAME, Payload=json.dumps(payload))
        result = json.loads(resp["Payload"].read())

        if resp.get("FunctionError"):
            print(f"{day}  ERROR  {result}")
        else:
            failed = len(result.get("failed", []))
            print(f"{day}  files={result['files']:>3}  rows={result['rows']:>5}  failed={failed}")
        day += timedelta(days=1)


if __name__ == "__main__":
    main()