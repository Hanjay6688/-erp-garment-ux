"""Actual52eed raw10 remains8PASS2INCOMPLETE; no partial prerequisite credit."""
from pathlib import Path
from hashlib import sha256
import gzip
import json
import zipfile


def check(repo,here):
    repo,here=Path(repo),Path(here)
    cfg=json.loads((here/'CONFIG.json').read_bytes());rca=json.loads((here/'evidence/LOCKED_INITIAL_RCA.json').read_bytes())
    zip_path=here/'retained-52eed/ORIGINAL.zip';raw=zip_path.read_bytes();pin=cfg['failed_52eed']
    if len(raw)!=pin['zip_bytes']or sha256(raw).hexdigest()!=pin['zip_sha256']:raise ValueError('S05_EXACT_FIRST52EED_ZIP_REQUIRED')
    with zipfile.ZipFile(zip_path)as archive:
        if len(archive.namelist())!=114 or archive.testzip()is not None:raise ValueError('S05_EXACT_FIRST52EED_ZIP_CRC_REQUIRED')
    docs={}
    for name,pin in rca['raw5'].items():
        raw=gzip.decompress((here/'retained-52eed'/(name+'.gz')).read_bytes())
        if len(raw)!=pin['bytes']or sha256(raw).hexdigest()!=pin['sha256']:raise ValueError('S05_EXACT_FIRST52EED_RAW5_REQUIRED:'+name)
        docs[name]=json.loads(raw)
    original=docs['CP7_S05_ACCESSORY_STANDARD_NATIVE10.json'];group=docs['CP7_S05_ACCESSORY_STANDARD_NATIVE10_CASES.json'];package=docs['T3_PACKAGE_INSTALL.json']
    if group['status']!='INCOMPLETE'or group['counts']!={'PASS':8,'INCOMPLETE':2}or group['missing']or len(group['cases'])!=10:raise ValueError('S05_FIRST52EED_PARTIAL_IS_NOT_PASS')
    if original['error']!='S05_EXACT_NATIVE10_PASS_REQUIRED'or original['qualification_commit']!=cfg['base_public_head']:raise ValueError('S05_FIRST52EED_OUTER_OR_HEAD_CHANGED')
    if any(not row['full_boundary_restored']or not row['public_schema_unchanged']for row in group['cases'].values()):raise ValueError('S05_FIRST52EED_BOUNDARY_CHANGED')
    bundle=original['committed']['S05_NATIVE10_AND_SEPARATE_COMMITTED_USED_INVERSE']
    if bundle.get('separate_committed_business_witness')is not None or bundle['actual_Native_cases']!=0:raise ValueError('S05_FIRST52EED_WITNESS_NOT_REACHED')
    expected=dict(installed=True,primary_unchanged=True,backup_restore_drill=True,security_advisors=True,writer_runtime=False)
    if package['gate']!=expected:raise ValueError('S05_FIRST52EED_EXACT_FOUR_NOT_FIVE_GATES_REQUIRED')
    if cfg['failed_52eed']['usable_prerequisite']is not False:raise ValueError('S05_FIRST52EED_MUST_REMAIN_NEGATIVE')
    return dict(status='EXACT_ACTUAL52EED_8PASS2INCOMPLETE_RETAINED_ONLY',counts=group['counts'],
        all10_attempted=True,full_boundary_restored=True,package_gate=expected,
        committed_business_witness_reached=False,usable_prerequisite=False,Native_case_credit=0)
