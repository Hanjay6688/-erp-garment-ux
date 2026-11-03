"""Load both real derived modules with explicit modeled admission/parent inputs.

No accepted Root file is constructed. The actual declared gates stay None
outside this isolated test scope, and the retained network/DB fence is active.
"""
from pathlib import Path
from contextlib import chdir
from unittest.mock import patch
from types import ModuleType
import argparse
import importlib.util
import json
import sys

HERE=Path(__file__).resolve().parent


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def check(child,parent_file):
    child=Path(child).resolve();parent_file=Path(parent_file).resolve()
    scripts=child/'scripts';sys.path.insert(0,str(scripts))
    cli=load('money_bridge_original_cli_context',scripts/'current-sku-cost-money-qualification/check.py')
    fence=load('money_bridge_original_source_fence',scripts/'current-sku-managed-recovery-native27-qualification/source_context.py')
    a=load('money_bridge_real_module_context',HERE/'assembly.py')
    declared_before={n:getattr(a.admission,n)for n in a.admission.GATES}
    assert all(v is None for v in declared_before.values())
    original_cwd=Path.cwd()
    with chdir(child),cli.retained_arguments(),fence.fenced_source_read()as guard:
        from cp7_sku_cost_components import composition as original
        original_sources=original.sources();old_moving=original.parent()
        money_before=dict(original.__dict__);moving_before=dict(old_moving.__dict__)
        parent_sources=dict(classification='EXPLICIT_PARENT_INTERFACE_MODEL_NOT_ERP',
            Afui={'complete_nested_source':'modeled'},Mandor={'complete_nested_source':'modeled'})
        class ParentModel:
            def sources(self):return parent_sources
        parent=ParentModel();receipt=dict(classification='EXPLICIT_ADMISSION_INTERFACE_MODEL_NOT_ROOT',actual_composite_cases=0)
        identity=dict(SKU_HEAD=a.git(child,'rev-parse','HEAD').decode().strip(),
            SKU_TREE=a.git(child,'rev-parse','HEAD^{tree}').decode().strip(),
            SKU_SOURCE_PIN=a.admission.pin(a.admission.canonical(original_sources)),
            PARENT_MODULE_PIN=a.admission.pin(parent_file.read_bytes()),
            PARENT_SOURCE_PIN=a.admission.pin(a.admission.canonical(parent_sources)))
        gates={n:identity.get(n,'EXPLICIT_SOURCE_TEST_ONLY')for n in a.admission.GATES}
        real_getfile=a.inspect.getfile
        def getfile(cls):return str(parent_file)if cls is ParentModel else real_getfile(cls)
        own=dict(classification='EXPLICIT_CLOSED_MANIFEST_INTERFACE_MODEL')
        with patch.multiple(a.admission,**gates),patch.object(a.admission,'admitted',return_value=receipt),\
             patch.object(a,'source_manifest',return_value=own),patch.object(a,'FROZEN_SKU',child),\
             patch.object(a,'EXPECTED_PARENT_MODULE',parent_file),patch.object(a.inspect,'getfile',side_effect=getfile):
            selected=a.load_prepared(parent,original,b'modeled parent interface',b'modeled child interface')
            moving=selected.parent();observed=selected.sources()
            assert selected is not original and moving is not old_moving
            assert moving.parent()is parent
            assert selected.CONTRACT=='cp7.sku-cost-money-on-current-mandor.v1'
            assert moving.CONTRACT=='cp7.sku-moving-average-on-current-mandor.v1'
            assert observed['predecessor']['predecessor']==parent_sources
            assert observed['files']==original_sources['files']
            assert observed['current_parent_bridge']['parent_state_projection']is False
            assert observed['predecessor']['current_parent_bridge']['parent_state_projection']is False
            assert selected.__package__==original.__package__ and moving.__package__==old_moving.__package__
            assert selected.__name__ not in sys.modules and moving.__name__ not in sys.modules
            contracts=[observed['contract'],observed['predecessor']['contract']]
            component=load('money_bridge_real_nineteen_component',HERE/'component.py')
            quiet=lambda *args:None  # Never called: this is an import-context model.
            runner,component_proof=component.load_prepared(a,selected,b'modeled parent interface',b'modeled child interface',quiet)
            scope=runner.exercise.__globals__
            assert scope['product']is selected and scope['_FROZEN_SKU']==child
            assert scope['ROOT']==HERE.parents[1] and runner.scheduler_quiet is quiet
            business=scope['load']('money_bridge_exact_nineteen_callback_context',scripts/'current-sku-cost-money-qualification/native_cases.py')
            preflight=scope['load']('money_bridge_exact_nineteen_preflight_context',scripts/'current-sku-cost-money-qualification/native_preflight.py')
            assert list(business.IDS)==a.prepared_sources()[0]['native_case_ids']
            assert callable(preflight.check) and callable(business.cases)
            package=load('money_bridge_real_owning_package',HERE/'package.py')
            code,package_proof=package.derive((child/package.ORIGINAL).read_bytes())
            engine=ModuleType('money_bridge_owning_package_import_control')
            engine.__file__=str(child/package.ORIGINAL)
            exec(compile(code,engine.__file__+'::import_only','exec'),engine.__dict__)
            engine.product=selected;engine.runner=runner
            assert callable(engine.run) and engine.run.__globals__['product']is selected
            assert engine.run.__globals__['runner']is runner
        assert set(money_before)==set(original.__dict__)and all(original.__dict__[k]is v for k,v in money_before.items())
        assert set(moving_before)==set(old_moving.__dict__)and all(old_moving.__dict__[k]is v for k,v in moving_before.items())
    assert {n:getattr(a.admission,n)for n in a.admission.GATES}==declared_before
    assert Path.cwd()==original_cwd
    assert not guard['attempts']and not guard['network_nonGit_attempts']
    return dict(status='REAL_DERIVED_MODULE_CONTEXT_WITH_MODELED_PARENT_PASS_NOT_ERP',
        actual_immutable_child_tree=identity['SKU_TREE'],loaded_contracts=contracts,
        real_money_source_files=len(original_sources['files']),original_module_objects_unchanged=True,
        loaded_native_case_ids=list(business.IDS),component=component_proof,whole_package=package_proof,
        declared_admission_gates_restored=True,working_directory_restored=True,network_database_guard=guard,
        modeled_interfaces=['accepted Root admission','closed preparation manifest','current Mandor parent source provider'],
        actual_parent_adopted=False,actual_ERP_cases=0,actual_Auth_HTTP_cases=0,production_go=False,
        independent_acceptance=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--child',required=True)
    parser.add_argument('--parent-file',required=True);parser.add_argument('--report',required=True);args=parser.parse_args()
    result=check(args.child,args.parent_file)
    with Path(args.report).open('x')as out:json.dump(result,out,indent=2);out.write('\n')
    print(json.dumps({k:result[k]for k in('status','real_money_source_files','actual_ERP_cases')}))
