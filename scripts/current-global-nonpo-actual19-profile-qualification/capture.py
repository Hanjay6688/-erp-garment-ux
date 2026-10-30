"""Extract exact finite source evidence; never execute the captured functions."""
from pathlib import Path
from hashlib import sha256
import argparse
import importlib.util
import json
import os
import subprocess
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE='14b6490e4ceab9fa8806c78fe10ddc820580de21'
PRODUCT='scripts/cp7_global_nonpo_native_graph_adapter/'
OLD='scripts/current-global-nonpo-native-graph-qualification/'
HEAD='e7875cde9709c7375335bade4e1010be9459163e'
ARCHIVE_SHA='5bb0d0fd4247f12e1c28a7716c04a880c4ddb2639d519b7a5132061d6719c194'
CHANGED=('erp.compute_non_po_product_hpp_book_v2620f(uuid)','erp.require_internal()')


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def frozen(name):return subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':'+name],env=dict(os.environ,GIT_NO_LAZY_FETCH='1'))


def source_module():
    path=ROOT/PRODUCT/'source.py'
    if path.read_bytes()!=frozen(PRODUCT+'source.py'):raise ValueError('ACTUAL19_FROZEN_SOURCE_HELPER_CHANGED')
    spec=importlib.util.spec_from_file_location('actual19_original_source_parser',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def extract(archive):
    if len(ARCHIVE_SHA)!=64:raise ValueError('ACTUAL19_ARCHIVE_SHA256_FORMAT_REQUIRED')
    raw=Path(archive).read_bytes()
    if pin(raw)!=dict(bytes=8001776,sha256=ARCHIVE_SHA):raise ValueError('ACTUAL19_EXACT_ORIGINAL_ARCHIVE_REQUIRED')
    with zipfile.ZipFile(archive)as z:
        if len(z.infolist())!=119 or z.testzip()is not None:raise ValueError('ACTUAL19_ORIGINAL_MEMBERS_OR_CRC_CHANGED')
        report_raw=z.read('CP7_ATTENDANCE_MIDNIGHT_NATIVE1.json');outer=json.loads(report_raw)
        package=json.loads(z.read('T3_PACKAGE_INSTALL.json'))
    if outer['status']!='PASS' or outer['qualification_commit']!=HEAD:
        raise ValueError('ACTUAL19_EXACT_OBSERVED_MIDNIGHT_RUN_REQUIRED')
    identity=package['run_identity']
    if identity['run_id']!='41007933625' or identity['tool_head']!=HEAD or identity['github_sha']!=HEAD:
        raise ValueError('ACTUAL19_RAW_PACKAGE_RUN_IDENTITY_CHANGED')
    c=outer['committed']['S03_MIDNIGHT_NATIVE1_AND_UNCHANGED_USED_WITNESS']
    catalogues={
        'committed.S03_MIDNIGHT_NATIVE1_AND_UNCHANGED_USED_WITNESS.actual_installed_capture.actual_all22':c['actual_installed_capture']['actual_all22'],
        'committed.S03_MIDNIGHT_NATIVE1_AND_UNCHANGED_USED_WITNESS.used_inverse_refusal_before.actual_all22':c['used_inverse_refusal_before']['actual_all22'],
        'committed.S03_MIDNIGHT_NATIVE1_AND_UNCHANGED_USED_WITNESS.used_inverse_refusal_after.actual_all22':c['used_inverse_refusal_after']['actual_all22'],
    }
    authority=json.loads(frozen(PRODUCT+'AUTHORITY.json'));names=set(authority['known_functions'])
    if len(names)!=19:raise ValueError('ACTUAL19_EXACT_FINITE_SOURCE_SET_REQUIRED')
    rows=None;view=None;observations=[]
    for path,cat in catalogues.items():
        if len(cat)!=22:raise ValueError('ACTUAL19_FULL_TYPED_CAPTURE_REQUIRED')
        selected={name:cat['functions'][name]for name in sorted(names)}
        current_view=cat['relations']['erp.v_current_hpp']
        if any(len(row)!=19 for row in selected.values())or len(current_view)!=13:
            raise ValueError('ACTUAL19_EXACT_CATALOG_ROW_ABI_REQUIRED')
        if rows is not None and(rows!=selected or view!=current_view):
            raise ValueError('ACTUAL19_THREE_ACTUAL_SOURCE_CAPTURES_DISAGREE')
        rows,view=selected,current_view
        observations.append(dict(path=path,function_count=len(cat['functions']),
            selected19_sha256=sha256(canonical(selected)).hexdigest(),view13_sha256=sha256(canonical(view)).hexdigest()))
    parser=source_module();changed=[];differences={}
    for name,row in rows.items():
        body,definition=parser.function_text(row[0],name.split('(')[0])
        expected=authority['known_functions'][name]['prosrc_sha256'];actual=sha256(body.encode()).hexdigest()
        if actual!=expected:
            changed.append(name);differences[name]=dict(original_prosrc_sha256=expected,actual_prosrc_sha256=actual,
                actual_definition_sha256=sha256(definition.encode()).hexdigest())
    if set(changed)!=set(CHANGED):raise ValueError('ACTUAL19_UNDECLARED_NATIVE_SOURCE_DIFFERENCE')
    return dict(classification='ACTUAL_THREE_CATALOG_SOURCE_CAPTURE_NOT_FINAL_COMPOSITE_ACCEPTANCE',
        source_base=BASE,observed_head=HEAD,run_id='41007933625',artifact_id=12958410980,
        archive=dict(name=Path(archive).name,**pin(raw)),report=dict(name='CP7_ATTENDANCE_MIDNIGHT_NATIVE1.json',**pin(report_raw)),
        catalogue_observations=observations,functions=rows,view_relation=view,changed_source_bodies=differences,
        unchanged_known_source_bodies=17,raw_function_or_relation_acl_observed=False,
        acl_semantics='EXPANDED_ACL_WITH_ACLDEFAULT; RAW_NULL_VS_EXPLICIT_NOT_INFERRED',
        current_final_composite_accepted=False,runtime_entry=None,actual_Native_credit=0,
        production_go=False,independent_acceptance=False)


def native_inputs(captured):
    parser=source_module();original=frozen(OLD+'retained/Native_authority.sql').decode();value=original;two=[]
    for signature in CHANGED:
        _,before=parser.function_text(original,signature.split('(')[0])
        _,after=parser.function_text(captured['functions'][signature][0],signature.split('(')[0])
        # pg_get_functiondef omits the statement semicolon. Add only that SQL
        # separator outside the captured body; the raw catalogue stays exact.
        after=after.rstrip()
        if not after.endswith(';'):after+=';'
        if value.count(before)!=1:raise ValueError('ACTUAL19_EXACT_RETAINED_NATIVE_SOURCE_ANCHOR_REQUIRED')
        value=value.replace(before,after,1);two.append(after+'\n')
    return value.encode(),(''.join(two)).encode()


def write(archive):
    if os.environ.get('CI')or os.environ.get('GITHUB_ACTIONS')=='true':raise ValueError('ACTUAL19_CAPTURE_WRITER_FORBIDDEN_IN_CI')
    value=extract(archive);native,two=native_inputs(value)
    (HERE/'CAPTURE.json').write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
    (HERE/'ACTUAL_NATIVE_AUTHORITY.sql').write_bytes(native)
    (HERE/'ACTUAL_TWO_FUNCTIONS.sql').write_bytes(two)
    first=dict(classification='FIRST_OLD_PROFILE_VERSUS_ACTUAL_SOURCE_MISMATCH',old_source_base=BASE,
        unchanged_body_count=17,mismatches=value['changed_source_bodies'],observations=value['catalogue_observations'],
        financial_Native_source_changed=False,actual_Native_credit=0)
    (HERE/'FIRST_PROFILE_MISMATCH.json').write_text(json.dumps(first,indent=2)+'\n')
    return dict(status='EXACT_THREE_ACTUAL_SOURCE_CAPTURES_EXTRACTED',functions=19,changed_expected_bodies=2,actual_Native_credit=0)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',required=True);args=p.parse_args()
    print(json.dumps(write(args.archive)))
