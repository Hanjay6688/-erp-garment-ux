#!/usr/bin/env python3
"""Real two-session acceptance harness for the CP3 attendance-HPP candidate.

Safety boundary:
- refuses non-local database hosts;
- requires an explicit disposable-environment acknowledgement;
- requires a fixture file with a database-name guard;
- never connects to ERP Enteng UAT or ERP-Garment legacy;
- emits a redacted JSON report and no credentials.

The fixture must be created in a disposable/local database after applying the two
CP3 source-candidate migrations. It supplies an authoritative prepare payload
whose payroll, journal-line, policy, and SELESAI_DIJAHIT facts already exist.
"""

from __future__ import annotations

import concurrent.futures
import copy
import json
import os
import sys
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

ACK_VALUE = "I_UNDERSTAND_THIS_DATABASE_WILL_BE_DESTROYED"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


class HarnessError(RuntimeError):
    pass


@dataclass
class CallResult:
    name: str
    ok: bool
    value: dict | None = None
    sqlstate: str | None = None
    error: str | None = None

    def redacted(self) -> dict:
        return {
            "name": self.name,
            "ok": self.ok,
            "value": self.value,
            "sqlstate": self.sqlstate,
            "error": self.error,
        }


def load_fixture() -> dict:
    fixture_path = os.environ.get("CP3_FIXTURE_JSON")
    if not fixture_path:
        raise HarnessError("CP3_FIXTURE_JSON is required; the harness never invents fixture identity")
    fixture = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
    required = {
        "expected_database_name",
        "database_role",
        "jwt_claims",
        "prepare_payload",
        "request_ids",
    }
    missing = sorted(required - fixture.keys())
    if missing:
        raise HarnessError(f"fixture missing required keys: {missing}")
    request_ids = fixture["request_ids"]
    for key in ("prepare_same", "cancel", "finalize", "stale"):
        if key not in request_ids:
            raise HarnessError(f"fixture.request_ids.{key} is required")
        uuid.UUID(str(request_ids[key]))
    return fixture


def guarded_database_url(fixture: dict) -> str:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise HarnessError("DATABASE_URL is required")
    parsed = urlparse(database_url)
    if parsed.hostname not in LOCAL_HOSTS:
        raise HarnessError(
            f"refusing non-local database host {parsed.hostname!r}; use a disposable local Supabase/Postgres stack"
        )
    if os.environ.get("CP3_DISPOSABLE_CONFIRM") != ACK_VALUE:
        raise HarnessError("CP3_DISPOSABLE_CONFIRM acknowledgement is missing")
    if not fixture.get("disposable_database", True):
        raise HarnessError("fixture does not declare disposable_database=true")
    return database_url


def connect(database_url: str, fixture: dict) -> psycopg.Connection:
    connection = psycopg.connect(database_url, autocommit=True, connect_timeout=10)
    with connection.cursor() as cursor:
        cursor.execute("select current_database()")
        observed = cursor.fetchone()[0]
        if observed != fixture["expected_database_name"]:
            connection.close()
            raise HarnessError(
                f"database guard mismatch: expected {fixture['expected_database_name']!r}, observed {observed!r}"
            )
        role = fixture["database_role"]
        if role:
            cursor.execute(sql.SQL("set role {}").format(sql.Identifier(role)))
        cursor.execute(
            "select set_config('request.jwt.claims', %s, false)",
            (json.dumps(fixture["jwt_claims"], sort_keys=True),),
        )
    return connection


def normalize_json(value: object) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return json.loads(value)
    raise HarnessError(f"unexpected JSON result type: {type(value).__name__}")


def call_function(
    database_url: str,
    fixture: dict,
    name: str,
    query: str,
    parameters: tuple,
    barrier: threading.Barrier | None = None,
) -> CallResult:
    try:
        with connect(database_url, fixture) as connection:
            if barrier is not None:
                barrier.wait(timeout=15)
            with connection.cursor() as cursor:
                cursor.execute(query, parameters)
                row = cursor.fetchone()
                return CallResult(name=name, ok=True, value=normalize_json(row[0]))
    except Exception as error:  # report database failures without credentials
        sqlstate = getattr(error, "sqlstate", None)
        message = str(error).splitlines()[0][:500]
        return CallResult(name=name, ok=False, sqlstate=sqlstate, error=message)


def run_parallel(calls: list[tuple[str, str, tuple]], database_url: str, fixture: dict) -> list[CallResult]:
    barrier = threading.Barrier(len(calls))
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(calls)) as executor:
        futures = [
            executor.submit(call_function, database_url, fixture, name, query, params, barrier)
            for name, query, params in calls
        ]
        return [future.result(timeout=60) for future in futures]


def query_pool(database_url: str, fixture: dict, pool_id: str) -> dict:
    with connect(database_url, fixture) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            select jsonb_build_object(
              'pool_id',id,'status',status,'row_version',row_version,
              'numerator_cents',numerator_cents,'denominator_qty',denominator_qty,
              'manifest_sha256',manifest_sha256
            )
            from erp.attendance_hpp_pools where id=%s::uuid
            """,
            (pool_id,),
        )
        row = cursor.fetchone()
        if row is None:
            raise HarnessError(f"pool {pool_id} disappeared")
        return normalize_json(row[0])


def count_pool_effect(database_url: str, fixture: dict, pool_id: str) -> dict:
    with connect(database_url, fixture) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            select jsonb_build_object(
              'pool_rows',(select count(*) from erp.attendance_hpp_pools where id=%s::uuid),
              'source_rows',(select count(*) from erp.attendance_hpp_pool_sources where pool_id=%s::uuid),
              'sewing_rows',(select count(*) from erp.attendance_hpp_pool_sewing_sources where pool_id=%s::uuid),
              'allocation_rows',(select count(*) from erp.attendance_hpp_pool_allocations where pool_id=%s::uuid),
              'terminal_credit_rows',(select count(*) from erp.attendance_hpp_terminal_credit_intents where pool_id=%s::uuid)
            )
            """,
            (pool_id, pool_id, pool_id, pool_id, pool_id),
        )
        return normalize_json(cursor.fetchone()[0])


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise HarnessError(message)


def main() -> int:
    try:
        fixture = load_fixture()
        database_url = guarded_database_url(fixture)
        payload = fixture["prepare_payload"]
        same_request_id = str(fixture["request_ids"]["prepare_same"])

        prepare_query = "select erp.prepare_attendance_hpp_pool_v1(%s::jsonb,%s::uuid)"
        parallel_prepare = run_parallel(
            [
                ("prepare_same_a", prepare_query, (Jsonb(payload), same_request_id)),
                ("prepare_same_b", prepare_query, (Jsonb(payload), same_request_id)),
            ],
            database_url,
            fixture,
        )

        successful_prepare = [result for result in parallel_prepare if result.ok]
        assert_true(successful_prepare, "same-key concurrent prepare produced no successful result")
        canonical_pool_id = successful_prepare[0].value["pool_id"]

        # Regardless of an implementation-defined in-progress response during
        # the collision, a post-commit retry must resolve to the same effect.
        retry = call_function(
            database_url,
            fixture,
            "prepare_same_retry",
            prepare_query,
            (Jsonb(payload), same_request_id),
        )
        assert_true(retry.ok, f"same-key retry did not resolve: {retry.error}")
        assert_true(retry.value["pool_id"] == canonical_pool_id, "same-key retry returned a different pool")
        for result in successful_prepare:
            assert_true(result.value["pool_id"] == canonical_pool_id, "same key created divergent pool IDs")

        effect = count_pool_effect(database_url, fixture, canonical_pool_id)
        assert_true(effect["pool_rows"] == 1, "same key created more than one pool row")

        changed_payload = copy.deepcopy(payload)
        changed_payload["reason"] = str(changed_payload.get("reason", "CP3")) + " / changed payload"
        different_payload = call_function(
            database_url,
            fixture,
            "same_key_different_payload",
            prepare_query,
            (Jsonb(changed_payload), same_request_id),
        )
        assert_true(not different_payload.ok, "same idempotency key with different payload was accepted")

        pool_before_race = query_pool(database_url, fixture, canonical_pool_id)
        assert_true(pool_before_race["status"] == "ACTIVE", f"race fixture must be ACTIVE, observed {pool_before_race['status']}")
        version = int(pool_before_race["row_version"])

        race_results = run_parallel(
            [
                (
                    "cancel_vs_finalize_cancel",
                    "select erp.cancel_attendance_hpp_pool_v1(%s::uuid,%s,%s::uuid,%s::bigint)",
                    (
                        canonical_pool_id,
                        "CP3 real two-session cancellation race",
                        str(fixture["request_ids"]["cancel"]),
                        version,
                    ),
                ),
                (
                    "cancel_vs_finalize_finalize",
                    "select erp.finalize_attendance_hpp_pool_intent_v1(%s::uuid,%s,%s::uuid,%s::bigint)",
                    (
                        canonical_pool_id,
                        "CP3 real two-session finalization race",
                        str(fixture["request_ids"]["finalize"]),
                        version,
                    ),
                ),
            ],
            database_url,
            fixture,
        )
        race_successes = [result for result in race_results if result.ok]
        assert_true(len(race_successes) == 1, f"cancel/finalize race expected exactly one winner, observed {len(race_successes)}")

        pool_after_race = query_pool(database_url, fixture, canonical_pool_id)
        assert_true(pool_after_race["status"] in {"CANCELLED", "READY"}, "race left an invalid terminal state")
        assert_true(int(pool_after_race["row_version"]) > version, "race winner did not advance row_version")

        stale = call_function(
            database_url,
            fixture,
            "stale_version_after_race",
            "select erp.cancel_attendance_hpp_pool_v1(%s::uuid,%s,%s::uuid,%s::bigint)",
            (
                canonical_pool_id,
                "CP3 stale version must reject",
                str(fixture["request_ids"]["stale"]),
                version,
            ),
        )
        assert_true(not stale.ok, "stale expected_version was accepted after terminal race")

        report = {
            "status": "PASS",
            "harness": "CP3_REAL_TWO_SESSION_V1",
            "database_host_class": "LOCAL_ONLY",
            "database_name": fixture["expected_database_name"],
            "same_key_parallel": [result.redacted() for result in parallel_prepare],
            "same_key_retry": retry.redacted(),
            "same_key_different_payload": different_payload.redacted(),
            "single_effect_counts": effect,
            "cancel_vs_finalize": [result.redacted() for result in race_results],
            "pool_before_race": pool_before_race,
            "pool_after_race": pool_after_race,
            "stale_version": stale.redacted(),
            "claims_subject_present": bool(fixture["jwt_claims"].get("sub")),
            "cleanup": "DISPOSABLE_STACK_MUST_BE_DESTROYED_BY_CALLER",
        }
        output = Path(os.environ.get("CP3_CONCURRENCY_REPORT", "cp3-concurrency-report.json"))
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(report, sort_keys=True))
        return 0
    except Exception as error:
        print(f"CP3 concurrency harness FAILED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
