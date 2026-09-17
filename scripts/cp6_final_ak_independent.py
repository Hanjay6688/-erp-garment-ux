#!/usr/bin/env python3
"""Independent AK observations on original functions and synthetic documents.

The writer provides runtime qualification and fixture actors, not these oracles.
Every case persists, including a proven defect, before the next one executes.
Temporary native schema USAGE is restored; this is not an HTTP/CSV claim.
"""
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
import json, os, subprocess, sys, traceback, uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import psycopg
import cp6_v2620ak_runtime as runtime
import cp6_v2620ak_review as setup
import cp6_final_gap_native as gaps
from cp6_v2620n_rollback_guards import function_catalog

PRODUCT = '684b708dee785934fe5fe4fe567c454cba873ea9'
PRODUCT_TREE = '1f4c57517c0d4abd6612d4a8b36b2e9cbe437834'
REPORT = Path('cp6-proof/final-audit/AK_INDEPENDENT.json')
actors, base, production = setup.actors, setup.base, setup.production


def owner(cur):
    production.owner(cur)


def attempt(cur, fn):
    actors.admin(cur)
    before = actors.boundary(cur)
    cur.execute('savepoint ak_independent_operation')
    try:
        result = fn()
    except psycopg.Error as exc:
        error = dict(sqlstate=exc.sqlstate, message=exc.diag.message_primary)
        cur.execute('rollback to savepoint ak_independent_operation')
        actors.admin(cur)
        assert actors.boundary(cur) == before, error
        result = dict(ok=False, error=error, atomic_refusal=True)
    else:
        result = dict(ok=True, result=result)
    actors.admin(cur)
    cur.execute('release savepoint ak_independent_operation')
    return result


def run_owner(cur, sql, params):
    owner(cur)
    return cur.execute(sql, params)


def stage(cur, batch, entity, n, payload):
    return run_owner(cur, 'select erp.stage_migration_row(%s,%s,%s,%s,%s::jsonb,%s::jsonb)',
                     (batch, entity, n, entity+'-'+str(n), json.dumps(payload), json.dumps(payload))).fetchone()[0]


def new_batch(cur, day):
    return run_owner(cur, 'select erp.create_migration_batch(%s,%s,null,null)',
                     ('AKI-'+uuid.uuid4().hex, production.at(day-timedelta(days=1), 0))).fetchone()[0]


def validate(cur, batch):
    result = run_owner(cur, 'select * from erp.validate_migration_batch(%s)', (batch,)).fetchone()
    actors.admin(cur)
    rows = cur.execute('select source_row_no,validation_status,validation_errors from erp.migration_staging_rows '
                       'where batch_id=%s order by entity_type,source_row_no', (batch,)).fetchall()
    return dict(counts=result, rows=rows)


def prepare(cur, batch):
    ident = run_owner(cur, 'select erp.prepare_migration_opening_balance(%s,null)', (batch,)).fetchone()[0]
    actors.admin(cur)
    return ident


def post(cur, ident):
    run_owner(cur, 'select erp.post_opening_balance(%s)', (ident,))
    actors.admin(cur)


def opening_state(cur, ident):
    actors.admin(cur)
    h = cur.execute('select opening_number,opening_date,status from erp.opening_balance_headers where id=%s', (ident,)).fetchone()
    return dict(header=h,
        lines=cur.execute('select balance_type,qty,amount,unit_cost_snapshot from erp.opening_balance_items where opening_id=%s order by id', (ident,)).fetchall(),
        bs=cur.execute('select qty_pcs from erp.bs_cases where bs_number like %s', ('OBS-'+h[0]+'-%',)).fetchall(),
        journal=cur.execute("select a.mapping_key,sum(l.debit-l.credit) from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id join erp.accounting_account_mappings a on a.account_id=l.account_id where j.source_type='OPENING_BALANCE' and j.source_id=%s group by a.mapping_key order by a.mapping_key", (ident,)).fetchall())


def simple_balance(cur, day, balance_type, payload, invalid, direct=False):
    data = dict(balance_type=balance_type, **payload)
    if direct:
        owner(cur)
        ident = cur.execute("insert into erp.opening_balance_headers(opening_number,opening_date,status) values(%s,%s,'DRAFT') returning id",
                            ('AKI-'+uuid.uuid4().hex, day-timedelta(days=1))).fetchone()[0]
        cur.execute('insert into erp.opening_balance_items(opening_id,balance_type,qty,amount,unit_cost_snapshot) values(%s,%s,%s,%s,%s)',
                    (ident, balance_type, data.get('qty'), data.get('amount'), data.get('unit_cost')))
        preview = None
    else:
        batch = new_batch(cur, day)
        stage(cur, batch, 'OPENING_BALANCE_ITEM', 1, data)
        preview = validate(cur, batch)
        if preview['counts'] == (1, 0, 1):
            assert invalid and preview['rows'][0][2], preview
            refusal = attempt(cur, lambda: prepare(cur, batch))
            assert not refusal['ok'], refusal
            return dict(status='PASS', preview=preview, refused=refusal)
        assert preview['counts'] == (1, 1, 0), preview
        ident = prepare(cur, batch)
    result = attempt(cur, lambda: post(cur, ident))
    state = opening_state(cur, ident)
    if invalid:
        status = ('PASS' if direct else 'GAP_PROVEN') if not result['ok'] else 'BUG_PROVEN'
        return dict(status=status, input=data, direct_draft=direct, preview=preview, posting=result, state=state,
                    invariant='Invalid BS pieces or negative WIP must not become a posted opening document')
    assert result['ok'] and state['header'][2] == 'POSTED', (result, state)
    if balance_type == 'BS':
        assert state['bs'] == [(2,)], state
    else:
        assert dict(state['journal']).get('WIP') == Decimal('3.75'), state
    return dict(status='PASS', input=data, direct_draft=direct, preview=preview, state=state)


def direct_material(cur, day):
    batch, material = gaps.raw_batch(cur, day, 'VALID')
    assert validate(cur, batch)['counts'] == (1, 1, 0)
    ident = prepare(cur, batch)
    before = production.ledger(cur)
    run_owner(cur, 'update erp.opening_balance_items set qty=20,unit_cost_snapshot=2.75 where opening_id=%s', (ident,))
    assert production.ledger(cur) == before
    post(cur, ident)
    qty, value = cur.execute('select sum(qty_signed),sum(qty_signed*unit_cost_snapshot) from erp.material_stock_movements where material_id=%s', (material,)).fetchone()
    assert (qty, value) == (20, Decimal('55.00')), (qty, value)
    refused = attempt(cur, lambda: run_owner(cur, 'update erp.opening_balance_items set qty=21 where opening_id=%s', (ident,)).rowcount)
    assert not refused['ok'], refused
    return dict(status='PASS', actual_qty=qty, actual_value=value, draft_ledger_inert=True, posted_edit=refused)


def direct_stage_refusal(cur, day, target):
    batch, _ = gaps.raw_batch(cur, day, 'VALID')
    if target == 'ROW':
        fn = lambda: run_owner(cur, "update erp.migration_staging_rows set normalized_payload=jsonb_set(normalized_payload,'{qty}','20'::jsonb) where batch_id=%s", (batch,)).rowcount
    else:
        fn = lambda: run_owner(cur, 'update erp.migration_batches set cutover_at=%s where id=%s', (production.at(day, 0), batch)).rowcount
    result = attempt(cur, fn)
    assert not result['ok'] and result['error']['sqlstate'] in ('42501', 'P0001'), result
    return dict(status='PASS', native_owner_write=result)


def roll_draft(cur, day, after_prepare):
    batch, material = gaps.raw_batch(cur, day, 'VALID')
    actors.admin(cur)
    cur.execute('delete from erp.migration_staging_rows where batch_id=%s', (batch,))
    cur.execute("update erp.materials set material_type='FABRIC' where id=%s", (material,))
    sku = cur.execute('select material_sku from erp.materials where id=%s', (material,)).fetchone()[0]
    loc = cur.execute("select location_code from erp.locations where is_active and location_type='RAW_MATERIAL_WAREHOUSE' order by id limit 1").fetchone()[0]
    payload = dict(material_sku=sku, roll_number='AKI-'+uuid.uuid4().hex, opening_qty='10', unit_cost='1.25', location_code=loc)
    stage(cur, batch, 'MATERIAL_ROLL', 1, payload)
    if not after_prepare:
        payload.update(opening_qty='8', unit_cost='2.75')
        stage(cur, batch, 'MATERIAL_ROLL', 1, payload)
    assert validate(cur, batch)['counts'] == (1, 1, 0)
    assert run_owner(cur, 'select erp.apply_migration_master_rows(%s)', (batch,)).fetchone()[0] == 1
    ident = prepare(cur, batch)
    if after_prepare:
        # The applied roll identity is a master; its unposted opening item is
        # still an ordinary editable draft, under the existing owner RLS.
        run_owner(cur, 'update erp.opening_balance_items set qty=8,unit_cost_snapshot=2.75 where opening_id=%s', (ident,))
    post(cur, ident)
    actual = cur.execute('select sum(qty_signed),sum(qty_signed*unit_cost_snapshot) from erp.material_stock_movements where material_id=%s', (material,)).fetchone()
    assert actual == (8, Decimal('22')), actual
    run_owner(cur, 'select erp.finalize_migration_batch(%s)', (batch,))
    actors.admin(cur)
    before = actors.boundary(cur)
    run_owner(cur, 'select erp.finalize_migration_batch(%s)', (batch,))
    actors.admin(cur)
    assert actors.boundary(cur) == before
    return dict(status='PASS', edit_after_prepare=after_prepare, actual=actual, finalization_replay_inert=True)


def typed_preview(cur, day, entity, field):
    batch = new_batch(cur, day)
    tag = 'AKI-'+uuid.uuid4().hex[:16]
    payloads = {
        'CUSTOMER': dict(customer_code=tag, customer_name='Synthetic typed import'),
        'SIZE': dict(size_code=tag),
        'SUPPLIER': dict(supplier_code=tag, supplier_name='Synthetic typed supplier'),
        'CONTRACTOR': dict(contractor_code=tag, contractor_name='Synthetic typed contractor'),
    }
    payload = payloads[entity]
    payload[field] = 'invalid-value'
    stage(cur, batch, entity, 1, payload)
    preview = validate(cur, batch)
    if preview['counts'] == (1, 0, 1):
        assert preview['rows'][0][2]
        return dict(status='PASS', entity=entity, field=field, preview=preview)
    assert preview['counts'] == (1, 1, 0), preview
    result = attempt(cur, lambda: run_owner(cur, 'select erp.apply_migration_master_rows(%s)', (batch,)).fetchone()[0])
    assert not result['ok'], result
    return dict(status='GAP_PROVEN', entity=entity, field=field, preview=preview, apply_refusal=result)


def run():
    head, tree = runtime.verify_audit_source()
    root = Path(__file__).resolve().parents[1]
    git = lambda *args: subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()
    assert git('rev-parse', PRODUCT+'^{tree}') == PRODUCT_TREE
    assert not git('diff', '--name-only', PRODUCT, 'HEAD', '--', 'src', 'supabase', 'package.json', 'package-lock.json')
    report = dict(status='INCOMPLETE', audit_head=head, audit_tree=tree, product_head=PRODUCT,
                  product_tree=PRODUCT_TREE, runtime_generation='AK', cases={}, production_go=False,
                  csv_transport_tested=False, global_cp6_acceptance=False)
    def save():
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(report, indent=2, default=str)+'\n')
    with psycopg.connect(setup.ADMIN) as conn, conn.cursor() as cur:
        cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='180s';set local lock_timeout='8s'")
        assert len(runtime.verified_successor(cur)) == 690
        initial, catalog = actors.boundary(cur), function_catalog(cur)
        usage = cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        report['temporary_schema_usage_grant'] = not usage
        if not usage:
            cur.execute('grant usage on schema erp to authenticated')
        actors.actors.claims(cur, dict(sub=base.OPERATOR_AUTH, role='authenticated'))
        base.load_fixture_foundation(cur)
        actors.admin(cur)
        day = cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
        specs = [('DIRECT_MATERIAL_DRAFT', lambda c: direct_material(c, day))]
        specs += [('DIRECT_STAGE:'+target, lambda c,t=target: direct_stage_refusal(c, day, t)) for target in ('ROW', 'BATCH')]
        specs += [('ROLL_DRAFT:'+str(after), lambda c,a=after: roll_draft(c, day, a)) for after in (False, True)]
        for direct in (False, True):
            for qty in ('2', '1.5', '-2', '0', None):
                payload = {} if qty is None else dict(qty=qty)
                specs.append(('BS:'+str(direct)+':'+str(qty), lambda c,p=payload,b=qty!='2',d=direct: simple_balance(c, day, 'BS', p, b, d)))
            for tag, payload, invalid in [('AMOUNT',dict(amount='3.75'),False), ('COST',dict(qty='3',unit_cost='1.25'),False),
                                          ('NEGATIVE_AMOUNT',dict(amount='-5.25'),True), ('NEGATIVE_QTY',dict(qty='-2',unit_cost='1.25'),True)]:
                specs.append(('WIP:'+str(direct)+':'+tag, lambda c,p=payload,b=invalid,d=direct: simple_balance(c, day, 'WIP', p, b, d)))
        specs += [('TYPED:'+entity+':'+field, lambda c,e=entity,f=field: typed_preview(c, day, e, f))
                  for entity, field in [('CUSTOMER','is_active'),('SIZE','sort_order'),('SUPPLIER','supplier_type'),('CONTRACTOR','attendance_required')]]
        report['planned_case_ids'] = [name for name, _ in specs]
        save()
        for name, fn in specs:
            actors.admin(cur)
            before = actors.boundary(cur)
            cur.execute('savepoint ak_independent_case')
            try:
                row = fn(cur)
            except Exception as exc:
                row = dict(status='INCOMPLETE', error=str(exc), traceback=traceback.format_exc())
            finally:
                cur.execute('rollback to savepoint ak_independent_case')
                actors.admin(cur)
                cur.execute('release savepoint ak_independent_case')
            row['boundary_restored'] = actors.boundary(cur) == before
            if not row['boundary_restored']:
                row['status'] = 'INCOMPLETE'
            report['cases'][name] = row
            save()
            print(json.dumps(dict(case=name, status=row['status'], error=row.get('error'))), flush=True)
        report['catalog_unchanged'] = function_catalog(cur) == catalog
        conn.rollback()
        cur.execute("set local timezone='Asia/Jakarta'")
        report['boundary_restored'] = actors.boundary(cur) == initial
        report['schema_usage_restored'] = cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0] == usage
        report['auth_users'], report['app_users'] = cur.execute('select (select count(*) from auth.users),(select count(*) from erp.app_users)').fetchone()
        conn.rollback()
    report['counts'] = {s:sum(row['status']==s for row in report['cases'].values()) for s in ('PASS','BUG_PROVEN','GAP_PROVEN','INCOMPLETE')}
    clean = all(report[k] for k in ('catalog_unchanged','boundary_restored','schema_usage_restored')) and report['auth_users'] == report['app_users'] == 0
    if clean and not report['counts']['INCOMPLETE']:
        report['status'] = 'CP6_HOLD' if report['counts']['BUG_PROVEN'] or report['counts']['GAP_PROVEN'] else 'INDEPENDENT_PASS_REVIEWED_SCOPE'
    save()
    return report


if __name__ == '__main__':
    assert os.environ['PGURL'] == setup.URL and os.environ['CP6_AI_INDEPENDENT_CONFIRM'] == 'postgres'
    result = run()
    print(json.dumps({k:v for k,v in result.items() if k not in ('cases','planned_case_ids')}))
    raise SystemExit(0 if result['status'] == 'INDEPENDENT_PASS_REVIEWED_SCOPE' else 1)
