"""Exercise the current P19 financial actuals reader on the restored AB QC fixture."""

from hashlib import sha256
import json
from pathlib import Path
from uuid import uuid4

from psycopg import connect
from psycopg.types.json import Jsonb

import qc_cost_source_probe as qc
from loopback_postgres import cluster
from restore_fixture_erp import original, restore


ROOT = Path('scripts/cp7-src')
REPORT = ROOT / 'planning/report-staged.sql'
BRIDGE = ROOT / 'planning/analysis-finance.sql'
OWNER = ROOT / 'finance/read.sql'
FINANCE = ROOT / 'finance/analysis.sql'
AW = Path('supabase/dev/cp6_aw_t1_family.sql')


def extract(source, anchor, closing):
    body = source.read_text()
    assert body.count(anchor) == 1, anchor
    start = body.index(anchor)
    return body[start:body.index(closing, start) + len(closing)]


def setup(conn, catalogue):
    qc.setup(conn, catalogue)
    conn.execute("""
      create role cp7_capture nologin noinherit nosuperuser nocreatedb nocreaterole noreplication bypassrls;
      create schema cp7_analysis_native authorization cp7_capture;
      create schema cp7_analysis_stage authorization cp7_capture;
      grant usage on schema erp,auth to cp7_capture;
      grant select on erp.products,erp.fg_stock_movements to cp7_capture;
      create table cp7_analysis_stage.jobs(id uuid primary key);
    """, prepare=False)
    conn.execute(extract(ROOT / 'planning/analysis-stages.sql',
                         'create table cp7_analysis_stage.plan_targets(', ';'))
    conn.execute('grant select on cp7_analysis_stage.plan_targets to cp7_capture')
    conn.execute(extract(AW, 'create table erp.accounting_close_filings_v1 (', '\n);'))
    # The read-only ADMIN fixture below lacks close-management permission, so
    # the installed report uses the ordinary optional-preflight branch.
    functions = dict(catalogue['functions'])
    conn.execute('set local check_function_bodies=off')
    conn.execute(functions['erp.accounting_close_preflight_v1(date)'][0])
    conn.execute('set local check_function_bodies=on')
    conn.execute(OWNER.read_text(), prepare=False)
    conn.execute(extract(FINANCE, 'grant select on erp.cash_accounts,', ';'))
    anchor = 'grant execute on function cp7_analysis_native.financial_source(jsonb,timestamptz)to cp7_capture;'
    source = BRIDGE.read_text()
    assert source.count(anchor) == 1
    conn.execute(source[:source.index(anchor) + len(anchor)], prepare=False)
    conn.execute(extract(REPORT, 'create function cp7_analysis_stage.report_actuals(', '\n$$;'))
    conn.execute('alter function cp7_analysis_stage.report_actuals(uuid,jsonb,boolean,timestamptz) owner to cp7_capture')
    for signature in (
        'cp7_analysis_stage.report_actuals(uuid,jsonb,boolean,timestamp with time zone)',
        'cp7_analysis_native.financial_source(jsonb,timestamp with time zone)',
        'public.erp_cp7_get_finance_report_v1(jsonb)',
    ):
        actual = conn.execute('select pg_get_functiondef(to_regprocedure(%s))', (signature,)).fetchone()[0]
        assert actual == functions[signature][0], signature


def viewer(cur, fixture, *, stage=True):
    qc.retained.admin(cur)
    role = cur.execute("select id from erp.app_roles where role_code='ADMIN' and is_active").fetchone()[0]
    cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.period_close.manage'", (role,))
    cur.execute("insert into erp.app_role_permissions(role_id,permission_key) values(%s,'finance.reports.view') on conflict do nothing", (role,))
    user, subject = uuid4(), uuid4()
    cur.execute('insert into auth.users(id) values(%s)', (subject,))
    cur.execute("""insert into erp.app_users
                   select (jsonb_populate_record(null::erp.app_users,to_jsonb(u)||
                     jsonb_build_object('id',%s::uuid,'auth_user_id',%s::uuid,'role_id',%s::uuid,
                                       'full_name','Disposable finance viewer'))).*
                   from erp.app_users u where id=%s""",
                (user, subject, role, qc.retained.base.OPERATOR_APP))
    root, size = cur.execute('select coalesce(identity_root_id,id),size_id from erp.products where id=%s',
                             (fixture['product'],)).fetchone()
    job = uuid4()
    if stage:
        cur.execute('insert into cp7_analysis_stage.jobs(id) values(%s)', (job,))
        cur.execute('insert into cp7_analysis_stage.plan_targets(job_id,ord,target_key,row) values(%s,1,%s,%s)',
                    (job, f'{root}:{size}', Jsonb({})))
    return subject, job, str(root)


def read(cur, fixture, today):
    if 'finance_viewer' not in fixture:
        fixture['finance_viewer'] = viewer(cur, fixture)
    subject, job, root = fixture['finance_viewer']
    roles = qc.retained.prior.actors
    qc.retained.admin(cur)
    roles.claims(cur, dict(sub=str(subject), role='authenticated'))
    checks = cur.execute("""select erp.current_app_role(),erp.has_permission('finance.reports.view'),
                              erp.has_permission('finance.period_close.manage')""").fetchone()
    assert checks == ('ADMIN', True, False)
    q = dict(from_date=str(fixture['day']), through_date=str(today))
    cur.execute('set local role cp7_capture')
    actual = cur.execute('select cp7_analysis_stage.report_actuals(%s,%s,true,clock_timestamp())',
                         (job, Jsonb(q))).fetchone()[0]
    cur.execute('reset role')
    source = actual['finance']
    assert source['dates'] == {'from': q['from_date'], 'to': q['through_date'], 'as_of': str(today)}
    roles.session(cur, 'authenticated')
    native = cur.execute('select public.erp_cp7_get_finance_report_v1(%s)', (Jsonb(source['dates']),)).fetchone()[0]
    roles.session(cur, 'supabase_admin')
    assert source['report']['snapshot'] == native['snapshot']
    fingerprint = cur.execute('select cp7_analysis_native.financial_fingerprint(%s,%s)',
                              (Jsonb(native), source['book_signature'])).fetchone()[0]
    assert fingerprint == source['source_hash']
    assert actual['report_date'] == str(today)
    position = native['snapshot']['financial_position']
    return dict(stock=actual['stock'][root], wip=position['wip_inventory'], fg=position['fg_inventory'],
                cogs=native['snapshot']['performance']['cogs_gl'], dates=source['dates'], source_hash=fingerprint,
                live_native_report_matches=True, report_date=actual['report_date'])


def main():
    raw, catalogue = original(qc.ROOT / 'cp7-intake/SKU_43132617378_ORIGINAL_FAILURE.zip')
    with cluster(qc.ROOT / 'cp7-pg17/package/native/bin') as ci, connect(**ci) as conn:
        restore(conn, raw, catalogue)
        setup(conn, catalogue)
        result = qc.case(conn, read)
        before, after = (result[k]['report_actuals'] for k in ('before', 'after'))
        for value, pcs in ((before, '0'), (after, '3')):
            assert value['stock'] == dict(physical_fg_pcs=pcs, available_fg_pcs=pcs)
        assert before['source_hash'] != after['source_hash']
        assert before['dates'] == after['dates']
        conn.rollback()
        assert conn.execute("select to_regnamespace('erp')").fetchone() == (None,)
    result.update(status='QC_AB_BOOK_AND_CURRENT_P19_FINANCIAL_ACTUALS_MATCH',
                  exact_report_sql={str(p): sha256(p.read_bytes()).hexdigest() for p in (REPORT, BRIDGE, OWNER)},
                  authorization_fixture='ERP_ADMIN_WITH_FINANCE_REPORTS_VIEW',
                  public_finance_report_used=True, report_publications_completed=0, rollback_restored=True)
    print(json.dumps(result, indent=2, default=str))


if __name__ == '__main__':
    main()
