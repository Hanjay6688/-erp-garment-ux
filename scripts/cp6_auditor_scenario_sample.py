"""Sample auditor scenario for scripts/cp6_auditor_scenario.py (smoke test of the runner on push; auditors replace it with
their own file through the workflow input). It only replays writer control cases, so a green run shows the runtime works
(savepoint cases, the two-session mode and the real-HTTP mode); it is not independent evidence by itself."""
import cp6_az_probe as azp


def cases(cur,today):
    return [('SAMPLE:WRITE_OFF_REVERSED_THEN_LATE_INVOICE_LOWER',lambda:azp.writeoff_reversal(cur,today,'8.25'))]


def races(tools,today):
    # The AW probe's attendance race (close first, committed) on a fresh committed copy with two real sessions.
    return [('SAMPLE_RACE:ATTENDANCE_CLOSE_FIRST_COMMIT',lambda:tools.awp.attendance_race(tools.admin,today,'CLOSE',True))]


def http_cases(http,today):
    def preflight_by_role():
        owner=http.login('OWNER','owner');store=http.login('GUDANG','gudang')
        args=dict(p_through=str(today))
        a=owner.rpc('erp_accounting_close_preflight_v1',args)
        b=store.rpc('erp_accounting_close_preflight_v1',args)
        c=http.anon_rpc('erp_accounting_close_preflight_v1',args)
        ok=a['status']==200 and isinstance(a['body'],dict) and 'status' in a['body'] and b['status']>=400 and c['status'] in (401,403)
        return dict(status='PASS' if ok else 'FAIL',owner=dict(status=a['status'],readiness=(a['body'] or {}).get('status') if isinstance(a['body'],dict) else None),
                    gudang=b,anon=c)
    return [('SAMPLE_HTTP:PREFLIGHT_OWNER_ALLOWED_GUDANG_AND_ANON_REFUSED',preflight_by_role)]
