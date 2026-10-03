"""Read-only evidence from the actual disposable PostgREST command session.

No role/settings/function/timeout changes. Never emit query, claims, payload,
connection strings or unfiltered server logs. Timing is diagnostic only.
"""
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
stop = False
TARGETS = {
    'NOTE': ('erp_cp7_correct_note_v1', 'NOTE_'),
    'F05_CAPTURE': ('erp_cp7_capture_analysis_v1', 'F05_CAPTURE_'),
    'F05_LOCAL_CLAIM': ('erp_cp7_claim_local_preview_v1', 'F05_LOCAL_CLAIM_'),
}


def server_frames(raw):
    # Keep just static function names, type signatures and source line numbers.
    # STATEMENT/DETAIL and every other log byte remain private and unreported.
    pattern = r'(?:PL/pgSQL|SQL) function ("?[A-Za-z_][A-Za-z_0-9.]*"?(?:\([A-Za-z_0-9., \[\]]*\))?) (?:line|statement) ([0-9]+)'
    return [dict(function=name, line=int(line)) for name, line in re.findall(pattern, raw)]


def watch(suffix, family='NOTE'):
    global stop
    import psycopg
    assert re.fullmatch(r'[A-Z_]+', suffix), 'DIAGNOSTIC_CASE_LABEL_ONLY'
    rpc, prefix = TARGETS[family]
    target = os.environ['AUDITOR_BROWSER_DB_URL']
    parsed = urlparse(target)
    assert parsed.hostname in ('localhost', '127.0.0.1') and parsed.path == '/cp6_auditor_browser', 'DISPOSABLE_BROWSER_TRACE_ONLY'
    container = os.environ['CP6_DATABASE_CONTAINER']
    assert container == 'supabase_db_cp5-local', 'ACCEPTED_DISPOSABLE_CONTAINER_ONLY'
    started = time.monotonic()
    since = datetime.now(timezone.utc).isoformat()
    report = dict(diagnostic_only=True, product_qualification=False,
                  Native_exit_case_credit=0, SQL_settings_changed=False,
                  query_claims_payload_and_raw_log_emitted=False, samples=[])
    signal.signal(signal.SIGUSR1, lambda *_: globals().__setitem__('stop', True))
    try:
        with psycopg.connect(target, autocommit=True, connect_timeout=2) as connection:
            with connection.cursor() as cur:
                # Fixed readiness marker contains no database or actor data.
                # The browser waits briefly for this so the first command is
                # sampled too; failure to start stays diagnostic-only.
                print('CP7_HTTP_TRACE_READY', flush=True)
                # An exact current-session query fence avoids sampling Auth,
                # fixture preparation or unrelated Native commands.
                while not stop and time.monotonic() - started < 20:
                    rows = cur.execute("""
                      select pid, state, wait_event_type, wait_event,
                             extract(epoch from clock_timestamp()-query_start)*1000,
                             md5(query)
                      from pg_stat_activity
                      where datname=current_database() and pid<>pg_backend_pid()
                        and backend_type='client backend' and state='active'
                        and strpos(query,%s)>0
                    """, (rpc,)).fetchall()
                    report['samples'].append(dict(elapsed_ms=round((time.monotonic()-started)*1000),
                        command_sessions=[dict(pid=pid, state=state, wait_type=kind,
                            wait_event=event, query_elapsed_ms=str(elapsed),
                            opaque_query_md5=digest) for pid, state, kind, event, elapsed, digest in rows]))
                    time.sleep(.1)
        logs = subprocess.run(['docker', 'logs', '--since', since, '--tail', '800', container],
                              capture_output=True, text=True, timeout=10)
        report.update(status='TRACE_EMITTED', server_function_frames=server_frames(logs.stdout+'\n'+logs.stderr),
                      raw_server_log_sha256=hashlib.sha256((logs.stdout+'\n'+logs.stderr).encode()).hexdigest(),
                      docker_log_read_exit_code=logs.returncode)
    except Exception as error:
        # Emit only the exception class; a driver message can contain a URL.
        report.update(status='TRACE_INCOMPLETE', error_type=type(error).__name__)
    report['elapsed_ms'] = round((time.monotonic()-started)*1000)
    destination = ROOT/'cp6-proof/t3'/(prefix+suffix+'_HTTP_TRACE.json')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    watch(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else 'NOTE')
