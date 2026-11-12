"""Run the unchanged owning Money and Automatic installer methods in a disposable DDL fixture."""
import ast
from contextlib import contextmanager
from hashlib import sha256
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import re
import sys
from types import SimpleNamespace

import psycopg
from psycopg import sql
from psycopg.pq import TransactionStatus

from loopback_postgres import cluster
from cp7_sku_cost_components import catalog_additions as money_checks, financial_delta, prepared_product
from cp7_sku_automatic_pending import catalog_additions as automatic_checks, installation_product

P = Path(__file__).resolve().parent
FROZEN = P / 'frozen/scripts'
MONEY = FROZEN / 'cp7_sku_cost_components'
AUTO = FROZEN / 'cp7_sku_automatic_pending'
AREA = 'scripts/current-sku-automatic-composite-preparation'


def load(file, name):
    spec = spec_from_file_location(name, file)
    obj = module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def methods(path, names, variables):
    parsed = ast.parse(path.read_bytes())
    selected = [n for n in parsed.body if (
        isinstance(n, ast.FunctionDef) and n.name in names or
        isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in names for t in n.targets)
    )]
    assert len(selected) == len(names), (path, names)
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), 'exec'), variables)
    return variables


def exact_catalog():
    path = FROZEN / 'cp7_ow04_restore_bundle.py'
    assert sha256(path.read_bytes()).hexdigest() == 'a1605193347cf5b3321a7bdbf8ff6c634df4f4c0a5113eb295e8c3ce44428e00'
    keys = {'NAMESPACE','QUERIES','_acl','_authority','_catalog','_catalog_rows','_data','_lock_tables','canonical','digest'}
    ns = methods(path, keys, dict(contextmanager=contextmanager, TransactionStatus=TransactionStatus,
                                  sql=sql, json=json, sha256=sha256))
    return SimpleNamespace(**{key:ns[key] for key in keys})


def owning_stage(path, label, catalog, parent, adapter, **extra):
    owner = methods(FROZEN/'cp7_customer_credit/consumer/composition.py', {'as_owner'},
                    dict(contextmanager=contextmanager, owning=SimpleNamespace(TransactionStatus=TransactionStatus)))
    atomic = methods(FROZEN/'cp7_consumer_owning_install.py', {'atomic'}, dict(contextmanager=contextmanager))
    # The actual stage-local verification, role switch, DDL, and inverse are unchanged.
    # The earlier ERP parent is supplied by the DDL fixture's exact catalogue/data.
    upstream = SimpleNamespace(atomic=atomic['atomic'], predecessor=SimpleNamespace(
                               predecessor=SimpleNamespace(_locks=lambda cur: None)))
    ns = dict(parent=lambda:parent, runtime=lambda:(None,None,None,upstream,catalog), sources=lambda:dict(fixture=label),
              as_owner=owner['as_owner'], sql=sql, **extra)
    names = {'binding','prepared','verify','install_delta','rollback_delta_preuse','USED_ERROR'}
    methods(path,names,ns)
    ns['prepared'] = adapter(ns['prepared'])
    return SimpleNamespace(**{key:ns[key] for key in names|{'sources'}})


def setup(cur, product):
    mp=json.loads((MONEY/'CATALOG_ADDITIONS.json').read_bytes())
    ap=json.loads((AUTO/'CATALOG_ADDITIONS.json').read_bytes())
    rows={k:v for k,v in (ap['replacement_before']|mp['replacement_before']).items()
          if k not in mp['groups']['functions']}
    moving=(FROZEN/'cp7_sku_moving_average/valuation.sql').read_text()
    ddl='\n'.join((moving,product['ddl'],(AUTO/'context.sql').read_text()))
    own=set(re.findall(r'^create table ([\w.]+)\(',ddl,re.M))
    deps={}
    for table,column in re.findall(r'references\s+([\w.]+)\((\w+)\)',ddl,re.I):
        if table not in own:
            assert deps.setdefault(table,column)==column,table
    sources='\n'.join([ddl,*product['definitions'].values(),*(row[0] for row in rows.values())])
    for name in re.findall(r'([\w]+\.[\w]+)%rowtype',sources,re.I):
        if name not in own:
            deps.setdefault(name,'id')
    assert all(re.fullmatch(r'(?:erp|cp7_sku_conversion|cp7_credit)\.\w+',n) for n in deps),deps
    cur.execute("create role postgres nosuperuser; create role anon; create role authenticated; "
                "create role service_role; create role cp7_fg_read; "
                "create schema erp authorization postgres; create schema cp7_sku_conversion authorization postgres; "
                "create schema cp7_credit authorization postgres; "
                "set search_path=''; set timezone='UTC'; set check_function_bodies=off",prepare=False)
    cur.execute('set role postgres')
    for key,col in deps.items():
        tail=sql.SQL(', status text') if key in {'erp.sales_headers','erp.sales_returns'} else sql.SQL('')
        cur.execute(sql.SQL('create table {} ({} uuid primary key{})').format(
                    sql.Identifier(*key.split('.')),sql.Identifier(col),tail))
    cur.execute("create function cp7_sku_conversion.immutable_v1() returns trigger language plpgsql "
                "as $$begin raise exception 'DDL_PROFILE_ONLY';end$$")
    cur.execute(moving,prepare=False)
    for sig,row in rows.items():
        assert row[1]=='postgres'
        cur.execute(row[0],prepare=False)
        cur.execute('revoke all on function '+sig+' from public,anon,authenticated,service_role,cp7_fg_read')
        for role,grantor,permission,grantable in row[18]:
            assert (grantor,permission,grantable)==('postgres','EXECUTE',False)
            if role!='postgres':
                cur.execute(sql.SQL('grant execute on function '+sig+' to {}').format(
                    sql.SQL('public') if role=='PUBLIC' else sql.Identifier(role)))
    cur.execute('grant usage on schema cp7_sku_conversion to cp7_fg_read')
    cur.execute('reset role')
    cur.connection.commit()
    return sorted(deps),len(rows)


def refuse(conn, error, action):
    try:
        with conn.transaction(force_rollback=True):
            action()
    except ValueError as exc:
        assert str(exc)==error,(error,str(exc))
        return str(exc)
    raise AssertionError('Accepted: '+error)


def main(pg_bin):
    current={n:load(P/'candidate'/AREA/(n+'.py'),n)
             for n in ('cost_source_timezone','context_timezone','module_scope','non_po_rounding')}
    old=load(P/'previous'/AREA/'cost_source_timezone.py','af6e_utc')
    raw_bytes=(P/'CP7_SKU_MANAGED_RECOVERY_NATIVE27.json').read_bytes()
    rounding=current['non_po_rounding']
    assert (len(raw_bytes),sha256(raw_bytes).hexdigest())==rounding.ORIGINAL_PIN
    raw=json.loads(raw_bytes)['committed'][rounding.ORIGINAL_CASE]['Native_to_copy_handoff']['raw_current_catalog']
    originals={s:raw['functions'][s][0] for s in prepared_product.parent_original_signatures()}
    catalog=exact_catalog()

    def money_adapter(tz):
        def bind(prepared):
            bound=current['module_scope'].bind_money_preparation(prepared,financial_delta)
            def call(before,prior):
                product,profile,tables=bound(before,prior)
                product,profile=rounding.correct(product,profile)
                product,profile=tz.adapt(product,profile)
                return product,profile,tables
            return call
        return bind

    def auto_adapter(prepared):
        bound=current['module_scope'].bind_money_preparation(prepared,financial_delta)
        return current['context_timezone'].bind(bound)

    with cluster(pg_bin) as settings:
        with psycopg.connect(**settings,autocommit=True) as bootstrap:
            bootstrap.execute('create role supabase_admin superuser login')
        with psycopg.connect(**dict(settings,user='supabase_admin'),autocommit=True) as admin:
            admin.execute('alter role postgres rename to fixture_bootstrap')
        with psycopg.connect(**dict(settings,user='supabase_admin')) as conn, conn.cursor() as cur:
            assert cur.execute('show server_version').fetchone()[0]=='17.6'
            def seed_product(before, _):
                return prepared_product.derive(before, originals)
            prepare_seed=current['module_scope'].bind_money_preparation(seed_product,financial_delta)
            deps,prior_count=setup(cur,prepare_seed(raw,None))
            before,data=catalog._catalog_rows(cur),catalog._data(cur)
            prior=dict(sources=dict(fixture='moving'),originals=originals,after=before,before=before,
                       parent_binding='fixture',definitions={},preinstall_data_and_sequences=data,preuse_data_and_sequences=data)

            def parent_verify(cursor,state):
                assert state==prior and catalog._catalog_rows(cursor)==before and catalog._data(cursor)==data
                return dict(fixture_catalogue_and_data_exact=True)

            parent=SimpleNamespace(sources=lambda:prior['sources'],verify=parent_verify)
            kwargs=dict(catalog_additions=money_checks,prepared_product=prepared_product)
            broken=owning_stage(MONEY/'composition.py','af6e',catalog,parent,money_adapter(old),**kwargs)
            error='SKU_MONEY_EXACT_CATALOG_ADDITION_CHANGED:functions:'+old.SIGNATURE
            prior_failure=refuse(conn,error,lambda:broken.install_delta(cur,prior))
            assert catalog._catalog_rows(cur)==before and catalog._data(cur)==data

            repaired=current['cost_source_timezone']
            money=owning_stage(MONEY/'composition.py','882f Money',catalog,parent,money_adapter(repaired),**kwargs)
            money_ddl,mp,_=money.prepared(before,prior)
            assert repaired.pin(money_ddl['ddl'])==dict(bytes=86374,sha256='7e26cc355f7120041a43156dde61690539e9cc3426811a992a0d03eda4a310c7')
            money_state=money.install_delta(cur,prior)
            money_checked=money.verify(cur,money_state)
            capture=money_state['after']['functions'][repaired.SIGNATURE]
            assert capture==mp['groups']['functions'][repaired.SIGNATURE] and repaired.MONEY_STATE in capture[0]
            automatic=owning_stage(AUTO/'composition.py','882f Automatic',catalog,money,auto_adapter,
                money_product=prepared_product,catalog_additions=automatic_checks,installation_product=installation_product)
            auto_ddl,ap,_=automatic.prepared(money_state['after'],money_state)
            auto_state=automatic.install_delta(cur,money_state)
            auto_checked=automatic.verify(cur,auto_state)
            auto_rows={}
            for sig,*_ in current['context_timezone'].REPAIRS:
                row=auto_state['after']['functions'][sig]
                assert row==ap['groups']['functions'][sig]
                auto_rows[sig]=dict(definition=repaired.pin(row[0]),config=row[12],acl=row[18])

            def grant_leak():
                cur.execute('grant execute on function '+next(iter(auto_rows))+' to authenticated')
                automatic.verify(cur,auto_state)

            def used(stage,state):
                cur.execute("insert into erp.products(id) values ('cf740690-d196-46cc-8529-e145b737d101')")
                stage.rollback_delta_preuse(cur,state)

            def timezone_removed():
                cur.execute('alter function '+repaired.SIGNATURE+' reset "TimeZone"')
                money.verify(cur,money_state)

            acl=refuse(conn,'AUTOMATIC_ACTUAL_ALL22_CHANGED',grant_leak)
            auto_used=refuse(conn,automatic.USED_ERROR,lambda:used(automatic,auto_state))
            auto_restore=automatic.rollback_delta_preuse(cur,auto_state)
            assert catalog._catalog_rows(cur)==money_state['after'] and catalog._data(cur)==money_state['preuse_data_and_sequences']
            tz=refuse(conn,'SKU_MONEY_ACTUAL_ALL22_CHANGED',timezone_removed)
            money_used=refuse(conn,money.USED_ERROR,lambda:used(money,money_state))
            money_restore=money.rollback_delta_preuse(cur,money_state)
            assert catalog._catalog_rows(cur)==before and catalog._data(cur)==data
            result=dict(status='SKU_MONEY_AND_AUTOMATIC_OWNING_INSTALL_VERIFY_INVERSE_PASS',postgres='17.6',
                head='882fdd376387f66e607cce62152eba9732654211',first_failure=prior_failure,
                money=money_checked,automatic=auto_checked,auto_restore=auto_restore,money_restore=money_restore,
                catalogue_groups_restored=len(before),data_and_sequences_restored=len(data),
                money_ddl=repaired.pin(money_ddl['ddl']),automatic_ddl=repaired.pin(auto_ddl['ddl']),
                repaired_capture=dict(definition=repaired.pin(capture[0]),config=capture[12],acl=capture[18]),
                repaired_automatic=auto_rows,controls=[acl,auto_used,tz,money_used],
                dependency_tables=deps,exact_existing_functions=prior_count,modeled_dependency_tables=True,
                outer_predecessor_installed=False,check_function_bodies_enabled=False,actual_ERP_cases=0,
                runtime_admission=False,production_go=False)
    (P/'SKU_882F_OWNING_INSTALL_REPLAY.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],result['catalogue_groups_restored'],len(result['controls']))


if __name__=='__main__':
    main(sys.argv[1])

