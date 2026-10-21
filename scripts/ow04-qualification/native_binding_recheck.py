"""Execute the real qualified_core function against synthetic receipt controls.

Only its filesystem/git inputs are replaced. No transport fixture, database,
Native writer, job outcome or new real63 receipt is produced by this check.
"""
import ast
import copy
import hashlib
import json
from pathlib import Path
import tempfile

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
SOURCE=(HERE/'transport_probe.py').read_text()
node=next(n for n in ast.parse(SOURCE).body if isinstance(n,ast.FunctionDef)and n.name=='qualified_core')
function_code=compile(ast.Module(body=[node],type_ignores=[]),str(HERE/'transport_probe.py'),'exec')
sha=lambda value:hashlib.sha256(value).hexdigest()


def exercise(count,mutation=None):
    with tempfile.TemporaryDirectory(prefix='ow04-binding-controls-')as folder:
        root=Path(folder);entry=root/'scripts/ow04-qualification/transport_probe.py'
        entry.parent.mkdir(parents=True)
        name={44:'NATIVE_EMPTY_QUALIFICATION.json',58:'NATIVE_FRACTIONAL_QUALIFICATION.json',
              63:'NATIVE_SIGNED_SOURCE_QUALIFICATION.json'}[count]
        declaration=(REPO/'docs/cp7/d17-14/ow04'/name).read_bytes()
        target=root/'docs/cp7/d17-14/ow04'/name;target.parent.mkdir(parents=True);target.write_bytes(declaration)
        ids=json.loads(declaration)['required_case_ids']
        receipt=dict(candidate='a'*40,tree='b'*40,run_id=100,job_id=200,workflow_conclusion='success',
            counts={'PASS':count},summary=dict(status='PASS',expected_case_count=count,
                observed_case_count=count,cp6_restored=True,advisor_gate=True),
            cases=[dict(id=ident,status='PASS')for ident in ids],
            package_gate={key:True for key in('installed','primary_unchanged','backup_restore_drill','security_advisors','writer_runtime')})
        binding=dict(status='PASS',native_case_count=count,candidate=receipt['candidate'],tree=receipt['tree'],
            run_id=100,job_id=200,core_directory_tree='c'*40,native_probe_blob='d'*40,
            receipt='docs/cp7/d17-14/ow04/NATIVE_SYNTHETIC_CONTROL.json',
            qualification_declaration='docs/cp7/d17-14/ow04/'+name,qualification_declaration_sha256=sha(declaration))
        git_values=dict(core=binding['core_directory_tree'],probe=binding['native_probe_blob'],changes='scripts/ow04-qualification/native_binding_recheck.py')
        override={}
        if mutation:mutation(binding,receipt,git_values,override)
        raw=(json.dumps(receipt,sort_keys=True)+'\n').encode()
        (root/binding['receipt']).write_bytes(raw)
        binding['receipt_sha256']=override.get('receipt_sha256',sha(raw))
        (entry.parent/'QUALIFIED_CORE.json').write_text(json.dumps(binding))
        def git(*args):
            if args==('rev-parse','HEAD:scripts/cp7_customer_credit'):return git_values['core']
            if args==('rev-parse','HEAD:scripts/cp7_ow04_probe.py'):return git_values['probe']
            assert args==('diff','--name-only',binding['candidate'],'--','scripts','src','supabase'),args
            return git_values['changes']
        namespace=dict(Path=Path,json=json,hashlib=hashlib,REPO=root,git=git,__file__=str(entry))
        exec(function_code,namespace)
        return namespace['qualified_core']()


def edit(target,key,value):
    def mutation(binding,receipt,git_values,override):
        {'binding':binding,'receipt':receipt,'git':git_values,'override':override}[target][key]=value
    return mutation


def summary(key,value):
    return lambda b,r,g,o:r['summary'].__setitem__(key,value)


CONTROL_IDS=(
    'valid44','valid58','unsupported32','binding_incomplete','core_changed','probe_changed',
    'product_dependency_changed','receipt_hash_changed','receipt_candidate_changed','receipt_tree_changed',
    'observed_count_changed','restore_failed','advisor_failed','missing_case','duplicate_case','failed_case',
    'declaration_hash_changed','package_gate_failed','package_gate_missing','workflow_failed','run_changed',
    'valid63','fake58_relabelled63','missing_zero_difference63','declaration_hash_changed63',
    'workflow_failed63','job_changed63','core_changed63')
controls=(
    ('valid44',44,None,True),('valid58',58,None,True),
    ('unsupported32',58,edit('binding','native_case_count',32),False),
    ('binding_incomplete',58,edit('binding','status','INCOMPLETE'),False),
    ('core_changed',58,edit('git','core','e'*40),False),
    ('probe_changed',58,edit('git','probe','e'*40),False),
    ('product_dependency_changed',58,edit('git','changes','scripts/cp7-src/sales/read.sql'),False),
    ('receipt_hash_changed',58,edit('override','receipt_sha256','0'*64),False),
    ('receipt_candidate_changed',58,edit('receipt','candidate','e'*40),False),
    ('receipt_tree_changed',58,edit('receipt','tree','e'*40),False),
    ('observed_count_changed',58,summary('observed_case_count',57),False),
    ('restore_failed',58,summary('cp6_restored',False),False),
    ('advisor_failed',58,summary('advisor_gate',False),False),
    ('missing_case',58,lambda b,r,g,o:r['cases'].pop(),False),
    ('duplicate_case',58,lambda b,r,g,o:r['cases'].__setitem__(0,copy.deepcopy(r['cases'][1])),False),
    ('failed_case',58,lambda b,r,g,o:r['cases'][0].__setitem__('status','FAIL'),False),
    ('declaration_hash_changed',58,edit('binding','qualification_declaration_sha256','0'*64),False),
    ('package_gate_failed',58,lambda b,r,g,o:r['package_gate'].__setitem__('writer_runtime',False),False),
    ('package_gate_missing',58,lambda b,r,g,o:r['package_gate'].pop('backup_restore_drill'),False),
    ('workflow_failed',58,edit('receipt','workflow_conclusion','failure'),False),
    ('run_changed',58,edit('receipt','run_id',999),False),
    ('valid63',63,None,True),
    ('fake58_relabelled63',63,lambda b,r,g,o:r.__setitem__('cases',r['cases'][:58]),False),
    ('missing_zero_difference63',63,lambda b,r,g,o:r.__setitem__('cases',[row for row in r['cases']if row['id']!='OW04_SIGNED_ZERO_DIFF_EARLIER_ZERO_RETURN_REVERSE']),False),
    ('declaration_hash_changed63',63,edit('binding','qualification_declaration_sha256','0'*64),False),
    ('workflow_failed63',63,edit('receipt','workflow_conclusion','failure'),False),
    ('job_changed63',63,edit('receipt','job_id',999),False),
    ('core_changed63',63,edit('git','core','e'*40),False))
assert tuple(row[0]for row in controls)==CONTROL_IDS
results=[]
for ident,count,mutation,want_pass in controls:
    try:
        exercise(count,mutation);accepted=True;error=None
    except AssertionError as caught:
        accepted=False;error=str(caught)
    assert accepted is want_pass,('BINDING_CONTROL_UNEXPECTED',ident,accepted,error)
    results.append(dict(id=ident,status='PASS',expected_acceptance=want_pass,observed_acceptance=accepted,rejection=error))
print(json.dumps(dict(classification='SYNTHETIC_REAL_FUNCTION_BINDING_GUARDS_NOT_NATIVE_OR_HTTP',
    status='PASS',count=len(results),transport_source_sha256=sha(SOURCE.encode()),
    checker_source_sha256=sha(Path(__file__).read_bytes()),results=results,database_calls=0,Native_executed=False)))
