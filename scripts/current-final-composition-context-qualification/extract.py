"""Writer-only extraction of exact narrow actual catalogues and future source set."""
from pathlib import Path
from hashlib import sha256
import ast
import importlib.util
import json
import os
import subprocess
import zipfile

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
BASE='e46233133753cd31b0b4120a3a5a88be745aa223'
OLD='scripts/cp7_customer_credit/integration/typed_context_inventory.py'
INPUTS={
 'S03':dict(name='ERP_S03_Midnight_Native1_e7875_20261030.zip',bytes=8001776,
     sha256='5bb0d0fd4247f12e1c28a7716c04a880c4ddb2639d519b7a5132061d6719c194',members=119,
     head='e7875cde9709c7375335bade4e1010be9459163e',run_id=41007933625,
     report='CP7_ATTENDANCE_MIDNIGHT_NATIVE1.json'),
 'SKU':dict(name='ERP_SKU_Native27_01ef_FirstFailure_20261030.zip',bytes=35386172,
     sha256='039dbd62b8b6b08ffa181ff47a31266014d09eb12308c0cc8a0e50b2f650bb0d',members=140,
     head='01ef15ad1d914ae59b78d5d6811385dc6f4fc9bd',run_id=40994565363,
     report='SKU_COST_RECOVERY_OVER_FIRST_PART_REFUSAL_b5f607be2686_FULL_CURRENT_CENSUS.json')}
ADDITIONS={
 'cp7_credit_correction_de.work_v1':'scripts/cp7_credit_correction_de/facts.sql',
 'cp7_credit_correction_de.posting_v1':'scripts/cp7_credit_correction_de/facts.sql',
 'cp7_credit_note_carry_de.work_v1':'scripts/cp7_credit_correction_de/note_carry/01_facts.sql',
 'cp7_sku_conversion.execution_v1':'scripts/cp7_sku_pair_conversion/conversion.sql',
 'cp7_attendance_choice.cancel_context_v1':'scripts/cp7_attendance_period_choice/choice.sql'}


def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def git(name):return subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'show',BASE+':'+name],env=dict(os.environ,GIT_NO_LAZY_FETCH='1'))


def load_catalog():
    spec=importlib.util.spec_from_file_location('final_context_offline_catalog',HERE/'catalog.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def old_specs():
    raw=git(OLD)
    if (ROOT/OLD).read_bytes()!=raw:raise ValueError('FINAL_CONTEXT_OLD30_SOURCE_CHANGED')
    tree=ast.parse(raw)
    values={target.id:ast.literal_eval(node.value)for node in tree.body if isinstance(node,ast.Assign)
            for target in node.targets if isinstance(target,ast.Name)and target.id in ('SPECS','NEW_SCHEMAS')}
    if len(values['SPECS'])!=30:raise ValueError('FINAL_CONTEXT_ORIGINAL30_CHANGED')
    return values


def read_input(directory,key):
    expected=INPUTS[key];path=Path(directory)/expected['name'];raw=path.read_bytes()
    if pin(raw)!={k:expected[k]for k in ('bytes','sha256')}:raise ValueError('FINAL_CONTEXT_EXACT_ARCHIVE_REQUIRED:'+key)
    with zipfile.ZipFile(path)as z:
        if len(z.namelist())!=expected['members']or len(set(z.namelist()))!=expected['members']or z.testzip()is not None:
            raise ValueError('FINAL_CONTEXT_ARCHIVE_INTEGRITY_CHANGED')
        report=z.read(expected['report']);document=json.loads(report)
    if key=='S03':
        c=document['committed']['S03_MIDNIGHT_NATIVE1_AND_UNCHANGED_USED_WITNESS']
        observations=[c['actual_installed_capture']['actual_all22'],
                      c['used_inverse_refusal_before']['actual_all22'],c['used_inverse_refusal_after']['actual_all22']]
    else:observations=[document['before']['catalog'],document['after']['catalog']]
    return observations,pin(report)


def write(directory):
    if os.environ.get('CI')or os.environ.get('GITHUB_ACTIONS')=='true':raise ValueError('FINAL_CONTEXT_EXTRACTION_IN_CI_FORBIDDEN')
    catalog=load_catalog();specs=old_specs();known={row[0]for row in specs['SPECS']};profiles={};raws={}
    for key in INPUTS:
        observations,raw=read_input(directory,key);selected=[catalog.select(c)for c in observations]
        if not all(v==selected[0]for v in selected):raise ValueError('FINAL_CONTEXT_NARROW_CATALOG_CHANGED:'+key)
        profiles[key]=selected[0];raws[key]=dict(archive=INPUTS[key],report=raw,actual_catalogue_observations=len(observations),
            runtime_acceptance_inferred=False,first_failure_retained=key=='SKU')
    s03=set(profiles['S03']['names']);sku=set(profiles['SKU']['names'])
    if s03-sku!={'cp7_attendance_choice.cancel_context_v1'}or sku-s03!={'cp7_sku_conversion.execution_v1'}:
        raise ValueError('FINAL_CONTEXT_EXACT_STANDALONE_DIFFERENCE_CHANGED')
    common=s03&sku
    if len(common)!=51 or not known<=common:raise ValueError('FINAL_CONTEXT_COMPLETE_BASE51_REQUIRED')
    # Compare each inherited table's complete portable metadata independently;
    # whole schemas may intentionally gain a later component's own objects.
    for group in ('relations','columns','constraints','policies','triggers'):
        values=[]
        for key in ('S03','SKU'):
            values.append({k:v for k,v in profiles[key]['catalog'][group].items()if k.split(':',1)[0]in common})
        if values[0]!=values[1]:raise ValueError('FINAL_CONTEXT_COMMON_PORTABLE_TABLE_DRIFT:'+group)
    additions={}
    for name,path in ADDITIONS.items():
        raw=git(path)
        if (ROOT/path).read_bytes()!=raw or raw.lower().count(('create table '+name+'(').encode())!=1:
            raise ValueError('FINAL_CONTEXT_EXACT_NEW_TABLE_SOURCE_REQUIRED:'+name)
        additions[name]=dict(path=path,source=pin(raw),actual_portable_catalog_observed=name in(s03|sku),
                             actual_final_composite_catalog_observed=False)
    expected=common|set(ADDITIONS)
    if len(expected)!=56:raise ValueError('FINAL_CONTEXT_EXACT_PROPOSED56_REQUIRED')
    result=dict(contract='cp7.final-context.closed-source-inventory.v1',base=BASE,
        original30_source=pin(git(OLD)),original30_specs=specs['SPECS'],original_schema_exclusions_retained_as_history=specs['NEW_SCHEMAS'],
        actual_common51=sorted(common),additional21_over_original30=sorted(common-known),proposed_exact56=sorted(expected),
        component_context_sources=additions,narrow_profiles=profiles,provenance=raws,
        no_schema_exclusions_in_new_discovery=True,historical_transaction_facts_are_not_ephemeral_contexts=True,
        missing_actual_component_catalogues=['D1 work/posting and E work'],
        raw_schema_relation_column_ACL_and_visibility_final_binding=False,
        current_actor_request_backend_tx_phase_and_original_domain_guards_qualified=False,
        full_final_catalogue_captured=False,runtime_entry=None,actual_Native_credit=0,production_go=False,independent_acceptance=False)
    (HERE/'INVENTORY.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    return dict(status='CLOSED_CONTEXT_SOURCE_INVENTORY_ONLY',actual_narrow_contexts={k:len(v['names'])for k,v in profiles.items()},
                actual_common=51,old_known=30,proposed_final=56,actual_final=0,runtime_entry=None)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--archive-directory',required=True)
    print(json.dumps(write(parser.parse_args().archive_directory)))
