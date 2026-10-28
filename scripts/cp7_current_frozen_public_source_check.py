"""Local parser and refusal controls only; no PostgreSQL or Auth credit."""
from contextlib import ExitStack,nullcontext
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch
import ast
import importlib.util
import json
import sys

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]


def run():
    sys.argv=sys.argv[:1];sys.path.insert(0,str(ROOT/'scripts'))
    import psycopg
    from pglast import parse_sql
    def forbidden(*args,**kwargs):raise AssertionError('LOCAL_SOURCE_CHECK_MUST_NOT_CONNECT_DATABASE')
    with patch.object(psycopg,'connect',forbidden):
        spec=importlib.util.spec_from_file_location('public_guard_qualified_probe_graph',
            ROOT/'scripts/current-frozen-finance-native-qualification/probe.py')
        graph=importlib.util.module_from_spec(spec);spec.loader.exec_module(graph)
        import cp7_current_frozen_public as stage
        import cp7_current_frozen_public_installation as product
        render=stage.render;directory=stage.ROOT
        sources=stage.verify_sources()
        parsed=len(parse_sql((directory/'bridge.sql').read_text()))
        assert parsed==8
        for path in [*directory.glob('*.py'),Path(__file__),ROOT/'scripts/cp7_current_frozen_public_installation.py']:
            ast.parse(path.read_bytes())
        refused=[]
        def rejects(label,operation):
            try:operation()
            except ValueError:refused.append(label)
            else:raise AssertionError('NEGATIVE_CONTROL_ACCEPTED:'+label)
        def changed_file(name,change):
            p=directory/name;raw=p.read_bytes()
            try:p.write_bytes(change(raw));stage.verify_sources()
            finally:p.write_bytes(raw)
        rejects('changed_B_delegate',lambda:changed_file('B_facade.sql',lambda raw:raw.replace(b'units_v2.request',b'units_v2.unqualified')))
        rejects('changed_upstream_head',lambda:changed_file('UPSTREAM.json',lambda raw:raw.replace(render.B_HEAD.encode(),b'0'*40)))
        rejects('changed_generated_bridge',lambda:changed_file('bridge.sql',lambda raw:raw.replace(b'request_finance(',b'unqualified_finance(')))
        rejects('changed_manifest_authority',lambda:changed_file('MANIFEST.json',lambda raw:raw.replace(b'cp7_capture',b'authenticated')))
        before={**{f'group{i}':{}for i in range(21)},'functions':{'public.retained()':['retained','owner','closed']}}
        after=deepcopy(before);rows={}
        grants=[['cp7_capture','cp7_capture','EXECUTE',False],['authenticated','cp7_capture','EXECUTE',False]]
        for signature,definition in render.definitions().items():
            rows[signature]=[definition,stage._body(definition),'cp7_capture',True,'v',['search_path=""','TimeZone=UTC']]
            after['functions'][signature]=[definition,'cp7_capture',deepcopy(grants)]
        stage.admit_catalog(before,after)
        def catalog_mutation(change):
            b,a=deepcopy(before),deepcopy(after);change(b,a);stage.admit_catalog(b,a)
        rejects('missing_catalog_group',lambda:catalog_mutation(lambda b,a:a.pop('group0')))
        rejects('changed_old_function',lambda:catalog_mutation(lambda b,a:a['functions'].__setitem__('public.retained()',['changed','owner','closed'])))
        rejects('changed_old_grant',lambda:catalog_mutation(lambda b,a:a['group0'].__setitem__('old_acl',['open'])))
        rejects('new_table',lambda:catalog_mutation(lambda b,a:a['group1'].__setitem__('new_table',['unqualified'])))
        rejects('undeclared_public_function',lambda:catalog_mutation(lambda b,a:a['functions'].__setitem__('public.unqualified()',['new'])))
        rejects('missing_financial_facade',lambda:catalog_mutation(lambda b,a:a['functions'].pop(render.FINANCE)))
        class Cursor:
            def __init__(self,override=None):self.override=override or {};self.answer=None
            def execute(self,query,args=()):
                if query=='select has_function_privilege(%s,%s,\'EXECUTE\')':
                    self.answer=(self.override.get(tuple(args),args[0]=='authenticated'),)
                elif query=="select has_schema_privilege('cp7_capture','public','CREATE')":
                    self.answer=(self.override.get('public_create',False),)
                else:raise AssertionError('UNEXPECTED_LOCAL_CURSOR_QUERY:'+query)
                return self
            def fetchone(self):return self.answer
        state=dict(sources=sources,before=before,after=after,rows=rows)
        def verify(candidate,cursor=None):
            with ExitStack()as stack:
                stack.enter_context(patch.object(stage.catalog,'_authority',lambda cur:None))
                stack.enter_context(patch.object(stage.catalog,'_catalog_rows',lambda cur:candidate['after']))
                stack.enter_context(patch.object(stage,'_row',lambda cur,key:candidate['rows'][key]))
                return stage.verify(cursor or Cursor(),candidate)
        verify(state)
        for label,change in (
            ('new_function_owner',lambda s:s['rows'][render.FINANCE].__setitem__(2,'anon')),
            ('new_function_definer',lambda s:s['rows'][render.FINANCE].__setitem__(3,False)),
            ('new_function_search_path',lambda s:s['rows'][render.FINANCE].__setitem__(5,['search_path=public','TimeZone=UTC'])),
            ('new_function_grantor',lambda s:s['after']['functions'][render.FINANCE][-1][1].__setitem__(1,'postgres')),
            ('new_function_public_grant',lambda s:s['after']['functions'][render.FINANCE][-1].append(['PUBLIC','cp7_capture','EXECUTE',False])),
            ('new_function_grant_option',lambda s:s['after']['functions'][render.FINANCE][-1][1].__setitem__(3,True)),
        ):
            candidate=deepcopy(state);change(candidate);rejects(label,lambda:verify(candidate))
        rejects('effective_anon_execute',lambda:verify(state,Cursor({('anon',render.FINANCE):True})))
        rejects('effective_service_execute',lambda:verify(state,Cursor({('service_role',render.FINANCE):True})))
        rejects('authenticated_execute_missing',lambda:verify(state,Cursor({('authenticated',render.FINANCE):False})))
        rejects('owner_public_create',lambda:verify(state,Cursor({'public_create':True})))
        rejects('missing_actual_predecessor',lambda:stage.install_delta(None,None))
        inverse_calls=[];baseline={'rows':'same','sequence:x':1}
        for module in(product,stage):
            for label,actual in [('changed_rows',{'rows':'changed','sequence:x':1}),('changed_sequence',{'rows':'same','sequence:x':2})]:
                with ExitStack()as stack:
                    stack.enter_context(patch.object(module,'atomic',lambda cur:nullcontext()))
                    stack.enter_context(patch.object(module,'_locks',lambda cur:None))
                    stack.enter_context(patch.object(module,'verify',lambda cur,state:None))
                    stack.enter_context(patch.object(module.catalog,'_data',lambda cur:actual))
                    for downstream in((stage,product.predecessor)if module is product else ()):
                        stack.enter_context(patch.object(downstream,'rollback_preuse',lambda *args:inverse_calls.append('inverse')))
                    try:module.rollback_preuse(None,dict(preuse_data_and_sequences=baseline))
                    except ValueError as error:assert str(error)==module.USED_ERROR
                    else:raise AssertionError('GLOBAL_USED_GUARD_ACCEPTED:'+label)
                    refused.append(module.CONTRACT+':'+label)
        assert inverse_calls==[]
        assert stage.verify_sources()==sources
        return dict(status='LOCAL_SOURCE_AND_REFUSAL_CONTROLS_PASS',sql_statements=parsed,
            negative_controls=refused,negative_control_count=len(refused),new_public_rpcs=2,
            B_delegate_byte_exact=True,all22_change_allowlist_closed=True,
            full_rows_and_sequences_guard_before_inverse=True,financial_math_added=False,
            local_mock_catalog_only=True,database_executed=False,actual_Auth_HTTP_credit=False,
            default_adopted=False,production_go=False)


if __name__=='__main__':print(json.dumps(run()),flush=True)
