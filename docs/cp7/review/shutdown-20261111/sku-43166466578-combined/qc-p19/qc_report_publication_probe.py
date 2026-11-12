"""Publish and reopen two actual P19 report revisions over the same staged QC fixture."""

from decimal import Decimal
from hashlib import sha256
import json
from uuid import uuid4

from psycopg import Error, connect, sql
from psycopg.types.json import Jsonb

import qc_cost_source_probe as qc
import qc_report_actuals_probe as actuals
from loopback_postgres import cluster
from restore_fixture_erp import original, restore


STAGE = actuals.ROOT / 'planning/analysis-stages.sql'
FRESH = actuals.ROOT / 'planning/analysis-stage-snapshot.sql'
V1 = actuals.ROOT / 'planning/report-publication.sql'
REPORT_NAMES = ('erp_cp7_publish_report_v2', 'erp_cp7_step_report_v2', 'erp_cp7_read_report_v2',
                'erp_cp7_read_report_section_v2')
ROLES = qc.retained.prior.actors


def create_table(conn, path, name):
    conn.execute(actuals.extract(path, 'create table ' + name + '(', ';'))
    conn.execute(sql.SQL('alter table {} owner to cp7_capture').format(sql.Identifier(*name.split('.'))))


def setup(conn, catalogue):
    actuals.setup(conn, catalogue)
    conn.execute('drop function cp7_analysis_stage.report_actuals(uuid,jsonb,boolean,timestamptz); '
                 'drop table cp7_analysis_stage.plan_targets; drop table cp7_analysis_stage.jobs; '
                 'create schema cp7_private; create schema cp7_schedule_native authorization cp7_capture; '
                 'create schema cp7_wip authorization cp7_capture; '
                 'create table cp7_analysis_native.runs(id uuid primary key); '
                 'grant usage on schema cp7_private to cp7_capture; '
                 'grant execute on function erp.get_my_access_v1(),erp.has_permission(text) to cp7_capture',
                 prepare=False)
    for name in ('jobs', 'headers', 'pages', 'page_sets', 'capture_marks', 'plan_targets'):
        create_table(conn, STAGE, 'cp7_analysis_stage.' + name)
    create_table(conn, FRESH, 'cp7_analysis_stage.source_checks')
    create_table(conn, V1, 'cp7_analysis_native.publications')
    create_table(conn, V1, 'cp7_analysis_native.report_requests')
    funcs, columns = map(dict, (catalogue['functions'], catalogue['columns']))
    for signature in (
        'cp7_private.immutable_run()', 'cp7_private.access_now()', 'cp7_schedule_native.access_now(boolean)',
        'cp7_wip.fields(jsonb,text[])', 'cp7_wip.ref(text,text,text)',
        'cp7_analysis_native.fact(text,text,jsonb,jsonb)', 'cp7_analysis_native.finance_apply(jsonb,jsonb)',
        'cp7_analysis_native.report_fact(jsonb)',
        'cp7_analysis_stage.retention_days()', 'cp7_analysis_stage.retention(text,timestamp with time zone)',
        'cp7_analysis_stage.require_kept(uuid)', 'cp7_analysis_stage.change_sources()',
        'cp7_analysis_stage.changes_since(timestamp with time zone,pg_snapshot,timestamp with time zone,pg_snapshot)',
        'cp7_analysis_stage.freshness(uuid)',
    ):
        conn.execute(funcs[signature][0])
        conn.execute(sql.SQL('alter function {} owner to {}').format(sql.SQL(signature), sql.Identifier(funcs[signature][1])))
    for src in conn.execute('select cp7_analysis_stage.change_sources()').fetchone()[0]:
        namespace, table = src['schema'], src['table']
        name = namespace + '.' + table
        relation = sql.Identifier(namespace, table)
        names = src['columns']
        if conn.execute('select to_regclass(%s)', (name,)).fetchone()[0] is None:
            conn.execute(sql.SQL('create schema if not exists {}').format(sql.Identifier(namespace)))
            conn.execute(sql.SQL('grant usage on schema {} to cp7_capture').format(sql.Identifier(namespace)))
            conn.execute(sql.SQL('create table {} ()').format(relation))
        for column in names:
            datatype = next(row[2] for key, row in columns.items() if key.startswith(name + ':') and row[0] == column)
            conn.execute(sql.SQL('alter table {} add column if not exists {} {}').format(
                relation, sql.Identifier(column), sql.SQL(datatype)))
        conn.execute(sql.SQL('grant select ({}) on {} to cp7_capture').format(
            sql.SQL(',').join(map(sql.Identifier, [*names, 'xmin'])), relation))
    conn.execute('grant select(entity_type,action,changed_at,xmin) on erp.audit_logs to cp7_capture')
    conn.execute(actuals.REPORT.read_text(), prepare=False)
    for signature in funcs:
        if signature.split('(')[0] in {'public.' + name for name in REPORT_NAMES}:
            actual = conn.execute('select pg_get_functiondef(to_regprocedure(%s))', (signature,)).fetchone()[0]
            assert actual == funcs[signature][0], signature


def authority(cur, subject):
    qc.retained.admin(cur)
    ROLES.claims(cur, dict(sub=str(subject), role='authenticated'))
    ROLES.session(cur, 'authenticated')
    cur.execute("set local statement_timeout='8s'")


def fixture_snapshot(cur, fixture, today):
    subject, job, root = actuals.viewer(cur, fixture, stage=False)
    role = cur.execute("select id from erp.app_roles where role_code='ADMIN' and is_active").fetchone()[0]
    permissions = ('master.product.view', 'production.wip.view', 'warehouse.stock.view', 'sales.invoice.view',
                   'finance.reports.view')
    cur.execute("insert into erp.app_role_permissions(role_id,permission_key) "
                "select %s,permission_key from erp.app_permissions where permission_key=any(%s) and is_active "
                "on conflict do nothing", (role, list(permissions)))
    run = uuid4()
    capture = cur.execute('select clock_timestamp()').fetchone()[0]
    size = cur.execute('select size_id from erp.products where id=%s', (fixture['product'],)).fetchone()[0]
    target = f'{root}:{size}'
    q = Jsonb(dict(from_date=str(fixture['day']), through_date=str(today), group_mode='AS_SOLD'))
    row = dict(target=dict(key=target, size_id=str(size), membership=[fixture['product']]),
               actual_fg=dict(state='KNOWN', value='0', unit='PCS', refs=[]), production_state='ACTIVE')
    body = json.dumps(dict(items=dict(recommendations=[row])))
    labels = json.dumps(dict(product_labels=[dict(target_key=target, sku='QC-8', product_name='QC fixture')]))
    head_hash, body_hash = (sha256(raw.encode()).hexdigest() for raw in (labels, body))
    identity = sha256((head_hash + '\n' + body_hash).encode()).hexdigest()
    cur.execute("""insert into cp7_analysis_stage.jobs(id,actor,request_id,query,reference,run_id,access_at_capture,
                   captured_at,source_hash,state,unit_count,units_done,plan_final,targets_total,created_at,updated_at)
                   values(%s,%s,%s,%s,'{}',%s,'{}',%s,%s,'DONE',1,1,true,1,%s,%s)""",
                (job, subject, uuid4(), q, run, capture, identity, capture, capture))
    cur.execute('insert into cp7_analysis_stage.capture_marks(job_id,source_snapshot) values(%s,null)', (job,))
    cur.execute("""insert into cp7_analysis_stage.headers(run_id,job_id,body,utf8_bytes,sha256,paged,targets_total,page_count,cuts)
                   values(%s,%s,%s,%s,%s,'{}',1,1,'[]')""", (run, job, labels, len(labels.encode()), head_hash))
    cur.execute("""insert into cp7_analysis_stage.pages(run_id,idx,target_lo,target_hi,counts,offsets,summary,body,utf8_bytes,sha256)
                   values(%s,0,1,1,'{}','{}','{}',%s,%s,%s)""", (run, body, len(body.encode()), body_hash))
    cur.execute("insert into cp7_analysis_stage.page_sets(run_id,identity_hash,totals,created_at) values(%s,%s,'{}',%s)",
                (run, identity, capture))
    cur.execute('insert into cp7_analysis_stage.plan_targets(job_id,ord,target_key,row) values(%s,1,%s,%s)',
                (job, target, Jsonb(row)))
    return subject, root, dict(run_id=str(run), identity_hash=identity, kind='PERIOD', series_id=None, expected_revision=None,
                               title='QC 8 unit', reason='Penerbitan Business Report untuk fixture QC', finance='INCLUDED', explicit_review=True)


def read_archive(cur, subject, publication):
    authority(cur, subject)
    doc = cur.execute('select public.erp_cp7_read_report_v2(%s)', (publication,)).fetchone()[0]
    section = cur.execute('select public.erp_cp7_read_report_section_v2(%s,0,%s)',
                          (publication, doc['access_epoch'])).fetchone()[0]
    assert sha256(doc['summary'].encode()).hexdigest() == doc['summary_sha256']
    assert sha256(section['body'].encode()).hexdigest() == section['sha256']
    assert sha256((doc['summary_sha256'] + '\n' + section['sha256']).encode()).hexdigest() == doc['report_hash']
    return doc, section


def publish(cur, fixture, today):
    first = 'report_state' not in fixture
    if first:
        fixture['report_state'] = fixture_snapshot(cur, fixture, today)
    subject, root, payload = fixture['report_state']
    if not first:
        old, old_section = fixture['prior_publication']
        payload = dict(payload, series_id=old['series_id'], expected_revision='1')
    authority(cur, subject)
    request = uuid4()
    state = cur.execute('select public.erp_cp7_publish_report_v2(%s,%s)', (Jsonb(payload), request)).fetchone()[0]
    assert state['state'] == 'RUNNING' and state['unit_count'] == 4
    stages = []
    for _ in range(state['unit_count']):
        stages.append(state['stage'])
        state = cur.execute('select public.erp_cp7_step_report_v2(%s)', (request,)).fetchone()[0]
        if state['state'] == 'FAILED':
            qc.retained.admin(cur)
            stored_error = cur.execute('select failure_message from cp7_analysis_stage.report_jobs where request_id=%s',
                                       (request,)).fetchone()[0]
            raise AssertionError((state['failure'], stored_error))
    assert state['state'] == 'DONE' and stages == ['ACTUALS', 'SECTION', 'FRESHNESS', 'SUMMARY']
    doc, section = read_archive(cur, subject, state['publication_id'])
    qc.retained.admin(cur)
    stored = cur.execute("""select r.body from cp7_analysis_stage.report_reads r join cp7_analysis_stage.report_jobs j
                            on j.id=r.job_id where j.request_id=%s and r.kind='ACTUALS'""", (request,)).fetchone()[0]
    assert doc['finance'] == 'INCLUDED' and doc['financial_source_hash'] == stored['finance']['source_hash']
    assert doc['report_date'] == stored['finance']['dates']['as_of'] == str(today)
    pcs = '0' if first else '3'
    assert stored['stock'][root] == dict(physical_fg_pcs=pcs, available_fg_pcs=pcs)
    assert f'stok fisik aktual per ' in section['body'] and f' {pcs} PCS; stok tersedia setelah reservasi aktual {pcs} PCS' in section['body']
    authority(cur, subject)
    native = cur.execute('select public.erp_cp7_get_finance_report_v1(%s)', (Jsonb(stored['finance']['dates']),)).fetchone()[0]
    assert native['snapshot'] == stored['finance']['report']['snapshot']
    assert Decimal(native['snapshot']['performance']['cogs_gl']) == 0
    result = dict(revision=doc['revision'], report_hash=doc['report_hash'], finance_source_hash=doc['financial_source_hash'],
                  actual_stock_pcs=pcs, finance_dates=stored['finance']['dates'], stages=stages,
                  same_owner_report=True, freshness=doc['freshness']['state'])
    if first:
        fixture['prior_publication'] = (doc, section)
    else:
        reopened, reopened_section = read_archive(cur, subject, old['id'])
        assert reopened['is_latest'] is False and reopened_section == old_section
        for key in ('summary', 'report_hash', 'summary_sha256', 'sections', 'actuals_read_at', 'financial_source_hash'):
            assert reopened[key] == old[key], key
        assert doc['freshness']['state'] == 'CHANGES_RECORDED'
        result['archive_unchanged'] = True
        qc.retained.admin(cur)
        try:
            with cur.connection.transaction(force_rollback=True):
                cur.execute("""delete from erp.app_role_permissions rp using erp.app_roles r
                               where rp.role_id=r.id and r.role_code='ADMIN'
                               and rp.permission_key='finance.reports.view'""")
                read_archive(cur, subject, old['id'])
        except Error as error:
            assert error.sqlstate == '42501', error
        else:
            raise AssertionError('Archived finance remained visible after the role lost permission')
        result['archive_refused_after_finance_permission_removed'] = True
    return result


def main():
    raw, catalogue = original(qc.ROOT / 'cp7-intake/SKU_43132617378_ORIGINAL_FAILURE.zip')
    with cluster(qc.ROOT / 'cp7-pg17/package/native/bin') as ci, connect(**ci) as conn:
        restore(conn, raw, catalogue)
        setup(conn, catalogue)
        result = qc.case(conn, publish)
        assert result['before']['report_actuals']['finance_source_hash'] != result['after']['report_actuals']['finance_source_hash']
        assert result['after']['report_actuals']['archive_unchanged']
        conn.rollback()
        assert conn.execute("select to_regnamespace('erp')").fetchone() == (None,)
    result.update(status='QC_AB_P19_INCLUDED_REVISIONS_AND_ARCHIVE_VERIFIED', publications=2,
                  actual_current_combined_candidate_cases=0, fixture_analysis_target=True, rollback_restored=True)
    print(json.dumps(result, indent=2, default=str))


if __name__ == '__main__':
    main()
