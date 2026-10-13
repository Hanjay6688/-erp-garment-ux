#!/usr/bin/env python3
"""Opt-in, read-only Supabase database check. Never prints connection details."""
import json
import os
import re
import sys
import time
from urllib.parse import unquote, urlsplit

import psycopg

TARGET_PROJECT = "siimvrusnzxexizpyoib"  # Enteng, owner decision D13-7.
ROLE = "erp_healthcheck"
QUERY = """SELECT 1, current_database(), current_setting('transaction_read_only'),
                    current_user, rolsuper, rolcreatedb, rolcreaterole, rolbypassrls
             FROM pg_catalog.pg_roles WHERE rolname = current_user"""


class Refused(Exception):
    pass


def connection_args(env):
    if env.get("ERP_HEALTHCHECK_ENABLED") != "true":
        raise Refused("NOT_ENABLED")
    if env.get("ERP_HEALTHCHECK_PROJECT_REF") != TARGET_PROJECT:
        raise Refused("PROJECT_NOT_APPROVED")
    raw = env.get("ERP_HEALTHCHECK_DATABASE_URL", "")
    try:
        url = urlsplit(raw)
        if (url.scheme != "postgresql" or url.query or url.fragment
                or unquote(url.path) != "/postgres" or url.port not in (None, 5432)
                or not url.password):
            raise ValueError()
        host = url.hostname or ""
        user = unquote(url.username or "")
        direct = host == f"db.{TARGET_PROJECT}.supabase.co" and user == ROLE
        pooled = (re.fullmatch(r"aws-\d+-[a-z0-9-]+\.pooler\.supabase\.com", host)
                  and user == f"{ROLE}.{TARGET_PROJECT}")
        if not (direct or pooled):
            raise ValueError()
        return dict(host=host, port=5432, dbname="postgres", user=user,
                    password=unquote(url.password), sslmode="verify-full",
                    sslrootcert="system", connect_timeout=8,
                    application_name="erp_readonly_healthcheck", prepare_threshold=None)
    except (ValueError, UnicodeError):
        raise Refused("INVALID_CONNECTION_CONFIG") from None


def probe(conn):
    """No business tables or custom functions; rollback even after a good result."""
    conn.read_only = True
    try:
        conn.execute("SET LOCAL statement_timeout = '5s'")
        conn.execute("SET LOCAL lock_timeout = '2s'")
        conn.execute("SET LOCAL idle_in_transaction_session_timeout = '10s'")
        row = conn.execute(QUERY).fetchone()
        if row != (1, "postgres", "on", ROLE, False, False, False, False):
            raise Refused("UNEXPECTED_DATABASE_OR_ROLE")
    finally:
        conn.rollback()


def run(env, connect=psycopg.connect):
    started = time.monotonic()
    try:
        args = connection_args(env)
        conn = connect(**args)
        try:
            probe(conn)
        finally:
            conn.close()
        code, status, result = "DATABASE_RESPONDED_READ_ONLY", "PASS", 0
    except Refused as exc:
        code, status, result = str(exc), "REFUSED", 1
    except Exception:
        # Connection exceptions can contain credentials, hostnames or server output.
        code, status, result = "CONNECTION_OR_QUERY_FAILED", "FAIL", 1
    print(json.dumps({"status": status, "code": code,
                      "duration_ms": round((time.monotonic() - started) * 1000)}))
    return result


if __name__ == "__main__":
    sys.exit(run(os.environ))
