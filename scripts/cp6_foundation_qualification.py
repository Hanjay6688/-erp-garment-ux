#!/usr/bin/env python3
"""Original AL transactions qualify S01–S05; findings are not acceptance.

Only the already populated disposable Auth clone is admitted. Synthetic masters
are inserted, but stock and posted documents use the installed original APIs.
Native legacy calls use an ordinary authenticated OWNER with its existing
function EXECUTE grants. Temporary schema USAGE is recorded and rolled back;
this is not an HTTP exposure claim. No installed function or guard is modified.
"""
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys
import traceback
import uuid

import psycopg
from psycopg import sql

import cp6_v2620al_runtime as runtime
from cp6_v2620n_rollback_guards import function_catalog
from cp6_v2620u_install_diagnostic import snapshot

PG = 'postgresql://postgres:postgres@127.0.0.1:54322/cp6_auth'
ADMIN = PG.replace('postgres:postgres@', 'supabase_admin:postgres@')
OWNER = None
MASTER = {}


def encode(value):
    return json.dumps(value, default=lambda x: x.isoformat() if hasattr(x, 'isoformat') else str(x))


def admin(cur):
    cur.execute('reset session authorization')


def owner(cur):
    admin(cur)
    cur.execute("select set_config('request.jwt.claims',%s,true)", (encode(dict(sub=OWNER, role='authenticated')),))
    cur.execute('set local session authorization authenticated')
    assert cur.execute('select session_user').fetchone()[0] == 'authenticated'


def call(cur, name, *args):
    assert re.fullmatch(r'(erp|public)\.[a-z][a-z0-9_]*', name)
    owner(cur)
    query = sql.SQL('select {}({})').format(sql.Identifier(*name.split('.')),
        sql.SQL(',').join(sql.Placeholder() for _ in args))
    value = cur.execute(query, args).fetchone()[0]
    admin(cur)
    return value


def attempt(cur, operation):
    admin(cur)
    before = snapshot(cur)
    cur.execute('savepoint ordinary_command')
    error = None
    result = None
    try:
        result = operation()
    except psycopg.Error as exc:
        error = dict(sqlstate=exc.sqlstate, message=exc.diag.message_primary)
        cur.execute('rollback to savepoint ordinary_command')
    finally:
        admin(cur)
        cur.execute('release savepoint ordinary_command')
    if error:
        assert snapshot(cur) == before, 'Rejected command changed transactional data/catalog'
    return result, error


def tag():
    return 'CP6-S-' + uuid.uuid4().hex[:14].upper()


def locations(cur):
    admin(cur)
    result = []
    for _ in range(2):
        result.append(cur.execute("insert into erp.locations(location_code,location_name,location_type,is_active) values(%s,'Synthetic foundation warehouse','RAW_MATERIAL_WAREHOUSE',true) returning id", (tag(),)).fetchone()[0])
    return result


def material(cur, kind='OTHER', category=None):
    admin(cur)
    return cur.execute("insert into erp.materials(material_sku,material_name,material_type,unit_code,accessory_category_id) values(%s,'Synthetic foundation material',%s,%s,%s) returning id",
        (tag(), kind, 'yd' if kind == 'FABRIC' else MASTER['pcs'], category)).fetchone()[0]


def category(cur, factor=None):
    admin(cur)
    ident = cur.execute("insert into erp.accessory_categories(category_code,category_name,base_uom_code,is_active) values(%s,'Synthetic count accessory',%s,true) returning id", (tag(), MASTER['pcs'])).fetchone()[0]
    if factor:
        # Real dozen/gross units, without redefining any installed unit.
        wanted = {12:'LUSIN',144:'GROSS'}[factor]
        uom = cur.execute("select unit_code from erp.uom_definitions where dimension='COUNT' and is_active and upper(unit_code)=%s", (wanted,)).fetchone()[0]
        cur.execute('insert into erp.accessory_category_uom_conversions(category_id,uom_code,base_qty_per_uom,effective_from) values(%s,%s,%s,%s)', (ident, uom, factor, MASTER['start']))
    else:
        uom = MASTER['pcs']
    return ident, uom


def purchase(cur, mat, location, qty, cost, at, rolls=0):
    number = tag()
    line = dict(material_id=mat, qty=qty, unit_price=cost,
        price_state='ESTIMATED', price_source='MANUAL_ESTIMATE')
    if rolls:
        line['rolls'] = [dict(roll_number=number+'-'+str(i), qty=qty/rolls) for i in range(rolls)]
    payload = dict(purchase_number=number, supplier_id=MASTER['supplier'], location_id=location,
        physical_at=at, change_reason='Synthetic original foundation receipt', lines=[line])
    saved = call(cur, 'erp.save_material_purchase_draft_v2', encode(payload), uuid.uuid4(), None)
    posted = call(cur, 'erp.post_material_purchase_v2', saved['purchase_id'], uuid.uuid4(),
        saved['row_version'], 'Synthetic original foundation receipt post')
    assert posted['status'] == 'POSTED'
    return saved['purchase_id']


def transfer(cur, source, destination, items, at):
    payload = dict(transfer_number=tag(), from_location_id=source, to_location_id=destination,
        physical_at=at, change_reason='Synthetic original warehouse transfer',
        items=[dict(material_id=mat, qty=qty) for mat, qty in items])
    return call(cur, 'erp.save_material_transfer_draft_v2', encode(payload), uuid.uuid4(), None)


def post_transfer(cur, draft):
    return call(cur, 'erp.post_material_transfer_v2', draft['material_transfer_id'], uuid.uuid4(),
        draft['row_version'], 'Synthetic ordinary transfer posting')


def stock(cur, mat):
    admin(cur)
    qty, value = cur.execute('select coalesce(sum(qty_signed),0),coalesce(sum(qty_signed*unit_cost_snapshot),0) from erp.material_stock_movements where material_id=%s', (mat,)).fetchone()
    cache = cur.execute('select cached_stock_qty,moving_average_cost from erp.materials where id=%s', (mat,)).fetchone()
    moves = cur.execute('select movement_type,location_id,qty_signed,input_unit_cost,unit_cost_snapshot,physical_at,system_created_at from erp.material_stock_movements where material_id=%s order by physical_at,system_created_at,id', (mat,)).fetchall()
    return dict(qty=qty, value=value, cached_qty=cache[0], average=cache[1], movements=moves)


def gl(cur):
    admin(cur)
    return cur.execute('select account_id,sum(debit-credit),count(*) from erp.journal_lines group by account_id order by account_id').fetchall()


def pcs_case(cur, factor, qty):
    cat, uom = category(cur, factor if factor != 1 else None)
    mat = material(cur, 'ACCESSORY', cat)
    source, _ = locations(cur)
    purchase(cur, mat, source, 300, 2, MASTER['t0'])
    cur.execute('insert into erp.contractor_accessory_price_versions(contractor_id,category_id,selling_price,selling_uom_code,effective_from) values(%s,%s,%s,%s,%s)',
        (MASTER['contractor'], cat, Decimal(factor)*3, uom, MASTER['start']))
    before = stock(cur, mat)
    payload = dict(issue_number=tag(), contractor_id=MASTER['contractor'], location_id=source,
        physical_at=MASTER['t3'], change_reason='Exact whole PCS original issue', items=[dict(material_id=mat, qty=qty)])
    result, error = attempt(cur, lambda: call(cur, 'erp.save_contractor_material_issue_draft_v2', encode(payload), uuid.uuid4(), None))
    if error:
        assert qty == 7 and factor != 1 and 'whole base-unit' in error['message'], error
        assert stock(cur, mat) == before
        return dict(status='GAP_PROVEN', input_pcs=qty, factor=factor, refusal=error,
            atomic_guard_control=True, posted_corruption_proven=False, pricing_policy_selected=False)
    issue = result['contractor_material_issue_id']
    values = cur.execute('select qty,transaction_qty,base_qty_per_transaction_uom,total_receivable from erp.contractor_material_issue_items where issue_id=%s', (issue,)).fetchone()
    assert values[0] == qty, values
    assert stock(cur, mat) == before
    posted = call(cur, 'erp.post_contractor_material_issue_v2', issue, uuid.uuid4(), result['row_version'], 'Exact native PCS control')
    after = stock(cur, mat)
    assert posted['status'] == 'POSTED' and after['qty'] == 300-qty
    return dict(status='CONTROL_PASS', input_pcs=qty, factor=factor, stored=values,
        posted_qty=before['qty']-after['qty'], pricing_policy_selected=False)


def neutral_transfer(cur, qty, backdate):
    source, destination = locations(cur)
    mat = material(cur)
    purchase(cur, mat, source, 100, 10, MASTER['t0'])
    purchase(cur, mat, source, 100, 20, MASTER['t2'])
    before = stock(cur, mat)
    assert (before['qty'], before['value']) == (200, 3000), before
    journal = gl(cur)
    draft = transfer(cur, source, destination, [(mat, qty)], MASTER['t1'] if backdate else MASTER['t3'])
    posted = post_transfer(cur, draft)
    after = stock(cur, mat)
    assert posted['status'] == 'POSTED' and after['qty'] == 200 and gl(cur) == journal
    neutral = after['value'] == before['value']
    if not backdate:
        assert neutral, after
    return dict(status='CONTROL_PASS' if neutral else 'BUG_PROVEN', input_transfer_qty=qty,
        backdate=backdate, expected_global_qty=200, expected_global_value=3000,
        before=before, after=after, journal_unchanged=True,
        actual_value_delta=after['value']-before['value'])


def deactivate(cur, mat, cat):
    admin(cur)
    sku, name, version = cur.execute('select material_sku,material_name,row_version from erp.materials where id=%s', (mat,)).fetchone()
    return call(cur, 'erp.save_accessory_material_v2', encode(dict(id=mat,material_sku=sku,
        material_name=name,accessory_category_id=cat,is_active=False,
        change_reason='Deactivate after original receipt reversal to zero stock')), uuid.uuid4(), version)


def inactive_lines(cur, mode):
    source, destination = locations(cur)
    cat, _ = category(cur)
    first, second = material(cur, 'ACCESSORY', cat), material(cur, 'ACCESSORY', cat)
    receipt = purchase(cur, first, source, 5, 2, MASTER['t0'])
    purchase(cur, second, source, 5, 2, MASTER['t0'])
    items = [(first, 5)] if mode == 'ALL_INACTIVE' else [(first, 5), (second, 5)]
    draft = transfer(cur, source, destination, items, MASTER['t3'])
    if mode != 'ACTIVE_CONTROL':
        _, refused = attempt(cur, lambda: deactivate(cur, first, cat))
        assert refused and 'non-zero stock' in refused['message'], refused
        call(cur, 'erp.reverse_material_purchase', receipt, 'Synthetic unused receipt returned before transfer')
        assert stock(cur, first)['qty'] == 0
        assert deactivate(cur, first, cat)['status'] == 'INACTIVE'
    else:
        refused = None
    before = dict(first=stock(cur, first), second=stock(cur, second))
    posted, error = attempt(cur, lambda: post_transfer(cur, draft))
    after = dict(first=stock(cur, first), second=stock(cur, second))
    if mode == 'ACTIVE_CONTROL':
        assert not error and posted['movement_count'] == 4
        assert before['first']['qty'] == after['first']['qty'] and before['second']['qty'] == after['second']['qty']
        status = 'CONTROL_PASS'
    elif error:
        assert re.search(r'active|stock|material', error['message'], re.I), error
        assert after == before
        status = 'CONTROL_PASS'
    else:
        assert posted['status'] == 'POSTED' and posted['movement_count'] < 2*len(items)
        status = 'BUG_PROVEN'
    return dict(status=status, mode=mode, nonzero_deactivation_refusal=refused,
        lifecycle='original receipt POST -> whole receipt REVERSE -> zero-stock DEACTIVATE' if refused else 'active control',
        all_lines_required=len(items), posting=posted, refusal=error, before=before, after=after)


def location_history(cur, backdate):
    first, second = locations(cur)
    mat = material(cur)
    purchase(cur, mat, second, 100, 10, MASTER['t0'])
    post_transfer(cur, transfer(cur, second, first, [(mat, 10)], MASTER['t2']))
    assert cur.execute('select sum(qty_signed) from erp.material_stock_movements where material_id=%s and location_id=%s', (mat,first)).fetchone()[0] == 10
    draft = transfer(cur, first, second, [(mat, 5)], MASTER['t1'] if backdate else MASTER['t3'])
    posted, error = attempt(cur, lambda: post_transfer(cur, draft))
    if error:
        assert backdate and re.search(r'negative|histor|stock|available', error['message'], re.I), error
        return dict(status='CONTROL_PASS', backdate=True, current_source_qty_before=10, refusal=error, atomic=True)
    minimum = cur.execute('''select min(prefix) from(select sum(qty_signed) over(partition by location_id,roll_id order by physical_at,system_created_at,id rows unbounded preceding) prefix from erp.material_stock_movements where material_id=%s) q''', (mat,)).fetchone()[0]
    observed = stock(cur, mat)
    assert observed['qty'] == 100 and observed['value'] == 1000
    if not backdate:
        assert minimum >= 0
    return dict(status='BUG_PROVEN' if minimum < 0 else 'CONTROL_PASS', backdate=backdate,
        current_source_qty_before=10, posting=posted, minimum_location_prefix=minimum, observed=observed)


def po(cur, number, target=1):
    admin(cur)
    return cur.execute("insert into erp.production_orders(po_number,model_id,contractor_id,target_qty_pcs,status,current_stage,physical_start_at,notes) values(%s,%s,%s,%s,'CUTTING','CUTTING',%s,'Synthetic eligible selector fixture') returning id",
        (number,MASTER['model'],MASTER['contractor'],target,MASTER['t0'])).fetchone()[0]


def cut_draft(cur, order, location, roll):
    return call(cur, 'public.erp_save_cutting_group_before_sewing_v2', encode(dict(action='SAVE_DRAFT',
        po_id=order,pattern_id=MASTER['pattern'],source_location_id=location,cut_at=MASTER['t2'],
        change_reason='Ordinary eligible draft outside selector window',
        size_slots=[dict(slot_no=1,size_id=MASTER['size'],drawing_no=1)],
        rolls=[dict(roll_id=roll,qty_issued=1,qty_consumed=1,qty_reported_remaining=0,
            yields=[dict(slot_no=1,qty_pcs=1)])])), uuid.uuid4(), None)


def selector(cur, drafts):
    source, _ = locations(cur)
    mat = material(cur, 'FABRIC')
    prefix = 'ZZ-'+tag()
    if drafts:
        orders = [po(cur, prefix, 101)]
        count = 101
    else:
        orders = [po(cur, prefix+'-'+str(i).zfill(4)) for i in range(201)]
        count = 1
    receipt = purchase(cur, mat, source, count, 1, MASTER['t0'], rolls=count)
    rolls = [r[0] for r in cur.execute('select r.id from erp.material_rolls r join erp.material_purchase_items i on i.id=r.purchase_item_id where i.purchase_id=%s order by r.roll_number', (receipt,)).fetchall()]
    before = stock(cur, mat)
    saved = [cut_draft(cur, orders[-1], source, roll) for roll in rolls]
    assert stock(cur, mat) == before, 'SAVE_DRAFT moved physical inventory'
    if drafts:
        oldest = cur.execute('select id,group_number from erp.cutting_groups where po_id=%s order by updated_at,id limit 1', (orders[0],)).fetchone()
        key, ident, query = 'drafts', str(oldest[0]), oldest[1]
        field = 'cutting_group_id'
    else:
        key, ident, query = 'orders', str(orders[-1]), prefix+'-0200'
        field = 'id'
    pages = [call(cur, 'public.erp_get_cutting_workspace_v1', q, source, 200, off)
        for q, off in ((None,0),(query,0),(query,200))]
    found = [any(x[field] == ident for x in page[key]) for page in pages]
    assert len(saved) == count and all(x['material_issue_posted'] is False for x in saved)
    return dict(status='GAP_PROVEN' if not any(found) else 'CONTROL_PASS', collection=key,
        eligible_synthetic_count=101 if drafts else 201, target_id=ident,
        original_draft_save_succeeded=True, original_drafts_created=len(saved), stock_unchanged=True,
        visible_lengths=[len(p[key]) for p in pages], found_default_exact_query_and_offset=found,
        existing_rpc_parameters='p_roll_query and p_offset apply only to rolls')


def run():
    global OWNER, MASTER
    assert os.environ['CP6_AUTH_PGURL'] == PG
    OWNER = str(uuid.UUID(sys.argv[1]))
    path = Path(sys.argv[2])
    assert path.name == 'FOUNDATION_QUALIFICATION.json'
    path.parent.mkdir(parents=True,exist_ok=True)
    root = Path(__file__).resolve().parents[1]
    head = subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
    tree = subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=root,text=True).strip()
    assert head == os.environ['CP6_RUNTIME_HEAD'] and tree == os.environ['CP6_RUNTIME_TREE']
    report = dict(status='INCOMPLETE',classification='WRITER_ORIGINAL_AL_NATIVE_QUALIFICATION',
        candidate_head=head,candidate_tree=tree,runtime_generation='AL',production_go=False,
        independent_acceptance=False,http_transport_proven=False,installed_functions_modified=False,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cases={})
    def save():
        path.write_text(json.dumps(report,indent=2,default=str)+'\n')
    save()
    with psycopg.connect(ADMIN) as connection, connection.cursor() as cur:
        assert cur.execute('select current_database()').fetchone()[0] == 'cp6_auth'
        cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='120s';set local lock_timeout='8s'")
        assert len(runtime.verified_successor(cur)) == 690
        initial, catalog = snapshot(cur), function_catalog(cur)
        report['runtime_objects_verified'] = 690
        usage = cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        report['temporary_schema_usage_grant'] = not usage
        report['function_execute_grants_added'] = False
        if not usage:
            cur.execute('grant usage on schema erp to authenticated')
        owner(cur)
        assert cur.execute('select erp.current_app_role()').fetchone()[0] == 'OWNER'
        admin(cur)
        now, start = cur.execute("select clock_timestamp(),date_trunc('day',clock_timestamp())").fetchone()
        assert now-start > timedelta(seconds=10), 'Insufficient elapsed time for same-open-day fixture'
        closed = cur.execute('select closed_through from erp.accounting_period_control where singleton_id=1').fetchone()[0]
        assert closed is None or closed < now.date()
        model, contractor = cur.execute("select model_id,contractor_id from erp.production_orders where po_number='CP6-RACE-PO'").fetchone()
        MASTER = dict(model=model,contractor=contractor,start=start,
            supplier=cur.execute("select id from erp.suppliers where supplier_code='CP6-RACE-SUP'").fetchone()[0],
            pattern=cur.execute('select id from erp.production_patterns where is_active order by pattern_code limit 1').fetchone()[0],
            size=cur.execute('select s.id from erp.product_model_sizes m join erp.sizes s on s.id=m.size_id where m.model_id=%s and s.is_active order by s.sort_order limit 1',(model,)).fetchone()[0],
            pcs=cur.execute("select unit_code from erp.uom_definitions where upper(unit_code)='PCS' and dimension='COUNT'").fetchone()[0],
            **{'t'+str(i):start+(now-start)*fraction for i,fraction in enumerate((.2,.4,.6,.8))})
        selected_names = {'normalize_contractor_issue_item_uom_price','post_material_transfer_v2',
            '_recalculate_material_cost_core','guard_material_negative_stock','get_cutting_workspace_v1',
            'reverse_material_transfer_v2','save_material_transfer_draft_v2'}
        definitions = [dict(identity=identity,definition=definition,acl=acl,owner=owner_name,
            sha256=hashlib.sha256(definition.encode()).hexdigest()) for identity,definition,acl,owner_name in catalog
            if identity.split('(')[0].split('.')[-1] in selected_names]
        assert len(definitions) == len(selected_names)
        path.with_name('FOUNDATION_ORIGINAL_FUNCTIONS.json').write_text(json.dumps(definitions,indent=2)+'\n')
        specs = [('S01:PCS:'+str(f)+':'+str(q),lambda c,f=f,q=q:pcs_case(c,f,q)) for f,q in [(1,7),(12,12),(144,144),(12,7),(144,7)]]
        specs += [('S02:TRANSFER:'+str(q)+':'+str(b),lambda c,q=q,b=b:neutral_transfer(c,q,b)) for q,b in [(10,False),(10,True),(100,True)]]
        specs += [('S03:'+mode,lambda c,m=mode:inactive_lines(c,m)) for mode in ['ACTIVE_CONTROL','MIXED','ALL_INACTIVE']]
        specs += [('S04:PREFIX:'+str(b),lambda c,b=b:location_history(c,b)) for b in [False,True]]
        specs += [('S05:ORDERS',lambda c:selector(c,False)),('S05:DRAFTS',lambda c:selector(c,True))]
        report['planned_case_ids'] = [name for name,_ in specs]
        save()
        for name, test in specs:
            admin(cur)
            before = snapshot(cur)
            cur.execute('savepoint foundation_case')
            try:
                result = test(cur)
            except Exception as exc:
                result = dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
            finally:
                cur.execute('rollback to savepoint foundation_case')
                admin(cur)
                cur.execute('release savepoint foundation_case')
            result['transactional_boundary_restored'] = snapshot(cur) == before
            if not result['transactional_boundary_restored']:
                result['status'] = 'INCOMPLETE'
            report['cases'][name] = result
            save()
            print(json.dumps(dict(case=name,status=result['status'],error=result.get('error'))),flush=True)
        report['catalog_unchanged'] = function_catalog(cur) == catalog
        connection.rollback()
        cur.execute("set local timezone='Asia/Jakarta'")
        report['transactional_boundary_restored'] = snapshot(cur) == initial
        report['schema_usage_restored'] = cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0] == usage
        report['runtime_objects_restored'] = len(runtime.verified_successor(cur)) == 690
        connection.rollback()
    report['counts'] = {s:sum(row['status']==s for row in report['cases'].values()) for s in ['CONTROL_PASS','BUG_PROVEN','GAP_PROVEN','INCOMPLETE']}
    if not report['counts']['INCOMPLETE'] and all(report[k] for k in ['catalog_unchanged','transactional_boundary_restored','schema_usage_restored','runtime_objects_restored']):
        report['status'] = 'QUALIFIED_WITH_FINDINGS' if report['counts']['BUG_PROVEN']+report['counts']['GAP_PROVEN'] else 'QUALIFIED_CONTROLS_ONLY'
    save()
    return report


if __name__ == '__main__':
    result = run()
    print(json.dumps({k:v for k,v in result.items() if k not in ['cases','planned_case_ids']}))
    raise SystemExit(1 if result['status'] == 'INCOMPLETE' else 0)
