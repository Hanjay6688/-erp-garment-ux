"""Private stable copy of the exact observed Native opening-date reader."""
from pathlib import Path
from hashlib import sha256
import json

HERE=Path(__file__).resolve().parent
NATIVE='erp.product_opening_physical_at(uuid,date)'
HPP='cp7_finance.read_opening_hpp_diagnostic_v1(uuid,date)'
PRIVATE='cp7_finance.read_opening_physical_at_consistent_v1(uuid,date)'
OLD='erp.product_opening_physical_at(i.product_id,p_opening_date)'
NEW=PRIVATE.split('(')[0]+'(i.product_id,p_opening_date)'


def derived():
    binding=json.loads((HERE/'BINDING.json').read_bytes())
    native=binding['native_opening'];hpp=binding['private_hpp']
    for row in (native,hpp):assert sha256(row['definition'].encode()).hexdigest()==row['definition_sha256']
    assert native['volatility']=='v'and native['owner']=='postgres'and native['security_definer']is True
    assert native['return_type']=='timestamp with time zone'
    body=native['definition'].split('$function$')[1]
    old=hpp['definition'].split('$function$')[1]
    assert old.count(OLD)==1
    changed=old.replace(OLD,NEW,1)
    definition=('create function '+PRIVATE.split('(')[0]+'(p_product_id uuid,p_opening_date date) returns timestamptz\n'
        "language plpgsql stable security definer set search_path='' as $opening$"+body+'$opening$;')
    return dict(native=native,hpp=hpp,body=body,hpp_body=changed,definition=definition)


def row(cur,signature):
    return cur.execute('select p.prosrc,p.provolatile,p.prosecdef,pg_get_userbyid(p.proowner),p.proconfig,pg_get_functiondef(p.oid) '
        'from pg_proc p where p.oid=%s::regprocedure',(signature,)).fetchone()


def expected_original(metadata):
    return (metadata['definition'].split('$function$')[1],metadata['volatility'],metadata['security_definer'],
        metadata['owner'],metadata['config'],metadata['definition'])


def verify(cur,state,catalog):
    prepared=derived()
    assert row(cur,NATIVE)==expected_original(prepared['native'])==state['native_before'],'OPENING_NATIVE_DEFINITION_CHANGED'
    before=expected_original(prepared['hpp']);actual=row(cur,HPP)
    assert actual==(prepared['hpp_body'],*before[1:5],before[5].replace(before[0],prepared['hpp_body'],1))
    helper=row(cur,PRIVATE)
    assert helper[:5]==(prepared['body'],'s',True,'postgres',['search_path=""'])
    assert cur.execute('select pg_get_function_result(%s::regprocedure)',(PRIVATE,)).fetchone()==('timestamp with time zone',)
    assert catalog._catalog_rows(cur)['functions'][PRIVATE][-1]==[['postgres','postgres','EXECUTE',False]]
    for role in ('anon','authenticated','service_role','cp7_capture','cp7_finance_read'):
        assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,PRIVATE)).fetchone()[0]
    return dict(private_STABLE_opening_reader=True,original_Native_body_and_metadata_unchanged=True,
        private_HPP_only_one_callee_replaced=True,opening_date_and_HPP_arithmetic_unchanged=True,
        new_public_rpcs=0,broadened_role_privileges=0)


def install(cur,catalog):
    prepared=derived();native=row(cur,NATIVE);before=row(cur,HPP)
    assert native==expected_original(prepared['native'])and before==expected_original(prepared['hpp'])
    assert cur.execute('select to_regprocedure(%s)',(PRIVATE,)).fetchone()==(None,)
    cur.execute(prepared['definition'],prepare=False)
    cur.execute('alter function '+PRIVATE+' owner to postgres')
    cur.execute('revoke all on function '+PRIVATE+' from public,anon,authenticated,service_role,cp7_capture,cp7_finance_read')
    cur.execute(before[5].replace(before[0],prepared['hpp_body'],1),prepare=False)
    state=dict(native_before=native,hpp_before=before,helper=row(cur,PRIVATE),hpp_after=row(cur,HPP))
    state['verified']=verify(cur,state,catalog);return state


def restore(cur,state):
    cur.execute(state['hpp_before'][5],prepare=False)
    cur.execute('drop function '+PRIVATE+' restrict')
    assert row(cur,NATIVE)==state['native_before']and row(cur,HPP)==state['hpp_before']
