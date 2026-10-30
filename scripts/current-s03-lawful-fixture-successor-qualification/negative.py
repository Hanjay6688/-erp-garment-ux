"""Verify first actual failed bytes and actual capture provenance, never credit."""
from pathlib import Path
from hashlib import sha256
import gzip
import importlib.util
import io
import json
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ZIP_SHA='90e6cc9eed6f5c33bb5902df2dc2ba43a0f4f408b9e3ddcf9d2fd7ad633b9a05'
ZIP_SIZE=4176290
FAILURES={
    'S03_NATIVE_P2_PAYROLL_POOL_COEXIST_AND_POLICY_FENCES',
    'S03_NATIVE_BOTH_CORRECTIONS_LINKED_INVERSES_NO_RECOGNITION',
    'S03_NATIVE_FINISHED_PO_FG_COGS_COST_AND_CANCEL_EXACT',
}


def check(root=ROOT,here=HERE):
    root,here=Path(root),Path(here);folder=here/'retained-9ac-first'
    raw=(folder/'ORIGINAL.zip').read_bytes()
    if len(raw)!=ZIP_SIZE or sha256(raw).hexdigest()!=ZIP_SHA:
        raise ValueError('S03_LAWFUL_FIRST_ACTUAL_ORIGINAL_ZIP_CHANGED')
    manifest=json.loads((folder/'MANIFEST.json').read_bytes())
    with zipfile.ZipFile(io.BytesIO(raw))as original:
        names=original.namelist()
        if len(names)!=118 or len(set(names))!=118 or original.testzip()is not None:
            raise ValueError('S03_LAWFUL_FIRST_ACTUAL_ZIP_MEMBERS_CRC_CHANGED')
        docs={}
        for name,pin in manifest['reports'].items():
            packed=(folder/(name+'.gz')).read_bytes();content=gzip.decompress(packed)
            if (len(packed)!=pin['gzip_bytes']or sha256(packed).hexdigest()!=pin['gzip_sha256']
                    or len(content)!=pin['bytes']or sha256(content).hexdigest()!=pin['sha256']
                    or content!=original.read(name)):
                raise ValueError('S03_LAWFUL_EXACT_ROOT_RAW_ORIGINAL_CHANGED:'+name)
            docs[name]=json.loads(content)
    group=docs['CP7_S03_ATTENDANCE_CHOICE_NATIVE11_CASES.json']
    if (group['counts']!={'PASS':8,'INCOMPLETE':3}or group['complete_boundary_restored']is not True
            or {key for key,row in group['cases'].items()if row['status']=='INCOMPLETE'}!=FAILURES):
        raise ValueError('S03_LAWFUL_FIRST_ACTUAL_COUNTS_FAILURES_CHANGED')
    outer=docs['CP7_S03_ATTENDANCE_CHOICE_NATIVE14.json']
    for key in ('cp6_restored','baseline_full22_all_rows_all_sequences_equal','baseline_advisors_equal','advisor_gate'):
        if outer[key]is not True:
            raise ValueError('S03_LAWFUL_FIRST_FAILURE_RESTORE_UNPROVEN:'+key)
    component=outer['committed']['S03_ATTENDANCE_NATIVE14_AND_USED_INVERSE']
    if component.get('reader_native3')is not None or component.get('committed_choice_and_allocation')is not None:
        raise ValueError('S03_LAWFUL_FIRST_FAILURE_READER_USED_COUNT_MISLABELLED')
    capture=component['actual_installed_capture'];abi=json.loads((here/'ACTUAL9AC_ABI.json').read_bytes())
    if (len(capture['originals'])!=15 or len(capture['clones'])!=2
            or capture['source_derived_local_ABI_used']is not False
            or abi['current15']!={key:capture[key]for key in ('originals','definitions','clones')}):
        raise ValueError('S03_LAWFUL_ACTUAL_CAPTURE15_PROOF_CHANGED')
    for sig,row in abi['definitions'].items():
        observed=capture['actual_all22']['functions'][sig]
        if row!=dict(definition=observed[0],owner=observed[1],definition_sha256=sha256(observed[0].encode()).hexdigest()):
            raise ValueError('S03_LAWFUL_ACTUAL_ABI_PROVENANCE_CHANGED:'+sig)
    # Pure source transformer, not a new installed-catalog projection.
    path=root/'scripts/cp7_attendance_period_choice/native_delta.py'
    spec=importlib.util.spec_from_file_location('s03_lawful_actual_capture_transformer',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    if module.patched(capture['originals'])!=capture['definitions']or module.clones(capture['originals'])!=capture['clones']:
        raise ValueError('S03_LAWFUL_PRODUCT_NATIVE_BODY_CHANGED_SINCE_FIRST_ACTUAL')
    package=docs['T3_PACKAGE_INSTALL.json']
    if (package['gate']['writer_runtime']is not False or sum(v is True for v in package['gate'].values())!=4
            or package['backup_restore_drill']!='RESTORED_IDENTICAL'
            or package['auth_users_before']!=package['auth_users_after']):
        raise ValueError('S03_LAWFUL_FIRST_FAILURE_PACKAGE_RESTORE_CHANGED')
    return dict(status='EXACT_FIRST_FAILURE_8PARTIAL_PASS_3INCOMPLETE_NOT_PREREQUISITE',
        Original_ZIP_sha256=ZIP_SHA,raw_reports=6,strict11_counts=group['counts'],
        actual_partial_pass=8,complete_bundle_credit=0,Reader3_reached=False,
        committed_used_witness_reached=False,current15_body_provenance_exact=True,
        full_outer_restore=True,all5_pass=False,actual_fresh_successor_credit=0)
