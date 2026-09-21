#!/usr/bin/env python3
"""Native versioned selectors against real ordinary legacy-save fixtures."""
from datetime import timedelta
from pathlib import Path
import hashlib,json,os,traceback,uuid
import psycopg
import cp6_v2620an_runtime as runtime
import cp6_v2620al_review as setup
import cp6_foundation_qualification as f
from cp6_v2620an_review import boundary
ROOT=Path('cp6-proof/writer-an')
FIELDS=('p_roll_query','p_location_id','p_limit','p_offset','p_order_query','p_order_limit','p_order_offset','p_draft_query','p_draft_limit','p_draft_offset','p_selected_order_id','p_selected_draft_id')


def read(cur,**changes):
    values=dict(zip(FIELDS,(None,None,100,0,None,50,0,None,25,0,None,None),strict=True));values.update(changes)
    assert set(values)==set(FIELDS)
    before=boundary(cur)
    result=f.call(cur,'public.erp_get_cutting_workspace_v2',*(values[k] for k in FIELDS))
    assert boundary(cur)==before,'Read changed application data/catalog'
    assert result['contract_version']==2
    for kind in ('order','draft'):
        page=result[kind+'_page'];rows=result['orders' if kind=='order' else 'drafts']
        assert page['limit']==values['p_'+kind+'_limit'] and page['offset']==values['p_'+kind+'_offset']
        assert len(rows)==min(page['limit'],max(0,page['total']-page['offset']))
    assert result['selected_order_id']==(str(values['p_selected_order_id']) if values['p_selected_order_id'] else None)
    assert result['selected_draft_id']==(str(values['p_selected_draft_id']) if values['p_selected_draft_id'] else None)
    return result


def prepare(cur):
    f.OWNER=setup.base.OPERATOR_AUTH
    setup.actors.actors.claims(cur,dict(sub=f.OWNER,role='authenticated'))
    setup.base.load_fixture_foundation(cur);f.admin(cur)
    now,start=cur.execute("select clock_timestamp(),date_trunc('day',clock_timestamp())").fetchone()
    assert now-start>timedelta(seconds=10)
    model,contractor=cur.execute("select model_id,contractor_id from erp.production_orders where po_number='CP6-RACE-PO'").fetchone()
    f.MASTER=dict(model=model,contractor=contractor,start=start,
        supplier=cur.execute("select id from erp.suppliers where supplier_code='CP6-RACE-SUP'").fetchone()[0],
        pattern=cur.execute('select id from erp.production_patterns where is_active order by pattern_code limit 1').fetchone()[0],
        size=cur.execute('select s.id from erp.product_model_sizes m join erp.sizes s on s.id=m.size_id where m.model_id=%s and s.is_active order by s.sort_order limit 1',(model,)).fetchone()[0],
        pcs=cur.execute("select unit_code from erp.uom_definitions where upper(unit_code)='PCS' and dimension='COUNT'").fetchone()[0],
        **{'t'+str(i):start+(now-start)*fraction for i,fraction in enumerate((.2,.4,.6,.8))})


def run():
    assert os.environ['PGURL']==setup.URL and os.environ['CP6_AI_INDEPENDENT_CONFIRM']=='postgres'
    head,tree=runtime.verify_audit_source()
    ids=['LEGACY_ORDERS_LIMIT','ORDER_EXACT_201','ORDER_ALL_PAGES','ORDER_EMPTY_PAGE','ORDER_SELECTED_OUTSIDE_FILTER',
         'ORDER_MISSING_SELECTION','LEGACY_DRAFTS_LIMIT','DRAFT_EXACT_101','DRAFT_ALL_PAGES','DRAFT_SELECTED_OUTSIDE_FILTER',
         'DRAFT_MODEL_SIZES','DRAFT_CURRENT_VERSION','DRAFT_POSTED_SELECTION',
         'ROLE_DENIED_VIEW','ROLE_VIEW_ALLOWED','ROLE_WRITE_DENIED','ROLE_UNMAPPED','ANON_EXECUTE_DENIED']
    invalid=[('ORDER_ZERO',dict(p_order_limit=0)),('ORDER_NULL',dict(p_order_limit=None)),('ORDER_TOO_LARGE',dict(p_order_limit=201)),
        ('DRAFT_ZERO',dict(p_draft_limit=0)),('DRAFT_NULL',dict(p_draft_limit=None)),('DRAFT_TOO_LARGE',dict(p_draft_limit=101)),
        ('ORDER_NEGATIVE_OFFSET',dict(p_order_offset=-1)),('DRAFT_NEGATIVE_OFFSET',dict(p_draft_offset=-1)),
        ('ORDER_LONG_QUERY',dict(p_order_query='x'*201)),('DRAFT_LONG_QUERY',dict(p_draft_query='x'*201))]
    ids += [name for name,_ in invalid]
    report=dict(status='INCOMPLETE',head=head,tree=tree,planned_case_ids=ids,cases={},production_go=False,independent_acceptance=False)
    ROOT.mkdir(parents=True,exist_ok=True)
    def save():(ROOT/'SELECTORS_NATIVE.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
    def passed(name,**detail):
        assert name in ids and name not in report['cases'];report['cases'][name]=dict(status='CONTROL_PASS',**detail);save()
    save()
    with psycopg.connect(setup.ADMIN) as conn,conn.cursor() as cur:
        cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='240s';set local lock_timeout='8s'")
        assert len(runtime.verified_successor(cur))==692
        initial=boundary(cur)
        usage=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        if not usage:cur.execute('grant usage on schema erp to authenticated')
        try:
            prepare(cur)
            original=f.selector(cur,False);assert original['status']=='GAP_PROVEN';passed('LEGACY_ORDERS_LIMIT',original=original)
            target=original['target_id'];number,model=cur.execute('select po_number,model_id from erp.production_orders where id=%s',(target,)).fetchone()
            row=read(cur,p_order_query=number);assert [r['id'] for r in row['orders']]==[target];passed('ORDER_EXACT_201')
            prefix=number.rsplit('-',1)[0];all_ids=[]
            for offset in range(0,201,50):
                row=read(cur,p_order_query=prefix,p_order_offset=offset);assert row['order_page']['total']==201
                all_ids.extend(r['id'] for r in row['orders'])
            assert len(all_ids)==len(set(all_ids))==201 and all_ids[-1]==target;passed('ORDER_ALL_PAGES',pages=5,unique_orders=201)
            assert read(cur,p_order_query=prefix,p_order_offset=250)['orders']==[];passed('ORDER_EMPTY_PAGE')
            row=read(cur,p_order_query='not-present-'+uuid.uuid4().hex,p_selected_order_id=target)
            assert row['orders']==[] and row['selected_order']['id']==target;passed('ORDER_SELECTED_OUTSIDE_FILTER')
            assert read(cur,p_selected_order_id=uuid.uuid4())['selected_order'] is None;passed('ORDER_MISSING_SELECTION')
            original=f.selector(cur,True);assert original['status']=='GAP_PROVEN';passed('LEGACY_DRAFTS_LIMIT',original=original)
            group=original['target_id'];number,po=cur.execute('select group_number,po_id from erp.cutting_groups where id=%s',(group,)).fetchone()
            row=read(cur,p_draft_query=number);assert [r['cutting_group_id'] for r in row['drafts']]==[group];passed('DRAFT_EXACT_101')
            po_number=cur.execute('select po_number from erp.production_orders where id=%s',(po,)).fetchone()[0]
            all_ids=[]
            for offset in range(0,101,25):
                row=read(cur,p_draft_query=po_number,p_draft_offset=offset);assert row['draft_page']['total']==101
                all_ids.extend(r['cutting_group_id'] for r in row['drafts'])
            assert len(all_ids)==len(set(all_ids))==101 and all_ids[-1]==group;passed('DRAFT_ALL_PAGES',pages=5,unique_drafts=101)
            row=read(cur,p_draft_query='not-present-'+uuid.uuid4().hex,p_order_query='not-present',p_selected_draft_id=group,p_selected_order_id=po)
            draft=row['selected_draft'];assert row['drafts']==[] and draft['cutting_group_id']==group;passed('DRAFT_SELECTED_OUTSIDE_FILTER')
            assert draft['model_id']==row['selected_order']['model_id']==str(model)
            assert any(str(model) in size['model_ids'] for size in row['sizes']);passed('DRAFT_MODEL_SIZES')
            payload=dict(action='SAVE_DRAFT',id=group,po_id=draft['po_id'],pattern_id=draft['pattern_id'],
                source_location_id=draft['source_location_id'],cut_at=draft['cut_at'],notes='AN ordinary version change',
                change_reason='AN read observes current version',size_slots=draft['size_slots'],
                rolls=[dict(roll_id=r['roll_id'],qty_issued=r['qty_issued'],qty_consumed=r['qty_consumed'],
                    qty_reported_remaining=r['qty_reported_remaining'],yields=r['yields']) for r in draft['rolls']])
            changed=f.call(cur,'public.erp_save_cutting_group_before_sewing_v2',f.encode(payload),uuid.uuid4(),draft['row_version'])
            current=read(cur,p_selected_draft_id=group)['selected_draft'];assert current['row_version']==changed['row_version']>draft['row_version'];passed('DRAFT_CURRENT_VERSION')
            posted=f.call(cur,'public.erp_save_cutting_group_before_sewing_v2',f.encode(dict(payload,action='POST')),uuid.uuid4(),changed['row_version'])
            assert posted['material_issue_posted'] and read(cur,p_selected_draft_id=group)['selected_draft'] is None;passed('DRAFT_POSTED_SELECTION')
            for name,changes in invalid:
                _,error=f.attempt(cur,lambda changes=changes:read(cur,**changes))
                assert error and ('AN_INVALID_SELECTOR_PAGE' in error['message'] or 'AN_SELECTOR_QUERY_TOO_LONG' in error['message']),error
                passed(name,refusal=error)
            original_owner=f.OWNER
            role_code='AN_VIEW_'+uuid.uuid4().hex[:12].upper();user=str(uuid.uuid4())
            role=cur.execute('insert into erp.app_roles(role_code,role_name) values(%s,%s) returning id',(role_code,'AN selector read permission')).fetchone()[0]
            cur.execute('insert into erp.app_users(auth_user_id,full_name,role,role_id,is_active) values(%s,%s,%s,%s,true)',(user,'AN ordinary selector viewer',role_code,role))
            f.OWNER=user
            _,error=f.attempt(cur,lambda:read(cur));assert error and error['sqlstate']=='42501';passed('ROLE_DENIED_VIEW',refusal=error)
            cur.execute("insert into erp.app_role_permissions(role_id,permission_key) values(%s,'production.cutting.view')",(role,))
            assert read(cur)['contract_version']==2;passed('ROLE_VIEW_ALLOWED')
            _,error=f.attempt(cur,lambda:f.call(cur,'public.erp_save_cutting_group_before_sewing_v2',f.encode(payload),uuid.uuid4(),changed['row_version']))
            assert error and error['sqlstate']=='42501';passed('ROLE_WRITE_DENIED',refusal=error)
            f.OWNER=str(uuid.uuid4());_,error=f.attempt(cur,lambda:read(cur));assert error and error['sqlstate']=='42501';passed('ROLE_UNMAPPED',refusal=error)
            f.OWNER=original_owner
            def anonymous():
                cur.execute('set local session authorization anon')
                return cur.execute('select public.erp_get_cutting_workspace_v2()').fetchone()
            _,error=f.attempt(cur,anonymous);assert error and error['sqlstate']=='42501';passed('ANON_EXECUTE_DENIED',refusal=error)
        except Exception as exc:report['failure']=dict(error=str(exc),traceback=traceback.format_exc())
        finally:
            conn.rollback();cur.execute("set local timezone='Asia/Jakarta'")
            report['boundary_restored']=boundary(cur)==initial
            report['schema_usage_restored']=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]==usage
            report['runtime_verified']=len(runtime.verified_successor(cur))==692
            conn.rollback()
    for name in ids:
        if name not in report['cases']:report['cases'][name]=dict(status='INCOMPLETE')
    report['counts']={s:sum(r['status']==s for r in report['cases'].values()) for s in ('CONTROL_PASS','INCOMPLETE')}
    if report['counts']['CONTROL_PASS']==len(ids) and all(report[k] for k in ('boundary_restored','schema_usage_restored','runtime_verified')):report['status']='WRITER_PASS'
    save();return report

if __name__=='__main__':
    result=run();print(json.dumps({k:v for k,v in result.items() if k not in ('cases','planned_case_ids')},default=str))
    raise SystemExit(0 if result['status']=='WRITER_PASS' else 1)
