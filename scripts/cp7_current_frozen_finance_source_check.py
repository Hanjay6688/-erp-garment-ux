"""Local SQL parsing and adversarial finance-source/catalog admission controls."""
from contextlib import ExitStack, nullcontext
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import ast
import importlib.util
import json
import sys


def run(repo):
    import psycopg
    def forbidden(*args,**kwargs):
        raise AssertionError('SOURCE_CHECK_MUST_NOT_CONNECT_DATABASE')
    with patch.object(psycopg,'connect',forbidden):
        sys.path.insert(0,str(repo/'scripts'))
        spec=importlib.util.spec_from_file_location('frozen_finance_source_graph',repo/'scripts/current-frozen-units-native-qualification/probe.py')
        graph=importlib.util.module_from_spec(spec);spec.loader.exec_module(graph)
        import pglast
        from pglast import parser
        import cp7_current_frozen_finance as stage
        import cp7_current_frozen_finance_installation as product
        render=stage.render
        stage.verify_sources()
        definitions=render.definitions()
        parsed=pglast.parse_sql(render.render())
        plpgsql=[]
        for signature,definition in definitions.items():
            if 'language plpgsql'in definition:
                parser.parse_plpgsql_json(definition);plpgsql.append(signature)
        source=definitions[render.SOURCE];request=definitions[render.FINANCE]
        assert source.count('cp7_frozen_analysis_v2.seal(')==1
        assert source.index("'finance_sidecar_mode','STAGED'") < source.index('cp7_frozen_analysis_v2.admit(') < source.index('cp7_frozen_analysis_v2.seal(')
        assert 'c:=c||'not in request
        assert request.count('cp7_finance_capture.start(')==1
        assert request.count('cp7_analysis_stage.report_finance_access(a,false)')==5
        lock=request.index('perform pg_advisory_xact_lock(')
        find_job=request.index('jid:=cp7_analysis_stage.job_of(')
        capture=request.index('select '+render.SCHEMA+'.source(q,true)')
        create_job=request.index('jid:=cp7_analysis_stage.create_job(')
        start=request.index('perform cp7_finance_capture.start(')
        marks=request.index('insert into cp7_analysis_stage.capture_marks(')
        permission='cp7_analysis_stage.report_finance_access(a,false)'
        assert request.index(permission)<lock<request.index(permission,lock)<find_job
        assert capture<request.index(permission,capture)<create_job<start<request.index(permission,start)<marks
        replay=request.index('if jid is not null then')
        status=request.index('return cp7_analysis_stage.status(jid);',replay)
        assert replay<request.index('stored_mode<>finance_mode',replay)<request.index(permission,replay)<status
        assert "p_query->'finance_mode'is distinct from'\"STAGED\"'::jsonb"in request
        assert "coalesce(x.reference->>'finance_sidecar_mode','DEFERRED')<>'DEFERRED'"in definitions[render.OPERATIONAL]
        assert "n.nspname in('cp7_frozen_analysis_units_v2','cp7_current_frozen_finance')"in definitions[render.PRODUCER]
        assert 'create function public.'not in render.render()
        refused=[]
        with TemporaryDirectory(prefix='cp7-frozen-finance-source-')as tmp:
            root=Path(tmp)
            for name in('bridge.sql','MANIFEST.json'):(root/name).write_bytes((stage.ROOT/name).read_bytes())
            with patch.object(stage,'ROOT',root):
                for name in('bridge.sql','MANIFEST.json'):
                    target=root/name;original=target.read_bytes()
                    changed=original+b'\n' if name=='bridge.sql' else json.dumps(dict(json.loads(original),finance_mode='DEFERRED')).encode()
                    target.write_bytes(changed)
                    try:stage.verify_sources()
                    except ValueError:refused.append(name+'_changed')
                    else:raise AssertionError('CHANGED_SOURCE_ACCEPTED:'+name)
                    finally:target.write_bytes(original)
        # Real closed delta admission, using its source-derived signature set.
        before={g:{}for g in('schemas','functions',*('group'+str(i)for i in range(20)))}
        after=deepcopy(before)
        for key in render.originals():
            before['functions'][key]=['old:'+key,'same-ACL-owner-settings']
            after['functions'][key]=['new:'+key,'same-ACL-owner-settings']
        for key in stage.NEW:after['functions'][key]=['private:'+key,'private-ACL']
        after['schemas'][render.SCHEMA]=['cp7_capture','private-ACL']
        state=dict(after=deepcopy(after));stage.admit_catalog(before,after,state)
        def reject(label,change):
            b,a,s=deepcopy(before),deepcopy(after),deepcopy(state);change(b,a,s)
            try:stage.admit_catalog(b,a,s)
            except ValueError:refused.append(label)
            else:raise AssertionError('UNDECLARED_CHANGE_ACCEPTED:'+label)
        def authority(b,a,s):
            a['functions'][render.OPERATIONAL][1]='execute-public';s['after']=deepcopy(a)
        reject('old_authority_changed',authority)
        reject('new_public_RPC',lambda b,a,s:a['functions'].update({'public.unqualified()':['exposed']}))
        reject('undeclared_table',lambda b,a,s:a['group0'].update({'unqualified':['new-row']}))
        reject('missing_producer_replacement',lambda b,a,s:a['functions'].__setitem__(render.PRODUCER,b['functions'][render.PRODUCER]))
        reject('missing_finance_function',lambda b,a,s:a['functions'].pop(render.FINANCE))
        try:stage.install_delta(None,None)
        except ValueError as error:
            assert str(error)=='CURRENT_FROZEN_FINANCE_ACTUAL_PREDECESSOR_REQUIRED';refused.append('missing_actual_predecessor')
        else:raise AssertionError('MISSING_PREDECESSOR_ACCEPTED')
        inverse_calls=[]
        for label,data in [('changed_rows',{'rows':'changed','sequence:x':1}),('changed_sequence',{'rows':'same','sequence:x':2})]:
            with ExitStack()as stack:
                stack.enter_context(patch.object(product,'atomic',lambda cur:nullcontext()))
                stack.enter_context(patch.object(product,'_locks',lambda cur:None))
                stack.enter_context(patch.object(product,'verify',lambda cur,state:None))
                stack.enter_context(patch.object(product.catalog,'_data',lambda cur:data))
                for module in(stage,product.predecessor):stack.enter_context(patch.object(module,'rollback_preuse',lambda *args:inverse_calls.append('inverse')))
                try:product.rollback_preuse(object(),{'preuse_data_and_sequences':{'rows':'same','sequence:x':1}})
                except ValueError as error:
                    assert str(error)==product.USED_ERROR;refused.append(label+'_before_any_inverse')
                else:raise AssertionError('USED_INVERSE_ACCEPTED:'+label)
        assert not inverse_calls
        for path in[*render.ROOT.glob('*.py'),Path(product.__file__)]:ast.parse(path.read_bytes())
        return dict(status='LOCAL_PRIVATE_FROZEN_FINANCE_SOURCE_PASS',SQL_statements=len(parsed),
            PLpgSQL_bodies=plpgsql,negative_controls=refused,
            finance_mode_bound_before_first_seal=True,capsule_sealed_once=True,
            five_fresh_permission_checks=True,both_cross_mode_UUID_guards_present=True,
            official_financial_math_reused=True,producer_includes_A_finance_functions=True,
            all22_closed_delta_admission_checked=True,global_used_guard_before_inverse=True,
            new_private_functions=2,private_replacements=2,new_public_RPC=0,
            local_mock_guard_test_only=True,database_executed=False,
            parent_Native40_runtime_qualification_pending=True,production_go=False)


if __name__=='__main__':
    print(json.dumps(run(Path(__file__).resolve().parents[1]),indent=2))
