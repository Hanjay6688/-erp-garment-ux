"""Exercise the output boundary and all retained business-source guards without DB."""
from pathlib import Path
from tempfile import TemporaryDirectory
import ast
import importlib.util
import json
import subprocess
import sys

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def run():
    sys.argv=sys.argv[:1];sys.path[:0]=[str(HERE),str(REPO/'scripts')]
    import source_worktree as check
    refused=[]
    with TemporaryDirectory(prefix='factory-output-boundary2-')as td:
        root=Path(td);proof=root/'cp6-proof/t3';proof.mkdir(parents=True)
        for name in('ALIGNED_CHAIN.json','CLONE_install.source-erp.sql','CLONE_install.txt'):
            (proof/name).write_text('{}'if name.endswith('.json')else'evidence')
        allowed=['cp6-proof/t3/'+p.name for p in proof.iterdir()]
        assert len(check.validate(root,'',allowed)['allowed_generated_evidence_paths'])==3
        def reject(name,tracked,paths):
            try:check.validate(root,tracked,paths)
            except ValueError:refused.append(name)
            else:raise AssertionError('OUTPUT_BOUNDARY_ACCEPTED:'+name)
        reject('tracked_source_changed',' M scripts/qualified.py',allowed)
        (root/'untracked.py').write_text('unqualified')
        reject('untracked_code_outside_evidence','',allowed+['untracked.py'])
        (proof/'untracked.py').write_text('unqualified')
        reject('code_disguised_as_evidence','',allowed+['cp6-proof/t3/untracked.py'])
        (proof/'linked.json').symlink_to(root/'untracked.py')
        reject('symlink_evidence','',allowed+['cp6-proof/t3/linked.json'])
        reject('parent_traversal','',allowed+['cp6-proof/t3/../../../untracked.py'])
        reject('absolute_path','',allowed+[str(proof/'ALIGNED_CHAIN.json')])
        reject('undeclared_file_location','',allowed+['cp6-proof/elsewhere.json'])
        reject('missing_evidence_file','',allowed+['cp6-proof/t3/missing.json'])
        for path in(proof/'untracked.py',proof/'linked.json',root/'untracked.py'):path.unlink()
        (root/'qualified.py').write_text('qualified')
        subprocess.run(['git','init','-q',str(root)],check=True)
        subprocess.run(['git','-C',str(root),'add','qualified.py'],check=True)
        subprocess.run(['git','-C',str(root),'-c','user.name=Qualification','-c','user.email=qualification@example.invalid',
            '-c','gc.auto=0','commit','-qm','qualified source fixture'],check=True)
        assert len(check.admit(root)['allowed_generated_evidence_paths'])==3
        (root/'qualified.py').write_text('changed')
        try:check.admit(root)
        except ValueError:refused.append('actual_Git_tracked_change')
        else:raise AssertionError('ACTUAL_TRACKED_CHANGE_ACCEPTED')
    import psycopg
    def forbidden(*args,**kwargs):raise AssertionError('LOCAL_SOURCE_CONTROL_MUST_NOT_CONNECT_DATABASE')
    psycopg.connect=forbidden
    load('factory_output2_real_qualified_graph',HERE/'probe.py')
    guard=load('factory_output2_business_guard',HERE/'source_guard.py').source_binding()
    assert sum(guard['retained_assertions'].values())==63
    old=REPO/'scripts/current-versioned-performance-factory-qualification'
    for name in('runner.py','fixture.py','probe.py','source_guard.py','evidence.py','fetch_originals.py'):
        assert(HERE/name).read_bytes()==(old/name).read_bytes(),name
    for path in HERE.glob('*.py'):ast.parse(path.read_bytes())
    return dict(status='LOCAL_OUTPUT_BOUNDARY_CORRECTION_PASS',allowed_generated_evidence_files=3,
        negative_controls=refused,retained_business_guards=guard,old_qualification_unchanged=True,
        new_product_changes=0,Original_created=False,database_executed=False,production_go=False)


if __name__=='__main__':print(json.dumps(run()),flush=True)
