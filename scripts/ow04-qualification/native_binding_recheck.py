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
              63:'NATIVE_SIGNED_SOURCE_QUALIFICATION.json',73:'CREDIT_DEPENDENCY_NATIVE_QUALIFICATION.json',
              87:'DIRECT_NATIVE_FRACTIONAL_QUALIFICATION.json'}[count]
        declaration=(REPO/'docs/cp7/d17-14/ow04'/name).read_bytes()
        target=root/'docs/cp7/d17-14/ow04'/name;target.parent.mkdir(parents=True);target.write_bytes(declaration)
        ids=json.loads(declaration)['required_case_ids']
        receipt=dict(candidate='a'*40,tree='b'*40,run_id=100,job_id=200,workflow_conclusion='success',
            counts={'PASS':count},summary=dict(status='PASS',expected_case_count=count,
                observed_case_count=count,cp6_restored=True,advisor_gate=True),
            cases=[dict(id=ident,status='PASS',full_boundary_restored=True,public_schema_unchanged=True,
                session_leaks={'advisory_locks':0,'advisory_lock_keys':[],'other_sessions':[]})for ident in ids],
            package_gate={key:True for key in('installed','primary_unchanged','backup_restore_drill','security_advisors','writer_runtime')})
        binding=dict(status='PASS',native_case_count=count,candidate=receipt['candidate'],tree=receipt['tree'],
            run_id=100,job_id=200,core_directory_tree='c'*40,native_probe_blob='d'*40,
            receipt='docs/cp7/d17-14/ow04/NATIVE_SYNTHETIC_CONTROL.json',
            qualification_declaration='docs/cp7/d17-14/ow04/'+name,qualification_declaration_sha256=sha(declaration))
        git_values=dict(core=binding['core_directory_tree'],probe=binding['native_probe_blob'],changes='scripts/ow04-qualification/native_binding_recheck.py')
        if count in(73,87):
            old_name='docs/cp7/d17-14/ow04/FULL_INSTALL_QUALIFICATION.json'
            old_bytes=(REPO/old_name).read_bytes();(root/old_name).write_bytes(old_bytes)
            binding.update(classification=f'REUSED_FULL_NATIVE{count}_RUNTIME_EXACT_CORE_BINDING_NOT_NEW_TRANSPORT_EXECUTION',
                owning_installer_blob='e'*40,native_full_probe_blob='f'*40,
                retained_native64_declaration=old_name,retained_native64_declaration_sha256=sha(old_bytes))
            git_values.update(owning='e'*40,full_probe='f'*40)
            receipt['full_composition']=dict(owning_installer_blob='e'*40,native_full_probe_blob='f'*40,
                retained_case_count=64,additional_readonly_case_count=9,
                preuse_exact_CP6_restore=True,used_rollback_refused=True)
            if count==87:
                retained_name='docs/cp7/d17-14/ow04/CREDIT_DEPENDENCY_NATIVE_QUALIFICATION.json'
                retained_bytes=(REPO/retained_name).read_bytes();(root/retained_name).write_bytes(retained_bytes)
                native_name='scripts/cp7_customer_credit/hpp-fractional/NATIVE_EXPECTED.json'
                native_bytes=(REPO/native_name).read_bytes();(root/native_name).parent.mkdir(parents=True)
                (root/native_name).write_bytes(native_bytes)
                binding.update(retained_native73_declaration=retained_name,retained_native73_declaration_sha256=sha(retained_bytes))
                receipt['full_composition'].update(additional_direct_native_case_count=14,direct_native_fractional_expected_sha256=sha(native_bytes))
        override={}
        if mutation:mutation(binding,receipt,git_values,override)
        if 'admin_source'in override:
            admin=root/'scripts/cp7_ow04_restore_bundle.py'
            admin.write_bytes(override['admin_source'])
        if 'admin_declaration'in override:
            (root/'docs/cp7/d17-14/ow04/USED_RESTORE_QUALIFICATION.json').write_text(json.dumps(override['admin_declaration']))
        raw=(json.dumps(receipt,sort_keys=True)+'\n').encode()
        (root/binding['receipt']).write_bytes(raw)
        binding['receipt_sha256']=override.get('receipt_sha256',sha(raw))
        (entry.parent/'QUALIFIED_CORE.json').write_text(json.dumps(binding))
        def git(*args):
            if args==('rev-parse','HEAD:scripts/cp7_customer_credit'):return git_values['core']
            if args==('rev-parse','HEAD:scripts/cp7_ow04_probe.py'):return git_values['probe']
            if args==('rev-parse','HEAD:scripts/cp7_full_owning_install.py'):return git_values['owning']
            if args==('rev-parse','HEAD:scripts/cp7_full_ow04_probe.py'):return git_values['full_probe']
            if args==('rev-parse','HEAD:scripts/cp7_ow04_restore_bundle.py'):return git_values['admin_blob']
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

additional=(
    ('valid73',73,None,True),
    ('fake63_relabelled73',73,lambda b,r,g,o:r.__setitem__('cases',r['cases'][:63]),False),
    ('missing_dependency73',73,lambda b,r,g,o:r['cases'].pop(),False),
    ('full_installer_changed73',73,edit('git','owning','0'*40),False),
    ('full_probe_changed73',73,edit('git','full_probe','0'*40),False),
    ('full_composition_changed73',73,lambda b,r,g,o:r['full_composition'].__setitem__('owning_installer_blob','0'*40),False),
    ('preuse_restore_unproven73',73,lambda b,r,g,o:r['full_composition'].__setitem__('preuse_exact_CP6_restore',False),False),
    ('used_rollback_unproven73',73,lambda b,r,g,o:r['full_composition'].__setitem__('used_rollback_refused',False),False),
    ('private_boundary_changed73',73,lambda b,r,g,o:r['cases'][0].__setitem__('full_boundary_restored',False),False),
    ('public_catalog_changed73',73,lambda b,r,g,o:r['cases'][0].__setitem__('public_schema_unchanged',False),False),
    ('advisory_lock_leak73',73,lambda b,r,g,o:r['cases'][0]['session_leaks'].__setitem__('advisory_locks',1),False),
    ('other_session_leak73',73,lambda b,r,g,o:r['cases'][0]['session_leaks'].__setitem__('other_sessions',[12345]),False),
    ('retained64_declaration_changed73',73,edit('binding','retained_native64_declaration_sha256','0'*64),False),
    ('readonly_case_failed73',73,lambda b,r,g,o:r['cases'][-1].__setitem__('status','INCOMPLETE'),False),
)
controls+=additional
CONTROL_IDS+=tuple(row[0]for row in additional)

native87=(
    ('valid87',87,None,True),
    ('fake73_relabelled87',87,lambda b,r,g,o:r.__setitem__('cases',r['cases'][:73]),False),
    ('missing_direct_native87',87,lambda b,r,g,o:r['cases'].pop(),False),
    ('direct_native_case_failed87',87,lambda b,r,g,o:r['cases'][-1].__setitem__('status','INCOMPLETE'),False),
    ('direct_native_count_wrong87',87,lambda b,r,g,o:r['full_composition'].__setitem__('additional_direct_native_case_count',13),False),
    ('direct_native_expected_changed87',87,lambda b,r,g,o:r['full_composition'].__setitem__('direct_native_fractional_expected_sha256','0'*64),False),
    ('retained73_declaration_changed87',87,edit('binding','retained_native73_declaration_sha256','0'*64),False),
    ('wrong_class87',87,edit('binding','classification','REUSED_FULL_NATIVE73_RUNTIME_EXACT_CORE_BINDING_NOT_NEW_TRANSPORT_EXECUTION'),False),
    ('core_changed87',87,edit('git','core','0'*40),False),
    ('full_installer_changed87',87,edit('git','owning','0'*40),False),
    ('full_probe_changed87',87,edit('git','full_probe','0'*40),False),
    ('preuse_restore_unproven87',87,lambda b,r,g,o:r['full_composition'].__setitem__('preuse_exact_CP6_restore',False),False),
    ('workflow_failed87',87,edit('receipt','workflow_conclusion','failure'),False),
    ('native_boundary_leaked87',87,lambda b,r,g,o:r['cases'][-1]['session_leaks'].__setitem__('advisory_locks',1),False),
)
controls+=native87
CONTROL_IDS+=tuple(row[0]for row in native87)


def admin_source(change=None):
    def mutation(b,r,g,o):
        data=b'"""Administrative restore source, synthetic binding control only."""\n'
        path='scripts/cp7_ow04_restore_bundle.py'
        g.update(changes=path,admin_blob='9'*40)
        o['admin_source']=data
        o['admin_declaration']=dict(required_native_case_count=87,expected_scenario_count=1,
            required_restore_module=path,scenario_id='OW04_USED_CREDIT_REFUND_RESTORE_CONTINUE',
            separate_administrative_source=dict(path=path,git_blob='9'*40,sha256=sha(data),
                native_runtime_covered=False,classification='SEPARATE_ADMIN_RESTORE_REQUIRES_OWN_ACTUAL_RUNTIME'))
        if change:change(b,r,g,o)
    return mutation


admin_controls=(
    ('separate_admin_exact_source87',87,admin_source(),True),
    ('separate_admin_blob_changed87',87,admin_source(lambda b,r,g,o:g.__setitem__('admin_blob','0'*40)),False),
    ('separate_admin_bytes_changed87',87,admin_source(lambda b,r,g,o:o.__setitem__('admin_source',b'changed')),False),
    ('separate_admin_native_coverage_faked87',87,admin_source(lambda b,r,g,o:o['admin_declaration']['separate_administrative_source'].__setitem__('native_runtime_covered',True)),False),
    ('separate_admin_missing87',87,admin_source(lambda b,r,g,o:o.pop('admin_source')),False),
    ('separate_admin_wrong_declaration87',87,admin_source(lambda b,r,g,o:o['admin_declaration'].__setitem__('required_native_case_count',73)),False),
    ('separate_admin_unknown_script87',87,admin_source(lambda b,r,g,o:g.__setitem__('changes',g['changes']+'\nscripts/unqualified.py')),False),
    ('separate_admin_not_historical73',73,admin_source(),False),
)
controls+=admin_controls
CONTROL_IDS+=tuple(row[0]for row in admin_controls)

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
