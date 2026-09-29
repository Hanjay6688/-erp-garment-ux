"""Native Nota source qualification only; not a claim of connected note/payroll writes."""
from decimal import Decimal
import json,uuid
import cp7_fg_cases as fg
import cp7_fg_book_cases as book
import cp7_procurement_cases as procurement
auth,b,ax=fg.p02,fg.b,fg.ax

def read(cur,contractor=None,subject=None,**query):
    auth.actor(cur,subject);r=cur.execute('select public.erp_cp7_get_nota_sources_v1(%s)',(json.dumps(dict(contractor_id=contractor,**query)),)).fetchone()[0];b.api.admin(cur);return r
def repair(cur,today,qty=2):
    f=ax.repair_fixture(cur,today);r=ax.post(cur,ax.repair_payload(f,qty));return dict(f,receipt=r['receipt_id'])
def keys(value):
    if isinstance(value,dict):return set(value).union(*(keys(v) for v in value.values()))
    if isinstance(value,list):return set().union(*(keys(v) for v in value))
    return set()

def cases(cur,today):
    def fixed_repair():
        f=repair(cur,today);before=book.facts(cur);r=read(cur,f['contractor']);c=r['page']['rows'][0];line=c['lines'][0]
        assert r['page']['total']=='1' and c['source_type']=='FG_REPAIR' and c['origin_id']==f['receipt'] and c['contractor_id']==f['contractor']
        assert c['line_count']=='1' and line['source_qty']==line['remaining_qty']=='2' and Decimal(line['rate'])==2000 and Decimal(line['amount'])==4000 and Decimal(c['remaining_amount'])==4000,r
        assert c['card_key']=='FG_REPAIR:'+f['receipt']+':'+f['contractor'] and book.facts(cur)==before
        return dict(status='PASS',ordinary_unsourced_bs_repair_source=True,qty=2,rate='2000',amount='4000',no_read_side_effect_on_fg_hpp_journals=True)
    def regular_outstanding():
        f=b.fixture(cur,today,'P12 sewing entitlement')
        sent=b.bd(cur,'POST_PRICED_DELIVERY',dict(delivery=b.delivery_payload(f),expected_version=str(fg.base.group_version(cur,f['group'])),pricing=dict(deferred=True)))
        contractor=cur.execute('select contractor_id::text from erp.production_orders where id=%s',(f['po'],)).fetchone()[0]
        r=read(cur,contractor);rows=[c for c in r['page']['rows'] if c['po_id']==f['po']];assert len(rows)==1,r
        c=rows[0];assert c['source_type']=='PRODUCTION' and c['cutting_group_id']==f['group'] and c['lines']
        assert all(l['source_qty']==l['eligible_qty']==l['remaining_qty']=='10' and l['held_qty']=='0' and l['eligibility_reason']=='COMPONENT_PAYABLE_LAUNDRY_OUTSTANDING' for l in c['lines']),c
        assert cur.execute('select count(*) from erp.laundry_receipts where delivery_id=%s',(sent['delivery_id'],)).fetchone()[0]==0
        return dict(status='PASS',ordinary_sewing_before_laundry_return=True,source_qty=10,held_qty=0,no_good_or_return_denominator=True,zero_component_rate_is_explicit_fixture_not_vendor_tariff=True)
    def native_allocation_release():
        f=repair(cur,today);w=read(cur,f['contractor']);c=w['page']['rows'][0];pid=uuid.uuid4()
        cur.execute("insert into erp.payroll_settlements(id,payroll_number,contractor_id,period_start,period_end,notes) values(%s,%s,%s,%s,%s,'P12 source test administrative draft only')",(pid,'P12-'+pid.hex[:12],f['contractor'],today,today))
        version=cur.execute('select row_version from erp.payroll_settlements where id=%s',(pid,)).fetchone()[0]
        before=book.facts(cur);fg.b.chain.production.owner(cur)
        cur.execute('select erp.merge_eligible_work_into_payroll_v2(%s,%s,%s,%s)',(pid,json.dumps([dict(source_type='FG_REPAIR',source_id=c['lines'][0]['source_id'],qty=1)]),uuid.uuid4(),version));b.api.admin(cur)
        after=read(cur,f['contractor'])['page']['rows'][0];assert after['lines'][0]['remaining_qty']=='1' and Decimal(after['remaining_amount'])==2000 and after['source_token']!=c['source_token']
        fg.b.chain.production.owner(cur);cur.execute('select erp.cancel_unpaid_payroll(%s,%s)',(pid,'Release native source allocation'));b.api.admin(cur)
        released=read(cur,f['contractor'])['page']['rows'][0];assert released['lines'][0]['remaining_qty']=='2' and Decimal(released['remaining_amount'])==4000 and book.facts(cur)==before
        return dict(status='PASS',administrative_header_fixture_only=True,ordinary_native_merge_and_cancel=True,remaining=[2,1,2],source_token_changes=True,no_duplicate_fg_hpp_or_journal=True)
    def pages_access():
        f=repair(cur,today,1);ax.post(cur,ax.repair_payload(f,1))
        a=read(cur,f['contractor'],limit=1);z=read(cur,f['contractor'],limit=1,offset=1)
        assert a['page']['total']==z['page']['total']=='2' and a['page']['next_offset']==1 and z['page']['next_offset'] is None and a['page']['rows'][0]['card_key']!=z['page']['rows'][0]['card_key']
        subject,role=procurement.custom(cur,('production.fg_handoff.view',));ops=read(cur,f['contractor'],subject)
        assert not ops['financial_captured'] and not ops['can_post'] and not {'rate','amount','remaining_amount'}.intersection(keys(ops))
        assert ops['page']['rows'][0]['source_token']==read(cur,f['contractor'])['page']['rows'][0]['source_token']
        cur.execute('delete from erp.app_role_permissions where role_id=%s',(role,));auth.refused(cur,lambda:read(cur,f['contractor'],subject),'CP7_PAYROLL_ACCESS_DENIED')
        for who in ('anon','authenticated','service_role','cp7_capture'):assert not cur.execute("select has_schema_privilege(%s,'cp7_payroll','USAGE')",(who,)).fetchone()[0]
        assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p','v') and has_table_privilege('cp7_payroll_read',c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER'))").fetchone()[0]
        return dict(status='PASS',complete_card_pages=True,ops_no_monetary_fields=True,source_token_uses_row_revision_not_price_hash=True,current_revocation=True,private_read_no_business_writes=True)
    def timezones():
        f=repair(cur,today);saved=cur.execute('show timezone').fetchone()[0];cards=[];legacy=[]
        try:
            for zone in ('Asia/Jakarta','UTC','America/Los_Angeles'):
                cur.execute("select set_config('TimeZone',%s,true)",(zone,));cards.append(read(cur,f['contractor'])['page']['rows'])
                legacy.append(cur.execute("select md5(jsonb_agg(jsonb_build_array(e.source_id,e.work_component_id,e.source_qty,e.eligible_qty,e.allocated_qty,e.remaining_qty,e.held_qty,e.source_revision,e.eligible_at) order by e.source_id,e.work_component_id)::text) from cp7_payroll.source_lines() e where contractor_id=%s",(f['contractor'],)).fetchone()[0])
        finally:cur.execute("select set_config('TimeZone',%s,true)",(saved,))
        assert cards[0]==cards[1]==cards[2] and len(set(legacy))==3
        return dict(status='PASS',legacy_timestamp_hash_defect_reproduced=True,source_tokens_and_full_card_snapshots_invariant_across_session_timezones=True,zones=['Asia/Jakarta','UTC','America/Los_Angeles'])
    return [('P12_NOTA_SOURCE_'+k,fn) for k,fn in [('REPAIR_FIXED_VALUE',fixed_repair),('REGULAR_LAUNDRY_OUTSTANDING',regular_outstanding),('NATIVE_ALLOCATION_RELEASE',native_allocation_release),('PAGES_ACCESS',pages_access),('CROSS_TIMEZONE',timezones)]]

def http_cases(http,today):
    def flow():
        owner=http.login('OWNER','p12-nota-source-owner');ops=http.login('ADMIN','p12-nota-source-ops')
        with http.connect() as conn,conn.cursor() as cur:
            f=repair(cur,today);role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0];cur.execute('delete from erp.app_role_permissions where role_id=%s',(role,));cur.execute("insert into erp.app_role_permissions(role_id,permission_key) values(%s,'production.fg_handoff.view')",(role,));conn.commit()
        args=dict(p_query=dict(contractor_id=f['contractor']));a=owner.rpc('erp_cp7_get_nota_sources_v1',args);o=ops.rpc('erp_cp7_get_nota_sources_v1',args)
        assert a['status']==o['status']==200 and Decimal(a['body']['page']['rows'][0]['remaining_amount'])==4000 and not {'rate','amount','remaining_amount'}.intersection(keys(o['body'])),(a,o)
        assert http.anon_rpc('erp_cp7_get_nota_sources_v1',args)['status'] in(401,403)
        with http.connect() as conn,conn.cursor() as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(ops.auth_user_id,));conn.commit()
        assert ops.rpc('erp_cp7_get_nota_sources_v1',args)['status']==403
        return dict(status='PASS',real_auth_http_source=True,finance_and_operations_projection_separate=True,current_access=True)
    return [('P12_NOTA_SOURCE_HTTP',flow)]
