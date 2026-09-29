#!/usr/bin/env python3
"""
data_api_utils.py — Shared RDS Data API helpers for the Rete Lambdas
(the API and the niggrid loader).

Every handler imports these rather than reimplementing them. This is the one
place the retry-with-backoff logic (ADR-2) and Data API response unwrapping live.
"""

import os
import time

import boto3
from botocore.exceptions import ClientError

rds_data = boto3.client("rds-data")

CLUSTER_ARN = os.environ["CLUSTER_ARN"]
SECRET_ARN = os.environ["SECRET_ARN"]
DATABASE = os.environ.get("DATABASE", "rete")

# The API keeps the default of 4 (a request can't outlast API Gateway's 30s
# anyway). The loader sets a higher value so it can wait out an Aurora resume.
MAX_RETRIES = int(os.environ.get("DATA_API_MAX_RETRIES", "4"))
BASE_DELAY_SECONDS = 2


def _call_with_retry(call):
    """
    Run a Data API call with retry-with-backoff.

    Required per ADR-2: the first call after Aurora resumes from 0 ACU
    raises DatabaseResumingException during the cold-start window. Retries
    with increasing delay rather than failing the request outright.
    """
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            return call()
        except ClientError as e:
            last_error = e
            error_code = e.response.get("Error", {}).get("Code", "")
            if attempt < MAX_RETRIES - 1:
                delay = BASE_DELAY_SECONDS * (2 ** attempt)
                print(f"Attempt {attempt + 1} failed ({error_code}), retrying in {delay}s...")
                time.sleep(delay)
            else:
                raise
    raise last_error


def execute_with_retry(sql: str, parameters: list = None) -> dict:
    kwargs = {
        "resourceArn": CLUSTER_ARN,
        "secretArn": SECRET_ARN,
        "database": DATABASE,
        "sql": sql,
        "includeResultMetadata": True,
    }
    if parameters:
        kwargs["parameters"] = parameters
    return _call_with_retry(lambda: rds_data.execute_statement(**kwargs))


def batch_with_retry(sql: str, parameter_sets: list) -> dict:
    """One statement run once per parameter set (bulk insert)."""
    return _call_with_retry(
        lambda: rds_data.batch_execute_statement(
            resourceArn=CLUSTER_ARN,
            secretArn=SECRET_ARN,
            database=DATABASE,
            sql=sql,
            parameterSets=parameter_sets,
        )
    )


def unwrap_field(field: dict):
    """
    Data API returns each field as {"stringValue": ...}, {"longValue": ...},
    {"doubleValue": ...}, {"booleanValue": ...}, or {"isNull": True}.
    Unwrap to a plain Python value.
    """
    if field.get("isNull"):
        return None
    for key in ("stringValue", "longValue", "doubleValue", "booleanValue"):
        if key in field:
            return field[key]
    return None


def unwrap_records(response: dict) -> list:
    """Convert a Data API response into a list of plain dicts, keyed by column name."""
    column_names = [col["name"] for col in response.get("columnMetadata", [])]
    records = []
    for record in response.get("records", []):
        row = {col: unwrap_field(field) for col, field in zip(column_names, record)}
        records.append(row)
    return records


def json_response(status: int, body) -> dict:
    """Standard API Gateway Lambda proxy response envelope."""
    import json
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body, default=str),
    }