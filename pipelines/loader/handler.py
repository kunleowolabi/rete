#!/usr/bin/env python3
"""
handler.py — Automated niggrid loader (S3 → Aurora, via the RDS Data API).

Triggered by S3 ObjectCreated events: every file the two niggrid scrapers
write (niggrid/hourly/... and niggrid/disco_load/...) is loaded seconds later.

Event shapes:
    S3 event                          load the object(s) named in the event
    {"backfill_date": "YYYY-MM-DD"}   load every file for that day, both prefixes
    add "dry_run": true               parse and resolve names, write nothing

Idempotent: inserts use ON CONFLICT DO NOTHING, so reprocessing is safe.
Raw capture is independent of the database — if Aurora is unavailable the
file is still in S3 and can be replayed with a backfill.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from urllib.parse import unquote_plus

import boto3
from botocore.exceptions import ClientError

from data_api_utils import batch_with_retry, execute_with_retry, unwrap_records

S3_BUCKET = os.environ.get("S3_BUCKET", "rete-raw-270269786078")
PLANT_PREFIX = "niggrid/hourly/"
DISCO_PREFIX = "niggrid/disco_load/"

# niggrid's DISCO names -> our disco_id
DISCO_NAME_MAP = {
    "Abuja Disco": "abuja",
    "Benin Disco": "benin",
    "Eko Disco": "eko",
    "Enugu Disco": "enugu",
    "Ibadan Disco": "ibadan",
    "Ikeja Disco": "ikeja",
    "Jos Disco": "jos",
    "Kaduna Disco": "kaduna",
    "Kano Disco": "kano",
    "PHarcourt Disco": "ph",
    "Yola Disco": "yola",
}

s3 = boto3.client("s3")

_alias_map = None          # reset at the start of every invocation
_partitions_seen = set()   # survives warm invocations


# ── Data API parameter helpers ──────────────────────────────────────────────

def _s(name, value):
    if value is None:
        return {"name": name, "value": {"isNull": True}}
    return {"name": name, "value": {"stringValue": str(value)}}


def _l(name, value):
    if value is None:
        return {"name": name, "value": {"isNull": True}}
    return {"name": name, "value": {"longValue": int(value)}}


# ── Audit trail (meta.ingestion_run) ────────────────────────────────────────

def start_run(s3_uri):
    run_id = str(uuid.uuid4())
    execute_with_retry(
        "INSERT INTO meta.ingestion_run (ingestion_run_id, source_id, status, s3_raw_uri) "
        "VALUES (CAST(:run_id AS uuid), 'niggrid', 'running', :uri)",
        [_s("run_id", run_id), _s("uri", s3_uri)],
    )
    return run_id


def finish_run(run_id, rows=None, partial=False, error=None):
    try:
        if error is None:
            execute_with_retry(
                "UPDATE meta.ingestion_run SET completed_at = now(), status = :status, "
                "rows_written = :rows WHERE ingestion_run_id = CAST(:run_id AS uuid)",
                [_s("status", "partial" if partial else "success"), _l("rows", rows), _s("run_id", run_id)],
            )
        else:
            execute_with_retry(
                "UPDATE meta.ingestion_run SET completed_at = now(), status = 'failed', "
                "error_detail = :error WHERE ingestion_run_id = CAST(:run_id AS uuid)",
                [_s("error", str(error)[:2000]), _s("run_id", run_id)],
            )
    except Exception as e:
        print(f"Could not update ingestion run {run_id}: {e}")


# ── Reference lookups ───────────────────────────────────────────────────────

def get_alias_map():
    global _alias_map
    if _alias_map is None:
        rows = unwrap_records(
            execute_with_retry("SELECT alias, plant_id FROM ref.plant_alias WHERE source_id = 'niggrid'")
        )
        _alias_map = {r["alias"]: r["plant_id"] for r in rows}
    return _alias_map


def ensure_partition(observed_hour_iso):
    """obs.niggrid_plant_hourly is partitioned by month — create the month if missing."""
    dt = datetime.fromisoformat(observed_hour_iso).astimezone(timezone.utc)
    year, month = dt.year, dt.month
    if (year, month) in _partitions_seen:
        return

    start = f"{year}-{month:02d}-01"
    end = f"{year + (month == 12)}-{(month % 12) + 1:02d}-01"
    name = f"obs.niggrid_plant_hourly_{year}_{month:02d}"
    try:
        execute_with_retry(
            f"CREATE TABLE IF NOT EXISTS {name} PARTITION OF obs.niggrid_plant_hourly "
            f"FOR VALUES FROM ('{start}') TO ('{end}')"
        )
    except ClientError as e:
        if "overlap" not in str(e).lower():
            raise
        print(f"Partition {name}: range already covered by an existing partition")
    _partitions_seen.add((year, month))


# ── Plant generation (niggrid/hourly) ───────────────────────────────────────

PLANT_SQL = """
    INSERT INTO obs.niggrid_plant_hourly (
        plant_id, observed_hour, generation_mw, reporting_gencos,
        dashboard_total_mw, captured_at, ingestion_run_id
    ) VALUES (
        :plant_id, CAST(:observed_hour AS timestamptz), CAST(:generation_mw AS numeric),
        :reporting_gencos, CAST(:dashboard_total_mw AS numeric),
        CAST(:captured_at AS timestamptz), CAST(:run_id AS uuid)
    )
    ON CONFLICT (plant_id, observed_hour) DO NOTHING
"""


def prepare_plant(payload):
    if not payload.get("dashboard_timestamp"):
        raise ValueError("payload has no dashboard_timestamp")
    alias_map = get_alias_map()
    rows, unresolved = [], set()
    for g in payload.get("gencos", []):
        plant_id = alias_map.get(g["name"])
        if not plant_id:
            unresolved.add(g["name"])
            continue
        rows.append((plant_id, g["generation_mw"]))
    return rows, unresolved


def write_plant(payload, rows, run_id):
    if not rows:
        return 0
    ts = payload["dashboard_timestamp"]
    ensure_partition(ts)
    sets = [
        [
            _s("plant_id", plant_id),
            _s("observed_hour", ts),
            _s("generation_mw", mw),
            _l("reporting_gencos", payload.get("reporting_gencos")),
            _s("dashboard_total_mw", payload.get("dashboard_total_mw")),
            _s("captured_at", payload.get("captured_at")),
            _s("run_id", run_id),
        ]
        for plant_id, mw in rows
    ]
    batch_with_retry(PLANT_SQL, sets)
    return len(sets)


# ── DISCO load allocation (niggrid/disco_load) ──────────────────────────────

DISCO_SQL = """
    INSERT INTO obs.niggrid_disco_load_hourly (
        disco_id, observed_hour, allocation_mw, total_mw, captured_at, ingestion_run_id
    ) VALUES (
        :disco_id, CAST(:observed_hour AS timestamptz), CAST(:allocation_mw AS numeric),
        CAST(:total_mw AS numeric), CAST(:captured_at AS timestamptz), CAST(:run_id AS uuid)
    )
    ON CONFLICT (disco_id, observed_hour) DO NOTHING
"""


def prepare_disco(payload):
    if not payload.get("dashboard_timestamp"):
        raise ValueError("payload has no dashboard_timestamp")
    rows, unresolved = [], set()
    for d in payload.get("discos", []):
        disco_id = DISCO_NAME_MAP.get(d["name"])
        if not disco_id:
            unresolved.add(d["name"])
            continue
        rows.append((disco_id, d["allocation_mw"]))
    return rows, unresolved


def write_disco(payload, rows, run_id):
    if not rows:
        return 0
    ts = payload["dashboard_timestamp"]
    sets = [
        [
            _s("disco_id", disco_id),
            _s("observed_hour", ts),
            _s("allocation_mw", mw),
            _s("total_mw", payload.get("total_mw")),
            _s("captured_at", payload.get("captured_at")),
            _s("run_id", run_id),
        ]
        for disco_id, mw in rows
    ]
    batch_with_retry(DISCO_SQL, sets)
    return len(sets)


# ── One file, end to end ────────────────────────────────────────────────────

def process_key(key, dry_run=False):
    payload = json.loads(s3.get_object(Bucket=S3_BUCKET, Key=key)["Body"].read())

    if key.startswith(PLANT_PREFIX):
        rows, unresolved = prepare_plant(payload)
        writer = write_plant
    elif key.startswith(DISCO_PREFIX):
        rows, unresolved = prepare_disco(payload)
        writer = write_disco
    else:
        print(f"Skipping unrecognised key: {key}")
        return 0

    if unresolved:
        print(f"WARNING {key}: unresolved names {sorted(unresolved)}")

    if dry_run:
        print(f"DRY RUN {key}: {len(rows)} rows would be written")
        return len(rows)

    run_id = start_run(f"s3://{S3_BUCKET}/{key}")
    try:
        written = writer(payload, rows, run_id)
    except Exception as e:
        finish_run(run_id, error=e)
        raise
    finish_run(run_id, rows=written, partial=bool(unresolved))
    return written


# ── Event handling ──────────────────────────────────────────────────────────

def list_keys(prefix):
    keys = []
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=S3_BUCKET, Prefix=prefix):
        keys += [o["Key"] for o in page.get("Contents", []) if o["Key"].endswith(".json")]
    return sorted(keys)


def keys_for_event(event):
    if "backfill_date" in event:
        year, month, day = event["backfill_date"].split("-")
        return list_keys(f"{PLANT_PREFIX}{year}/{month}/{day}/") + list_keys(
            f"{DISCO_PREFIX}{year}/{month}/{day}/"
        )
    keys = [unquote_plus(r["s3"]["object"]["key"]) for r in event.get("Records", [])]
    return [k for k in keys if k.endswith(".json")]


def lambda_handler(event, context):
    global _alias_map
    _alias_map = None

    dry_run = bool(event.get("dry_run"))
    backfill = "backfill_date" in event

    keys = keys_for_event(event)
    rows_written, failed = 0, []

    for key in keys:
        try:
            rows_written += process_key(key, dry_run)
        except Exception as e:
            print(f"FAILED {key}: {e}")
            failed.append(key)
            if not backfill:
                raise  # let S3's async retry handle live files

    summary = {"files": len(keys), "rows": rows_written, "failed": failed}
    print(json.dumps(summary))
    return summary