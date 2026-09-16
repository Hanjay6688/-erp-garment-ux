#!/usr/bin/env python3
"""Additional writer checks on frozen AG; no independent acceptance claim."""
from pathlib import Path
from datetime import timedelta
import hashlib, json, os, sys, traceback, uuid
sys.path.insert(0, str(Path.cwd() / 'scripts'))
import psycopg
import cp6_af_independent_review as peer
import cp6_v2620ag_runtime as runtime
from cp6_v2620n_rollback_guards import function_catalog
from cp6_v2620u_install_diagnostic import snapshot

HEAD = '119f8f133131eaf373f08cc45b7b3d6fc27a3d3e'
TREE = 'bd7dd026d40e64f08f03e122338d8a82ebfd292c'
ROOT = Path('cp6-proof/ag-residual')
actors, base, prior = peer.actors, peer.base, peer.prior

def save(value):
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / 'RESULT.json').write_text(json.dumps(value, indent=2, default=str) + '\n')

def state(cur):
    actors.admin(cur)
    return actors.boundary(cur)

def success(operation):
    assert not operation['refused'], operation
    return operation['rows'][0][0] if operation['rows'] else None

def refusal(cur, query, params, message):
    before = state(cur)
    result = peer.operation(cur, query, params)
    assert result['refused'] and message in result['error']['message'], result
    assert state(cur) == before
    return result

def posted_fixture(cur, day):
    f = peer.fixture(cur, day)
    success(peer.operation(cur, 'select erp.post_sale_v2(%s,%s,%s)',
                           (f['sale']['sale_id'], uuid.uuid4(), f['sale']['row_version'])))
    actors.admin(cur)
    f['allocation'] = base.one(cur, 'select id from erp.sale_stock_allocations where sale_item_id=%s', (f['item'],))
    return f

def create_return(cur, day, f, destination, grade, quantities=(1,)):
    # Prepare a valid DRAFT through native trigger validation with the fixture
    # administrator. Ordinary direct INSERT cannot read locations in AG; no
    # table grants are added. Posting below always uses authenticated/OWNER.
    actors.admin(cur)
    rid = uuid.uuid4()
    cur.execute("insert into erp.sales_returns(id,return_number,sale_id,customer_id,physical_at,status) values(%s,%s,%s,%s,%s,'DRAFT')",
                (rid, 'AG-RESIDUAL-' + rid.hex, f['sale']['sale_id'], f['customers'][0], day.isoformat() + 'T12:00:00+07:00'))
    for qty in quantities:
        cur.execute("insert into erp.sales_return_items(return_id,sale_stock_allocation_id,location_id,qty_pcs,refund_amount,quality_grade) values(%s,%s,%s,%s,%s,%s)",
                    (rid, f['allocation'], destination, qty, qty * 20, grade))
    return rid

def return_case(destination_mode, grade, mode='NORMAL'):
    def case(cur, day):
        f = posted_fixture(cur, day)
        dest = f['second_location'] if destination_mode == 'OTHER' else base.LOCATION
        qty = (2, 2) if mode == 'OVER_QTY' else (1,)
        rid = create_return(cur, day, f, dest, grade, qty)
        before = state(cur)
        result = peer.operation(cur, 'select erp.post_sales_return(%s)', (rid,))
        if mode == 'OVER_QTY':
            assert result['refused'] and 'exceeds quantity originally sold' in result['error']['message'], result
            assert state(cur) == before
            return dict(status='CONTROL_PASS', operation=result, atomic_refusal=True)
        if result['refused']:
            assert result['error']['sqlstate'] == 'P0001' and 'Returned product/lot/location was not allocated on the original sale' in result['error']['message'], result
            assert destination_mode == 'OTHER' and state(cur) == before
            return dict(status='BUG_PROVEN', family='RETURN_SOURCE_VS_DESTINATION', operation=result,
                        selected_destination=dest, original_warehouse=base.LOCATION, grade=grade,
                        valid_draft_accepted=True, atomic_refusal=True,
                        business_requirement='An eligible sale allocation may return to any active FG warehouse selected as destination. Source eligibility must use the allocation; receipt stock must use destination.',
                        source_contract='normalize_sales_return_item_from_allocation accepts active FG destination; SalesPages offers main and reserve warehouses',
                        synthetic_detector_control=False)
        actors.admin(cur)
        movement = cur.execute("select m.location_id,m.quality_grade,m.qty_signed from erp.fg_stock_movements m join erp.sales_return_items i on i.id=m.source_id where i.return_id=%s and m.movement_type='SALE_RETURN'", (rid,)).fetchall()
        assert movement == [(uuid.UUID(str(dest)), grade, 1)], movement
        report = peer.confidence(cur, day)
        assert report['data_confidence']['status'] == 'READY', report
        detail = dict(status='CONTROL_PASS', operation=result, movements=movement, report=report)
        if mode == 'REPEAT_POST':
            detail['repeat'] = refusal(cur, 'select erp.post_sales_return(%s)', (rid,), 'must be DRAFT')
        if mode == 'REVERSE':
            success(peer.operation(cur, "select erp.reverse_sales_return(%s,'Residual legitimate reversal')", (rid,)))
            reversed_state = state(cur)
            success(peer.operation(cur, "select erp.reverse_sales_return(%s,'Residual legitimate reversal')", (rid,)))
            assert state(cur) == reversed_state
            report = peer.confidence(cur, day)
            assert report['data_confidence']['status'] == 'READY', report
            detail['reversal_idempotent'] = True
        if mode == 'SPLIT':
            for index in range(2):
                next_id = create_return(cur, day, f, dest, grade)
                success(peer.operation(cur, 'select erp.post_sales_return(%s)', (next_id,)))
            next_id = create_return(cur, day, f, dest, grade)
            detail['over_limit'] = refusal(cur, 'select erp.post_sales_return(%s)', (next_id,), 'exceeds quantity originally sold')
        return detail
    return case

def draft_case(mode):
    def case(cur, day):
        f = peer.fixture(cur, day)
        sale = f['sale']['sale_id']
        payload = dict(f['payload'], sale_id=sale, reason='Residual legal draft edit')
        payload['items'] = [dict(f['payload']['items'][0])]
        req = uuid.uuid4()
        version = f['sale']['row_version']
        if mode == 'BEFORE_STOCK':
            payload['sale_date'] = (day - timedelta(days=4)).isoformat() + 'T10:00:00+07:00'
            e = refusal(cur, 'select erp.save_sale_draft_v2(%s::jsonb,%s,%s)', (json.dumps(payload), req, version), 'lebih awal dari tanggal barang/lot tersedia')
            return dict(status='CONTROL_PASS', atomic_refusal=e)
        if mode == 'CANCEL_REPLAY':
            query = "select erp.cancel_sale_draft_v2(%s,'Residual cancellation',%s,%s)"
            params = (sale, req, version)
            first = success(peer.operation(cur, query, params)); before = state(cur)
            second = success(peer.operation(cur, query, params))
            assert first == second and state(cur) == before
            return dict(status='CONTROL_PASS', idempotent=True)
        if mode == 'TWO_LINES':
            payload['items'] = [dict(payload['items'][0], qty_pcs=4), dict(payload['items'][0], qty_pcs=6)]
        if mode == 'FULL_STOCK_RESAVE':
            payload['items'][0]['qty_pcs'] = 10
        saved = success(peer.operation(cur, 'select erp.save_sale_draft_v2(%s::jsonb,%s,%s)', (json.dumps(payload), req, version)))
        if mode == 'DIFFERENT_PAYLOAD':
            changed = dict(payload, notes='different request')
            e = refusal(cur, 'select erp.save_sale_draft_v2(%s::jsonb,%s,%s)', (json.dumps(changed), req, version), 'different payload')
            return dict(status='CONTROL_PASS', atomic_refusal=e)
        if mode == 'FULL_STOCK_RESAVE':
            for _ in range(4):
                saved = success(peer.operation(cur, 'select erp.save_sale_draft_v2(%s::jsonb,%s,%s)', (json.dumps(payload), uuid.uuid4(), saved['row_version'])))
        before = peer.observe(cur, sale)
        request = uuid.uuid4()
        params = (sale, request, saved['row_version'])
        posted = success(peer.operation(cur, 'select erp.post_sale_v2(%s,%s,%s)', params))
        boundary = state(cur)
        retry = success(peer.operation(cur, 'select erp.post_sale_v2(%s,%s,%s)', params))
        assert retry == posted and state(cur) == boundary
        after = peer.observe(cur, sale)
        assert after['stock'] == before['stock'] and after['journal_count'] == 1 and not after['mismatches']
        report = peer.confidence(cur, day)
        assert report['data_confidence']['status'] == 'READY', report
        return dict(status='CONTROL_PASS', reserved=saved['reserved_qty_pcs'], stock_neutral=True, idempotent=True, report=report)
    return case

def rebind_case(mode):
    def case(cur, day):
        f = posted_fixture(cur, day)
        rid = create_return(cur, day, f, base.LOCATION, 'GRADE_A')
        if mode == 'CUSTOMER':
            success(peer.operation(cur, 'update erp.sales_returns set customer_id=%s where id=%s', (f['customers'][1], rid)))
            message = 'customer does not match original sale customer'
        else:
            payload = dict(f['payload'], sale_number='AG-OTHER-' + uuid.uuid4().hex, reason='Other legitimate sale')
            other = success(peer.operation(cur, 'select erp.save_sale_draft_v2(%s::jsonb,%s,null)', (json.dumps(payload), uuid.uuid4())))
            success(peer.operation(cur, 'select erp.post_sale_v2(%s,%s,%s)', (other['sale_id'], uuid.uuid4(), other['row_version'])))
            success(peer.operation(cur, 'update erp.sales_returns set sale_id=%s where id=%s', (other['sale_id'], rid)))
            message = 'Return allocation does not belong'
        result = refusal(cur, 'select erp.post_sales_return(%s)', (rid,), message)
        return dict(status='CONTROL_PASS', atomic_refusal=result)
    return case

def cases():
    found = [('RETURN_' + dest + '_' + grade, return_case(dest, grade)) for dest in ('SAME', 'OTHER') for grade in ('GRADE_A', 'GRADE_B', 'HOLD')]
    found += [('RETURN_' + mode, return_case('SAME', 'GRADE_A', mode)) for mode in ('OVER_QTY', 'REPEAT_POST', 'REVERSE', 'SPLIT')]
    found += [('DRAFT_' + mode, draft_case(mode)) for mode in ('FULL_STOCK_RESAVE', 'TWO_LINES', 'DIFFERENT_PAYLOAD', 'CANCEL_REPLAY', 'BEFORE_STOCK')]
    found += [('RETURN_REBIND_' + mode, rebind_case(mode)) for mode in ('CUSTOMER', 'SALE')]
    found += [('RETURN_ALLOCATION_' + mode, allocation_case(mode)) for mode in ('ONE_DOCUMENT', 'TWO_DOCUMENTS')]
    found += [('RETURN_DRAFT_SOURCE', draft_source_case)]
    return found

def allocation_case(mode):
    def case(cur, day):
        f = peer.fixture(cur, day)
        payload = dict(f['payload'], sale_id=f['sale']['sale_id'], reason='Two legitimate sale lines',
                       items=[dict(f['payload']['items'][0]), dict(f['payload']['items'][0])])
        saved = success(peer.operation(cur, 'select erp.save_sale_draft_v2(%s::jsonb,%s,%s)', (json.dumps(payload), uuid.uuid4(), f['sale']['row_version'])))
        success(peer.operation(cur, 'select erp.post_sale_v2(%s,%s,%s)', (saved['sale_id'], uuid.uuid4(), saved['row_version'])))
        actors.admin(cur)
        f['allocation'] = base.one(cur, 'select a.id from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=%s order by a.id limit 1', (saved['sale_id'],))
        ids = [create_return(cur, day, f, base.LOCATION, 'GRADE_A', (2, 2) if mode == 'ONE_DOCUMENT' else (2,))]
        if mode == 'TWO_DOCUMENTS': ids.append(create_return(cur, day, f, base.LOCATION, 'GRADE_A', (2,)))
        operations = []
        for rid in ids:
            operations.append(peer.operation(cur, 'select erp.post_sales_return(%s)', (rid,)))
            success(operations[-1])
        actors.admin(cur)
        sold, returned = cur.execute("select a.qty_pcs,(select coalesce(sum(i.qty_pcs),0) from erp.sales_return_items i join erp.sales_returns r on r.id=i.return_id where i.sale_stock_allocation_id=a.id and r.status='POSTED') from erp.sale_stock_allocations a where a.id=%s", (f['allocation'],)).fetchone()
        assert (sold, returned) == (3, 4), (sold, returned)
        peer.ordinary(cur)
        legacy = cur.execute("select severity,issue_count from erp.run_v253_financial_integrity_checks() where check_name='SALES_RETURN_OVER_ALLOCATION'").fetchone()
        report = peer.confidence(cur, day)
        return dict(status='BUG_PROVEN', family='RETURN_SOURCE_ALLOCATION_ELIGIBILITY', sold_from_selected_allocation=sold,
                    returned_against_selected_allocation=returned, operations=operations, existing_legacy_detector=legacy, report=report,
                    business_requirement='Cumulative active returns must not exceed the selected original sale allocation, across documents and repeated lines.', synthetic_detector_control=False)
    return case

def draft_source_case(cur, day):
    f = peer.fixture(cur, day)
    actors.admin(cur)
    f['allocation'] = base.one(cur, 'select id from erp.sale_stock_allocations where sale_item_id=%s', (f['item'],))
    rid = create_return(cur, day, f, base.LOCATION, 'GRADE_A')
    payload = dict(f['payload'], sale_id=f['sale']['sale_id'], reason='Legal draft edit after unposted return draft',
                   items=[dict(f['payload']['items'][0], product_id=f['products'][1])])
    before = state(cur)
    edit = peer.operation(cur, 'select erp.save_sale_draft_v2(%s::jsonb,%s,%s)', (json.dumps(payload), uuid.uuid4(), f['sale']['row_version']))
    assert edit['refused'] and edit['error']['sqlstate'] == '23503' and 'sales_return_items_sale_stock_allocation_id_fkey' in edit['error']['message'], edit
    assert state(cur) == before
    return dict(status='BUG_PROVEN', family='RETURN_SOURCE_ALLOCATION_ELIGIBILITY', draft_return_id=rid, legal_draft_edit=edit,
                business_requirement='A return draft must reference an active posted sale. It must not pin a temporary reservation and prevent legal edits to an unposted sale.', synthetic_detector_control=False)

def run():
    assert os.environ.get('PGURL') == peer.URL
    assert os.environ.get('CP6_AG_RESIDUAL_CONFIRM') == 'postgres'
    assert runtime.verify_audit_source() == (HEAD, TREE)
    result = dict(format='CP6_AG_ADDITIONAL_WRITER_REVIEW_V1', status='INCOMPLETE', candidate_head=HEAD, candidate_tree=TREE,
                  harness_head=os.environ['CP6_AG_HARNESS_HEAD'], run_id=os.environ.get('GITHUB_RUN_ID'), cases={},
                  source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), independent_ag='PENDING',
                  production_go=False, hosted_database_used=False, http_ui_csv_reachability_proven=False)
    result['return_draft_fixture_writer'] = 'supabase_admin; native trigger validation retained; no posted history forged'
    result['return_posting_caller'] = 'authenticated/OWNER'
    result['ordinary_return_draft_creation'] = 'BELUM TERUJI: original attempt refused on missing locations SELECT; no grant added'
    with psycopg.connect(peer.URL.replace('postgres:postgres@', 'supabase_admin:postgres@')) as conn, conn.cursor() as cur:
        cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='180s';set local lock_timeout='8s'")
        assert len(runtime.verified_successor(cur)) == 690
        unseeded = snapshot(cur); catalog = function_catalog(cur)
        usage = base.one(cur, "select has_schema_privilege('authenticated','erp','USAGE')")
        result['schema_usage_fixture_grant'] = not usage
        if not usage: cur.execute('grant usage on schema erp to authenticated')
        cur.execute("select set_config('request.jwt.claims',%s,true)", (json.dumps(dict(sub=base.OPERATOR_AUTH, role='authenticated')),))
        base.load_fixture_foundation(cur); actors.admin(cur)
        day = base.one(cur, "select (statement_timestamp() at time zone 'Asia/Jakarta')::date") - timedelta(days=3)
        prior.set_open_period(cur, day - timedelta(days=5))
        for name, case in cases():
            before = state(cur); cur.execute('savepoint residual_case')
            try: record = case(cur, day)
            except Exception as exc: record = dict(status='INCOMPLETE', error=str(exc), traceback=traceback.format_exc())
            finally:
                cur.execute('rollback to savepoint residual_case'); actors.admin(cur); cur.execute('release savepoint residual_case')
            record['case_boundary_restored'] = state(cur) == before
            if not record['case_boundary_restored']: record['status'] = 'INCOMPLETE'
            result['cases'][name] = record; save(result)
            print(json.dumps(dict(case=name, status=record['status'], error=record.get('error'))), flush=True)
        actors.admin(cur); assert function_catalog(cur) == catalog
        conn.rollback(); cur.execute("set local timezone='Asia/Jakarta'")
        result['entire_unseeded_boundary_exact'] = snapshot(cur) == unseeded and function_catalog(cur) == catalog
        result['schema_usage_restored'] = base.one(cur, "select has_schema_privilege('authenticated','erp','USAGE')") == usage
        result['native_runtime_objects'] = len(runtime.verified_successor(cur))
        result['auth_users'], result['app_users'] = cur.execute('select (select count(*) from auth.users),(select count(*) from erp.app_users)').fetchone()
        conn.rollback()
    result.update(expected_cases=len(cases()), controls=sum(c['status'] == 'CONTROL_PASS' for c in result['cases'].values()),
                  counterexamples=sum(c['status'] == 'BUG_PROVEN' for c in result['cases'].values()), incomplete=sum(c['status'] == 'INCOMPLETE' for c in result['cases'].values()))
    if result['entire_unseeded_boundary_exact'] and result['schema_usage_restored'] and result['auth_users'] == result['app_users'] == result['incomplete'] == 0:
        result['status'] = 'QUALIFIED_COUNTEREXAMPLE' if result['counterexamples'] else 'PASS_WITHIN_RECORDED_SCOPE'
    save(result); return result

if __name__ == '__main__':
    try: result = run()
    except Exception as exc:
        result = dict(status='INCOMPLETE', error=str(exc), traceback=traceback.format_exc(), production_go=False); save(result)
    print(json.dumps({k:v for k,v in result.items() if k != 'cases'}, default=str))
    raise SystemExit(0 if result['status'] == 'PASS_WITHIN_RECORDED_SCOPE' else 1 if result['status'] == 'QUALIFIED_COUNTEREXAMPLE' else 2)
