"""Retained restore guards, complete control identities and actual prior receipt checks."""
from pathlib import Path
import ast,importlib.util,json,subprocess,sys,yaml

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'scripts'));sys.path.insert(0,str(HERE))
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def run():
    import psycopg
    original=psycopg.connect
    def no_db(*a,**kw):raise AssertionError('LOCAL_RESTORE_PREFLIGHT_MUST_NOT_CONNECT_DATABASE')
    psycopg.connect=no_db
    try:
        probe=load('public_restore_preflight_probe',HERE/'probe.py')
        binding=load('public_restore_preflight_binding',HERE/'source_binding.py');proof=binding.verify()
        evidence=load('public_restore_preflight_evidence',HERE/'evidence.py')
        assert probe.composed is probe.recovery.installation
        assert probe.scoped_composed is probe.composed.predecessor.predecessor.predecessor.predecessor.predecessor
        assert probe.target_composed is probe.recovery.target_installation
        assert probe.choice is probe.target_composed.predecessor.predecessor.predecessor.choice
        ids=evidence.control_ids((HERE/'probe.py').read_text())
        ids+=evidence.control_ids((HERE/'performance_controls.py').read_text(),'run')
        ids+=evidence.control_ids((HERE/'public_controls.py').read_text(),'run')
        assert len(ids)==len(set(ids))==42
        text=(HERE/'probe.py').read_text();rejected=[]
        for name,a,b in [
            ('old_composer','import cp7_current_frozen_public_installation as composed','import cp7_current_versioned_performance_installation as composed'),
            ('missing_public_fixture',"held_public_finance=public_finance_fixture.prepare(cur,comparison['row']['query'],report)",'held_public_finance=None'),
            ('missing_restored_public_read',"public_finance_fixture.assert_restored(cur,held_public_finance,report,'BEFORE_RESTORED_CLEAR')",'pass'),
            ('missing_next_return_public_read',"public_finance_fixture.assert_restored(cur,held_public_finance,report,'AFTER_NEXT_NATIVE_RETURN')",'pass'),
            ('business_data_restore_check_removed',"assert catalog._data(cur)==backup['data'],'SECOND_RESTORE_ROWS_OR_SEQUENCES_CHANGED'",'assert True'),
            ('full_catalog_restore_check_removed',"assert catalog._portable(catalog._catalog_rows(cur))==catalog._portable(backup['catalog']),'SECOND_RESTORE_FULL22_CHANGED'",'assert True'),
            ('used_guard_removed','assert str(error)==composed.USED_ERROR','assert True'),
            ('public_controls_removed','public_controls.run(cur,backup,refused,bind,model_metadata,catalog,composed)','pass')]:
            assert a in text,name
            try:binding.verify(probe_text=text.replace(a,b))
            except AssertionError:rejected.append(name)
            else:raise AssertionError(('RESTORE_WEAKENING_ACCEPTED',name))
        workflow=yaml.safe_load((REPO/'.github/workflows/cp7-current-frozen-public-restore.yml').read_text());shells=0
        assert workflow['on']['push']['branches']==['astra-a/d17-14-frozen-public-restore-20261026']
        for step in workflow['jobs']['p21']['steps']:
            if 'run'in step:
                p=subprocess.run(['bash','-n'],input=step['run'],text=True,capture_output=True)
                assert p.returncode==0,(step.get('name'),p.stderr);shells+=1
        for p in HERE.glob('*.py'):ast.parse(p.read_text())
        result=dict(status='PASS_LOCAL_PREPARATION_ONLY',source_binding=proof,required_steps=list(probe.STEPS),
            negative_control_ids=sorted(ids),retained_and_added_controls=42,source_negative_controls=rejected,
            composer_and_recovery_ancestry_exact=True,bash_steps=shells,
            public_finance_fixture_preserves_all_original_assertions=True,
            SOURCE_bound=(HERE/'SOURCE.json').exists(),database_executed=False,actual_restore_qualified=False,
            production_go=False,independent_acceptance=False)
        (HERE/'LOCAL_PREFLIGHT.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({k:v for k,v in result.items()if k not in('source_binding','negative_control_ids')}),flush=True)
    finally:psycopg.connect=original
if __name__=='__main__':run()
