"""Ensure the explicit adaptation gate rejects weakened business assertions."""
from pathlib import Path
import importlib.util,inspect,json,sys,tempfile
sys.argv=sys.argv[:1];sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE.parent)]
import cases


def run():
    proof=cases.source_binding();negative=[]
    with tempfile.TemporaryDirectory(prefix='versioned-source-guard-')as directory:
        def refused(name,function,old,new):
            original=getattr(cases.target,function)
            source=inspect.getsource(original);assert old in source
            path=Path(directory)/(name+'.py');path.write_text(source.replace(old,new,1))
            spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            setattr(cases.target,function,getattr(module,function))
            try:
                try:cases.source_binding()
                except AssertionError:negative.append(name)
                else:raise AssertionError('WEAKENED_BUSINESS_ASSERTION_ADMITTED: '+name)
            finally:setattr(cases.target,function,original)
        refused('money_history_assertion_removed','cases','and plan.monetary_state(cur)==physical','and True')
        refused('ordinary_latency_limit_relaxed','call','ms<8000','ms<80000')
        refused('wrong_used_refusal_substituted','cases','CURRENT_VERSIONED_TARGET_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE','UNRELATED_ERROR')
    assert cases.source_binding()==proof
    return dict(status='PASS',scope='LOCAL_SOURCE_GUARD_ONLY',retained_business_cases=25,versioned_business_cases=5,
        exact_allowed_AST_changes=proof['explicit_AST_changes'],negative_controls=negative,
        Native_runtime_qualified=False,production_go=False,independent_acceptance=False)


if __name__=='__main__':print(json.dumps(run(),indent=2))
