"""One disposable QC posting and current CP7 snapshot/report readers."""
import argparse
from datetime import timedelta
from hashlib import sha256
import json
from pathlib import Path
import re
from uuid import UUID, uuid4

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb


HEAD = 'd08032a28b9f00d0ee70a6f98c6b7d0f5b770c4a'
CASE = 'SKU_NATIVE7_COST5_RACES3_PERMISSION_WAITS7_RECOVERY_BUSY1_AUTH_BROWSER4'
ORIGINAL_SHA = '5e22077e71e34add6fd0627c89e9d21a2235f463818e45b233c7619bcfb0d48f'
DB = 'cp7_b_snapshot'
ROLES = ('anon', 'authenticated', 'service_role', 'cp7_capture')
WIP_FILES = ['bootstrap', 'source', 'graph', 'rewash', 'bs', 'normalize', 'other-source', 'other-normalize', 'production']
FILES = [f'scripts/cp7-src/wip/{name}.sql' for name in WIP_FILES] + ['scripts/cp7-src/planning/report-staged.sql']
FRESHNESS_FILE = 'scripts/cp7-src/planning/analysis-stage-snapshot.sql'
NATIVE = (
    'erp._request_hash(jsonb)', 'erp._idempotency_actor_key()', 'erp._idempotency_begin(text,uuid,text)',
    'erp._idempotency_complete(text,uuid,jsonb)', 'erp.pocket_period_lock_v1()',
    'erp.assert_product_identity_time(uuid,timestamp with time zone,text)',
    'erp.assert_fg_chronological_nonnegative(uuid,uuid,uuid,text)',
    'erp.post_fg_movement(uuid,uuid,uuid,text,text,integer,numeric,uuid,text,uuid,timestamp with time zone,text,boolean)',
    'erp.post_qc(uuid)', 'erp.post_fg_partial_completion_v2_legacy_v2610(jsonb,uuid,bigint)',
    'erp.post_fg_partial_completion_v2(jsonb,uuid,bigint)', 'erp.post_final_sku_allocation_v1(jsonb,uuid,bigint)',
    'cp7_private.immutable_run()', 'cp7_analysis_native.report_fact(jsonb)',
    'cp7_analysis_stage.retention_days()', 'cp7_analysis_stage.retention(text,timestamp with time zone)',
    'cp7_analysis_stage.require_kept(uuid)', 'cp7_analysis_stage.change_sources()',
    'cp7_analysis_stage.changes_since(timestamp with time zone,pg_snapshot,timestamp with time zone,pg_snapshot)',
    'cp7_analysis_stage.freshness(uuid)',
)
# Posting calls these finance dependencies. The typed fixture records each call
# and leaves valuation unknown until an installed ERP finance chain is available.
FINANCE_HOOKS = (
    'erp.ensure_fg_accessory_cost_snapshot(uuid)', 'erp.post_accessory_reimbursement_accrual(uuid)',
    'erp.sync_laundry_accrual(uuid,date)', 'erp.rebuild_po_hpp(uuid,text)',
    'erp.propagate_conversion_hpp_for_po(uuid)', 'erp.sync_po_hpp_to_gl(uuid,date)',
)
STAGED_TABLES = {
    'cp7_analysis_stage.jobs', 'cp7_analysis_stage.headers', 'cp7_analysis_stage.page_sets',
    'cp7_analysis_stage.pages', 'cp7_analysis_stage.plan_targets', 'cp7_analysis_stage.capture_marks',
    'cp7_analysis_stage.source_checks', 'cp7_analysis_native.report_requests',
}
ACTOR = '72000000-0000-4000-8000-000000000001'
EXPECTED = {'input': 8, 'posted_fg': 3, 'wip_before': 8, 'wip_after': 5, 'fg_before': 0, 'fg_after': 3}
OUTSIDE_ROOT_PCS = 11


def pin(raw):
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def key(n):
    return str(UUID(f'72000000-0000-4000-8000-{n:012d}'))


def name(qualified):
    return sql.Identifier(*qualified.split('.'))


def one(conn, query, values=None):
    return conn.execute(query, values).fetchone()[0]


def report_rpc(conn, query, values):
    with conn.transaction():
        conn.execute('set local role authenticated')
        result = one(conn, query, values)
        conn.execute('reset role')
        return result


def insert(conn, table, **fields):
    def value(v):
        return Jsonb(v) if isinstance(v, (dict, list)) else v
    conn.execute(sql.SQL('insert into {} ({}) values ({})').format(
        name(table), sql.SQL(',').join(map(sql.Identifier, fields)),
        sql.SQL(',').join(sql.Placeholder() for _ in fields)), tuple(map(value, fields.values())))


def registry(conn):
    return {
        'db': one(conn, "select array_agg(datname order by datname) from pg_database"),
        'roles': one(conn, "select array_agg(rolname order by rolname) from pg_roles where rolname !~ '^pg_'"),
    }


def setup(conn, catalogue, sources, freshness_source, receipt):
    relations, columns, functions = (catalogue[k] for k in ('relations', 'columns', 'functions'))
    definitions = {sig: functions[sig][0] for sig in NATIVE}
    selected = set(STAGED_TABLES)
    selected.update({'erp.hpp_versions', 'erp.audit_logs', 'erp.idempotency_requests'})
    stock_sql = '\n'.join([*sources.values(), *definitions.values()])
    selected.update(n for n in set(re.findall(r'\berp\.\w+', stock_sql))
                    if n in relations and relations[n][1] in ('r', 'v'))
    selected.update(f'{schema}.{table}' for schema, table in re.findall(
        r'"schema":"([^"]+)","table":"([^"]+)"', definitions['cp7_analysis_stage.change_sources()']))
    assert selected <= relations.keys(), selected - relations.keys()

    view_order = []
    def views(table):
        if relations[table][1] != 'v' or table in view_order:
            return
        for parent in set(re.findall(r'\berp\.\w+', relations[table][9])) & relations.keys():
            if parent != table and relations[parent][1] in ('r', 'v'):
                selected.add(parent)
                views(parent)
        view_order.append(table)
    for table in sorted(selected):
        views(table)

    schemas = {r.split('.')[0] for r in selected} | {'cp7_private', 'auth', 'extensions'}
    for schema in sorted(schemas):
        owner, acl = catalogue['schemas'][schema]
        identifier = sql.Identifier(schema)
        conn.execute(sql.SQL('create schema {}').format(identifier))
        if owner == 'cp7_capture':
            conn.execute(sql.SQL('alter schema {} owner to cp7_capture').format(identifier))
        elif any(a[0] == 'cp7_capture' and a[2] == 'USAGE' for a in acl):
            conn.execute(sql.SQL('grant usage on schema {} to cp7_capture').format(identifier))
    conn.execute('create extension pgcrypto with schema extensions')
    conn.execute('set local check_function_bodies=off')
    conn.execute('create sequence erp.fg_stock_book_order_seq')
    typed = {}
    allowed_default = re.compile(r"^(gen_random_uuid\(\)|statement_timestamp\(\)|clock_timestamp\(\)|[+-]?\d+|true|false|'[^']*'(?:::[\w ]+)?|nextval\('erp\.fg_stock_book_order_seq'::regclass\))$")
    for table in sorted(selected - set(view_order)):
        metadata = sorted((r for k, r in columns.items() if k.startswith(table + ':')), key=lambda r: r[1])
        assert metadata, table
        typed[table] = metadata
        keys = {'cp7_analysis_stage.jobs': 'id', 'cp7_analysis_stage.page_sets': 'run_id'}
        field_sql = []
        for col in metadata:
            col_name, col_type, default = col[0], col[2], col[13]
            field = sql.SQL('{} {}').format(sql.Identifier(col_name), sql.SQL(col_type))
            if col[4] in ('a', 'd'):
                field += sql.SQL(' generated {} as identity').format(sql.SQL('always' if col[4] == 'a' else 'by default'))
            elif not col[5] and default and allowed_default.fullmatch(default):
                field += sql.SQL(' default ') + sql.SQL(default)
            if col_name == keys.get(table, 'id') and col_type == 'uuid':
                field += sql.SQL(' primary key')
            field_sql.append(field)
        conn.execute(sql.SQL('create table {} ({})').format(name(table), sql.SQL(',').join(field_sql)))
    conn.execute('alter table erp.idempotency_requests add unique(actor_key,operation_name,client_request_id)')
    conn.execute(catalogue['indexes']['erp.fg_inventory_balances_product_id_location_id_quality_grade_key'][0])
    for view in view_order:
        conn.execute(sql.SQL('create view {} as ').format(name(view)) + sql.SQL(relations[view][9]))
    for table in sorted(selected):
        if relations[table][0] == 'cp7_capture':
            conn.execute(sql.SQL('alter table {} owner to cp7_capture').format(name(table)))
        elif any(a[0] == 'cp7_capture' and a[2] == 'SELECT' for a in (relations[table][12] or ())):
            conn.execute(sql.SQL('grant select on {} to cp7_capture').format(name(table)))
        else:
            reads = [sql.Identifier(c[0]) for c in typed.get(table, ())
                     if any(a.startswith('cp7_capture=r/') for a in (c[12] or ()))]
            if reads:
                conn.execute(sql.SQL('grant select ({}) on {} to cp7_capture').format(sql.SQL(',').join(reads), name(table)))
    # The retained positive-attnum catalogue omits system column ACLs.
    freshness_grants = [line for line in freshness_source.splitlines() if line.startswith('grant select(')]
    assert len(freshness_grants) == 4, freshness_grants
    conn.execute('\n'.join(freshness_grants))
    for definition in definitions.values():
        conn.execute(definition)
    for sig in definitions:
        if functions[sig][1] == 'cp7_capture':
            conn.execute(sql.SQL('alter function {} owner to cp7_capture').format(sql.SQL(sig)))

    conn.execute(f"""
        create function auth.uid() returns uuid language sql stable as $$ select '{ACTOR}'::uuid $$;
        create function erp.current_app_user_id() returns uuid language sql stable as $$ select auth.uid() $$;
        create function erp.require_internal() returns void language plpgsql as $$ begin return; end $$;
        create function erp.has_permission(p text) returns boolean language sql stable as $$
            select p in ('production.final_sku.post','production.wip.view','warehouse.stock.view') $$;
        create function erp.require_permission(p text) returns void language plpgsql as $$
            begin if not erp.has_permission(p) then raise exception 'FIXTURE_PERMISSION_DENIED'; end if; end $$;
        create function cp7_private.access_now() returns jsonb language sql stable as $$
            select jsonb_build_object('actor',auth.uid(),'role','OWNER') $$;
        create function cp7_schedule_native.access_now(boolean) returns jsonb language sql stable as $$
            select cp7_private.access_now() $$;
        create function cp7_analysis_native.financial_source(jsonb,timestamptz) returns jsonb language plpgsql as $$
            begin raise exception 'FIXTURE_FINANCE_SOURCE_UNAVAILABLE'; end $$;
        create table public.fixture_finance_hooks(name text not null);
    """)
    for sig in FINANCE_HOOKS:
        raw = functions[sig][0]
        returns = re.search(r'(?m)^ RETURNS (\S+)\s*$', raw)[1]
        ret = 'return;' if returns == 'void' else 'return null;'
        conn.execute(f"create function {sig} returns {returns} language plpgsql as $$ begin "
                     f"insert into public.fixture_finance_hooks values('{sig}'); {ret} end $$")
    for source in sources.values():
        conn.execute(source)
    receipt['source'] = {
        'current_candidate': HEAD,
        'cp7_files': {path: pin(body.encode()) for path, body in sources.items()},
        'freshness_grants_source': {FRESHNESS_FILE: pin(freshness_source.encode())},
        'native27_bodies': {sig: pin(definition.encode()) for sig, definition in definitions.items()},
        'native27_views': {view: pin(relations[view][9].encode()) for view in view_order},
        'typed_fixture_relations': sorted(typed),
        'finance_dependencies_fixture_only': list(FINANCE_HOOKS),
    }


def seed(conn):
    now, day = conn.execute("select clock_timestamp(),(clock_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()
    at = now - timedelta(seconds=30)
    previous_day = str(day - timedelta(days=1))
    x = dict(product=key(2), root=key(3), size=key(4), model=key(5), po=key(6), group=key(7), fg_location=key(8),
             roll=key(9), slot=key(10), report_date=str(day),
             outside_product=key(11), outside_root=key(12),
             period=dict(from_date=previous_day, through_date=previous_day, group_mode='AS_SOLD'))
    insert(conn, 'erp.products', id=x['product'], identity_root_id=x['root'], model_id=x['model'], size_id=x['size'],
           sku='CP7-B-QC-8', product_name='Fixture QC 8 pcs', effective_from=at, is_active=True)
    insert(conn, 'erp.locations', id=x['fg_location'], is_active=True, location_type='FG_WAREHOUSE')
    insert(conn, 'erp.production_orders', id=x['po'], model_id=x['model'], status='SEWING', current_stage='SEWING')
    insert(conn, 'erp.cutting_groups', id=x['group'], po_id=x['po'], status='PICKED_UP',
           cut_at=at, picked_up_at=at, material_issue_posted=True, row_version=1)
    insert(conn, 'erp.cutting_group_rolls', id=x['roll'], cutting_group_id=x['group'])
    insert(conn, 'erp.cutting_group_size_slots', id=x['slot'], cutting_group_id=x['group'], size_id=x['size'], slot_no=1)
    insert(conn, 'erp.cutting_roll_yields', cutting_group_roll_id=x['roll'], size_slot_id=x['slot'], qty_pcs=8)
    # A seeded balance for a different root is a negative control for the
    # report filter. Only the selected SKU is posted through the QC writer.
    insert(conn, 'erp.products', id=x['outside_product'], identity_root_id=x['outside_root'], model_id=key(13), size_id=x['size'],
           sku='CP7-B-OUTSIDE', product_name='Outside report scope', effective_from=at, is_active=True)
    insert(conn, 'erp.fg_stock_movements', product_id=x['outside_product'], location_id=x['fg_location'],
           lot_id=key(14), qty_signed=OUTSIDE_ROOT_PCS, quality_grade='GRADE_A', movement_type='QC_GOOD',
           source_type='QC_INSPECTION_ITEM', source_id=key(15), physical_at=at, system_created_at=at)
    return x


def capture(conn, x):
    scope = dict(cutting_groups=[x['group']], opening_items=[], unsourced_bs=[])
    value = one(conn, 'select cp7_wip.capture_production(%s,%s)', (Jsonb(scope), uuid4()))
    assert value['capture_complete'] and value['result']['status'] == 'COMPLETE', value
    return value


def totals(snapshot):
    return {k: sum(int(t[k + '_pcs']) for t in snapshot['result']['totals'])
            for k in ('input', 'wip', 'fg', 'bs', 'withheld', 'exited')}


def source_progress(conn, group):
    return one(conn, """select jsonb_build_object('input',effective_qty_pcs,'qc_good',qc_good_qty_pcs,
        'remaining',remaining_qc_qty_pcs,'completions',completion_count)
        from erp.v_fg_partial_completion_progress where cutting_group_id=%s""", (group,))


def stage_fixture(conn, x, snapshot):
    now, snap = conn.execute('select clock_timestamp(),pg_current_snapshot()::text').fetchone()
    job, run = uuid4(), uuid4()
    target = f"{x['root']}:{x['size']}"
    identity = sha256(f"{run}:{target}:{snapshot['run_id']}".encode()).hexdigest()
    row = dict(target=dict(key=target, size_id=x['size'], membership=[x['product']]),
               actual_fg=dict(state='KNOWN', value='0', unit='PCS', refs=[]), production_state='ACTIVE')
    page = json.dumps(dict(index=0, page_count=1, target_lo=1, target_hi=1, targets_total=1,
                           items=dict(recommendations=[row])))
    header = json.dumps(dict(product_labels=[dict(target_key=target, sku='CP7-B-QC-8', product_name='Fixture QC 8 pcs')]))
    insert(conn, 'cp7_analysis_stage.jobs', id=job, run_id=run, actor=ACTOR, query=x['period'], state='DONE',
           captured_at=now, updated_at=now)
    conn.execute('insert into cp7_analysis_stage.capture_marks(job_id,source_snapshot) values(%s,%s::pg_snapshot)', (job, snap))
    insert(conn, 'cp7_analysis_stage.page_sets', run_id=run, identity_hash=identity, totals=dict(targets=1))
    insert(conn, 'cp7_analysis_stage.headers', run_id=run, job_id=job, body=header, page_count=1, targets_total=1)
    insert(conn, 'cp7_analysis_stage.pages', run_id=run, idx=0, target_lo=1, target_hi=1, body=page)
    insert(conn, 'cp7_analysis_stage.plan_targets', job_id=job, ord=1, target_key=target, row=row)
    return dict(run_id=str(run), identity_hash=identity, kind='PERIOD', series_id=None, expected_revision=None,
                title='Penyelesaian QC fixture B', reason='Uji stok dan arsip pada periode yang sama',
                finance='DEFERRED', explicit_review=True)


def publish(conn, payload):
    request = uuid4()
    status = report_rpc(conn, 'select public.erp_cp7_publish_report_v2(%s,%s)', (Jsonb(payload), request))
    assert status['state'] == 'RUNNING' and status['unit_count'] == 4, status
    for _ in range(status['unit_count']):
        status = report_rpc(conn, 'select public.erp_cp7_step_report_v2(%s)', (request,))
        if status['state'] == 'FAILED':
            row = one(conn, 'select to_jsonb(j) from cp7_analysis_stage.report_jobs j where request_id=%s', (request,))
            raise AssertionError({k: row[k] for k in ('failure_unit','failure_sqlstate','failure_code','failure_message')})
    assert status['state'] == 'DONE' and status['units_done'] == 4, status
    publication = status['publication_id']
    doc = report_rpc(conn, 'select public.erp_cp7_read_report_v2(%s)', (publication,))
    section = report_rpc(conn, 'select public.erp_cp7_read_report_section_v2(%s,0,%s)', (publication, doc['access_epoch']))
    stored = one(conn, 'select to_jsonb(p) from cp7_analysis_stage.report_publications p where id=%s', (publication,))
    actual = one(conn, """select r.body from cp7_analysis_stage.report_reads r
        where r.job_id=(select job_id from cp7_analysis_stage.report_publications where id=%s) and r.kind='ACTUALS'""", (publication,))
    assert sha256(doc['summary'].encode()).hexdigest() == doc['summary_sha256']
    assert sha256(section['body'].encode()).hexdigest() == section['sha256']
    assert sha256((doc['summary_sha256'] + '\n' + section['sha256']).encode()).hexdigest() == doc['report_hash']
    return dict(doc=doc, section=section, stored=stored, actual=actual)


def check_report_stock(conn, x, report, expected):
    actual = report['actual']
    # This fixture has no reservations or reversals. Sum the ledger rows
    # independently for both roots at the publication's actuals boundary.
    rows = conn.execute("""select p.identity_root_id::text,sum(m.qty_signed) from erp.fg_stock_movements m
        join erp.products p on p.id=m.product_id
        where p.identity_root_id in (%s,%s) and m.physical_at <= %s and m.system_created_at <= %s
        group by p.identity_root_id""", (x['root'], x['outside_root'], actual['read_at'], actual['read_at'])).fetchall()
    book = dict(rows)
    assert (book.get(x['root'],0),book.get(x['outside_root'])) == (expected,OUTSIDE_ROOT_PCS), book
    assert actual['stock'] == {x['root']: {'physical_fg_pcs':str(expected),'available_fg_pcs':str(expected)}}, actual
    return dict(target_pcs=book.get(x['root'],0), outside_filter_pcs=book[x['outside_root']], read_at=actual['read_at'])


def exercise(conn, receipt):
    receipt['expected'] = dict(EXPECTED, outside_filter_pcs=OUTSIDE_ROOT_PCS)
    with conn.transaction():
        x = seed(conn)
    receipt['fixture'] = x
    with conn.transaction():
        before = capture(conn, x)
        receipt['wip_before'] = before
        assert totals(before) == dict(input=8,wip=8,fg=0,bs=0,withheld=0,exited=0), totals(before)
        receipt['progress_book_before'] = source_progress(conn, x['group'])
        assert receipt['progress_book_before'] == dict(input=8,qc_good=0,remaining=8,completions=0)
        receipt['fg_ledger_before_pcs'] = one(conn, 'select coalesce(sum(qty_signed),0) from erp.fg_stock_movements where product_id=%s', (x['product'],))
        assert receipt['fg_ledger_before_pcs'] == EXPECTED['fg_before']
        payload = stage_fixture(conn, x, before)
    old_report = publish(conn, payload)
    receipt['report_before'] = old_report
    receipt['report_book_before'] = check_report_stock(conn, x, old_report, 0)
    with conn.transaction():
        physical_at = one(conn, 'select clock_timestamp()').isoformat()
        request = dict(cutting_group_id=x['group'], destination_location_id=x['fg_location'], completion_mode='PARTIAL_SELECTION',
                       good_qty_pcs=3, physical_at=physical_at, reason='Fixture partial QC',
                       lines=[dict(final_product_id=x['product'], qty_good_pcs=3, qty_bs_pcs=0)])
        posted = one(conn, 'select erp.post_final_sku_allocation_v1(%s,%s,%s)', (Jsonb(request), uuid4(), 1))
        receipt['qc_post'] = posted
    with conn.transaction():
        after = capture(conn, x)
        reopened = one(conn, 'select cp7_wip.serve_production(%s)', (before['run_id'],))
        receipt.update(wip_after=after, wip_reopened=reopened)
        assert totals(after) == dict(input=8,wip=5,fg=3,bs=0,withheld=0,exited=0), totals(after)
        receipt['progress_book_after'] = source_progress(conn, x['group'])
        assert receipt['progress_book_after'] == dict(input=8,qc_good=3,remaining=5,completions=1)
        assert reopened['source_state'] == 'ARCHIVED_STALE' and reopened['result'] == before['result']
        assert reopened['captured_at'] == before['captured_at']
        ledger = one(conn, """
          select jsonb_agg(jsonb_build_object('sku',m.product_id,'root',p.identity_root_id,'size',p.size_id,'location',m.location_id,
          'qty',m.qty_signed,'unit','PCS','grade',m.quality_grade,'source',m.source_id,'lot',m.lot_id,'movement',m.movement_type,
          'fg_cache',b.cached_qty_pcs,'lot_cache',l.cached_qty_pcs,'po',l.po_id,'qc',i.inspection_id,
          'ledger_time',m.system_created_at,'authoritative_hpp_available',exists(select 1 from erp.hpp_versions h where h.lot_id=l.id and h.is_current)))
          from erp.fg_stock_movements m join erp.products p on p.id=m.product_id
          join erp.fg_lots l on l.id=m.lot_id join erp.qc_inspection_items i on i.id=m.source_id
          join erp.fg_inventory_balances b on (b.product_id,b.location_id,b.quality_grade)=(m.product_id,m.location_id,m.quality_grade)
          where m.product_id=%s""", (x['product'],))
        receipt['fg_ledger'] = ledger
        assert len(ledger) == 1
        got = ledger[0]
        assert (got['sku'],got['root'],got['size'],got['location'],got['po'],got['qc']) == (
            x['product'],x['root'],x['size'],x['fg_location'],x['po'],posted['qc_inspection_id'])
        assert (got['qty'],got['fg_cache'],got['lot_cache'],got['unit'],got['grade'],got['movement']) == (
            3,3,3,'PCS','GRADE_A','QC_GOOD')
        pools = after['result']['graph']['pools']
        assert len(pools)==1 and pools[0]['size_id']==x['size'] and x['group'] in pools[0]['key']
        assert int(posted['fg_stock_in_qty_pcs']) == totals(after)['fg']
        assert totals(after)['wip'] + got['qty'] == EXPECTED['input']
        receipt['finance_hook_calls'] = conn.execute('select name from public.fixture_finance_hooks order by name').fetchall()
        assert set(r[0] for r in receipt['finance_hook_calls']) == set(FINANCE_HOOKS)
        assert not got['authoritative_hpp_available']
        receipt['snapshot_stock_status'] = 'PASS'

    revised = dict(payload, series_id=old_report['doc']['series_id'], expected_revision='1')
    new_report = publish(conn, revised)
    receipt['report_after'] = new_report
    receipt['report_book_after'] = check_report_stock(conn, x, new_report, 3)
    with conn.transaction():
        for report, qty in ((old_report,0), (new_report,3)):
            doc, body = report['doc'], report['section']['body']
            assert doc['period_query'] == x['period'] and doc['report_date'] == x['report_date']
            assert doc['run_id'] == payload['run_id'] and doc['identity_hash'] == payload['identity_hash']
            assert 'CP7-B-QC-8' in body and f'size {x["size"]}' in body
            assert f'stok tersedia setelah reservasi aktual {qty} PCS' in body
            assert 'stok fisik saat analisis 0 PCS' in body
            assert 'Data analisis per ' in body and 'Data analisis per ' in doc['summary']
            assert doc['finance'] == 'DEFERRED' and report['actual']['finance'] is None
        assert new_report['doc']['freshness']['state'] == 'CHANGES_RECORDED'
        assert new_report['doc']['revision'] == '2' and new_report['doc']['data_as_of'] == old_report['doc']['data_as_of']
        oid = old_report['doc']['id']
        old_doc = report_rpc(conn, 'select public.erp_cp7_read_report_v2(%s)', (oid,))
        old_sec = report_rpc(conn, 'select public.erp_cp7_read_report_section_v2(%s,0,%s)', (oid,old_doc['access_epoch']))
        old_raw = one(conn, 'select to_jsonb(p) from cp7_analysis_stage.report_publications p where id=%s', (oid,))
        assert old_raw == old_report['stored'] and old_sec == old_report['section']
        assert old_doc == dict(old_report['doc'],is_latest=False)
        receipt['archive_reopened'] = {'same_publication_row':True,'same_section':True,'same_hash':old_doc['report_hash'],'is_latest':False}
        count = one(conn, 'select count(*) from cp7_analysis_stage.report_jobs')
        try:
            with conn.transaction():
                report_rpc(conn, 'select public.erp_cp7_publish_report_v2(%s,%s)',
                    (Jsonb(dict(payload, identity_hash='0'*64)), uuid4()))
        except psycopg.Error as error:
            receipt['identity_refusal'] = dict(sqlstate=error.sqlstate,message=error.diag.message_primary)
            assert error.diag.message_primary == 'CP7_REPORT_V2_IDENTITY_CHANGED'
        else:
            raise AssertionError('Mismatched snapshot accepted')
        assert one(conn, 'select count(*) from cp7_analysis_stage.report_jobs') == count
        receipt['identity_refusal']['report_jobs_unchanged'] = True
        receipt['report_stock_archive_status'] = 'PASS'


def main(args):
    connect = dict(host='127.0.0.1', port=args.port, user='cp7_b_lab', connect_timeout=3)
    receipt = dict(scope='DISPOSABLE_NATIVE_QC_PHYSICAL_AND_CP7_REPORT_FIXTURE', candidate=HEAD,
                   snapshot_stock_status='BLOCKED', report_stock_archive_status='BLOCKED',
                   authoritative_hpp_value_status='BLOCKED', actual_combined_erp_cases=0)
    source_files = {f:(args.source/f).read_text() for f in FILES}
    freshness_source = (args.source/FRESHNESS_FILE).read_text()
    raw = args.native27.read_bytes()
    assert pin(raw) == {'bytes':30376182, 'sha256':ORIGINAL_SHA}
    catalogue = json.loads(raw)['committed'][CASE]['Native_to_copy_handoff']['raw_current_catalog']
    exit_code = 0
    with psycopg.connect(dbname='postgres', autocommit=True, **connect) as admin:
        assert admin.execute("""select host(inet_server_addr()),current_user,current_setting('server_version'),
            current_setting('data_directory')""").fetchone() == ('127.0.0.1','cp7_b_lab','17.6',str(args.data))
        baseline = registry(admin)
        assert baseline['roles'] == ['cp7_b_lab'] and DB not in baseline['db'], baseline
        try:
            for role in ROLES:
                admin.execute(sql.SQL('create role {}').format(sql.Identifier(role)))
            admin.execute(sql.SQL('create database {}').format(sql.Identifier(DB)))
            with psycopg.connect(dbname=DB, autocommit=True, **connect) as conn:
                conn.execute("set statement_timeout='15s'; set lock_timeout='3s'; set timezone='UTC'")
                with conn.transaction():
                    setup(conn, catalogue, source_files, freshness_source, receipt)
                exercise(conn, receipt)
        except Exception as error:
            receipt['first_failure'] = dict(type=type(error).__name__, message=str(error),
                sqlstate=getattr(error,'sqlstate',None))
            exit_code = 1
        finally:
            admin.execute(sql.SQL('drop database if exists {}').format(sql.Identifier(DB)))
            for role in reversed(ROLES):
                admin.execute(sql.SQL('drop role if exists {}').format(sql.Identifier(role)))
            final = registry(admin)
            receipt['recovery'] = dict(before=baseline, after=final, exact=baseline==final, disposable_db_dropped=DB not in final['db'])
    with args.output.open('x') as stream:
        json.dump(receipt, stream, indent=2, default=str)
        stream.write('\n')
    print(json.dumps({k:receipt.get(k) for k in ('snapshot_stock_status','report_stock_archive_status','first_failure','recovery')}))
    return exit_code or int(not receipt['recovery']['exact'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for opt in ('source','native27','data','output'):
        parser.add_argument(opt,type=Path)
    parser.add_argument('--port', type=int, default=55428)
    raise SystemExit(main(parser.parse_args()))
