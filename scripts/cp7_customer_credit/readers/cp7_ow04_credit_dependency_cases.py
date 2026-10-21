"""Read-only credit dependencies: predeclared actual Native/security controls.

Uses the unchanged initial settlement fixture/oracles, never fabricated credit.
Every case observes real Native and private rows before and after the read or
refusal; the outer strict harness independently proves full case restoration.
"""
import copy
import json
from decimal import Decimal
import re
import uuid

import psycopg
import cp7_full_owning_install as full
import cp7_ow04_signed_source_cases as signed

native, auth, b = signed.native, signed.auth, signed.b
IDS = (
    'OW04_DEPENDENCY_REFUND_DOCUMENT',
    'OW04_DEPENDENCY_CREDIT_PROVEN_EMPTY',
    'OW04_DEPENDENCY_CURRENT_PERMISSIONS',
    'OW04_DEPENDENCY_INACTIVE_ACTOR',
    'OW04_DEPENDENCY_STALE_VERSION_AND_REVIEW',
    'OW04_DEPENDENCY_MALFORMED_QUERY',
    'OW04_DEPENDENCY_MISSING_SOURCE',
    'OW04_DEPENDENCY_NEXT_PAGE',
    'OW04_DEPENDENCY_PRIVATE_AND_ANON_DENIED',
)
RPC = 'public.erp_cp7_get_sales_credit_dependencies_v1'


def observe(cur, fixture):
    return dict(actual=signed._observe(cur,fixture),
                all_cp7_and_ow04_private_rows=full.private_rows(cur),
                functions=full.p09.functions(cur))


def query(cur, fixture):
    b.api.admin(cur)
    return cur.execute("select jsonb_build_object('sale_id',id::text,"
        "'expected_version',row_version::text,'review_token',cp7_sales.review_token(id),"
        "'offset',0,'limit',25)from erp.sales_headers where id=%s",
        (fixture['f']['sale'],)).fetchone()[0]


def read(cur, request, subject=None):
    auth.actor(cur,subject)
    actor=str(cur.execute('select auth.uid()').fetchone()[0])
    reply=cur.execute('select '+RPC+'(%s::jsonb)',(json.dumps(request),)).fetchone()[0]
    b.api.admin(cur)
    assert reply['actor_scope_id']==actor,'OW04_DEPENDENCY_WRONG_ACTOR'
    return reply


def denied(cur, operation, sqlstate, message=None):
    b.api.admin(cur)
    savepoint='ow04_dependency_refusal_'+uuid.uuid4().hex
    cur.execute('savepoint '+savepoint)
    try:
        operation()
    except psycopg.Error as error:
        result=dict(sqlstate=error.sqlstate,message=error.diag.message_primary)
        cur.execute('rollback to savepoint '+savepoint)
        b.api.admin(cur)
        cur.execute('release savepoint '+savepoint)
        assert result['sqlstate']==sqlstate,result
        if message is not None:
            assert result['message']==message,result
        return result
    cur.execute('rollback to savepoint '+savepoint)
    b.api.admin(cur)
    cur.execute('release savepoint '+savepoint)
    raise AssertionError('OW04_DEPENDENCY_REQUIRED_REFUSAL_MISSING')


def validate(cur, fixture, outcome, actual, request, reply, mode):
    assert set(reply)=={'contract_version','actor_scope_id','read_at','read_only',
        'business_DML','source','dependency_sha256','page','dependencies'},reply
    assert reply['contract_version']=='cp7.sales-credit-dependencies.v1'
    assert reply['read_only'] is True and reply['business_DML'] is False
    assert re.fullmatch('[0-9a-f]{64}',reply['dependency_sha256'])
    expected_source=cur.execute("select jsonb_build_object('sale_id',id::text,"
        "'number',sale_number,'status',status::text,'row_version',row_version::text,"
        "'review_token',cp7_sales.review_token(id))from erp.sales_headers where id=%s",
        (fixture['f']['sale'],)).fetchone()[0]
    assert reply['source']==expected_source,'OW04_DEPENDENCY_WRONG_DOCUMENT_OR_REVISION'
    assert reply['page']==dict(offset=request['offset'],limit=25,
        total='1'if mode=='REFUND'else'0',next_offset=None),reply
    if mode=='CREDIT':
        assert actual['consumptions']['document']==[]
        assert reply['dependencies']==[],'OW04_DEPENDENCY_FALSE_CONSUMER'
        expected_hash=cur.execute("select cp7_credit.pg_jsonb_sha256('[]'::jsonb)").fetchone()[0]
    else:
        event=actual['consumptions']['document'][0]
        expected_hash=cur.execute("select cp7_credit.pg_jsonb_sha256(jsonb_build_array(to_jsonb(e)))"
            "from cp7_credit.consumption_events e where id=%s",(event['id'],)).fetchone()[0]
        if request['offset']==0:
            assert len(reply['dependencies'])==1
            row=reply['dependencies'][0]
            assert set(row)=={'event_id','kind','amount','economic_date','book_date',
                'source_sale_id','source_sale_number','source_return_id',
                'source_return_number','target_sale','journal_id'}
            assert row['event_id']==str(event['id'])==outcome['refund_event_id']
            assert row['kind']=='REFUND'and row['target_sale'] is None
            assert row['source_sale_id']==str(fixture['f']['sale'])
            assert row['source_return_id']==outcome['return_id']
            assert row['journal_id']==str(event['journal_id'])
            assert row['amount']==format(Decimal(str(event['amount'])),'.2f')
            assert row['economic_date']==event['economic_date']
            assert row['book_date']==event['transaction_date']
            actual_number=cur.execute('select return_number from erp.sales_returns where id=%s',
                (outcome['return_id'],)).fetchone()[0]
            assert row['source_return_number']==actual_number
            assert row['source_sale_number']==reply['source']['number']
        else:
            assert reply['dependencies']==[],'OW04_DEPENDENCY_PAGE_DROPPED_TOTAL'
    assert reply['dependency_sha256']==expected_hash,'OW04_DEPENDENCY_WRONG_COMPLETE_FACT_HASH'


def run(cur, today, index):
    mode='CREDIT'if index==1 else'REFUND'
    with native.isolated(cur):
        fixture, _account, outcome, actual=signed._setup(cur,today,mode)
        request=query(cur,fixture)
        errors=[]
        if index in(0,1,7):
            if index==7:
                request['offset']=25
            before=observe(cur,fixture)
            reply=read(cur,request)
            assert observe(cur,fixture)==before,'OW04_DEPENDENCY_READ_WROTE_FACTS'
            validate(cur,fixture,outcome,actual,request,reply,mode)
        elif index==2:
            # Administrative authority fixture, identical retained P11 pattern.
            subject,role=auth.custom_actor(cur)
            for missing in('finance.ar.view','sales.return.view','sales.invoice.view'):
                b.api.admin(cur)
                cur.execute('delete from erp.app_role_permissions where role_id=%s',(role,))
                for permission in('sales.invoice.view','sales.return.view','finance.ar.view'):
                    if permission!=missing:
                        cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)',
                            (role,permission))
                before=observe(cur,fixture)
                errors.append(denied(cur,lambda:read(cur,request,subject),'42501',
                    'CP7_SALES_ACCESS_DENIED'if missing=='sales.invoice.view'
                    else'CP7_CREDIT_DEPENDENCY_ACCESS_DENIED'))
                assert observe(cur,fixture)==before,'OW04_DEPENDENCY_REFUSAL_WROTE_FACTS'
            cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)',
                (role,'sales.invoice.view'))
            before=observe(cur,fixture)
            reply=read(cur,request,subject)
            assert observe(cur,fixture)==before
            validate(cur,fixture,outcome,actual,request,reply,mode)
        elif index==3:
            cur.execute("insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active)"
                "select %s,%s,'OW04 dependency second owner fixture',role,role_id,true "
                "from erp.app_users where auth_user_id=%s",
                (uuid.uuid4(),uuid.uuid4(),auth.base.OPERATOR_AUTH))
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',
                (auth.base.OPERATOR_AUTH,))
            before=observe(cur,fixture)
            errors.append(denied(cur,lambda:read(cur,request),'42501','CP7_SALES_ACCESS_DENIED'))
            assert observe(cur,fixture)==before
        elif index==4:
            for key,value in(('expected_version',str(int(request['expected_version'])+1)),
                              ('review_token','0'*32)):
                changed={**request,key:value}
                before=observe(cur,fixture)
                errors.append(denied(cur,lambda:read(cur,changed),'P0001','CP7_CREDIT_DEPENDENCY_SOURCE_CHANGED'))
                assert observe(cur,fixture)==before
        elif index==5:
            variants=[{**request,'offset':x}for x in(-1,1,1000025,'0',0.5)]
            variants += [{**request,'limit':x}for x in(1,26,'25',None)]
            variants += [{**request,'unknown':True},{**request,'sale_id':'bad'},
                         {**request,'expected_version':'0'},
                         {**request,'expected_version':'9223372036854775808'}]
            for changed in variants:
                before=observe(cur,fixture)
                errors.append(denied(cur,lambda:read(cur,changed),'P0001','CP7_CREDIT_DEPENDENCY_QUERY_INVALID'))
                assert observe(cur,fixture)==before
        elif index==6:
            changed={**request,'sale_id':str(uuid.uuid4())}
            before=observe(cur,fixture)
            errors.append(denied(cur,lambda:read(cur,changed),'P0001','CP7_CREDIT_DEPENDENCY_SOURCE_NOT_FOUND'))
            assert observe(cur,fixture)==before
        elif index==8:
            def direct(role,private):
                cur.execute('set local role '+role)
                name='cp7_credit.sales_credit_dependencies_v1'if private else RPC
                cur.execute('select '+name+'(%s::jsonb)',(json.dumps(request),))
            before=observe(cur,fixture)
            for role,private in(('anon',False),('service_role',False),('authenticated',True)):
                errors.append(denied(cur,lambda role=role,private=private:direct(role,private),'42501'))
                assert observe(cur,fixture)==before
            metadata=cur.execute("select pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig "
                "from pg_proc where oid='public.erp_cp7_get_sales_credit_dependencies_v1(jsonb)'::regprocedure").fetchone()
            assert metadata==('cp7_sales_read',True,'s',['search_path=""','TimeZone=UTC'])
            for role in('anon','authenticated','service_role','cp7_capture'):
                assert not cur.execute("select has_function_privilege(%s,"
                    "'cp7_credit.sales_credit_dependencies_v1(jsonb)','EXECUTE')",(role,)).fetchone()[0]
        else:
            raise AssertionError('OW04_DEPENDENCY_UNDECLARED_CASE')
        cur.execute('set constraints all immediate')
        return dict(status='PASS',native_executed=True,production_go=False,
                    classification='ACTUAL_NATIVE_READONLY_AND_AUTHORITY_CASE',
                    expected_id=IDS[index],mode=mode,readonly_business_and_private_boundary=True,
                    source_settlement=outcome,errors=errors,
                    reply=reply if index in(0,1,2,7)else None)


def cases(cur,today):
    return [(ident,lambda index=index:run(cur,today,index))for index,ident in enumerate(IDS)]
