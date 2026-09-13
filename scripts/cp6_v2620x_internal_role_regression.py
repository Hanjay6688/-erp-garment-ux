#!/usr/bin/env python3
"""Paired native W/X authorization proof; synthetic JWT context is not HTTP proof."""
import json,os,uuid
from decimal import Decimal
from pathlib import Path

import psycopg
from psycopg.conninfo import conninfo_to_dict
import cp6_v2620e_counterexample_regression as base
import cp6_v2620w_scrap_business_date_regression as scrap
import cp6_v2620w_runtime as w_runtime
import cp6_v2620x_runtime as x_runtime

CASES=('UNMAPPED_SUBJECT','MISSING_SUBJECT','INACTIVE_USER','INACTIVE_ROLE',
    'SPOOFED_APP_ROLE','EXTERNAL_ROLE','OWNER_CONTROL','ADMIN_CONTROL','STAFF_CONTROL')
NULL_CASES=set(CASES[:5])
one,boundary=base.one,scrap.boundary


def claims(cur,payload):
    cur.execute("select set_config('request.jwt.claim.sub','',true)")
    cur.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps(payload),))


def session(cur,name):
    if name not in ('supabase_admin','authenticated'):raise AssertionError('X_INVALID_TEST_SESSION')
    cur.execute('set session authorization '+name)
    cur.execute('select current_user,session_user')
    if cur.fetchone()!=(name,name):raise AssertionError('X_ACTUAL_SESSION_IDENTITY_MISMATCH')


def actor(cur,name):
    subject=str(uuid.uuid4());expected_role=None
    payload=dict(sub=subject,role='authenticated')
    if name=='MISSING_SUBJECT':payload.pop('sub');subject=None
    if name=='SPOOFED_APP_ROLE':payload.update(app_role='OWNER',role_code='OWNER')
    if name=='OWNER_CONTROL':subject=base.OPERATOR_AUTH;payload['sub']=subject;expected_role='OWNER'
    elif name in ('INACTIVE_USER','INACTIVE_ROLE','EXTERNAL_ROLE','ADMIN_CONTROL','STAFF_CONTROL'):
        code={'INACTIVE_USER':'STAFF','INACTIVE_ROLE':'X_INACTIVE','EXTERNAL_ROLE':'X_EXTERNAL',
            'ADMIN_CONTROL':'ADMIN','STAFF_CONTROL':'STAFF'}[name]
        rid=one(cur,'select id from erp.app_roles where role_code=%s',(code,))
        if rid is None:
            rid=uuid.uuid4()
            cur.execute("insert into erp.app_roles select (jsonb_populate_record(null::erp.app_roles,"
                "to_jsonb(r)||jsonb_build_object('id',%s::text,'role_code',%s::text,'role_name',%s::text,"
                "'is_protected',false,'is_active',%s::boolean))).* from erp.app_roles r where role_code='OWNER'",
                (str(rid),code,'X disposable '+code,name!='INACTIVE_ROLE'))
        if name=='INACTIVE_ROLE':cur.execute('update erp.app_roles set is_active=false where id=%s',(rid,))
        cur.execute("insert into erp.app_users select (jsonb_populate_record(null::erp.app_users,"
            "to_jsonb(u)||jsonb_build_object('id',%s::text,'auth_user_id',%s::text,'full_name','X disposable actor',"
            "'role','STAFF','role_id',%s::text,'is_active',%s::boolean))).* from erp.app_users u where id=%s",
            (str(uuid.uuid4()),subject,str(rid),name!='INACTIVE_USER',base.OPERATOR_APP))
        expected_role=None if name in ('INACTIVE_USER','INACTIVE_ROLE') else code
    claims(cur,payload)
    return subject,expected_role


def exercise(cur,cash,name,fixed):
    claims(cur,dict(sub=base.OPERATOR_AUTH,role='authenticated'))
    session(cur,'authenticated');transaction=scrap.draft(cur,cash)
    session(cur,'supabase_admin');subject,expected_role=actor(cur,name)
    before_reports=scrap.reports(cur,('2026-09-02','2026-09-03'));before=boundary(cur)
    session(cur,'authenticated')
    cur.execute("select current_user,session_user,auth.uid()::text,erp.current_app_role(),auth.jwt()->>'role'")
    observed=cur.fetchone()
    if observed!=('authenticated','authenticated',subject,expected_role,'authenticated'):
        raise AssertionError('X_ACTOR_ORACLE:'+str(observed))
    cur.execute('savepoint x_call');error=None
    try:cur.execute('select erp.post_scrap_sale(%s)',(transaction,))
    except psycopg.Error as exc:
        error=dict(sqlstate=exc.sqlstate,message=str(exc))
        cur.execute('rollback to savepoint x_call')
    cur.execute('release savepoint x_call');session(cur,'supabase_admin')
    allowed=expected_role in ('OWNER','ADMIN','STAFF')
    expected_acceptance=allowed or (not fixed and name in NULL_CASES)
    if (error is None)!=expected_acceptance:raise AssertionError('X_AUTHORIZATION_RESULT:'+str(error))
    if error and 'Internal ERP access required' not in error['message']:
        raise AssertionError('X_WRONG_AUTHORIZATION_REFUSAL:'+str(error))
    document=one(cur,'select status from erp.scrap_sales where id=%s',(transaction,));books=scrap.book(cur,transaction)
    if document!=('POSTED' if expected_acceptance else 'DRAFT') or len(books)!=int(expected_acceptance):
        raise AssertionError('X_POSTING_STATE_OR_JOURNAL_CARDINALITY')
    after_reports=scrap.reports(cur,tuple(before_reports));deltas={}
    for day in before_reports:
        actual=Decimal(str(after_reports[day]['financial_position']['cash']))-Decimal(str(before_reports[day]['financial_position']['cash']))
        expected=Decimal('.03') if expected_acceptance and day=='2026-09-03' else Decimal(0)
        if actual!=expected:raise AssertionError('X_EXACT_CASH_EFFECT')
        deltas[day]=dict(expected=str(expected),actual=str(actual))
    if error and boundary(cur)!=before:raise AssertionError('X_REFUSAL_NOT_ATOMIC')
    return dict(status='PASS' if fixed else 'KNOWN_W_AUTH_BUG_REPRODUCED' if name in NULL_CASES else 'CONTROL_PASS',
        identity=dict(current_user=observed[0],session_user=observed[1],auth_uid=observed[2],app_role=observed[3],jwt_role=observed[4]),
        authorized_by_internal_role=allowed,accepted=error is None,refusal=error,document_status=document,
        journals=books,per_date_cash=deltas,refusal_boundary_exact=bool(error),
        synthetic_jwt_context=True,http_ui_reachability_proven=False)


def run():
    params=conninfo_to_dict(os.environ.get('PGURL',''))
    if params!=dict(user='postgres',password='postgres',host='127.0.0.1',port='54322',dbname='postgres') or os.environ.get('CP6_X_DISPOSABLE_CONFIRM')!='postgres':
        raise AssertionError('X_EXACT_DISPOSABLE_ENDPOINT_REQUIRED')
    phase=os.environ.get('CP6_X_PHASE')
    if phase not in ('BEFORE_X','AFTER_X'):raise AssertionError('X_UNKNOWN_PHASE')
    fixed=phase=='AFTER_X';result=dict(head=os.environ.get('GITHUB_SHA','LOCAL_UNBOUND'),phase=phase,
        classification='NATIVE_POSTGRESQL_REAL_AUTHENTICATED_SESSION_INTERNAL_ROLE',status='FAIL',
        production_go=False,cases={},http_ui_reachability_proven=False)
    with psycopg.connect(**dict(params,user='supabase_admin'),autocommit=False) as conn,conn.cursor() as cur:
        cur.execute("set local timezone='UTC';set local statement_timeout='180s';set local lock_timeout='8s'")
        untouched=boundary(cur);w=w_runtime.verified_successor(cur);x=x_runtime.verified_successor(cur)
        if len(w)!=3 or bool(x)!=fixed or (fixed and len(x)!=1):raise AssertionError('X_RUNTIME_PHASE_MISMATCH')
        result['runtime']=dict(engine=one(cur,'select version()'),verified_w_functions=len(w),verified_x_functions=len(x),installed_function_hashes=list(x.values()))
        usage=one(cur,"select has_schema_privilege('authenticated','erp','USAGE')")
        result['schema_usage_before_alignment']=usage
        if not usage:cur.execute('grant usage on schema erp to authenticated')
        claims(cur,dict(sub=base.OPERATOR_AUTH,role='authenticated'))
        cur.execute("select set_config('app.change_reason','X disposable internal-role proof',true)")
        base.load_fixture_foundation(cur);cash=one(cur,'select id from erp.cash_accounts where is_active order by id limit 1')
        for name in CASES:
            cur.execute('savepoint x_case');before=boundary(cur)
            try:evidence=exercise(cur,cash,name,fixed)
            except Exception as exc:evidence=dict(status='FAIL',error=str(exc),sqlstate=getattr(exc,'sqlstate',None))
            finally:
                cur.execute('rollback to savepoint x_case');session(cur,'supabase_admin');cur.execute('release savepoint x_case')
            evidence['full_boundary_restored']=boundary(cur)==before
            if not evidence['full_boundary_restored']:raise AssertionError('X_CASE_ROLLBACK_RESIDUE:'+name)
            result['cases'][name]=evidence
        conn.rollback();result['entire_unseeded_runtime_restored']=boundary(cur)==untouched
        result['schema_usage_restored']=one(cur,"select has_schema_privilege('authenticated','erp','USAGE')")==usage;conn.rollback()
    expected={'PASS'} if fixed else {'KNOWN_W_AUTH_BUG_REPRODUCED','CONTROL_PASS'}
    valid=len(result['cases'])==9 and all(c['status'] in expected and c['full_boundary_restored'] for c in result['cases'].values())
    if not fixed:valid=valid and sum(c['status']=='KNOWN_W_AUTH_BUG_REPRODUCED' for c in result['cases'].values())==5
    result['status']='PASS' if valid and result['entire_unseeded_runtime_restored'] and result['schema_usage_restored'] else 'FAIL'
    return result


if __name__=='__main__':
    phase=os.environ.get('CP6_X_PHASE','UNKNOWN')
    target=Path('cp6-proof/CP6_V2620X_'+('W_COUNTEREXAMPLES' if phase=='BEFORE_X' else 'INTERNAL_ROLE_REGRESSION')+'.json')
    try:result=run()
    except Exception as exc:result=dict(status='FAIL',error=str(exc),phase=phase,production_go=False)
    target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(result,indent=2,default=str)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='cases'},default=str))
    raise SystemExit(0 if result['status']=='PASS' else 1)
