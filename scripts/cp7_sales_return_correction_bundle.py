"""Exact private Native helper derivation and return correction capabilities."""
from pathlib import Path
import hashlib,re
ROOT=Path(__file__).resolve().parents[1]
SCHEMA='cp7_sales_return_correction'
HELPERS=('reverse_fg_movement','_cp3_r4_reverse_journal_internal','reverse_journal','reverse_sales_return')
TABLES=('requests','context','links','journal_restatements','helper_sources')

def derived(definition,name):
    body=definition.split('$function$',2)[1]
    changed=re.sub(r'\bbegin\b','begin\n perform '+SCHEMA+'.require_context();',body,count=1,flags=re.I)
    assert changed!=body
    for helper in HELPERS[:-1]:changed=changed.replace('erp.'+helper+'(',SCHEMA+'.'+helper+'(')
    if name=='reverse_fg_movement':
        assert body.count('clock_timestamp()')==1
        changed=changed.replace('clock_timestamp()','m.physical_at')
    elif name=='_cp3_r4_reverse_journal_internal':
        assert body.count('RETURN v_new_id;')==1
        changed=changed.replace('RETURN v_new_id;','PERFORM '+SCHEMA+'.restate_reversal(p_journal_entry_id,v_new_id,p_reason); RETURN v_new_id;')
    elif name=='reverse_sales_return':
        anchor="((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date"
        assert anchor in body
        changed=changed.replace(anchor,"((h.physical_at AT TIME ZONE 'Asia/Jakarta'::text))::date")
    return definition.replace(body,changed).replace('FUNCTION erp.'+name+'(','FUNCTION '+SCHEMA+'.'+name+'(')

def verify(cur):
    expected={
        'access_now':(True,'v',False),'require_context':(True,'v',False),
        'immutable':(False,'v',False),'protect_link':(True,'v',False),'validate':(False,'i',False),
        'document':(True,'s',True),'review_token':(True,'s',False),'link_value':(True,'s',True),
        'restate_reversal':(True,'v',False),'workspace':(True,'v',True),
        'command':(True,'v',True),'report_lifecycle':(True,'s',False),
    }
    rows=cur.execute("select p.oid::regprocedure::text,p.proname,pg_get_userbyid(p.proowner),p.prosecdef,p.provolatile::text,p.proconfig from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname=%s",(SCHEMA,)).fetchall()
    assert {r[1]for r in rows}==set(expected)|set(HELPERS),rows
    for sig,name,owner,secdef,vol,config in rows:
        assert owner=='postgres',(sig,owner)
        if name in expected:
            security,volatility,utc=expected[name]
            assert (secdef,vol,config)==(security,volatility,['search_path=""']+(['TimeZone=UTC']if utc else[])),(sig,secdef,vol,config)
        else:
            native='erp.'+name+'(uuid,text)'
            original=cur.execute('select pg_get_functiondef(%s::regprocedure)',(native,)).fetchone()[0]
            digest=cur.execute('select native_definition_sha256 from '+SCHEMA+'.helper_sources where native_signature=%s',(native,)).fetchone()[0]
            assert hashlib.sha256(original.encode()).hexdigest()==digest,(native,'Native original changed')
            assert cur.execute('select pg_get_functiondef(%s::regprocedure)',(sig,)).fetchone()[0]==derived(original,name),(sig,'Undeclared private Native delta')
        for who in ('anon','authenticated','service_role','cp7_capture'):
            assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(who,sig)).fetchone()[0],(who,sig)
    for sig,owner in [('public.erp_cp7_get_sales_return_correction_v1(jsonb)','cp7_sales_read'),('public.erp_cp7_correct_sales_return_v1(jsonb,uuid,text)','cp7_sales_write')]:
        assert cur.execute('select pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig from pg_proc where oid=%s::regprocedure',(sig,)).fetchone()==(owner,True,'v',['search_path=""'])
        assert cur.execute('select has_function_privilege(\'authenticated\',%s,\'EXECUTE\')',(sig,)).fetchone()[0]
        for who in ('anon','service_role','cp7_capture'):assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(who,sig)).fetchone()[0]
    for table in TABLES:
        sig=SCHEMA+'.'+table
        assert cur.execute('select pg_get_userbyid(relowner),relrowsecurity from pg_class where oid=%s::regclass',(sig,)).fetchone()==('postgres',True)
        assert cur.execute("select count(*)from pg_policy where polrelid=%s::regclass and pg_get_expr(polqual,polrelid)='false'and pg_get_expr(polwithcheck,polrelid)='false'",(sig,)).fetchone()[0]==1
        for who in ('anon','authenticated','service_role','cp7_capture','cp7_sales_read','cp7_sales_write'):
            assert not cur.execute('select has_table_privilege(%s,%s,\'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER\')',(who,sig)).fetchone()[0],(who,sig)
    for who in ('anon','authenticated','service_role','cp7_capture'):
        assert not cur.execute('select has_schema_privilege(%s,%s,\'USAGE\')',(who,SCHEMA)).fetchone()[0]
    for table in ('links','journal_restatements','helper_sources'):
        assert cur.execute('select count(*)from pg_trigger where tgrelid=%s::regclass and tgfoid=%s::regprocedure and not tgisinternal',(SCHEMA+'.'+table,SCHEMA+'.immutable()')).fetchone()[0]==2
    assert cur.execute('select count(*)from pg_trigger where tgrelid=%s::regclass and tgfoid=%s::regprocedure and not tgisinternal',(SCHEMA+'.links',SCHEMA+'.protect_link()')).fetchone()[0]==1
    for sig in ('cp7_sales.command_access(text)','cp7_sales.review_token(uuid)','cp7_sales.validate_return(jsonb,boolean)','cp7_sales.header(erp.sales_headers,boolean)','cp7_fg.book_anchor(uuid,uuid,text)','public.erp_cp7_resolve_transaction_source_v1(jsonb)'):
        assert cur.execute('select has_function_privilege(\'postgres\',%s,\'EXECUTE\')',(sig,)).fetchone()[0]
    assert not cur.execute("select has_table_privilege('cp7_sales_write','erp.sales_returns','INSERT,UPDATE,DELETE')or has_function_privilege('cp7_sales_write','erp.post_sales_return(uuid)','EXECUTE')").fetchone()[0]
    assert not cur.execute('select exists(select 1 from '+SCHEMA+'.context)or exists(select 1 from cp7_sales.command_context)').fetchone()[0]
    return dict(private_return_atomic_Native_inverse_post=True,all4_Native_helpers_unchanged=True,exact_private_derivation=True,source_links_immutable=True,no_app_ERP_DML=True)
